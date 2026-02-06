from typing import Dict, List, Any, Optional
import logging
from config.config import get_config
from tools.adapter_factory import get_graph_adapter

logger = logging.getLogger("agents")


class GraphManager:
    """
    Manages interactions with graph database (Neo4j or NetworkX).
    Stores code structure (Files, Classes, Functions) and their relationships.
    """

    def __init__(self):
        config = get_config()
        self.adapter = get_graph_adapter(config)

    def close(self):
        if hasattr(self.adapter, "close"):
            self.adapter.close()

    def store_file_node(self, file_path: str, repo_name: str, language: str, loc: int):
        """Create or update a File node"""
        if self.adapter:
            self.adapter.store_file_node(file_path, repo_name, language, loc)

    def store_code_structure(
        self, file_path: str, repo_name: str, structure: Dict[str, Any]
    ):
        """
        Store classes and functions found in a file and link them.
        """
        if self.adapter:
            self.adapter.store_code_structure(file_path, repo_name, structure)

    def get_project_summary(self) -> str:
        """
        Retrieve a summary of the project structure from the Graph.
        """
        if not self.adapter:
            return "Graph database not available."

        return self.adapter.get_project_summary()

    def get_context_for_file(self, file_path: str, repo_name: str) -> str:
        """
        Retrieve graph context for a file (imports, callers, callees)
        """
        if not self.adapter:
            return ""

        # Check if adapter supports this method
        if hasattr(self.adapter, "get_context_for_file"):
            return self.adapter.get_context_for_file(file_path, repo_name)

        return ""

    def find_nodes_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Find nodes by name."""
        if self.adapter and hasattr(self.adapter, "find_nodes_by_name"):
            return self.adapter.find_nodes_by_name(name)
        return []

    def find_relationships(
        self, from_node: str = None, to_node: str = None, rel_type: str = None
    ) -> List[Dict[str, Any]]:
        """Find relationships."""
        if self.adapter and hasattr(self.adapter, "find_relationships"):
            return self.adapter.find_relationships(from_node, to_node, rel_type)
        return []

    def store_build_target(
        self,
        name: str,
        build_type: str,
        cmd: str,
        dependent_files: List[str],
        repo_name: str,
    ):
        """
        Store a Build Target and its dependencies.
        Example: 'test' (make), depends on [main.py, test_main.py]
        """
        if not self.adapter:
            return

        target_id = f"{repo_name}:build:{name}"

        # Add BuildTarget node
        if hasattr(self.adapter, "add_node"):
            self.adapter.add_node(
                target_id,
                labels=["BuildTarget"],
                name=name,
                build_type=build_type,
                command=cmd,
                repo_name=repo_name,
            )

            # Link to files
            for file_path in dependent_files:
                file_id = f"{repo_name}:{file_path}"
                # Target depends on file (File -> Used By -> Target or Target -> Depends -> File)
                # Let's do Target -> DEPENDS_ON -> File
                # But check if file node exists first? NetworkX adapter creates edge lazily usually?
                # NetworkX adds nodes if they don't exist in add_edge.
                # But we want to ensure File node has labels.

                # Assuming File nodes exist from store_file_node calling previously.
                if hasattr(self.adapter, "add_relationship"):
                    self.adapter.add_relationship(target_id, file_id, "DEPENDS_ON")

            # Save
            if hasattr(self.adapter, "save"):
                self.adapter.save()
