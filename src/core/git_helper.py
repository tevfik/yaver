"""
Git utilities for project analysis.

Provides commit tracking, diff detection, and history analysis.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


class GitHelper:
    """Git utilities for analysis integration."""
    
    def __init__(self, repo_path: str):
        """Initialize git helper for a repository."""
        self.repo_path = Path(repo_path)
    
    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception as e:
            logger.error(f"Failed to get current commit: {e}")
            return None
    
    def get_changed_files(self, since_commit: str) -> Optional[List[str]]:
        """
        Get files changed since a commit.
        
        Returns:
            List of file paths, or None if error
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{since_commit}..HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split('\n') if f]
            
            return None
        except Exception as e:
            logger.error(f"Failed to get changed files: {e}")
            return None
    
    def is_repository(self) -> bool:
        """Check if path is a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_commit_count(self) -> int:
        """Get total commit count."""
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            return int(result.stdout.strip()) if result.returncode == 0 else 0
        except Exception:
            return 0
    
    def is_ancestor(self, ancestor_commit: str, descendant_commit: str) -> bool:
        """Check if ancestor_commit is an ancestor of descendant_commit."""
        try:
            result = subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor_commit, descendant_commit],
                cwd=self.repo_path,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
