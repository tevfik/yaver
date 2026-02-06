import requests
from typing import List, Dict, Any, Optional
from tools.forge.provider import ForgeProvider


class GiteaAdapter(ForgeProvider):
    """
    Gitea implementation of ForgeProvider using requests.
    """

    def __init__(self, base_url: str, token: str, owner: str, repo: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )
        self.update_api_url()

    def update_api_url(self):
        self.api_url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}"

    def set_repo(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo
        self.update_api_url()

    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        url = f"{self.api_url}/pulls"
        data = {"title": title, "body": body, "head": head, "base": base}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_pr(self, pr_id: int) -> Dict[str, Any]:
        url = f"{self.api_url}/pulls/{pr_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_issues(self, state: str = "open") -> List[Dict[str, Any]]:
        """List issues in the repository."""
        url = f"{self.api_url}/issues"
        params = {"state": state}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_issue(self, title: str, body: str) -> Dict[str, Any]:
        url = f"{self.api_url}/issues"
        data = {"title": title, "body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def list_issue_comments(self, issue_id: int) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/issues/{issue_id}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def create_issue_comment(self, issue_id: int, body: str) -> Dict[str, Any]:
        # Gitea treats PRs as issues for comments
        url = f"{self.api_url}/issues/{issue_id}/comments"
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def add_issue_reaction(self, issue_id: int, reaction: str) -> Dict[str, Any]:
        url = f"{self.api_url}/issues/{issue_id}/reactions"
        data = {"content": reaction}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_issue_reactions(self, issue_id: int) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/issues/{issue_id}/reactions"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def add_comment_reaction(self, comment_id: int, reaction: str) -> Dict[str, Any]:
        # Gitea reaction API
        url = f"{self.api_url}/issues/comments/{comment_id}/reactions"
        data = {"content": reaction}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def find_pr_by_branch(self, head: str, base: str) -> Optional[Dict[str, Any]]:
        """Find an existing PR by head and base branch names."""
        url = f"{self.api_url}/pulls"
        params = {"state": "open"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        prs = response.json()

        for pr in prs:
            # Gitea PR head and base branches are often simple strings or full refs
            # We check both to be safe
            pr_head = pr.get("head", {}).get("label", "")
            pr_base = pr.get("base", {}).get("label", "")

            # Label format is often 'owner:branch' or just 'branch'
            if (head in pr_head or pr_head in head) and (
                base in pr_base or pr_base in base
            ):
                return pr
        return None

    def get_user(self) -> Dict[str, Any]:
        """Get the authenticated user info."""
        url = f"{self.base_url}/api/v1/user"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_repositories(self) -> List[Dict[str, Any]]:
        """List repositories the user can access."""
        url = f"{self.base_url}/api/v1/user/repos"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_mentions(self) -> List[Dict[str, Any]]:
        """List recent mentions (simulated in Gitea via notifications or keyword search if needed)."""
        # Gitea doesn't have a direct 'mentions' endpoint like GitHub, but it has notifications
        url = f"{self.base_url}/api/v1/notifications"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_assigned_issues(self) -> List[Dict[str, Any]]:
        """List issues assigned to the user."""
        # Gitea doesn't have a cross-repo assigned issues endpoint in API v1 directly for user easily
        # but we can filter the user's repos issues.
        # For now, we list issues in the current repo assigned to the user.
        try:
            user = self.get_user()
            username = user.get("login") or user.get("username")
            url = f"{self.api_url}/issues"
            params = {"assigned_to": username, "state": "open"}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # Fallback or log error
            return []

    def list_review_requests(self) -> List[Dict[str, Any]]:
        """List review requests (Gitea)."""
        # Gitea doesn't have a global review request endpoint in v1.
        # We can search in the current repo.
        try:
            url = f"{self.api_url}/pulls"
            # Gitea API often doesn't filter by review_requested directly in standard v1 list,
            # but we can fetch open PRs and check 'requested_reviewers'.
            # This is inefficient for large repos but workable for MVP.
            params = {"state": "open"}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            prs = response.json()

            user = self.get_user()
            username = user.get("login") or user.get("username")

            my_reviews = []
            for pr in prs:
                requested = pr.get("requested_reviewers", [])
                if any(r.get("login") == username for r in requested):
                    my_reviews.append(pr)
            return my_reviews

        except Exception:
            return []
