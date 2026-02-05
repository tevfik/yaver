"""
Git Analyzer - Analyzes git repositories
"""

from pathlib import Path
from typing import Optional, Dict, List, Any
import subprocess
from pydantic import BaseModel, Field
from tools.base import Tool


class GitClientSchema(BaseModel):
    command: str = Field(
        ..., description="Git operation: 'status', 'log', 'branch', 'diff', 'ls'"
    )
    arg: Optional[str] = Field(
        None, description="Optional argument (e.g. commit hash for diff)"
    )


class GitClient(Tool):
    """
    Analyzes git repositories for commits, changes, and history.
    """

    name = "git_client"
    description = "Read-only Git operations (status, log, diff, ls)"
    args_schema = GitClientSchema

    def run(self, command: str, arg: Optional[str] = None, **kwargs) -> Any:
        """Execute git command (wrapper for methods)."""
        mapping = {
            "status": "get_status",
            "log": "get_commits",
            "branch": "get_branch",
            "diff": "get_changed_files_since",
            "ls": "list_files",
        }

        method_name = mapping.get(command, command)
        method = getattr(self, method_name, None)

        if method:
            # Fix for diff without args
            if command == "diff":
                if arg:
                    return method(arg)
                return self.get_status()  # Fallback to status if no commit hash

            return method()

        return {"error": f"Unknown command: {command}"}

    def list_files(self) -> List[str]:
        """List tracked files."""
        if not self.is_git_repo:
            # Fallback to os walk
            return [
                str(p)
                for p in self.repo_path.rglob("*")
                if p.is_file() and ".git" not in str(p)
            ]

        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return result.stdout.splitlines()
        except Exception:
            return []

    def __init__(self, repo_path: Optional[str] = None):
        """Initialize git analyzer"""
        self.repo_path = Path(repo_path or ".")
        self.is_git_repo = (self.repo_path / ".git").exists()

    def get_status(self) -> Dict[str, Any]:
        """Get git repository status"""
        if not self.is_git_repo:
            return {"error": "Not a git repository"}

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            return {
                "status": "ok",
                "changes": result.stdout,
                "is_clean": result.returncode == 0 and not result.stdout,
                "active_branch": self.get_branch(),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_commits(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits"""
        if not self.is_git_repo:
            return []

        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            commits = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(" ", 1)
                    commits.append(
                        {
                            "hash": parts[0],
                            "message": parts[1] if len(parts) > 1 else "",
                        }
                    )

            return commits
        except Exception:
            return []

    def get_branch(self) -> Optional[str]:
        """Get current branch"""
        if not self.is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            return result.stdout.strip()
        except Exception:
            return None

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash"""
        if not self.is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            return result.stdout.strip()
        except Exception:
            return None

    def get_changed_files_since(self, commit_hash: str) -> List[str]:
        """Get list of files changed since a specific commit"""
        if not self.is_git_repo:
            return []

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            return [f for f in result.stdout.splitlines() if f.strip()]
        except Exception:
            return []

    def get_remotes(self) -> List[str]:
        """Get configured remotes"""
        if not self.is_git_repo:
            return []

        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )

            remotes = set()
            for line in result.stdout.strip().split("\n"):
                if line:
                    remotes.add(line.split()[0])

            return list(remotes)
        except Exception:
            return []

    def get_remote_url(self, remote: str = "origin") -> Optional[str]:
        """Get URL for a specific remote."""
        if not self.is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "remote", "get-url", remote],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
