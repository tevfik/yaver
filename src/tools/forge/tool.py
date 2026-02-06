from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger("yaver")

from tools.base import Tool
from tools.forge.provider import ForgeProvider
from tools.forge.adapters.gitea import GiteaAdapter
from config.config import (
    FORGE_PROVIDER,
    FORGE_URL,
    FORGE_TOKEN,
    FORGE_OWNER,
    FORGE_REPO,
)


class ForgeToolSchema(BaseModel):
    command: str = Field(
        ...,
        description="Forge operation: 'create_pr', 'list_issues', 'get_pr', 'comment_issue'",
    )
    title: Optional[str] = Field(None, description="Title for PR")
    body: Optional[str] = Field(None, description="Body for PR or comment")
    head: Optional[str] = Field(
        None, description="Head branch for PR (e.g. feature-branch)"
    )
    base: Optional[str] = Field(None, description="Base branch for PR (e.g. main)")
    issue_id: Optional[int] = Field(
        None, description="Issue or PR ID for comments/details"
    )
    comment_id: Optional[int] = Field(None, description="Comment ID for reactions")
    reaction: Optional[str] = Field(
        None, description="Reaction content (e.g. '+1', 'eyes')"
    )
    owner: Optional[str] = Field(None, description="Owner name (for set_repo)")
    repo: Optional[str] = Field(None, description="Repo name (for set_repo)")


class ForgeTool(Tool):
    """
    Tool for interacting with remote Git forges (Gitea/GitHub).
    """

    name = "forge_tool"
    description = (
        "Interact with remote Git forge (Gitea/GitHub) to manage PRs and Issues."
    )
    args_schema = ForgeToolSchema

    def __init__(self, repo_path: Optional[str] = None):
        self.provider: Optional[ForgeProvider] = None
        self.repo_path = repo_path or "."
        self._initialize_provider()

    def _initialize_provider(self):
        # 1. Try Dynamic Detection from Git Config
        try:
            from tools.git.client import GitClient
            from tools.forge.credential_manager import CredentialManager

            git = GitClient(repo_path=self.repo_path)
            remote_url = git.get_remote_url()

            if remote_url:
                creds = CredentialManager()
                host = creds.detect_host_from_url(remote_url)

                if host:
                    config = creds.get_host_config(host)
                    if config and config.provider == "gitea":
                        # Ensure we handle .git suffix correctly without stripping repo name characters
                        url_path = remote_url
                        if url_path.endswith(".git"):
                            url_path = url_path[:-4]

                        parts = url_path.split("/")
                        repo = parts[-1]
                        owner = parts[-2]

                        api_url = config.api_url or f"https://{host}"
                        self.provider = GiteaAdapter(api_url, config.token, owner, repo)
                        return
                    elif config and config.provider == "github":
                        from tools.forge.adapters.github import GitHubAdapter

                        # GitHub URLs often match host=github.com
                        parts = remote_url.replace(".git", "").split("/")
                        repo = parts[-1]
                        owner = parts[-2]
                        self.provider = GitHubAdapter(config.token, owner, repo)
                        return
                    elif config and config.provider == "gitlab":
                        from tools.forge.adapters.gitlab import GitLabAdapter

                        # GitLab logic, usually requires project ID or path encoding
                        # For simplicity, we assume path-based project ID here or config-provided project ID
                        # If project ID isn't in URL, we might need a lookup or config
                        # Using path as ID (URL encoded) is common in GitLab API
                        parts = remote_url.replace(".git", "").split("/")
                        # owner/repo -> owner%2Frepo
                        project_path = "/".join(parts[-2:])
                        project_id = project_path.replace("/", "%2F")

                        api_url = config.api_url or f"https://{host}"
                        self.provider = GitLabAdapter(api_url, config.token, project_id)
                        return
        except ImportError:
            pass  # Dependencies might not be ready

        # 2. Fallback to Environment Variables (Legacy/Single Mode)
        # Check explicit globals first (highest priority if set manually in env)
        if FORGE_PROVIDER == "gitea":
            if FORGE_URL and FORGE_TOKEN:
                self.provider = GiteaAdapter(
                    FORGE_URL, FORGE_TOKEN, FORGE_OWNER, FORGE_REPO
                )
                return

        # 3. Fallback: Try to use hosts.json default even if not inside a git repo
        # This allows 'yaver social run' to work from anywhere using the first configured host
        try:
            from tools.forge.credential_manager import CredentialManager

            creds = CredentialManager()
            if creds.hosts:
                # Pick the first one or one matching FORGE_PROVIDER if set
                # Ideally we check if user wants this behavior, but for 'social agent' it makes sense
                # to monitor *something* rather than fail.

                # Logic: If FORGE_URL matches a known host, use that config
                target_host = None

                if FORGE_URL:
                    # Try to match URL to host key
                    for h_key, h_cfg in creds.hosts.items():
                        if h_key in FORGE_URL:
                            target_host = h_key
                            break

                if not target_host and creds.hosts:
                    # Default: Use the first one
                    target_host = next(iter(creds.hosts))

                if target_host:
                    config = creds.get_host_config(target_host)
                    if config and config.provider == "gitea":
                        self.provider = GiteaAdapter(
                            config.api_url, config.token, config.default_owner, "yaver"
                        )  # Default repo?
                        # Wait, we can't guess repo name globally without context.
                        # BUT list_repositories command doesn't need repo name!
                        # So we can init with None/Dummy repo name if we only plan to list repos.

                        # Let's verify valid repo needed?
                        # GiteaAdapter __init__ requires owner/repo.
                        # But list_repositories uses /user/repos which is repo-agnostic.
                        # We can pass dummy values if we just want to list.

                        repo_name = FORGE_REPO or "yaver"
                        owner_name = config.default_owner or FORGE_OWNER or "tevfik"

                        self.provider = GiteaAdapter(
                            config.api_url, config.token, owner_name, repo_name
                        )
        except Exception:
            pass

    def run(self, command: str, **kwargs) -> Any:
        if not self.provider:
            return "Error: Forge provider not configured. Check FORGE_PROVIDER, FORGE_URL, and FORGE_TOKEN in config."

        try:
            if command == "create_pr":
                return self.provider.create_pr(
                    kwargs.get("title"),
                    kwargs.get("body"),
                    kwargs.get("head"),
                    kwargs.get("base"),
                )
            elif command == "list_issues":
                return self.provider.list_issues()
            elif command == "list_assigned_issues":
                return self.provider.list_assigned_issues()
            elif command == "list_review_requests":
                return self.provider.list_review_requests()
            elif command == "list_mentions":
                return self.provider.list_mentions()
            elif command == "list_repositories":
                return self.provider.list_repositories()
            elif command == "create_issue":
                return self.provider.create_issue(
                    kwargs.get("title"), kwargs.get("body")
                )
            elif command == "get_pr":
                return self.provider.get_pr(kwargs.get("issue_id"))
            elif command == "list_comments":
                return self.provider.list_issue_comments(kwargs.get("issue_id"))
            elif command == "comment_issue":
                return self.provider.create_issue_comment(
                    kwargs.get("issue_id"), kwargs.get("body")
                )
            elif command == "add_reaction":
                # Support both issue and comment reactions
                if kwargs.get("comment_id"):
                    return self.provider.add_comment_reaction(
                        kwargs.get("comment_id"), kwargs.get("reaction")
                    )
                else:
                    return self.provider.add_issue_reaction(
                        kwargs.get("issue_id"), kwargs.get("reaction")
                    )
            elif command == "get_issue_reactions":
                return self.provider.get_issue_reactions(kwargs.get("issue_id"))
            elif command == "find_pr_by_branch":
                return self.provider.find_pr_by_branch(
                    kwargs.get("head"), kwargs.get("base")
                )
            elif command == "get_user":
                return self.provider.get_user()
            elif command == "list_repositories":
                return self.provider.list_repositories()
            elif command == "list_mentions":
                return self.provider.list_mentions()
            elif command == "list_assigned_issues":
                return self.provider.list_assigned_issues()
            elif command == "set_repo":
                self.provider.set_repo(kwargs.get("owner"), kwargs.get("repo"))
                return f"Switched context to {kwargs.get('owner')}/{kwargs.get('repo')}"
            else:
                return f"Error: Unknown command '{command}'"
        except Exception as e:
            return f"Error executing {command}: {str(e)}"
