"""
RAG Service
Combines Graph retrieval (Neo4j) and Vector retrieval (Qdrant) to answer questions about the codebase.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.config.config import OllamaConfig
from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
from tools.code_analyzer.qdrant_adapter import QdrantAdapter
from tools.code_analyzer.embeddings import CodeEmbedder

logger = logging.getLogger(__name__)

class RAGService:
    """
    Retrieval Augmented Generation Service for Codebase.
    """

    def __init__(
        self, 
        neo4j_adapter: Neo4jAdapter,
        qdrant_adapter: QdrantAdapter,
        code_embedder: CodeEmbedder,
        config: Optional[OllamaConfig] = None
    ):
        self.neo4j = neo4j_adapter
        self.qdrant = qdrant_adapter
        self.embedder = code_embedder
        self.config = config or OllamaConfig()
        
        self.llm = ChatOllama(
            base_url=self.config.base_url,
            model=self.config.model_general,
            temperature=0.2
        )
        
        # Prompts
        self._init_prompts()

    def _load_prompt(self, filename: str) -> str:
        """Load prompt from utils/prompts directory."""
        # Assuming relative path from valid roots, or absolute.
        # Let's try to locate the prompts key file relative to project root
        # Ideally config should define this, but let's hardcode the utils/prompts location for now
        # based on user request.
        
        # We need to find the project root.
        # devmind/src/tools/rag/rag_service.py -> ../../../
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        prompt_path = project_root / "src/utils/prompts" / filename
        
        if not prompt_path.exists():
            # Fallback for installed package structure if needed
            # But here we are in source.
            logger.warning(f"Prompt file not found at {prompt_path}, using empty string.")
            return ""
            
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _init_prompts(self):
        """Initialize LangChain prompts from files."""
        
        # Intent Classification
        intent_template = self._load_prompt("rag_intent_classifier.md")
        self.intent_prompt = ChatPromptTemplate.from_template(intent_template)
        
        # Code Explanation
        qa_template = self._load_prompt("rag_qa_architect.md")
        self.qa_prompt = ChatPromptTemplate.from_template(qa_template)
        
        # Concept Explainer
        concept_template = self._load_prompt("concept_explainer.md")
        self.concept_prompt = ChatPromptTemplate.from_template(concept_template)
        
        # Similarity Analysis
        similarity_template = self._load_prompt("similar_code_finder.md")
        self.similarity_prompt = ChatPromptTemplate.from_template(similarity_template)

    def retrieve_context(self, question: str, strategy: str = "HYBRID") -> str:
        """
        Retrieve relevant context based on strategy.
        """
        context_parts = []
        
        # 1. Structural Retrieval (Neo4j)
        if strategy in ["STRUCTURE", "HYBRID"]:
            # TODO: Implement Text-to-Cypher or specific keyword lookup
            # For now, simple keyword matching for "calls", "dependencies"
            # Or just generic neighbor search if entities are named
            pass
            
        # 2. Semantic Retrieval (Qdrant)
        if strategy in ["SEMANTIC", "HYBRID"]:
            try:
                query_vec = self.embedder.embed_query(question)
                results = self.qdrant.search(query_vec, limit=5, score_threshold=0.6)
                
                if results:
                    context_parts.append("--- RELEVANT CODE SNIPPETS ---")
                    for res in results:
                        payload = res.get('payload', {})
                        name = payload.get('name', 'Unknown')
                        file = payload.get('file_path', 'Unknown')
                        # Prefer 'content' (chunk text) over 'source' (raw code) to keep context concise but rich
                        text = payload.get('content', '') 
                        
                        context_parts.append(f"File: {file} | Symbol: {name}\n{text}\n")
            except Exception as e:
                logger.error(f"Semantic retrieval failed: {e}")
        
        return "\n".join(context_parts)

    def answer(self, question: str) -> str:
        """
        End-to-end RAG pipeline.
        """
        # 1. Determine Intent
        try:
            intent_chain = self.intent_prompt | self.llm | StrOutputParser()
            intent = intent_chain.invoke({"question": question}).strip()
            logger.info(f"Query Intent: {intent}")
        except Exception:
            intent = "HYBRID"
        
        # 2. Retrieve
        context = self.retrieve_context(question, strategy=intent)
        
        if not context.strip():
            return "I couldn't find relevant information in the codebase to answer that."
            
        # 3. Generate Answer
        qa_chain = self.qa_prompt | self.llm | StrOutputParser()
        response = qa_chain.invoke({"context": context, "question": question})
        
        return response
