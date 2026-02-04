import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from config.onboarding import get_config as get_config_dict


def get_config():
    """Get config from onboarding"""
    return get_config_dict()


logger = logging.getLogger("yaver.interaction")


class InteractionDB:
    """SQLite Database manager for LLM interactions"""

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            config = get_config()
            # Use log directory for DB
            log_dir = Path(config.logging.log_file).parent
            db_path = str(log_dir / "interaction_history.sqlite")

        self.db_path = db_path
        self._init_db()
        self._prune_old_records()

    def _init_db(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create interactions table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    model TEXT,
                    inputs TEXT,
                    outputs TEXT,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    run_id TEXT
                )
            """
            )

            # Create index on timestamp for pruning
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp)
            """
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize Interaction DB: {e}")

    def log_interaction(
        self,
        run_id: str,
        model: str,
        inputs: str,
        outputs: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ):
        """Log a completed interaction"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO interactions (id, timestamp, model, inputs, outputs, tokens_in, tokens_out, run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(run_id),
                    datetime.now().isoformat(),
                    model,
                    inputs,
                    outputs,
                    tokens_in,
                    tokens_out,
                    str(run_id),
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")

    def _prune_old_records(self, max_records: int = 2000, days_to_keep: int = 7):
        """Prune database to prevent bloating"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 1. Date based pruning
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            cursor.execute(
                "DELETE FROM interactions WHERE timestamp < ?", (cutoff_date,)
            )

            # 2. Count based pruning (keep latest N)
            cursor.execute("SELECT COUNT(*) FROM interactions")
            count = cursor.fetchone()[0]

            if count > max_records:
                to_delete = count - max_records
                # Delete oldest records
                cursor.execute(
                    """
                    DELETE FROM interactions
                    WHERE id IN (
                        SELECT id FROM interactions
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                """,
                    (to_delete,),
                )

            conn.commit()

            # 3. Vacuum to reclaim space
            cursor.execute("VACUUM")

            conn.close()
        except Exception as e:
            logger.error(f"Failed to prune interaction DB: {e}")


class SQLLoggingCallback(BaseCallbackHandler):
    """LangChain callback to log interactions to SQLite"""

    def __init__(self, model_name: str = "unknown"):
        super().__init__()
        self.db = InteractionDB()
        self.runs = {}
        self.model_name = model_name

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM starts running."""
        # Convert messages to string representation
        prompt_text = ""
        for batch in messages:
            for msg in batch:
                prefix = f"[{msg.type.upper()}]"
                prompt_text += f"{prefix}: {msg.content}\n---\n"

        # Use provided model name, fallback to serialized if "unknown" was passed
        model_name = self.model_name
        if model_name == "unknown":
            model_name = serialized.get("kwargs", {}).get("model", "unknown")

        self.runs[run_id] = {
            "inputs": prompt_text,
            "model": model_name,
            "start_time": datetime.now(),
        }

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        """Run when LLM ends running."""
        run_data = self.runs.pop(run_id, None)
        if not run_data:
            return

        # Extract output text
        output_text = ""
        tokens_out = 0

        for generation_list in response.generations:
            for generation in generation_list:
                output_text += generation.text + "\n"

        # Log to DB
        self.db.log_interaction(
            run_id=str(run_id),
            model=run_data["model"],
            inputs=run_data["inputs"],
            outputs=output_text,
            tokens_in=0,  # Usage metadata might not be available in simple responses
            tokens_out=tokens_out,
        )
