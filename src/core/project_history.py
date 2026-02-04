"""
Project Analysis History Manager

Tracks analysis history for each project using SQLite.
Enables incremental updates based on git history.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectHistoryManager:
    """Manages project analysis metadata and history."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize history manager.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.yaver/analysis_history.db
        """
        if db_path is None:
            db_path = Path.home() / ".yaver" / "analysis_history.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    analysis_timestamp DATETIME NOT NULL,
                    analysis_type TEXT NOT NULL,
                    files_count INTEGER,
                    files_analyzed INTEGER,
                    duration_seconds REAL,
                    UNIQUE(project_id, commit_hash)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_metadata (
                    project_id TEXT PRIMARY KEY,
                    repo_path TEXT NOT NULL,
                    last_commit_hash TEXT,
                    last_analysis_timestamp DATETIME,
                    total_analyses INTEGER DEFAULT 0
                )
            """)
            
            conn.commit()
    
    def record_analysis(
        self, 
        project_id: str, 
        repo_path: str, 
        commit_hash: str,
        analysis_type: str = "full",
        files_count: int = 0,
        files_analyzed: int = 0,
        duration_seconds: float = 0.0
    ):
        """Record a completed analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Insert analysis record
                conn.execute("""
                    INSERT INTO project_analyses 
                    (project_id, repo_path, commit_hash, analysis_timestamp, 
                     analysis_type, files_count, files_analyzed, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id, repo_path, commit_hash, datetime.now().isoformat(),
                    analysis_type, files_count, files_analyzed, duration_seconds
                ))
                
                # Update metadata
                conn.execute("""
                    INSERT INTO project_metadata 
                    (project_id, repo_path, last_commit_hash, last_analysis_timestamp, total_analyses)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(project_id) DO UPDATE SET
                        last_commit_hash = ?,
                        last_analysis_timestamp = ?,
                        total_analyses = total_analyses + 1
                """, (
                    project_id, repo_path, commit_hash, datetime.now().isoformat(),
                    commit_hash, datetime.now().isoformat()
                ))
                
                conn.commit()
                logger.info(f"Recorded analysis for {project_id} @ {commit_hash}")
        except Exception as e:
            logger.error(f"Failed to record analysis: {e}")
    
    def get_last_analysis(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get last analysis metadata for a project."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM project_metadata WHERE project_id = ?
                """, (project_id,))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get last analysis: {e}")
            return None
    
    def get_history(self, project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get analysis history for a project."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM project_analyses 
                    WHERE project_id = ? 
                    ORDER BY analysis_timestamp DESC 
                    LIMIT ?
                """, (project_id, limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM project_metadata 
                    ORDER BY last_analysis_timestamp DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get projects: {e}")
            return []
    
    def cleanup_old_analyses(self, project_id: str, keep_last: int = 10):
        """Delete old analyses, keeping only the last N."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get IDs of analyses to keep
                cursor = conn.execute("""
                    SELECT id FROM project_analyses 
                    WHERE project_id = ? 
                    ORDER BY analysis_timestamp DESC 
                    LIMIT ?
                """, (project_id, keep_last))
                
                ids_to_keep = [row[0] for row in cursor.fetchall()]
                
                # Delete all others
                if ids_to_keep:
                    placeholders = ",".join("?" * len(ids_to_keep))
                    conn.execute(f"""
                        DELETE FROM project_analyses 
                        WHERE project_id = ? AND id NOT IN ({placeholders})
                    """, [project_id] + ids_to_keep)
                else:
                    # No records to keep, delete all
                    conn.execute("""
                        DELETE FROM project_analyses WHERE project_id = ?
                    """, (project_id,))
                
                conn.commit()
                deleted_count = conn.total_changes
                logger.info(f"Deleted {deleted_count} old analyses for {project_id}")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup analyses: {e}")
            return 0
    
    def should_reanalyze(self, project_id: str, current_commit: str) -> tuple[bool, str]:
        """
        Check if project needs reanalysis.
        
        Returns:
            (should_reanalyze: bool, reason: str)
        """
        last_analysis = self.get_last_analysis(project_id)
        
        if not last_analysis or not last_analysis.get('last_commit_hash'):
            return True, "FIRST_TIME"
        
        if last_analysis['last_commit_hash'] == current_commit:
            return False, "NO_CHANGES"
        
        return True, "NEW_COMMIT"
