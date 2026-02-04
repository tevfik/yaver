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
        
        # Initialize LLM with authentication
        init_kwargs = {
            "base_url": self.config.base_url,
            "model": self.config.model_general,
            "temperature": 0.2
        }
        
        # Add authentication if configured
        if self.config.username and self.config.password:
            import base64
            auth_str = f"{self.config.username}:{self.config.password}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            init_kwargs["client_kwargs"] = {
                "headers": {
                    "Authorization": f"Basic {b64_auth}"
                }
            }
            logger.info(f"🔐 RAG Service LLM authentication enabled for user: {self.config.username}")
        
        self.llm = ChatOllama(**init_kwargs)
        
        # Prompts
        self._init_prompts()

    def _load_prompt(self, filename: str) -> str:
        """Load prompt from utils/prompts directory."""
        # Assuming relative path from valid roots, or absolute.
        # Let's try to locate the prompts key file relative to project root
        # Ideally config should define this, but let's hardcode the utils/prompts location for now
        # based on user request.
        
        # We need to find the project root.
        # yaver/src/tools/rag/rag_service.py -> ../../../
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
        
        # Query Rewriter (History Context)
        rewriter_template = self._load_prompt("query_rewriter.md")
        self.rewriter_prompt = ChatPromptTemplate.from_template(rewriter_template)

    def rewrite_query(self, question: str, chat_history: List[Any]) -> str:
        """
        Rewrite question to be standalone using chat history.
        """
        if not chat_history:
            return question
            
        try:
            # Format history for prompt
            history_text = ""
            for msg in chat_history[-6:]: # Look at last few messages
                role = "User" if msg.type == "human" else "Assistant"
                content = msg.content
                history_text += f"{role}: {content}\n"
                
            chain = self.rewriter_prompt | self.llm | StrOutputParser()
            rewritten = chain.invoke({
                "history": history_text, 
                "question": question
            }).strip()
            
            # Sanity check: if empty or failed, return original
            if not rewritten:
                return question
                
            logger.info(f"Rewrote query: '{question}' -> '{rewritten}'")
            return rewritten
            
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return question

    def retrieve_context(self, question: str, strategy: str = "HYBRID", session_id: str = None) -> str:
        """
        Retrieve relevant context based on strategy.
        
        Args:
            question: User's question
            strategy: CHAT, STRUCTURE, SEMANTIC, or HYBRID
            session_id: Optional session ID to filter results (for multi-repo queries)
        """
        logger.info(f"retrieve_context called with strategy: {strategy}, session_id: {session_id}")
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
                
                # Apply session_id filter if provided
                filter_condition = None
                if session_id:
                    from qdrant_client import models
                    filter_condition = models.Filter(
                        must=[
                            models.FieldCondition(
                                key="session_id",
                                match=models.MatchValue(value=session_id)
                            )
                        ]
                    )
                    logger.info(f"Filtering by session_id: {session_id}")
                
                results = self.qdrant.search(
                    query_vec, 
                    limit=5, 
                    score_threshold=0.3,
                    query_filter=filter_condition
                )
                
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
                error_msg = str(e)
                if "Vector dimension error" in error_msg or "expected dim" in error_msg:
                    logger.error(f"Vector dimension mismatch detected. This happens when embedding model changes.")
                    logger.error(f"Current model '{self.config.model_embedding}' may produce different vector dimensions.")
                    logger.error(f"To fix: Delete the Qdrant collection and re-run analysis, or switch to the original embedding model.")
                    logger.error(f"Command: qdrant-client delete-collection yaver_memory (or restart Qdrant)")
                else:
                    logger.error(f"Semantic retrieval failed: {e}")
        
        final_context = "\n".join(context_parts)
        logger.info(f"Final context length: {len(final_context)} chars")
        return final_context

    def answer(self, question: str, session_id: str = None, chat_history: List[Any] = None, extra_context: str = "") -> str:
        """
        End-to-end RAG pipeline.
        
        Args:
            question: User's question
            session_id: Optional session ID to query across multiple repos
            chat_history: List of previous messages for context
            extra_context: Additional context to inject (e.g. static analysis findings)
        """
        # 0. Rewrite Query with History
        standalone_question = question
        if chat_history:
            standalone_question = self.rewrite_query(question, chat_history)

        # 1. Determine Intent (using standalone question)
        try:
            intent_chain = self.intent_prompt | self.llm | StrOutputParser()
            intent_response = intent_chain.invoke({"question": standalone_question}).strip()
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
                # Use standalone_question for better context even in chat
                # If extra_context is provided, prepend it to the question
                prompt_input = standalone_question
                if extra_context:
                    prompt_input = f"Context:\n{extra_context}\n\nQuestion: {standalone_question}"
                
                chat_response = self.llm.invoke(prompt_input)
                return chat_response.content if hasattr(chat_response, 'content') else str(chat_response)
            except Exception as e:
                logger.error(f"Chat LLM invocation failed: {e}")
                return "I'm here! How can I help you with your codebase?"
        
        # 2. Retrieve context for code-related queries (using standalone question)
        context = self.retrieve_context(standalone_question, strategy=intent, session_id=session_id)
        
        if extra_context:
            context = f"{extra_context}\n\n{context}"
        
        if not context.strip():
            return "I couldn't find relevant information in the codebase to answer that."
            
        # 3. Generate Answer using RAG (using standalone question)
        qa_chain = self.qa_prompt | self.llm | StrOutputParser()
        response = qa_chain.invoke({"context": context, "question": standalone_question})
        
        return response
