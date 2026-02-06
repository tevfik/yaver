"""
Vector Store Interface
"""

import abc
from typing import List, Dict, Any, Optional


class VectorStoreInterface(abc.ABC):
    """
    Abstract Base Class for Vector Store Adapters.
    """

    @abc.abstractmethod
    def store_embeddings(self, items: List[Dict[str, Any]]):
        """
        Store code snippets/items and their embeddings.

        Args:
            items: List of dicts containing 'embedding' and metadata keys.
                   Must contain 'embedding'.
        """
        pass

    @abc.abstractmethod
    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        query_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar items.

        Args:
            query_vector: The query embedding
            limit: Max results
            score_threshold: Minimum similarity score
            query_filter: Optional filter dictionary

        Returns:
            List of results with payload and score
        """
        pass

    @abc.abstractmethod
    def delete_collection(self):
        """Delete the collection/index."""
        pass

    @abc.abstractmethod
    def delete_by_filter(self, filter_key: str, filter_value: Any):
        """
        Delete items matching a filter.

        Args:
            filter_key: The metadata key to filter by.
            filter_value: The value to match.
        """
        pass

    @abc.abstractmethod
    def get_recent(
        self, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recently stored items.

        Args:
            limit: Max items to return
            filter: Optional filter dictionary

        Returns:
            List of items with payload and id
        """
        pass


class VectorStoreFactory:
    """
    Factory for creating VectorStore instances.
    """

    @staticmethod
    def get_instance(config=None) -> VectorStoreInterface:
        """
        Get the configured Vector Store instance.

        Args:
            config: Configuration object (should have vector_db_provider or similar)

        Returns:
            VectorStoreInterface: The configured adapter.
        """

        # Avoid circular imports by importing here
        from tools.code_analyzer.qdrant_adapter import QdrantAdapter
        from tools.code_analyzer.chroma_adapter import ChromaAdapter
        from tools.code_analyzer.chroma_adapter import ChromaAdapter

        from config.config import get_config

        # If config is passed, use it. Otherwise load default.
        # Check environment or config for provider
        import os

        provider = os.getenv("VECTOR_DB_PROVIDER", "qdrant").lower()

        # Override if config object has it
        if config:
            if hasattr(config, "provider"):
                provider = config.provider
            elif hasattr(config, "vector_db") and hasattr(config.vector_db, "provider"):
                provider = config.vector_db.provider

        if provider == "chroma":
            chroma_config = config
            if hasattr(config, "vector_db"):
                chroma_config = config.vector_db
            return ChromaAdapter(chroma_config)
        elif provider == "qdrant":
            qdrant_config = config
            if hasattr(config, "qdrant"):
                qdrant_config = config.qdrant
            return QdrantAdapter(qdrant_config)
        else:
            # Default to Qdrant
            qdrant_config = config
            if hasattr(config, "qdrant"):
                qdrant_config = config.qdrant
            return QdrantAdapter(qdrant_config)
