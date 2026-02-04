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
            
            # Prepare initialization arguments
            init_kwargs = {
                "base_url": self.config.base_url,
                "model": self.config.model_embedding
            }

            # Handle Authentication
            if self.config.username and self.config.password:
                import base64
                auth_str = f"{self.config.username}:{self.config.password}"
                b64_auth = base64.b64encode(auth_str.encode()).decode()
                
                # Use client_kwargs for header injection
                init_kwargs["client_kwargs"] = {
                    "headers": {
                        "Authorization": f"Basic {b64_auth}"
                    }
                }
                logger.info(f"🔐 Embedding model authentication enabled for user: {self.config.username}")

            self._embedding_model = OllamaEmbeddings(**init_kwargs)
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
            processed = self._preprocess_text(text)
            return self._embedding_model.embed_query(processed)
        except Exception as e:
            if "500" in str(e) and len(text) > 500:
                logger.warning(f"Embedding failed with 500 for text length {len(text)}. Retrying with truncation to 500 chars...")
                try:
                    processed = self._preprocess_text(text[:500])
                    return self._embedding_model.embed_query(processed)
                except Exception as e2:
                    logger.error(f"Retry failed: {e2}")
                    raise e
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
            
            # Preprocess texts to avoid NaN errors
            processed_texts = [self._preprocess_text(t) for t in texts]
                
            return self._embedding_model.embed_documents(processed_texts)
        except Exception as e:
            if "500" in str(e):
                logger.warning(f"Batch embedding failed with 500. Retrying individually with truncation...")
                results = []
                for idx, text in enumerate(texts):
                    try:
                        processed = self._preprocess_text(text)
                        results.append(self._embedding_model.embed_query(processed))
                    except Exception as inner_e:
                        if "500" in str(inner_e):
                            # Log problematic content for debugging
                            logger.warning(f"  > Problematic text sample (idx={idx}): {text[:100]}...")
                            if len(text) > 500:
                                logger.warning(f"  > Truncating text length {len(text)} -> 500")
                                try:
                                    processed = self._preprocess_text(text[:500])
                                    results.append(self._embedding_model.embed_query(processed))
                                except:
                                    logger.error(f"  > Even truncated text failed. Using zero vector.")
                                    results.append([0.0] * 1024) # Fallback zero vector
                            else:
                                logger.error(f"  > Short text still failed. Using zero vector.")
                                results.append([0.0] * 1024)
                        else:
                            logger.error(f"  > Failed to embed specific doc: {inner_e}")
                            results.append([0.0] * 1024) # Fallback zero vector
                return results

            logger.error(f"Error embedding documents: {e}")
            raise
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to avoid NaN errors in embedding model.
        Removes problematic patterns that can cause bge-m3 to produce NaN.
        """
        import re
        
        # Convert to string if not already
        if not isinstance(text, str):
            text = str(text)
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Remove excessive repetition (e.g., "======" repeated many times)
        text = re.sub(r'(.)\1{20,}', r'\1\1\1', text)
        
        # Limit overall length
        if len(text) > 800:
            text = text[:800]
        
        return text.strip()

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
