"""
Unified Analysis Engine
Refactored from git_analysis.py
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from tools.base import Tool
from tools.analysis.parser import CodeParser
from tools.analysis.graph import GraphIndexer, ImpactAnalyzer

logger = logging.getLogger("tools.analysis.engine")


class RepoManager:
    """Manages Git repository operations with caching."""

    def __init__(self, cache_dir: str = "./cache/git_repos", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_repo(self, repo_source: str) -> Dict[str, Any]:
        """Get repository (clone or usage local)."""
        if os.path.exists(repo_source):
            return {"path": str(Path(repo_source).resolve()), "type": "local"}

        # Remote repo logic
        repo_hash = hashlib.md5(repo_source.encode()).hexdigest()
        target_path = self.cache_dir / repo_hash

        if target_path.exists():
            # In a real app, check TTL here
            logger.info(f"Using cached repo at {target_path}")
            return {"path": str(target_path), "type": "cached"}

        logger.info(f"Cloning {repo_source} to {target_path}...")
        # Use simple git clone for now
        os.system(f"git clone {repo_source} {target_path}")
        return {"path": str(target_path), "type": "cloned"}


from pydantic import BaseModel, Field


class AnalysisEngineSchema(BaseModel):
    repo_source: str = Field(
        ".", description="Path to repository (default: current dir)"
    )
    analysis_type: str = Field(
        "overview", description="Type: 'overview', 'structure', 'graph_index'"
    )


class AnalysisEngine(Tool):
    """
    Main entry point for static analysis.
    Combines Parser, GraphIndexer, and ImpactAnalyzer.
    """

    name = "analysis_engine"
    description = "Static analysis engine (overview, structure, impact)"
    args_schema = AnalysisEngineSchema

    def __init__(self):
        self.repo_manager = RepoManager()
        self.parser = CodeParser()
        self.graph_indexer = GraphIndexer()
        self.impact_analyzer = ImpactAnalyzer()

    def run(
        self, repo_source: str = ".", analysis_type: str = "overview", **kwargs
    ) -> Any:
        # Wrapper to make it look like a Tool execution
        return self.analyze(repo_source, analysis_type, **kwargs)

    def analyze(
        self,
        repo_source: str,
        analysis_type: str = "overview",
        target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform analysis on a repository.
        analysis_type: 'overview', 'structure', 'search', 'graph_index', 'impact'
        """
        repo_info = self.repo_manager.get_repo(repo_source)
        repo_path = Path(repo_info["path"])

        if not repo_path.exists():
            return {"error": f"Repository not found at {repo_path}"}

        if analysis_type == "overview":
            return self._generate_overview(repo_path)
        elif analysis_type == "structure":
            return self._generate_structure(repo_path)
        elif analysis_type == "graph_index":
            structure = self._generate_structure(repo_path).get("structure", [])
            return self.graph_indexer.index_repo(structure)
        elif analysis_type == "impact":
            if not target:
                return {"error": "Target parameter required for impact analysis"}
            return self.impact_analyzer.analyze(target)
        elif analysis_type == "callgraph":
            return self.impact_analyzer.generate_call_graph()

        return {"error": "Unknown analysis type"}

    def _generate_overview(self, path: Path) -> Dict[str, Any]:
        file_counts = {}
        total_files = 0
        total_size = 0

        for root, _, files in os.walk(path):
            if ".git" in root:
                continue
            for file in files:
                total_files += 1
                ext = Path(file).suffix
                file_counts[ext] = file_counts.get(ext, 0) + 1
                total_size += (Path(root) / file).stat().st_size

        return {
            "summary": "Repository Overview",
            "files": total_files,
            "size_kb": total_size / 1024,
            "languages": file_counts,
        }

    def _generate_structure(self, path: Path) -> Dict[str, Any]:
        structure = []
        # Same list as in agent_git_analyzer, should ideally be shared constant.
        supported_ext = {
            ".py",
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".java",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
        }
        for root, _, files in os.walk(path):
            if ".git" in root:
                continue
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in supported_ext:
                    full_path = Path(root) / file
                    analysis = self.parser.parse_file(str(full_path))
                    structure.append(analysis)
        return {"structure": structure}
