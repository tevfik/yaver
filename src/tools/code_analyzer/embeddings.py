"""
Code Embeddings Generator

This module handles the generation of vector embeddings for code snippets
using Ollama or other configured embedding models.
"""

import logging
from typing import List, Optional, Union, Dict, Any
import numpy as np

from langchain_ollama import OllamaEmbeddings
from langchain_core.embeddings import Embeddings

from config.config import OllamaConfig

logger = logging.getLogger(__name__)

class CodeEmbedder:
    """
    Generates embeddings for code and text using configured models.
    """

    def __init__(self, config: Optional[OllamaConfig] = None):
        """
        Initialize the code embedder.

        Args:
            config: Optional Ollama configuration. If not provided, loads default.
        """
        self.config = config or OllamaConfig()
        self._embedding_model: Optional[Embeddings] = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the underlying embedding model."""
        try:
            logger.info(f"Initializing embedding model: {self.config.model_embedding}")
            self._embedding_model = OllamaEmbeddings(
                base_url=self.config.base_url,
                model=self.config.model_embedding
            )
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single search query.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the vector
        """
        if not self._embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            return self._embedding_model.embed_query(text)
        except Exception as e:
            logger.error(f"Error embedding query: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents (code snippets).

        Args:
            texts: List of strings to embed

        Returns:
            List of vectors
        """
        if not self._embedding_model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            # Check for empty inputs
            if not texts:
                return []
                
            return self._embedding_model.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            raise

    def embed_code_batch(self, code_snippets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Embed a batch of code snippets and attach vectors to the objects.

        Args:
            code_snippets: List of dicts, each containing at least 'content' or 'source'

        Returns:
            List of dicts with 'embedding' key added
        """
        texts_to_embed = []
        indices_to_embed = []

        for idx, snippet in enumerate(code_snippets):
            # Prefer 'content' (full code) or 'summary' or 'source'
            text = snippet.get('content') or snippet.get('source') or snippet.get('code')
            if text:
                texts_to_embed.append(str(text))
                indices_to_embed.append(idx)
        
        if not texts_to_embed:
            return code_snippets

        logger.info(f"Embedding {len(texts_to_embed)} code snippets...")
        embeddings = self.embed_documents(texts_to_embed)

        for i, embedding in zip(indices_to_embed, embeddings):
            code_snippets[i]['embedding'] = embedding
            
        return code_snippets
