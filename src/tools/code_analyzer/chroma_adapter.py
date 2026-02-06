"""
ChromaDB Adapter for Vector Storage

This module manages interactions with the ChromaDB vector database,
storing and retrieving code embeddings.
"""

import logging
import uuid
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from config.config import VectorDBConfig

logger = logging.getLogger(__name__)


from tools.code_analyzer.vector_store import VectorStoreInterface


class ChromaAdapter(VectorStoreInterface):
    """
    Adapter for ChromaDB Vector Database.
    """

    def __init__(self, config: Optional[VectorDBConfig] = None):
        """
        Initialize the ChromaDB adapter.

        Args:
            config: Optional VectorDBConfig.
        """
        self.config = config or VectorDBConfig()
        self.persist_directory = self.config.chroma_persist_dir
        self.collection_name = "yaver_code"
        self.client = None
        self.collection = None
        self._connect()

    def _connect(self):
        """Establish connection to ChromaDB."""
        try:
            # Ensure directory exists
            Path(self.persist_directory).expanduser().resolve().mkdir(
                parents=True, exist_ok=True
            )

            self.client = chromadb.PersistentClient(
                path=str(Path(self.persist_directory).expanduser().resolve()),
                settings=Settings(allow_reset=True),
            )

            self.collection = self.client.get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Connected to ChromaDB at {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
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

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for item in items:
            embedding = item.get("embedding")
            if not embedding:
                continue

            # Generate UUID from string ID if present
            item_id = item.get("id")
            if item_id:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(item_id)))
            else:
                point_id = str(uuid.uuid4())

            # Separate payload from embedding
            payload = {k: v for k, v in item.items() if k not in ["embedding", "id"]}

            # Chroma requires metadata values to be str, int, float, bool
            # We need to serialize complex objects or remove them
            clean_metadata = {}
            for k, v in payload.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_metadata[k] = v
                else:
                    clean_metadata[k] = str(v)

            ids.append(point_id)
            embeddings.append(embedding)
            metadatas.append(clean_metadata)
            documents.append(str(payload.get("content", "")))

        if ids:
            try:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )
                logger.info(f"Stored {len(ids)} vectors in ChromaDB")
            except Exception as e:
                logger.error(f"Failed to upsert to ChromaDB: {e}")
                raise

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.0,
        query_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code snippets.

        Args:
            query_vector: The query embedding
            limit: Max results
            score_threshold: Minimum similarity score (Chroma uses distance, so we need conversion or check logic)
            query_filter: Optional filter dictionary (e.g. {"session_id": "..."})

        Returns:
            List of results with payload and score
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        try:
            # Chroma query
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                where=query_filter if query_filter else None,
            )

            output = []
            if not results["ids"]:
                return []

            # Unpack results (Chroma returns lists of lists)
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                distance = results["distances"][0][i] if "distances" in results else 1.0
                metadata = results["metadatas"][0][i] if "metadatas" in results else {}

                # Convert cosine distance to similarity score approx (1 - distance)
                # Chroma cosine distance range: 0 (identical) to 2 (opposite)
                # But typically for normalized vectors it is 0 to 1?
                # Assuming simple 1 - distance for now.
                score = 1.0 - distance

                if score < score_threshold:
                    continue

                output.append({"id": doc_id, "score": score, "payload": metadata})

            return output

        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            raise

    def delete_collection(self):
        """Delete the collection."""
        if self.client:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass

    def delete_by_filter(self, filter_key: str, filter_value: Any):
        """
        Delete points where filter_key == filter_value.

        Args:
            filter_key: The metadata key to filter by.
            filter_value: The value to match.
        """
        if not self.collection:
            return

        try:
            self.collection.delete(where={filter_key: filter_value})
            logger.info(f"Deleted items with {filter_key}={filter_value}")
        except Exception as e:
            logger.error(f"Failed to delete from ChromaDB: {e}")

    def get_recent(
        self, limit: int = 5, filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recently stored items from ChromaDB.

        Args:
            limit: Max items to return
            filter: Optional filter dictionary

        Returns:
            List of items with payload and id
        """
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        try:
            # Chroma get() allows retrieving by filter without vector search
            results = self.collection.get(
                limit=limit,
                where=filter if filter else None,
                include=["metadatas", "documents"],
            )

            output = []
            if not results["ids"]:
                return []

            for i in range(len(results["ids"])):
                output.append(
                    {
                        "id": results["ids"][i],
                        "payload": results["metadatas"][i]
                        if results["metadatas"]
                        else {},
                    }
                )
            return output

        except Exception as e:
            logger.error(f"Failed to get recent items from ChromaDB: {e}")
            return []
