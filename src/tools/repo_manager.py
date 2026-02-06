"""
Repository Manager - Auto-detect repository information from git

Responsible for:
- Reading git remote URL and extracting repo information
- Detecting current branch and commit hash
- Identifying project type and frameworks
"""

import logging
from pathlib import Path
from typing import Optional, List
import subprocess
import json

logger = logging.getLogger("agents.repo_manager")


class RepositoryManager:
    """Manage repository information and auto-detection"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / ".git"

        if not self.git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")

        logger.debug(f"RepositoryManager initialized for {self.repo_path}")

    def get_remote_url(self) -> str:
        """Get git remote origin URL"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get remote URL: {e}")

        return "unknown"

    def get_current_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get current branch: {e}")

        return "unknown"

    def get_current_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.warning(f"Could not get commit hash: {e}")

        return "unknown"

    def detect_project_type(self) -> str:
        """
        Detect project type based on configuration files.
        Returns: "python", "go", "rust", "nodejs", "java", etc.
        """

        # Check for Python
        if (
            (self.repo_path / "setup.py").exists()
            or (self.repo_path / "pyproject.toml").exists()
            or (self.repo_path / "requirements.txt").exists()
            or (self.repo_path / "Pipfile").exists()
        ):
            return "python"

        # Check for Go
        if (self.repo_path / "go.mod").exists():
            return "go"

        # Check for Rust
        if (self.repo_path / "Cargo.toml").exists():
            return "rust"

        # Check for Node.js
        if (self.repo_path / "package.json").exists():
            return "nodejs"

        # Check for Java
        if (self.repo_path / "pom.xml").exists() or (
            self.repo_path / "build.gradle"
        ).exists():
            return "java"

        # Check for C#
        if (self.repo_path / "*.csproj").exists() or (
            self.repo_path / "*.sln"
        ).exists():
            return "csharp"

        return "unknown"

    def detect_frameworks(self) -> List[str]:
        """
        Detect frameworks used in the project.
        Returns: ["django", "fastapi", "numpy", "torch", etc.]
        """
        frameworks = []

        # Python frameworks
        requirements_files = [
            self.repo_path / "requirements.txt",
            self.repo_path / "requirements-dev.txt",
            self.repo_path / "setup.py",
            self.repo_path / "pyproject.toml",
        ]

        for req_file in requirements_files:
            if not req_file.exists():
                continue

            try:
                content = req_file.read_text()

                # Common Python frameworks
                if "django" in content.lower():
                    frameworks.append("django")
                if "fastapi" in content.lower():
                    frameworks.append("fastapi")
                if "flask" in content.lower():
                    frameworks.append("flask")
                if "numpy" in content.lower():
                    frameworks.append("numpy")
                if "pandas" in content.lower():
                    frameworks.append("pandas")
                if "torch" in content.lower() or "pytorch" in content.lower():
                    frameworks.append("pytorch")
                if "tensorflow" in content.lower():
                    frameworks.append("tensorflow")
                if "sqlalchemy" in content.lower():
                    frameworks.append("sqlalchemy")
                if "pydantic" in content.lower():
                    frameworks.append("pydantic")

            except Exception as e:
                logger.warning(f"Could not read {req_file}: {e}")

        # Go frameworks
        go_mod = self.repo_path / "go.mod"
        if go_mod.exists():
            try:
                content = go_mod.read_text()
                if "gin" in content:
                    frameworks.append("gin")
                if "echo" in content:
                    frameworks.append("echo")
                if "gorm" in content:
                    frameworks.append("gorm")
            except Exception as e:
                logger.warning(f"Could not read go.mod: {e}")

        # Node.js frameworks
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())
                deps = content.get("dependencies", {})
                dev_deps = content.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}

                if "react" in all_deps:
                    frameworks.append("react")
                if "next" in all_deps:
                    frameworks.append("next.js")
                if "express" in all_deps:
                    frameworks.append("express")
                if "nestjs" in all_deps or "@nestjs/core" in all_deps:
                    frameworks.append("nestjs")
                if "vue" in all_deps:
                    frameworks.append("vue")
                if "angular" in all_deps or "@angular/core" in all_deps:
                    frameworks.append("angular")
                if "tensorflow" in all_deps or "tf.js" in all_deps:
                    frameworks.append("tensorflow.js")
            except Exception as e:
                logger.warning(f"Could not read package.json: {e}")

        return list(set(frameworks))  # Remove duplicates

    @property
    def remote_url(self) -> str:
        """Cached property: remote URL"""
        if not hasattr(self, "_remote_url"):
            self._remote_url = self.get_remote_url()
        return self._remote_url

    @property
    def current_branch(self) -> str:
        """Cached property: current branch"""
        if not hasattr(self, "_current_branch"):
            self._current_branch = self.get_current_branch()
        return self._current_branch

    @property
    def current_commit(self) -> str:
        """Cached property: current commit"""
        if not hasattr(self, "_current_commit"):
            self._current_commit = self.get_current_commit()
        return self._current_commit

    @property
    def project_type(self) -> str:
        """Cached property: project type"""
        if not hasattr(self, "_project_type"):
            self._project_type = self.detect_project_type()
        return self._project_type

    @property
    def frameworks(self) -> List[str]:
        """Cached property: detected frameworks"""
        if not hasattr(self, "_frameworks"):
            self._frameworks = self.detect_frameworks()
        return self._frameworks

    def get_info(self) -> dict:
        """Get all repository information"""
        return {
            "path": str(self.repo_path),
            "remote_url": self.remote_url,
            "current_branch": self.current_branch,
            "current_commit": self.current_commit,
            "project_type": self.project_type,
            "frameworks": self.frameworks,
        }
