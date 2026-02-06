"""
Git Operations Module
Handles branching, committing, and PR simulation for Yaver Agents.
"""
import os
import logging
from typing import Any
from git import Repo, Actor
from datetime import datetime
import requests
import re
from config.config import get_config
from tools.base import Tool

logger = logging.getLogger("agents")


class GitOps(Tool):
    name = "git_ops"
    description = "Git operations (commit, push, pr)"

    def run(self, command: str, **kwargs) -> Any:
        method = getattr(self, command, None)
        if method:
            return method(**kwargs)
        return {"error": f"Unknown command: {command}"}

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        try:
            self.repo = Repo(repo_path)
            self.actor = Actor("Yaver AI", "agent@yaver.ai")
        except Exception as e:
            logger.warning(f"Failed to initialize Git repo at {repo_path}: {e}")
            self.repo = None

    def create_pr_branch(self, task_name: str) -> str:
        """Creates a new branch for the task."""
        if not self.repo:
            return None

        # Sanitize branch name
        slug = "".join(c if c.isalnum() else "-" for c in task_name.lower())[:30]
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        branch_name = f"yaver/feature/{slug}-{timestamp}"

        try:
            current = self.repo.active_branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"Switched to new branch: {branch_name}")
            return branch_name
        except Exception as e:
            logger.error(f"Git branch error: {e}")
            return None

    def commit_changes(self, file_path: str, message: str):
        """Stages and commits the specific file."""
        if not self.repo:
            return

        try:
            self.repo.index.add([file_path])
            self.repo.index.commit(message, author=self.actor, committer=self.actor)
            logger.info(f"Committed changes to {file_path}")
        except Exception as e:
            logger.error(f"Git commit error: {e}")

    def push_changes(self, branch_name: str) -> bool:
        """Pushes the branch to remote, injecting token if available for HTTPS."""
        if not self.repo:
            return False

        try:
            # 1. Get raw remote URL
            origin = self.repo.remote(name="origin")
            remote_url = origin.url

            # 2. Check for Token via CredentialManager
            auth_url = None
            try:
                from tools.forge.credential_manager import CredentialManager

                creds = CredentialManager()
                host = creds.detect_host_from_url(remote_url)

                if host and remote_url.startswith("https://"):
                    config = creds.get_host_config(host)
                    if config and config.token:
                        # Construct URL: https://<TOKEN>@domain/owner/repo.git
                        # Note: remote_url is like https://domain/owner/repo.git
                        # We strip https:// and prepend https://token@
                        clean_url = remote_url.replace("https://", "", 1)
                        auth_url = f"https://{config.token}@{clean_url}"
                        logger.info(f"Using authenticated push for host: {host}")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"Credential lookup failed: {e}")

            # 3. Push
            if auth_url:
                # Use git command directly for custom URL push
                self.repo.git.push(auth_url, branch_name)
            else:
                # Standard push (SSH or unauthenticated)
                origin.push(branch_name)

            logger.info(f"Pushed branch {branch_name} to origin")
            return True
        except Exception as e:
            logger.error(f"Git push error: {e}")
            return False

    def create_pull_request(
        self, branch_name: str, title: str, body: str, base: str = "main"
    ) -> str:
        """Creates a PR on GitHub."""
        config = get_config()
        token = config.git.github_token

        if not token:
            logger.warning("No GITHUB_TOKEN configured. Cannot create PR.")
            return None

        # Get owner/repo from remote URL
        try:
            remote_url = self.repo.remotes.origin.url
            # Parse owner/repo from https://github.com/owner/repo.git or git@github.com:owner/repo.git
            match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remote_url)
            if not match:
                logger.error(f"Could not parse GitHub repo from {remote_url}")
                return None

            owner, repo = match.groups()
            repo = repo.replace(".git", "")  # Cleanup

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            data = {"title": title, "body": body, "head": branch_name, "base": base}

            resp = requests.post(url, json=data, headers=headers)
            resp.raise_for_status()
            pr_data = resp.json()
            pr_url = pr_data.get("html_url", "unknown")
            logger.info(f"PR Created: {pr_url}")
            return pr_url

        except Exception as e:
            logger.error(f"Failed to create PR: {e}")
            return None
