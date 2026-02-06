"""
Memory Manager using mem0ai
Adapted from IntelligentAgent project.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from config.config import QdrantConfig, OllamaConfig

try:
    from mem0 import Memory
except ImportError:
    Memory = None

logger = logging.getLogger("memory_manager")


class MemoryManager:
    """Manages agent memory using mem0."""

    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        self.memory = None
        self.qdrant_config = QdrantConfig()
        self.ollama_config = OllamaConfig()

        if Memory:
            try:
                # Configure mem0 for Ollama + Qdrant
                config = {
                    "vector_store": {
                        "provider": "qdrant",
                        "config": {
                            "host": self.qdrant_config.host,
                            "port": self.qdrant_config.port,
                            "collection_name": self.qdrant_config.collection,
                            "embedding_model_dims": 768,
                        },
                    },
                    "llm": {
                        "provider": "ollama",
                        "config": {
                            "model": self.ollama_config.model_general,
                            "temperature": 0.1,
                        },
                    },
                    "embedder": {
                        "provider": "ollama",
                        "config": {"model": self.ollama_config.model_embedding},
                    },
                }

                logger.info(
                    f"Initializing mem0 with config: Ollama={self.ollama_config.model_general}, Qdrant={self.qdrant_config.host}"
                )
                self.memory = Memory.from_config(config)
                logger.info("mem0 initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize mem0: {e}")
        else:
            logger.warning("mem0ai package not installed")

    def add_memory(self, text: str, metadata: Optional[Dict] = None):
        """Add a memory item."""
        if self.memory:
            return self.memory.add(text, user_id=self.user_id, metadata=metadata)
        return None

    def search_memory(self, query: str, limit: int = 5):
        """Search related memories."""
        if self.memory:
            results = self.memory.search(query, user_id=self.user_id, limit=limit)
            if isinstance(results, dict) and "results" in results:
                return results["results"]
            return results
        return []

    def get_all_memories(self):
        """Retrieve all memories for the user."""
        if self.memory:
            return self.memory.get_all(user_id=self.user_id)
        return []

    def reset(self):
        """Clear all memories."""
        if self.memory:
            self.memory.delete_all(user_id=self.user_id)
