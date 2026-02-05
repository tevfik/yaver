"""
NetworkX Graph Database Adapter
Pure Python, zero-dependency alternative to Neo4j
"""

import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import networkx as nx

logger = logging.getLogger(__name__)


class NetworkXAdapter:
    """
    NetworkX-based graph database adapter
    Provides Neo4j-like interface with local file persistence
    """

    def __init__(self, persist_path: str = "~/.yaver/graph.pkl"):
        """
        Initialize NetworkX adapter

        Args:
            persist_path: Path to persist graph data
        """
        self.persist_path = Path(persist_path).expanduser()
        self.graph = nx.DiGraph()
        self.load()
        logger.info(f"NetworkX adapter initialized: {self.persist_path}")

    def add_node(self, node_id: str, labels: List[str] = None, **properties):
        """
        Add a node to the graph

        Args:
            node_id: Unique node identifier
            labels: Node labels (e.g., ['File', 'Python'])
            **properties: Node properties
        """
        labels = labels or []
        self.graph.add_node(node_id, labels=labels, **properties)

    def add_relationship(
        self, from_node: str, to_node: str, rel_type: str, **properties
    ):
        """
        Add a relationship between nodes

        Args:
            from_node: Source node ID
            to_node: Target node ID
            rel_type: Relationship type (e.g., 'CONTAINS', 'CALLS')
            **properties: Relationship properties
        """
        self.graph.add_edge(from_node, to_node, type=rel_type, **properties)

    def find_nodes(self, label: str = None, **filters) -> List[Dict[str, Any]]:
        """
        Find nodes by label and properties

        Args:
            label: Node label to filter by
            **filters: Property filters

        Returns:
            List of matching nodes with their properties
        """
        results = []
        for node_id, data in self.graph.nodes(data=True):
            # Check label
            if label and label not in data.get("labels", []):
                continue

            # Check filters
            match = True
            for key, value in filters.items():
                if data.get(key) != value:
                    match = False
                    break

            if match:
                results.append({"id": node_id, **data})

        return results

    def find_relationships(
        self, from_node: str = None, to_node: str = None, rel_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        Find relationships

        Args:
            from_node: Filter by source node
            to_node: Filter by target node
            rel_type: Filter by relationship type

        Returns:
            List of matching relationships
        """
        results = []
        for source, target, data in self.graph.edges(data=True):
            # Apply filters
            if from_node and source != from_node:
                continue
            if to_node and target != to_node:
                continue
            if rel_type and data.get("type") != rel_type:
                continue

            results.append({"from": source, "to": target, **data})

        return results

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a single node by ID"""
        if node_id in self.graph:
            data = self.graph.nodes[node_id]
            return {"id": node_id, **data}
        return None

    def delete_node(self, node_id: str):
        """Delete a node and its relationships"""
        if node_id in self.graph:
            self.graph.remove_node(node_id)

    def delete_all(self):
        """Delete all nodes and relationships"""
        self.graph.clear()
        logger.info("Cleared all graph data")

    def get_neighbors(self, node_id: str, direction: str = "out") -> List[str]:
        """
        Get neighboring nodes

        Args:
            node_id: Node to get neighbors for
            direction: 'out' (successors), 'in' (predecessors), 'both'

        Returns:
            List of neighbor node IDs
        """
        if node_id not in self.graph:
            return []

        if direction == "out":
            return list(self.graph.successors(node_id))
        elif direction == "in":
            return list(self.graph.predecessors(node_id))
        elif direction == "both":
            return list(self.graph.predecessors(node_id)) + list(
                self.graph.successors(node_id)
            )
        else:
            raise ValueError(f"Invalid direction: {direction}")

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics"""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
        }

    def save(self):
        """Persist graph to disk"""
        try:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, "wb") as f:
                pickle.dump(self.graph, f)
            logger.info(f"Saved graph to {self.persist_path}")
        except Exception as e:
            logger.error(f"Failed to save graph: {e}")

    def load(self):
        """Load graph from disk"""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "rb") as f:
                    self.graph = pickle.load(f)
                logger.info(
                    f"Loaded graph from {self.persist_path}: "
                    f"{self.graph.number_of_nodes()} nodes, "
                    f"{self.graph.number_of_edges()} edges"
                )
            except Exception as e:
                logger.error(f"Failed to load graph: {e}")
                self.graph = nx.DiGraph()
        else:
            logger.info("No existing graph found, starting fresh")

    def close(self):
        """Close connection and save"""
        self.save()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # Neo4j-compatible interface methods
    def store_analysis(
        self, analysis, repo_id: str, commit_hash: str = "HEAD", session_id: str = None
    ):
        """Store file analysis (Neo4j-compatible interface)"""
        file_id = f"{repo_id}:{analysis.file_path}"

        # Store file node
        self.add_node(
            file_id,
            labels=["File"],
            path=analysis.file_path,
            loc=analysis.loc,
            language=analysis.language,
            repo_id=repo_id,
            session_id=session_id,
            commit_hash=commit_hash,
            resolved_imports=analysis.resolved_imports,  # Store resolved imports for linking
            raw_calls=analysis.calls,  # Store raw calls for linking
        )

        # Store classes
        for cls in analysis.classes:
            class_id = f"{file_id}::{cls.name}"
            self.add_node(
                class_id,
                labels=["Class"],
                name=cls.name,
                start_line=cls.start_line,
                end_line=cls.end_line,
                session_id=session_id,
            )
            self.add_relationship(file_id, class_id, "CONTAINS")

            # Store methods
            for method in cls.methods:
                method_id = f"{class_id}::{method.name}"
                self.add_node(
                    method_id,
                    labels=["Function", "Method"],
                    name=method.name,
                    start_line=method.start_line,
                    end_line=method.end_line,
                    session_id=session_id,
                )
                self.add_relationship(class_id, method_id, "DEFINES_METHOD")

        # Store functions
        for func in analysis.functions:
            func_id = f"{file_id}::{func.name}"
            self.add_node(
                func_id,
                labels=["Function"],
                name=func.name,
                start_line=func.start_line,
                end_line=func.end_line,
                session_id=session_id,
            )
            self.add_relationship(file_id, func_id, "DEFINES_FUNCTION")

        # Auto-save after each analysis
        self.save()

    def link_unresolved_calls(self):
        """Link unresolved function calls (Neo4j-compatible)"""
        logger.info("Linking cross-file call relationships in NetworkX...")

        # Iterate all File nodes to process their raw calls
        file_nodes = self.find_nodes(label="File")

        for file_node in file_nodes:
            file_id = file_node["id"]
            repo_id = file_node.get("repo_id")
            raw_calls = file_node.get("raw_calls", [])
            resolved_imports = file_node.get("resolved_imports", {})

            if not raw_calls:
                continue

            for call in raw_calls:
                caller_name = call.get("caller")
                callee_name = call.get("callee")

                if not caller_name or not callee_name:
                    continue

                # 1. Resolve Caller ID
                # Try explicit function first (top-level)
                caller_id = f"{file_id}::{caller_name}"

                # If not found, check if it's a method content (class::method)
                if caller_name and "." in caller_name:
                    # This logic depends on how AST parser reports caller name for methods
                    pass

                # Verify caller exists in graph
                if not self.graph.has_node(caller_id):
                    # Try finding if it's a method
                    # This is tricky without knowing the class name if AST just says 'method_name'
                    # But ASTParser usually reports 'caller' as the function name enclosing the call.
                    # If it's a method, it might be nested.
                    # For now, assume top-level or search children of file.
                    potential_callers = [
                        n
                        for n in self.graph.successors(file_id)
                        if n.endswith(f"::{caller_name}")
                    ]
                    # Also check classes
                    if not potential_callers:
                        # Check methods in classes
                        for succ in self.graph.successors(file_id):
                            if "Class" in self.graph.nodes[succ].get("labels", []):
                                for method in self.graph.successors(succ):
                                    if method.endswith(f"::{caller_name}"):
                                        potential_callers.append(method)

                    if potential_callers:
                        caller_id = potential_callers[0]  # Pick first match
                    else:
                        # logger.debug(f"Caller node not found: {caller_id}")
                        continue

                # 2. Resolve Callee ID
                callee_id = None

                # Case A: Local call (in same file)
                local_target_candidate = f"{file_id}::{callee_name}"
                if self.graph.has_node(local_target_candidate):
                    callee_id = local_target_candidate

                # Case B: Imported call (e.g. db.connect)
                elif "." in callee_name:
                    module_part, func_part = callee_name.split(".", 1)
                    if module_part in resolved_imports:
                        target_file_path = resolved_imports[module_part]
                        # Target file ID
                        target_file_id = f"{repo_id}:{target_file_path}"
                        target_func_id = f"{target_file_id}::{func_part}"

                        if self.graph.has_node(target_func_id):
                            callee_id = target_func_id

                # Case C: From x import y (Direct import)
                elif callee_name in resolved_imports:
                    # resolved_imports usually maps module->path.
                    # But if 'from db import connect', 'connect' might be mapped?
                    # ImportResolver logic needs verification.
                    # Usually resolves to file path.
                    pass

                if callee_id:
                    self.add_relationship(caller_id, callee_id, "CALLS")
                    # logger.debug(f"Linked call: {caller_id} -> {callee_id}")

        self.save()

    def init_schema(self):
        """Initialize schema (Neo4j-compatible, no-op for NetworkX)"""
        pass

    def auto_tag_layers(self, repo_name: str):
        """Auto-tag architectural layers (Neo4j-compatible, no-op for NetworkX)"""
        pass
