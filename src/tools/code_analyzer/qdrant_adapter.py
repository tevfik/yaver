"""
Qdrant Adapter for Vector Storage

This module manages interactions with the Qdrant vector database,
storing and retrieving code embeddings.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional, Union

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from config.config import QdrantConfig

logger = logging.getLogger(__name__)


from tools.code_analyzer.vector_store import VectorStoreInterface


class QdrantAdapter(VectorStoreInterface):
    """
    Adapter for Qdrant Vector Database.
    """

    def __init__(self, config: Optional[QdrantConfig] = None):
        """
        Initialize the Qdrant adapter.

        Args:
            config: Optional QdrantConfig.
        """
        self.config = config or QdrantConfig()
        self.client: Optional[QdrantClient] = None
        self.collection_name = self.config.collection
        self._connect()

    def _connect(self):
        """Establish connection to Qdrant."""
        try:
            if self.config.use_local:
                if self.config.path:
                    logger.info(
                        f"Connecting to local Qdrant at path: {self.config.path}"
                    )
                    self.client = QdrantClient(path=self.config.path)
                else:
                    logger.info("Connecting to in-memory Qdrant")
                    self.client = QdrantClient(location=":memory:")
            else:
                logger.info(
                    f"Connecting to Qdrant server at {self.config.host}:{self.config.port}"
                )
                self.client = QdrantClient(
                    host=self.config.host,
                    port=self.config.port,
                    # Add api_key if needed later
                )
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def ensure_collection(self, vector_size: int = 768):
        """
        Ensure the collection exists with the correct vector size.

        Args:
            vector_size: Dimension of the embeddings (default 768 for nomic-embed-text)
        """
        if not self.client:
            raise RuntimeError("Qdrant client not connected")

        try:
            collections = self.client.get_collections()
            exists = any(
                c.name == self.collection_name for c in collections.collections
            )

            if not exists:
                logger.info(
                    f"Creating collection '{self.collection_name}' with size {vector_size}"
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=models.Distance.COSINE
                    ),
                )
            else:
                logger.debug(f"Collection '{self.collection_name}' already exists")
        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            raise

    def store_embeddings(self, items: List[Dict[str, Any]]):
        """
        Store code snippets and their embeddings.

        Args:
            items: List of dicts containing 'embedding' and metadata keys.
                   Must contain 'embedding'.
        """
        if not items:
            return

        # Ensure collection exists based on first item's embedding size
        vector_size = len(items[0]["embedding"])
        self.ensure_collection(vector_size)

        points = []
        for item in items:
            embedding = item.get("embedding")
            if not embedding:
                continue

            # Generate UUID from string ID if present, or random UUID
            # Use UUID5 for deterministic UUID generation from string IDs
            item_id = item.get("id")
            if item_id:
                # Create deterministic UUID from string ID (e.g., "file.py::function")
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(item_id)))
            else:
                point_id = str(uuid.uuid4())

            # Separate payload from embedding (exclude 'id' and 'embedding')
            payload = {k: v for k, v in item.items() if k not in ["embedding", "id"]}

            points.append(
                models.PointStruct(id=point_id, vector=embedding, payload=payload)
            )

        if points:
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
                logger.info(f"Stored {len(points)} vectors in {self.collection_name}")
            except Exception as e:
                logger.error(f"Failed to upsert points: {e}")
                raise

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        query_filter=None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets.

        Args:
            query_vector: The query embedding
            limit: Max results
            score_threshold: Minimum similarity score
            query_filter: Optional filter as dict or Qdrant Filter

        Returns:
            List of results with payload and score
        """
        if not self.client:
            raise RuntimeError("Qdrant client not connected")

        try:
            # Translate dict filter to Qdrant Filter if needed
            if isinstance(query_filter, dict):
                must_conditions = []
                for key, value in query_filter.items():
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )
                query_filter = models.Filter(must=must_conditions)

            # Use query_points for newer Qdrant client API
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            results = []
            for hit in search_result.points:
                results.append(
                    {"id": hit.id, "score": hit.score, "payload": hit.payload}
                )
            return results
        except UnexpectedResponse as e:
            # If collection doesn't exist, return empty
            if "Not found" in str(e):
                logger.warning(f"Collection {self.collection_name} not found")
                return []
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def delete_collection(self):
        """Delete the collection (useful for testing/reset)."""
        if self.client:
            self.client.delete_collection(self.collection_name)

    def delete_by_filter(self, filter_key: str, filter_value: Any):
        """
        Delete points where filter_key == filter_value.

        Args:
            filter_key: The payload key to filter by (e.g., "session_id")
            filter_value: The value to match
        """
        if not self.client:
            raise RuntimeError("Qdrant client not connected")

        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key=filter_key,
                                match=models.MatchValue(value=filter_value),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"Deleted points where {filter_key}={filter_value}")
        except Exception as e:
            # If collection doesn't exist, ignore
            if "Not found" in str(e) or "doesn't exist" in str(e):
                return
            logger.error(f"Failed to delete points: {e}")
            raise

    def get_recent(
        self, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recently stored items using scroll.

        Args:
            limit: Max items to return
            filter: Optional filter dictionary or Qdrant Filter

        Returns:
            List of items with payload and id
        """
        if not self.client:
            raise RuntimeError("Qdrant client not connected")

        try:
            # Translate dict filter to Qdrant Filter if needed
            if isinstance(filter, dict):
                must_conditions = []
                for key, value in filter.items():
                    must_conditions.append(
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value),
                        )
                    )
                filter = models.Filter(must=must_conditions)

            # Use scroll to get points without vector search
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                limit=limit,
                scroll_filter=filter,
                with_payload=True,
                with_vectors=False,
            )

            results = []
            for point in scroll_result[0]:
                results.append({"id": point.id, "payload": point.payload})
            return results
        except Exception as e:
            logger.error(f"Failed to get recent items from Qdrant: {e}")
            return []
