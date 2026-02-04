"""
Codebase analysis and Neo4j graph construction.

Analyzes Python/Go/Rust codebases to extract:
- File structure (modules, packages)
- Function/Method definitions and calls
- Class hierarchies
- Import dependencies
- Variable usage (reads/writes)
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional, Tuple
from enum import Enum
import ast
import os
from pathlib import Path
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class CodeElementType(str, Enum):
    """Types of code elements in the graph."""

    FILE = "File"
    MODULE = "Module"
    CLASS = "Class"
    FUNCTION = "Function"
    VARIABLE = "Variable"
    IMPORT = "Import"


class EdgeType(str, Enum):
    """Types of relationships between code elements."""

    CALLS = "CALLS"
    READS = "READS"
    WRITES = "WRITES"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    IMPORTS = "IMPORTS"
    DEPENDS_ON = "DEPENDS_ON"
    THROWS = "THROWS"
    AFFECTS = "AFFECTS"  # For ripple effect analysis
    DEFINED_IN = "DEFINED_IN"
    CONTAINS = "CONTAINS"


@dataclass
class CodeNode:
    """Represents a node in the code graph."""

    id: str
    name: str
    element_type: CodeElementType
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    signature: Optional[str] = None
    complexity: int = 1  # Cyclomatic complexity for functions
    lines_of_code: int = 0
    is_public: bool = True
    scope: str = "global"  # global, class, function
    docstring: Optional[str] = None
    properties: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for Neo4j insertion."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.element_type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "signature": self.signature,
            "complexity": self.complexity,
            "loc": self.lines_of_code,
            "is_public": self.is_public,
            "scope": self.scope,
            "docstring": self.docstring,
            **self.properties,
        }


@dataclass
class CodeEdge:
    """Represents an edge (relationship) in the code graph."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0  # Importance/frequency
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for Neo4j insertion."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.edge_type.value,
            "weight": self.weight,
            **self.metadata,
        }


@dataclass
class CodeGraph:
    """Complete graph representation of a codebase."""

    project_name: str
    root_path: Path
    nodes: Dict[str, CodeNode] = field(default_factory=dict)
    edges: List[CodeEdge] = field(default_factory=list)
    imports_map: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    call_graph: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def add_node(self, node: CodeNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: CodeEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        # Track relationships
        if edge.edge_type == EdgeType.CALLS:
            self.call_graph[edge.source_id].add(edge.target_id)
        elif edge.edge_type == EdgeType.IMPORTS:
            self.imports_map[edge.source_id].add(edge.target_id)

    def get_node(self, node_id: str) -> Optional[CodeNode]:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)

    def get_edges_from(
        self, node_id: str, edge_type: Optional[EdgeType] = None
    ) -> List[CodeEdge]:
        """Get all outgoing edges from a node."""
        edges = [e for e in self.edges if e.source_id == node_id]
        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def get_edges_to(
        self, node_id: str, edge_type: Optional[EdgeType] = None
    ) -> List[CodeEdge]:
        """Get all incoming edges to a node."""
        edges = [e for e in self.edges if e.target_id == node_id]
        if edge_type:
            edges = [e for e in edges if e.edge_type == edge_type]
        return edges

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "files": len(
                [
                    n
                    for n in self.nodes.values()
                    if n.element_type == CodeElementType.FILE
                ]
            ),
            "classes": len(
                [
                    n
                    for n in self.nodes.values()
                    if n.element_type == CodeElementType.CLASS
                ]
            ),
            "functions": len(
                [
                    n
                    for n in self.nodes.values()
                    if n.element_type == CodeElementType.FUNCTION
                ]
            ),
            "total_loc": sum(n.lines_of_code for n in self.nodes.values()),
        }


class PythonCodeAnalyzer:
    """Analyzes Python code to extract structure and build code graph."""

    def __init__(self, project_name: str, root_path: Path):
        self.project_name = project_name
        self.root_path = Path(root_path)
        self.graph = CodeGraph(project_name, self.root_path)
        self.current_file: Optional[str] = None
        self.current_scope: List[str] = []

    def analyze(self) -> CodeGraph:
        """Analyze entire project and build graph."""
        logger.info(f"Analyzing Python project: {self.project_name}")

        # Recursively find all Python files
        py_files = list(self.root_path.rglob("*.py"))
        logger.info(f"Found {len(py_files)} Python files")

        for py_file in py_files:
            self._analyze_file(py_file)

        logger.info(
            f"Analysis complete: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges"
        )
        return self.graph

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            self.current_file = str(file_path.relative_to(self.root_path))

            # Create File node
            file_node_id = f"file:{self.current_file}"
            file_node = CodeNode(
                id=file_node_id,
                name=file_path.name,
                element_type=CodeElementType.FILE,
                file_path=self.current_file,
                lines_of_code=len(content.split("\n")),
            )
            self.graph.add_node(file_node)

            # Walk AST
            self.current_scope = []
            self._walk_ast(tree, file_node_id)

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    def _walk_ast(self, node: ast.AST, parent_id: str) -> None:
        """Recursively walk AST tree."""
        for child in ast.walk(node):
            if isinstance(child, ast.FunctionDef) or isinstance(
                child, ast.AsyncFunctionDef
            ):
                self._process_function(child, parent_id)
            elif isinstance(child, ast.ClassDef):
                self._process_class(child, parent_id)
            elif isinstance(child, ast.Import) or isinstance(child, ast.ImportFrom):
                self._process_import(child, parent_id)

    def _process_function(self, node: ast.FunctionDef, parent_id: str) -> None:
        """Process function definition."""
        func_id = f"func:{self.current_file}:{node.name}"
        signature = self._get_function_signature(node)

        func_node = CodeNode(
            id=func_id,
            name=node.name,
            element_type=CodeElementType.FUNCTION,
            file_path=self.current_file,
            line_number=node.lineno,
            signature=signature,
            is_public=not node.name.startswith("_"),
            docstring=ast.get_docstring(node),
            lines_of_code=node.end_lineno - node.lineno if node.end_lineno else 0,
        )
        self.graph.add_node(func_node)

        # Add DEFINED_IN edge to file
        edge = CodeEdge(func_id, parent_id, EdgeType.DEFINED_IN)
        self.graph.add_edge(edge)

        # Extract function calls
        self._extract_calls(node, func_id)

    def _process_class(self, node: ast.ClassDef, parent_id: str) -> None:
        """Process class definition."""
        class_id = f"class:{self.current_file}:{node.name}"

        class_node = CodeNode(
            id=class_id,
            name=node.name,
            element_type=CodeElementType.CLASS,
            file_path=self.current_file,
            line_number=node.lineno,
            is_public=not node.name.startswith("_"),
            docstring=ast.get_docstring(node),
            lines_of_code=node.end_lineno - node.lineno if node.end_lineno else 0,
        )
        self.graph.add_node(class_node)

        # Add DEFINED_IN edge to file
        edge = CodeEdge(class_id, parent_id, EdgeType.DEFINED_IN)
        self.graph.add_edge(edge)

        # Process base classes (inheritance)
        for base in node.bases:
            base_name = ast.unparse(base)
            inherits_edge = CodeEdge(
                class_id, f"class:{self.current_file}:{base_name}", EdgeType.INHERITS
            )
            self.graph.add_edge(inherits_edge)

        # Process methods
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._process_function(item, class_id)

    def _process_import(
        self, node: ast.Import | ast.ImportFrom, parent_id: str
    ) -> None:
        """Process import statement."""
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                import_id = f"import:{module_name}:{alias.name}"
                import_edge = CodeEdge(parent_id, import_id, EdgeType.IMPORTS)
                self.graph.add_edge(import_edge)
        else:
            for alias in node.names:
                import_id = f"import:{alias.name}"
                import_edge = CodeEdge(parent_id, import_id, EdgeType.IMPORTS)
                self.graph.add_edge(import_edge)

    def _extract_calls(self, node: ast.AST, func_id: str) -> None:
        """Extract all function calls within a function."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    called_func = child.func.id
                    # Create edge to called function
                    called_id = f"func:{self.current_file}:{called_func}"
                    edge = CodeEdge(func_id, called_id, EdgeType.CALLS)
                    self.graph.add_edge(edge)
                elif isinstance(child.func, ast.Attribute):
                    called_method = child.func.attr
                    # For method calls, create generic edge
                    called_id = f"method:{called_method}"
                    edge = CodeEdge(func_id, called_id, EdgeType.CALLS, weight=0.5)
                    self.graph.add_edge(edge)

    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Extract function signature."""
        args = [arg.arg for arg in node.args.args]
        return f"{node.name}({', '.join(args)})"


class GoCodeAnalyzer:
    """Placeholder for Go code analysis."""

    def __init__(self, project_name: str, root_path: Path):
        self.project_name = project_name
        self.root_path = Path(root_path)

    def analyze(self) -> CodeGraph:
        """Analyze Go project (stub)."""
        logger.info(f"Go analysis not yet implemented: {self.project_name}")
        return CodeGraph(self.project_name, self.root_path)


class RustCodeAnalyzer:
    """Placeholder for Rust code analysis."""

    def __init__(self, project_name: str, root_path: Path):
        self.project_name = project_name
        self.root_path = Path(root_path)

    def analyze(self) -> CodeGraph:
        """Analyze Rust project (stub)."""
        logger.info(f"Rust analysis not yet implemented: {self.project_name}")
        return CodeGraph(self.project_name, self.root_path)


def create_analyzer(project_type: str, project_name: str, root_path: Path):
    """Factory function to create appropriate analyzer."""
    if project_type == "python":
        return PythonCodeAnalyzer(project_name, root_path)
    elif project_type == "go":
        return GoCodeAnalyzer(project_name, root_path)
    elif project_type == "rust":
        return RustCodeAnalyzer(project_name, root_path)
    else:
        logger.warning(f"Unknown project type: {project_type}, defaulting to Python")
        return PythonCodeAnalyzer(project_name, root_path)
