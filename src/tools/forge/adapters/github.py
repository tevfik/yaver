import requests
from typing import List, Dict, Any, Optional
from tools.forge.provider import ForgeProvider


class GitHubAdapter(ForgeProvider):
    """
    GitHub implementation of ForgeProvider.
    """

    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        self.base_url = "https://api.github.com"
        self.update_api_url()

    def update_api_url(self):
        self.api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

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
        url = f"{self.api_url}/issues/{issue_id}/comments"
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def add_comment_reaction(self, comment_id: int, reaction: str) -> Dict[str, Any]:
        # GitHub uses specific accept header for reactions
        url = f"{self.api_url}/issues/comments/{comment_id}/reactions"
        headers = {"Accept": "application/vnd.github.squirrel-girl-preview+json"}
        data = {"content": reaction}
        response = self.session.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def find_pr_by_branch(self, head: str, base: str) -> Optional[Dict[str, Any]]:
        url = f"{self.api_url}/pulls"
        params = {"state": "open", "head": f"{self.owner}:{head}", "base": base}
        response = self.session.get(url, params=params)
        if response.status_code == 200:
            prs = response.json()
            if prs:
                return prs[0]
        return None

    def get_user(self) -> Dict[str, Any]:
        url = f"{self.base_url}/user"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_repositories(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/user/repos"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def list_mentions(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/notifications"
        params = {"participating": "true"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_assigned_issues(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/issues"
        params = {"filter": "assigned", "state": "open"}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_review_requests(self) -> List[Dict[str, Any]]:
        """
        List PRs where review is requested from the authenticated user.
        Uses the search API: is:open is:pr review-requested:@me
        """
        url = f"{self.base_url}/search/issues"
        q = "is:open is:pr review-requested:@me"
        params = {"q": q}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json().get("items", [])
