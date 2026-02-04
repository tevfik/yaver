"""
Memory Management Agent for Yaver AI
Handles long-term and short-term memory using Qdrant vector database.
Integrates with Neo4j Graph Manager for structural memory.
"""
import os
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    ScoredPoint
)
from langchain_ollama import OllamaEmbeddings

from yaver_cli.agent_base import logger, get_config
from yaver_cli.agent_graph import GraphManager


class MemoryType(str, Enum):
    """Types of memory entries"""
    SHORT_TERM = "short_term"  # Recent context, analysis results
    LONG_TERM = "long_term"    # Persistent knowledge, patterns
    TASK = "task"              # Task-specific memory
    ARCHITECTURE = "architecture"  # Architecture decisions
    CODE_PATTERN = "code_pattern"  # Code patterns and best practices
    CODE_ELEMENT = "code_element"  # Vector representation of a Class/Function


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    content: str
    memory_type: MemoryType
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    embedding: Optional[List[float]] = None
    id: Optional[str] = None


class MemoryManager:
    """
    Unified Memory System for Yaver AI.
    
    1. Fast/Episodic Memory (Qdrant):
       - Stores interaction logs, task results, and code snippets for semantic search.
       - "How did I fix this error before?"
       - "Find code similar to X."

    2. Structural Memory (Neo4j via GraphManager):
       - Stores the relationship graph (Files, Classes, Functions).
       - "What functions call X?"
       - "Show the inheritance hierarchy of Class Y."
    """
    
    def __init__(self):
        config = get_config()
        
        # --- 1. Vector DB Setup (Qdrant) ---
        if config.qdrant.use_local:
            logger.info(f"💾 Initializing Qdrant with local storage: {config.qdrant.path}")
            os.makedirs(config.qdrant.path, exist_ok=True)
            self.client = QdrantClient(path=config.qdrant.path)
        elif config.qdrant.host:
            logger.info(f"🌐 Initializing Qdrant with server: {config.qdrant.host}:{config.qdrant.port}")
            self.client = QdrantClient(
                host=config.qdrant.host,
                port=config.qdrant.port,
            )
        else:
            logger.warning("⚠️ No Qdrant configuration found, using in-memory storage")
            self.client = QdrantClient(location=":memory:")
        
        self.collection_name = config.qdrant.collection
        
        # Build embeddings with optional authentication
        embedding_kwargs = {
            "model": config.ollama.model_embedding,
            "base_url": config.ollama.base_url,
        }
        
        # Add authentication if configured
        if config.ollama.username and config.ollama.password:
            embedding_kwargs["client_kwargs"] = {"auth": (config.ollama.username, config.ollama.password)}
            logger.info(f"🔐 Ollama embeddings with basic auth enabled")
        
        self.embeddings = OllamaEmbeddings(**embedding_kwargs)
        
        self.short_term_limit = config.memory.short_term_limit
        self.long_term_limit = config.memory.long_term_limit
        
        self._initialize_collection()

        # --- 2. Graph DB Setup (Neo4j) ---
        self.graph = GraphManager()
        
        logger.info(f"Memory Manager initialized with collection: {self.collection_name}")
    
    def _initialize_collection(self):
        """Initialize or recreate Qdrant collection"""
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Verify this matches your embedding model
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            else:
                logger.info(f"Using existing collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            # Do not raise, allow degradation to basic behavior if DB fails
    
    def add_memory(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a generic memory entry to the Vector DB.
        """
        try:
            embedding = self.embeddings.embed_query(content)
            entry_id = str(uuid.uuid4())
            
            entry = MemoryEntry(
                content=content,
                memory_type=memory_type,
                metadata=metadata or {},
                embedding=embedding,
                id=entry_id,
            )
            
            payload = {
                "content": entry.content,
                "memory_type": entry.memory_type.value,
                "timestamp": entry.timestamp.isoformat(),
                **entry.metadata,
            }
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=entry.id,
                        vector=entry.embedding,
                        payload=payload,
                    )
                ],
            )
            
            logger.info(f"Added {memory_type.value} memory: {entry.id}")
            self._enforce_memory_limits()
            return entry.id
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return ""

    def add_code_memory(self, file_path: str, code_snippet: str, symbol_name: str, symbol_type: str, metadata: Dict[str, Any]):
        """
        Add a specific Code Element to memory (Both Vector and Graph).
        
        1. Graph: (File)-[CONTAINS]->(Symbol)
        2. Vector: Embed the code snippet for semantic search ("Where is the login logic?")
        """
        # 1. Update Graph
        # Note: We rely on the caller (GitAnalyzer) to generally structure this data, 
        # but here we can enforce simple node creation if needed.
        # Ideally, GitAnalyzer calls graph.store_code_structure directly for batch ops.
        # But this method allows 'registering' a single interesting function found during runtime.
        
        # We delegate precise graph updates to GraphManager, here we focus on the Vector Index of code.
        
        # 2. Update Vector Index
        meta = metadata or {}
        meta.update({
            "file_path": file_path,
            "symbol_name": symbol_name,
            "symbol_type": symbol_type,
            "is_code": True
        })
        
        # The content for embedding should be descriptive
        content_for_embedding = f"{symbol_type} {symbol_name} in {file_path}\nRunning code:\n{code_snippet[:2000]}"
        
        self.add_memory(
            content=content_for_embedding,
            memory_type=MemoryType.CODE_ELEMENT,
            metadata=meta
        )
        
        # Also store in Graph for linkage
        self.graph.store_code_structure(file_path, meta.get("repo_name", "unknown"), {
            "classes": [symbol_name] if symbol_type == "Class" else [],
            "functions": [symbol_name] if symbol_type == "Function" else [],
            "calls": [] # Cannot infer calls from snippet alone easily here
        })

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 5,
        score_threshold: float = 0.65,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using semantic similarity.
        """
        try:
            query_embedding = self.embeddings.embed_query(query)
            
            query_filter = None
            if memory_type:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="memory_type",
                            match=MatchValue(value=memory_type.value),
                        )
                    ]
                )
            
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_embedding,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
            results = response.points
            
            memories = []
            for point in results:
                memories.append({
                    "id": point.id,
                    "content": point.payload.get("content"),
                    "memory_type": point.payload.get("memory_type"),
                    "score": point.score,
                    "metadata": {
                        k: v for k, v in point.payload.items()
                        if k not in ["content", "memory_type", "timestamp"]
                    },
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

    def get_related_code(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        High-level helper to find code snippets relevant to a natural language query.
        """
        return self.search_memories(query, MemoryType.CODE_ELEMENT, limit=limit)

    def get_recent_memories(
        self,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent memories sorted by timestamp."""
        try:
            query_filter = None
            if memory_type:
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="memory_type",
                            match=MatchValue(value=memory_type.value),
                        )
                    ]
                )
            
            records, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                with_vectors=False,
                with_payload=True,
                scroll_filter=query_filter,
            )
            
            sorted_records = sorted(
                records,
                key=lambda r: r.payload.get("timestamp", ""),
                reverse=True,
            )
            
            memories = []
            for record in sorted_records[:limit]:
                memories.append({
                    "id": record.id,
                    "content": record.payload.get("content"),
                    "memory_type": record.payload.get("memory_type"),
                    "timestamp": record.payload.get("timestamp"),
                    "metadata": {
                        k: v for k, v in record.payload.items()
                        if k not in ["content", "memory_type", "timestamp"]
                    },
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get recent memories: {e}")
            return []
    
    def _enforce_memory_limits(self):
        """Remove oldest memories if limits are exceeded"""
        try:
            for memory_type, limit_val in [
                (MemoryType.SHORT_TERM, self.short_term_limit),
                (MemoryType.LONG_TERM, self.long_term_limit),
            ]:
                memories = self.get_recent_memories(
                    memory_type=memory_type,
                    limit=limit_val + 50,
                )
                
                if len(memories) > limit_val:
                    # Delete oldest ones (end of list)
                    to_delete = [m["id"] for m in memories[limit_val:]]
                    self.client.delete(
                        collection_name=self.collection_name,
                        points_selector=to_delete,
                    )
                    logger.info(f"Deleted {len(to_delete)} old {memory_type.value} memories")
                    
        except Exception as e:
            logger.error(f"Failed to enforce memory limits: {e}")
    
    def clear_collection(self):
        """Clear all memories (use with caution!)"""
        try:
            self.client.delete_collection(self.collection_name)
            self._initialize_collection()
            logger.warning(f"Cleared all memories in {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")

# Singleton instance
_memory_manager: Optional[MemoryManager] = None

def get_memory_manager() -> MemoryManager:
    """Get or create the memory manager singleton"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
