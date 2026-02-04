import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import uuid

# Try to import leann, treat as optional dependency just in case, but here we know it is installed
try:
    from leann import LeannBuilder, LeannSearcher
except ImportError:
    LeannBuilder = None
    LeannSearcher = None

# Assuming config structure, though we might pass session_id directly
from config.config import MemoryConfig

logger = logging.getLogger(__name__)


class LeannAdapter:
    """
    Adapter for Leann Vector Search (Local, Python-native, Compressed).
    Stores one index per session/project to isolate contexts.
    """

    def __init__(self, session_id: str, config: Optional[Any] = None):
        """
        Initialize Leann adapter.

        Args:
            session_id: The project/session identifier.
            config: Optional global config object.
        """
        if LeannBuilder is None:
            raise ImportError(
                "Leann library not installed. Install with 'pip install leann'"
            )

        self.session_id = session_id

        # Determine storage path
        # Default to ~/.yaver/leann_indexes/{session_id}
        # Or obey some config if provided
        home = Path(os.path.expanduser("~"))
        self.base_path = home / ".yaver" / "leann_indexes" / self.session_id

        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

        self.index_path = str(self.base_path / "index.leann")
        self.searcher = None

        logger.debug(
            f"LeannAdapter initialized for session {session_id} at {self.index_path}"
        )

    def store_embeddings(self, items: List[Dict[str, Any]]):
        """
        Store code chunks.

        Args:
            items: List of dicts. Must contain 'content' or 'code' and optionally metadata.
                   The 'embedding' field, if present, is ignored as Leann handles it.
        """
        if not items:
            return

        builder = LeannBuilder()

        # If index exists, we treat this as an update.
        # Leann's update_index might require loading the existing one first?
        # The docs signature `update_index(index_path)` suggests it might do it in-place or load from path.
        # However, `LeannBuilder` is stateful for the *new* text added via `add_text`.
        # So we add new text, then call update_index.

        count = 0
        for item in items:
            # Prefer 'content' as used in CodeAnalyzer, fallback to 'code'
            text = item.get("content") or item.get("code")
            if not text:
                continue

            # Metadata preparation
            # Remove giant fields if any, and 'embedding'
            meta = item.copy()
            for key in ["embedding", "code", "content"]:
                if key in meta:
                    del meta[key]

            # Ensure ID is in metadata if not there
            if "id" not in meta and "id" in item:
                meta["id"] = item["id"]

            builder.add_text(str(text), meta)
            count += 1

        if count > 0:
            logger.info(f"Storing {count} items in Leann index: {self.index_path}")
            if os.path.exists(self.index_path):
                # Update existing index
                try:
                    builder.update_index(self.index_path)
                except Exception as e:
                    logger.error(f"Failed to update Leann index, trying rebuild: {e}")
                    # Fallback to rebuild if update fails? or raise?
                    # If update is not supported for 'pure' append, we might need a rebuild strategy.
                    # But assuming update_index works for now.
                    builder.build_index(self.index_path)
            else:
                # Create new
                builder.build_index(self.index_path)

            # Invalidate searcher
            self.searcher = None

    def search(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.0,
        query_filter=None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar code.

        Args:
            query: The search query string.
            limit: Max results.
            score_threshold: (Not fully used by Leann searcher directly in same way, but we can filter)
            query_filter: Metadata filters (dict). Leann supports this.

        Returns:
            List of dicts with 'id', 'score', 'payload' (metadata).
        """
        # Validations
        if not isinstance(query, str):
            logger.warning(
                f"LeannAdapter expected string query, got {type(query)}. If this is a vector, Leann does not support vector input directly yet."
            )
            return []

        if not os.path.exists(self.index_path):
            logger.debug("Index not found, returning empty results.")
            return []

        if not self.searcher:
            try:
                self.searcher = LeannSearcher(self.index_path)
            except Exception as e:
                logger.error(f"Failed to load Leann index: {e}")
                return []

        try:
            # Prepare filters if any
            # Leann expects `metadata_filters: dict`

            # Perform search
            # Note: Leann might return generic objects.
            results = self.searcher.search(
                query, top_k=limit, metadata_filters=query_filter
            )

            output = []
            for hit in results:
                # Inspect hit object structure. Usually has .metadata, .score, .id/text?
                # Based on previous usages/research, we assume it behaves like typical search result
                payload = getattr(hit, "metadata", {})
                score = getattr(hit, "score", 0.0)

                # Check threshold
                if score < score_threshold:
                    continue

                output.append(
                    {
                        "id": getattr(hit, "id", payload.get("id")),
                        "score": score,
                        "payload": payload,
                        # Leann also usually returns the matched text segment?
                        "preview": getattr(hit, "text", None),
                    }
                )

            return output

        except Exception as e:
            logger.error(f"Leann search error: {e}")
            return []

    def delete_collection(self):
        """Delete the entire index for this session."""
        import shutil

        if self.base_path.exists():
            try:
                shutil.rmtree(self.base_path)
                logger.info(f"Deleted Leann index at {self.base_path}")
            except Exception as e:
                logger.error(f"Failed to delete Leann index: {e}")

    def delete_by_filter(self, filter_key: str, filter_value: Any):
        """
        Delete items.
        Since we segment by session_id at the directory level, if the filter is session_id,
        we delete the whole index.
        """
        if filter_key == "session_id" and str(filter_value) == self.session_id:
            self.delete_collection()
        else:
            logger.warning(
                f"LeannAdapter does not support granular deletion by {filter_key} yet. Only session_id handled via folder deletion."
            )
