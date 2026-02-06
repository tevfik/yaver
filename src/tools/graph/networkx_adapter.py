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

    def find_nodes_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Find nodes by 'name' property (exact match).
        Useful for resolving function names to node IDs.
        """
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("name") == name:
                results.append({"id": node_id, **data})
        return results

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

    # --- Agent Graph Compatible Interface ---

    def store_file_node(self, file_path: str, repo_name: str, language: str, loc: int):
        """
        Store a file node (AgentGraph Interface)
        """
        node_id = f"{repo_name}:{file_path}"
        self.add_node(
            node_id,
            labels=["File"],
            path=file_path,
            repo_name=repo_name,
            language=language,
            loc=loc,
        )
        self.save()

    def store_code_structure(
        self, file_path: str, repo_name: str, structure: Dict[str, Any]
    ):
        """
        Store classes, functions, and their relationships (AgentGraph Interface)
        Also stores calls if provided in structure.
        """
        file_id = f"{repo_name}:{file_path}"
        # print(f"DEBUG: store_code_structure for {file_id}. Struct keys: {structure.keys()}")

        if not self.graph.has_node(file_id):
            # Should have been created by store_file_node, but ensure safe
            self.store_file_node(file_path, repo_name, "unknown", 0)

        # 1. Classes
        for class_name in structure.get("classes", []):
            class_id = f"{file_id}::{class_name}"
            self.add_node(
                class_id,
                labels=["Class"],
                name=class_name,
                file_path=file_path,
                repo_name=repo_name,
            )
            self.add_relationship(file_id, class_id, "CONTAINS")

        # 2. Functions
        for func_name in structure.get("functions", []):
            func_id = f"{file_id}::{func_name}"
            self.add_node(
                func_id,
                labels=["Function"],
                name=func_name,
                file_path=file_path,
                repo_name=repo_name,
            )
            self.add_relationship(file_id, func_id, "CONTAINS")

        # 3. Imports (Node-to-File linking is hard without resolving paths, storing as property for now)
        imports = structure.get("imports", [])
        if imports:
            # We can create "Import" nodes or just edges if we can resolve them.
            # For now, let's store them as property on the file node
            if file_id in self.graph.nodes:
                self.graph.nodes[file_id]["imports"] = imports
            else:
                logger.warning(f"File node {file_id} not found when storing imports")

            # Try to link if import looks like a file in our graph
            # This is naive but works for some cases
            for imp in imports:
                # Naive resolution attempt: check if any file node ends with this import
                # This is O(N) but graph size is usually manageable in memory for NetworkX
                # For optimized resolution, we need a separate index
                pass

        # 4. Calls
        calls = structure.get("calls", [])
        for call in calls:
            caller = call.get("caller")
            callee = call.get("callee")

            if caller and callee:
                # Construct IDs (Assuming top-level functions for simplicity)
                # In robust implementation, we need scope handling
                caller_id = f"{file_id}::{caller}"

                # Check if caller exists
                if self.graph.has_node(caller_id):
                    # We can't easily resolve callee to a specific node ID without global symbol table.
                    # But we can store an "Unresolved Call" edge or property.
                    # Or try to find if callee exists in current file
                    callee_id_local = f"{file_id}::{callee}"
                    if self.graph.has_node(callee_id_local):
                        self.add_relationship(caller_id, callee_id_local, "CALLS")
                    else:
                        # Store external call attempt
                        if "external_calls" not in self.graph.nodes[caller_id]:
                            self.graph.nodes[caller_id]["external_calls"] = []
                        self.graph.nodes[caller_id]["external_calls"].append(callee)

        self.save()

    def get_project_summary(self) -> str:
        """
        Get project stats for Agent
        """
        stats = self.get_stats()
        summary = f"Project Graph Summary (NetworkX):\n"
        summary += f"- Total Nodes: {stats['nodes']}\n"
        summary += f"- Total Edges: {stats['edges']}\n"

        # Count by label
        counts = {}
        for _, data in self.graph.nodes(data=True):
            for label in data.get("labels", []):
                counts[label] = counts.get(label, 0) + 1

        for label, count in counts.items():
            summary += f"- {label}s: {count}\n"

        return summary

    def get_context_for_file(self, file_path: str, repo_name: str) -> str:
        """
        Get connected nodes for a file to provide context for LLM.
        """
        file_id = f"{repo_name}:{file_path}"
        if not self.graph.has_node(file_id):
            return f"No graph data for {file_path}"

        context = []

        # 1. Imports (Property or Edge)
        file_data = self.graph.nodes[file_id]
        imports = file_data.get("imports", [])
        if imports:
            context.append(f"Imports: {', '.join(imports)}")

        # 2. Classes/Functions defined in file
        contains = self.get_neighbors(file_id, direction="out")
        defined = []
        for child_id in contains:
            data = self.graph.nodes[child_id]
            if "Class" in data.get("labels", []) or "Function" in data.get(
                "labels", []
            ):
                defined.append(data.get("name", "unknown"))

                # 3. Calls made by these functions
                calls = self.get_neighbors(child_id, direction="out")
                for call_target in calls:
                    call_data = self.graph.nodes[call_target]
                    edge_data = self.graph.get_edge_data(child_id, call_target)
                    if edge_data and edge_data.get("type") == "CALLS":
                        context.append(
                            f"Function '{data.get('name')}' calls '{call_data.get('name')}'"
                        )

        if defined:
            context.append(f"Defines: {', '.join(defined)}")

        return "\n".join(context)

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
