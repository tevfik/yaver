"""
Analysis History Manager
Tracks repository analysis history using SQLite for smart incremental updates.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class AnalysisHistory:
    """
    Manages analysis metadata and history for repositories.
    Uses SQLite to track commits and analysis state.
    """

    DB_PATH = Path.home() / ".yaver" / "analysis_history.db"

    def __init__(self):
        """Initialize or connect to SQLite database."""
        self.db_path = self.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS project_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                commit_hash TEXT NOT NULL,
                analysis_timestamp DATETIME NOT NULL,
                files_count INTEGER,
                analysis_type TEXT,
                changed_files INTEGER,
                status TEXT DEFAULT 'success',
                UNIQUE(project_id, commit_hash)
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_project_id ON project_analyses(project_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_commit_hash ON project_analyses(commit_hash)
        """
        )

        conn.commit()
        conn.close()

    def record_analysis(
        self,
        project_id: str,
        repo_path: str,
        commit_hash: str,
        files_count: int,
        analysis_type: str = "full",
        changed_files: int = None,
        status: str = "success",
    ):
        """Record a completed analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO project_analyses
                (project_id, repo_path, commit_hash, analysis_timestamp,
                 files_count, analysis_type, changed_files, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    str(repo_path),
                    commit_hash,
                    datetime.now().isoformat(),
                    files_count,
                    analysis_type,
                    changed_files,
                    status,
                ),
            )
            conn.commit()
            logger.info(
                f"Recorded analysis for {project_id}@{commit_hash[:8]}: "
                f"{files_count} files, type={analysis_type}"
            )
        except sqlite3.IntegrityError:
            logger.debug(f"Analysis already exists for {project_id}@{commit_hash[:8]}")
        finally:
            conn.close()

    def get_last_analysis(self, project_id: str) -> Optional[Dict]:
        """Get the most recent analysis for a project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT commit_hash, analysis_timestamp, files_count, analysis_type
            FROM project_analyses
            WHERE project_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT 1
            """,
            (project_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "commit_hash": row[0],
                "timestamp": row[1],
                "files_count": row[2],
                "analysis_type": row[3],
            }
        return None

    def get_history(self, project_id: str, limit: int = 10) -> List[Dict]:
        """Get analysis history for a project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT commit_hash, analysis_timestamp, files_count, analysis_type, changed_files, status
            FROM project_analyses
            WHERE project_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT ?
            """,
            (project_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "commit_hash": row[0][:8],
                "timestamp": row[1],
                "files_count": row[2],
                "analysis_type": row[3],
                "changed_files": row[4],
                "status": row[5],
            }
            for row in rows
        ]

    def cleanup_old_analyses(self, project_id: str, keep_last: int = 10):
        """Delete old analyses, keeping only the most recent N."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get IDs to keep
        cursor.execute(
            """
            SELECT id FROM project_analyses
            WHERE project_id = ?
            ORDER BY analysis_timestamp DESC
            LIMIT ?
            """,
            (project_id, keep_last),
        )

        keep_ids = [row[0] for row in cursor.fetchall()]

        if keep_ids:
            # Delete others
            placeholders = ",".join("?" * len(keep_ids))
            cursor.execute(
                f"""
                DELETE FROM project_analyses
                WHERE project_id = ? AND id NOT IN ({placeholders})
                """,
                [project_id] + keep_ids,
            )
        else:
            # No analyses to keep, delete all
            cursor.execute(
                "DELETE FROM project_analyses WHERE project_id = ?", (project_id,)
            )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up {deleted} old analyses for project {project_id}")
        return deleted

    def clear_project(self, project_id: str):
        """Delete all analyses for a project."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM project_analyses WHERE project_id = ?", (project_id,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleared {deleted} analyses for project {project_id}")
        return deleted
