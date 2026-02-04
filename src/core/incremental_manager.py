"""
Incremental Analysis Manager

Handles skip-if-no-changes logic and changed files detection.
"""

import logging
from pathlib import Path
from typing import Optional, List, Set

from core.project_history import ProjectHistoryManager
from core.git_helper import GitHelper

logger = logging.getLogger(__name__)


class IncrementalAnalysisManager:
    """Manages incremental analysis strategy."""
    
    def __init__(self, repo_path: str):
        """
        Initialize incremental manager.
        
        Args:
            repo_path: Path to repository
        """
        self.repo_path = Path(repo_path)
        self.git_helper = GitHelper(repo_path)
        self.history_mgr = ProjectHistoryManager()
    
    def should_skip_analysis(self, project_id: str) -> tuple[bool, str]:
        """
        Check if analysis should be skipped (no changes).
        
        Returns:
            (should_skip: bool, reason: str)
        """
        # Check if git repo
        if not self.git_helper.is_repository():
            return False, "NOT_GIT_REPO"
        
        # Get current commit
        current_commit = self.git_helper.get_current_commit()
        if not current_commit:
            return False, "NO_COMMIT"
        
        # Check history
        should_reanalyze, reason = self.history_mgr.should_reanalyze(project_id, current_commit)
        
        if should_reanalyze:
            return False, reason
        else:
            return True, "NO_CHANGES"
    
    def get_changed_files(self, project_id: str) -> Optional[List[Path]]:
        """
        Get list of changed files since last analysis.
        
        Returns:
            List of changed file paths, or None if cannot determine
        """
        # Get last analysis
        last_analysis = self.history_mgr.get_last_analysis(project_id)
        if not last_analysis or not last_analysis.get('last_commit_hash'):
            return None
        
        # Get changed files from git
        last_commit = last_analysis['last_commit_hash']
        changed = self.git_helper.get_changed_files(last_commit)
        
        if changed is None:
            return None
        
        # Filter to only Python files
        changed_paths = [
            self.repo_path / f for f in changed 
            if f.endswith('.py') and (self.repo_path / f).exists()
        ]
        
        return changed_paths
    
    def get_affected_functions(
        self, 
        changed_files: List[Path], 
        project_id: str,
        neo4j_adapter
    ) -> Set[str]:
        """
        Get all functions affected by changes (using Neo4j call graph).
        
        Args:
            changed_files: List of changed Python files
            project_id: Project ID for database queries
            neo4j_adapter: Neo4j adapter instance
        
        Returns:
            Set of affected function node IDs
        """
        if not neo4j_adapter or not changed_files:
            return set()
        
        affected = set()
        
        try:
            with neo4j_adapter.driver.session() as session:
                for file_path in changed_files:
                    # Get all functions in changed file
                    result = session.run("""
                        MATCH (f:Function {file: $file_path, session_id: $project_id})
                        RETURN f.name as name
                    """, {
                        "file_path": str(file_path),
                        "project_id": project_id
                    })
                    
                    for record in result:
                        affected.add(record['name'])
                    
                    # Get all callers of functions in changed file
                    result = session.run("""
                        MATCH (f:Function {file: $file_path, session_id: $project_id})
                        <-[CALLS]-(caller:Function)
                        RETURN DISTINCT caller.name as name
                    """, {
                        "file_path": str(file_path),
                        "project_id": project_id
                    })
                    
                    for record in result:
                        affected.add(record['name'])
        
        except Exception as e:
            logger.error(f"Failed to get affected functions: {e}")
        
        return affected
