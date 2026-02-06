import requests
from typing import List, Dict, Any, Optional
from tools.forge.provider import ForgeProvider


class GitLabAdapter(ForgeProvider):
    """
    GitLab implementation of ForgeProvider.
    """

    def __init__(self, base_url: str, token: str, project_id: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.project_id = project_id  # GitLab uses int IDs or URL-encoded path
        self.session = requests.Session()
        self.session.headers.update(
            {"Private-Token": self.token, "Content-Type": "application/json"}
        )
        self.api_url = f"{self.base_url}/api/v4/projects/{self.project_id}"

    def create_pr(self, title: str, body: str, head: str, base: str) -> Dict[str, Any]:
        url = f"{self.api_url}/merge_requests"
        data = {
            "title": title,
            "description": body,
            "source_branch": head,
            "target_branch": base,
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_pr(self, pr_id: int) -> Dict[str, Any]:
        url = f"{self.api_url}/merge_requests/{pr_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_issues(self, state: str = "opened") -> List[Dict[str, Any]]:
        url = f"{self.api_url}/issues"
        params = {"state": state}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_issue(self, title: str, body: str) -> Dict[str, Any]:
        url = f"{self.api_url}/issues"
        data = {"title": title, "description": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def list_issue_comments(self, issue_id: int) -> List[Dict[str, Any]]:
        url = f"{self.api_url}/issues/{issue_id}/notes"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def create_issue_comment(self, issue_id: int, body: str) -> Dict[str, Any]:
        url = f"{self.api_url}/issues/{issue_id}/notes"
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def add_comment_reaction(self, comment_id: int, reaction: str) -> Dict[str, Any]:
        # GitLab comments are 'notes'. This assumes project-level issue notes.
        # Note: Logic differs for MR notes.
        url = f"{self.api_url}/issues/notes/{comment_id}/award_emoji"
        data = {"name": reaction}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def find_pr_by_branch(self, head: str, base: str) -> Optional[Dict[str, Any]]:
        url = f"{self.api_url}/merge_requests"
        params = {"state": "opened", "source_branch": head, "target_branch": base}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            mrs = response.json()
            if mrs:
                return mrs[0]
        return None

    def get_user(self) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v4/user"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_repositories(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v4/projects"
        params = {"membership": "true"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_mentions(self) -> List[Dict[str, Any]]:
        # GitLab doesn't have a direct 'mentions' endpoint, closest is Todos
        url = f"{self.base_url}/api/v4/todos"
        params = {"action": "mentioned", "state": "pending"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_assigned_issues(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v4/issues"
        params = {"scope": "assigned_to_me", "state": "opened"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
