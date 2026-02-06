from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ForgeProvider(ABC):
    """
    Abstract Base Class for Git Forge Providers (GitHub, Gitea, GitLab).
    """

    @abstractmethod
    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        """Create a Pull Request."""
        pass

    @abstractmethod
    def get_pr(self, pr_id: int) -> Dict[str, Any]:
        """Get details of a Pull Request."""
        pass

    @abstractmethod
    def list_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in the repository."""
        pass

    @abstractmethod
    def create_issue(self, title: str, body: str) -> Dict[str, Any]:
        """Create a new issue."""
        pass

    @abstractmethod
    def create_issue_comment(self, issue_id: int, body: str) -> Dict[str, Any]:
        """Add a comment to an issue or PR."""
        pass

    def set_repo(self, owner: str, repo: str):
        """Switch the provider context to a different repository."""
        self.owner = owner
        self.repo = repo
        # Implementations should update their API URLs accordingly

    @abstractmethod
    def add_issue_reaction(self, issue_id: int, reaction: str) -> Dict[str, Any]:
        """Add a reaction to an issue."""
        pass

    @abstractmethod
    def get_issue_reactions(self, issue_id: int) -> List[Dict[str, Any]]:
        """Get reactions for an issue."""
        pass

    @abstractmethod
    def find_pr_by_branch(self, head: str, base: str) -> Optional[Dict[str, Any]]:
        """Find an existing PR by head and base branch names."""
        pass

    @abstractmethod
    def list_repositories(self) -> List[Dict[str, Any]]:
        """List repositories the user can access."""
        pass

    @abstractmethod
    def list_mentions(self) -> List[Dict[str, Any]]:
        """List recent mentions of the authenticated user."""
        pass

    @abstractmethod
    def list_assigned_issues(self) -> List[Dict[str, Any]]:
        """List issues assigned to the authenticated user."""
        pass

    @abstractmethod
    def list_review_requests(self) -> List[Dict[str, Any]]:
        """List PRs where review is requested from the authenticated user."""
        pass

    @abstractmethod
    def get_user(self) -> Dict[str, Any]:
        """Get the authenticated user info."""
        pass
