import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
from pydantic import BaseModel


class ForgeHostConfig(BaseModel):
    provider: str
    token: str
    api_url: Optional[str] = None
    default_owner: Optional[str] = None


class CredentialManager:
    """
    Manages credentials for multiple Forge hosts.
    Stores config in ~/.yaver/hosts.json
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".yaver"
        self.hosts_file = self.config_dir / "hosts.json"
        self._ensure_config_dir()
        self.hosts: Dict[str, ForgeHostConfig] = self._load_hosts()

    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _load_hosts(self) -> Dict[str, ForgeHostConfig]:
        if not self.hosts_file.exists():
            return {}
        try:
            with open(self.hosts_file, "r") as f:
                data = json.load(f)
                return {
                    host: ForgeHostConfig(**cfg)
                    for host, cfg in data.get("hosts", {}).items()
                }
        except Exception as e:
            print(f"Error loading hosts.json: {e}")
            return {}

    def save_host(self, domain: str, config: ForgeHostConfig):
        """Save or update a host configuration."""
        self.hosts[domain] = config
        self._save_to_disk()

    def get_host_config(self, domain: str) -> Optional[ForgeHostConfig]:
        """Get config for a specific domain."""
        return self.hosts.get(domain)

    def _save_to_disk(self):
        data = {
            "hosts": {
                host: cfg.model_dump(exclude_none=True)
                for host, cfg in self.hosts.items()
            }
        }
        with open(self.hosts_file, "w") as f:
            json.dump(data, f, indent=2)

    def detect_host_from_url(self, remote_url: str) -> Optional[str]:
        """
        Extracts domain from a git remote URL and checks if it exists in config.
        Supports:
        - https://github.com/user/repo.git -> github.com
        - git@gitea.company.com:user/repo.git -> gitea.company.com
        """
        if "@" in remote_url:
            # SSH: git@domain:user/repo
            part = remote_url.split("@")[1]
            domain = part.split(":")[0]
        elif "://" in remote_url:
            # HTTP: https://domain/user/repo OR https://user:pass@domain/user/repo
            part = remote_url.split("://")[1]
            domain_with_auth = part.split("/")[0]
            if "@" in domain_with_auth:
                domain = domain_with_auth.split("@")[1]
            else:
                domain = domain_with_auth
        else:
            return None

        # Check against known hosts
        if domain in self.hosts:
            return domain

        # Try to find a partial match (e.g. github.com)
        for host in self.hosts:
            if host in domain or domain in host:
                return host

        return None
