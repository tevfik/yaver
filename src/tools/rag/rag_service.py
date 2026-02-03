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

from config.config import OllamaConfig
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
        logger.info(f"retrieve_context called with strategy: {strategy}")
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
                logger.info(f"Starting semantic search for: {question[:50]}...")
                query_vec = self.embedder.embed_query(question)
                logger.info(f"Query vector generated, length: {len(query_vec)}")
                results = self.qdrant.search(query_vec, limit=5, score_threshold=0.3)  # Lowered to 0.3 for multilingual support
                
                logger.info(f"Qdrant search returned {len(results)} results")
                if results:
                    logger.debug(f"Top result score: {results[0].get('score', 0):.3f}")
                    context_parts.append("--- RELEVANT CODE SNIPPETS ---")
                    for res in results:
                        payload = res.get('payload', {})
                        name = payload.get('name', 'Unknown')
                        file = payload.get('file_path', 'Unknown')
                        # Prefer 'content' (chunk text) over 'source' (raw code) to keep context concise but rich
                        text = payload.get('content', '') 
                        
                        context_parts.append(f"File: {file} | Symbol: {name}\n{text}\n")
                else:
                    logger.warning("No results returned from Qdrant")
            except Exception as e:
                logger.error(f"Semantic retrieval failed: {e}", exc_info=True)
        
        final_context = "\n".join(context_parts)
        logger.info(f"Final context length: {len(final_context)} chars")
        return final_context

    def answer(self, question: str) -> str:
        """
        End-to-end RAG pipeline.
        """
        # 1. Determine Intent
        try:
            intent_chain = self.intent_prompt | self.llm | StrOutputParser()
            intent_response = intent_chain.invoke({"question": question}).strip()
            logger.info(f"Query Intent Response: {intent_response[:100]}...")
            
            # Extract intent label from response (look for CHAT, STRUCTURE, SEMANTIC, or HYBRID)
            # Look for markdown bold format **LABEL** or "Label:" pattern
            intent = "HYBRID"  # default
            intent_upper = intent_response.upper()
            
            # Priority: Check for bold markdown first (**LABEL**)
            import re
            bold_match = re.search(r'\*\*(CHAT|STRUCTURE|SEMANTIC|HYBRID)\*\*', intent_upper)
            if bold_match:
                intent = bold_match.group(1)
            # Then check for "LABEL:" pattern at line start
            elif re.search(r'^\s*(CHAT|STRUCTURE|SEMANTIC|HYBRID)\s*:', intent_upper, re.MULTILINE):
                match = re.search(r'^\s*(CHAT|STRUCTURE|SEMANTIC|HYBRID)\s*:', intent_upper, re.MULTILINE)
                intent = match.group(1)
            # Fallback: Check line that starts with label
            elif re.search(r'^(CHAT|STRUCTURE|SEMANTIC|HYBRID)\s*$', intent_upper, re.MULTILINE):
                match = re.search(r'^(CHAT|STRUCTURE|SEMANTIC|HYBRID)\s*$', intent_upper, re.MULTILINE)
                intent = match.group(1)
            
            logger.info(f"Parsed Intent: {intent}")
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            intent = "HYBRID"
        
        # Handle CHAT intent - direct LLM response without RAG
        if "CHAT" in intent.upper():
            try:
                chat_response = self.llm.invoke(question)
                return chat_response.content if hasattr(chat_response, 'content') else str(chat_response)
            except Exception as e:
                logger.error(f"Chat LLM invocation failed: {e}")
                return "I'm here! How can I help you with your codebase?"
        
        # 2. Retrieve context for code-related queries
        context = self.retrieve_context(question, strategy=intent)
        
        if not context.strip():
            return "I couldn't find relevant information in the codebase to answer that."
            
        # 3. Generate Answer using RAG
        qa_chain = self.qa_prompt | self.llm | StrOutputParser()
        response = qa_chain.invoke({"context": context, "question": question})
        
        return response
