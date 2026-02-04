"""
Neo4j-based code intelligence analyzers.

Provides:
- RippleEffectAnalyzer: What breaks if I change this function?
- DependencyChainAnalyzer: What are the dependencies?
- CriticalPathAnalyzer: Which functions are most important?
- CodeSmellDetector: What code quality issues exist?
"""

from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional, Tuple
from enum import Enum
import logging
from collections import defaultdict, deque

from .codebase_analyzer import CodeGraph, CodeNode, CodeEdge, EdgeType, CodeElementType

logger = logging.getLogger(__name__)


class IssueType(str, Enum):
    """Types of code quality issues."""

    GOD_CLASS = "god_class"  # Class with too many responsibilities
    CIRCULAR_DEPENDENCY = "circular_dependency"
    DEAD_CODE = "dead_code"  # Unreachable or unused function
    HIGH_COMPLEXITY = "high_complexity"  # Function too complex
    TIGHT_COUPLING = "tight_coupling"  # Too many dependencies


@dataclass
class IssueNode(CodeNode):
    """Code quality issue found during analysis."""

    issue_type: IssueType = IssueType.GOD_CLASS
    severity: str = "info"  # "critical", "warning", "info"
    description: str = ""
    suggested_fix: Optional[str] = None
    affected_nodes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.affected_nodes is None:
            self.affected_nodes = []


@dataclass
class RippleEffect:
    """Result of ripple effect analysis."""

    function_id: str
    affected_functions: List[str]  # Functions that would be affected
    severity: str  # "critical", "high", "medium", "low"
    transitive_impact: int  # How many levels deep
    explanation: str


@dataclass
class DependencyChain:
    """Result of dependency chain analysis."""

    source_id: str
    target_id: str
    path: List[str]  # Node IDs in path
    distance: int
    has_circular: bool = False


@dataclass
class CriticalPath:
    """Result of critical path analysis."""

    function_id: str
    importance_score: float  # 0.0 to 1.0
    call_count: int  # Number of functions that call this
    is_critical: bool
    suggestion: str


class RippleEffectAnalyzer:
    """Analyzes impact of changing a function."""

    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def analyze(self, function_id: str, depth: int = 3) -> RippleEffect:
        """
        Analyze what functions would be affected if this function changes.

        Args:
            function_id: The function to analyze
            depth: How many levels deep to traverse

        Returns:
            RippleEffect with affected functions and severity
        """
        if function_id not in self.graph.nodes:
            logger.warning(f"Function {function_id} not found in graph")
            return RippleEffect(function_id, [], "low", 0, "Function not found")

        affected = set()
        queue = deque([(function_id, 0)])
        visited = {function_id}

        # BFS to find all functions that call this function
        while queue:
            node_id, current_depth = queue.popleft()

            if current_depth > depth:
                continue

            # Find all edges pointing TO this node (incoming calls)
            incoming = self.graph.get_edges_to(node_id, EdgeType.CALLS)
            for edge in incoming:
                caller_id = edge.source_id
                if caller_id not in visited:
                    visited.add(caller_id)
                    affected.add(caller_id)
                    queue.append((caller_id, current_depth + 1))

        # Determine severity
        severity = self._determine_severity(len(affected), depth)
        explanation = f"Changing {function_id} would affect {len(affected)} functions"

        return RippleEffect(
            function_id=function_id,
            affected_functions=list(affected),
            severity=severity,
            transitive_impact=depth,
            explanation=explanation,
        )

    def _determine_severity(self, affected_count: int, depth: int) -> str:
        """Determine severity based on number of affected functions."""
        if affected_count > 10:
            return "critical"
        elif affected_count > 5:
            return "high"
        elif affected_count > 1:
            return "medium"
        else:
            return "low"


class DependencyChainAnalyzer:
    """Analyzes dependency chains between functions/modules."""

    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def find_path(self, source_id: str, target_id: str) -> Optional[DependencyChain]:
        """
        Find shortest path of dependencies between two functions.

        Args:
            source_id: Starting function
            target_id: Target function

        Returns:
            DependencyChain with path and distance, or None if no path
        """
        if source_id not in self.graph.nodes or target_id not in self.graph.nodes:
            logger.warning(f"One or both nodes not found")
            return None

        # BFS for shortest path
        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            node_id, path = queue.popleft()

            if node_id == target_id:
                return DependencyChain(
                    source_id=source_id,
                    target_id=target_id,
                    path=path,
                    distance=len(path) - 1,
                )

            # Follow outgoing edges (calls, imports, depends_on)
            for edge_type in [EdgeType.CALLS, EdgeType.IMPORTS, EdgeType.DEPENDS_ON]:
                outgoing = self.graph.get_edges_from(node_id, edge_type)
                for edge in outgoing:
                    next_id = edge.target_id
                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, path + [next_id]))

        return None

    def detect_circular_dependencies(self) -> List[DependencyChain]:
        """
        Detect circular dependency chains.

        Returns:
            List of circular dependency chains
        """
        cycles = []
        visited = set()

        for node_id in self.graph.nodes:
            if node_id in visited:
                continue

            # DFS to detect cycle
            path = self._dfs_cycle_detection(node_id, visited)
            if path:
                cycles.append(
                    DependencyChain(
                        source_id=path[0],
                        target_id=path[-1],
                        path=path,
                        distance=len(path),
                        has_circular=True,
                    )
                )

        return cycles

    def _dfs_cycle_detection(
        self,
        node_id: str,
        visited: Set[str],
        path: List[str] = None,
        rec_stack: Set[str] = None,
    ) -> Optional[List[str]]:
        """DFS to detect cycles."""
        if path is None:
            path = []
        if rec_stack is None:
            rec_stack = set()

        visited.add(node_id)
        rec_stack.add(node_id)
        path.append(node_id)

        for edge_type in [EdgeType.CALLS, EdgeType.IMPORTS]:
            outgoing = self.graph.get_edges_from(node_id, edge_type)
            for edge in outgoing:
                next_id = edge.target_id
                if next_id not in visited:
                    cycle = self._dfs_cycle_detection(
                        next_id, visited, path.copy(), rec_stack.copy()
                    )
                    if cycle:
                        return cycle
                elif next_id in rec_stack:
                    # Found cycle
                    return path + [next_id]

        return None


class CriticalPathAnalyzer:
    """Identifies most critical functions in codebase."""

    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def analyze_criticality(self, top_n: int = 10) -> List[CriticalPath]:
        """
        Identify most critical functions using PageRank-like scoring.

        Args:
            top_n: Number of top critical functions to return

        Returns:
            List of CriticalPath objects sorted by importance
        """
        # Calculate importance score for each function
        scores = self._calculate_importance_scores()

        # Get functions only (not files, classes, etc.)
        function_nodes = [
            node_id
            for node_id in self.graph.nodes
            if self.graph.nodes[node_id].element_type == CodeElementType.FUNCTION
        ]

        critical_paths = []
        for node_id in function_nodes:
            score = scores.get(node_id, 0.0)
            call_count = len(self.graph.get_edges_to(node_id, EdgeType.CALLS))

            is_critical = score > 0.5  # Threshold
            suggestion = self._get_suggestion(node_id, score, call_count)

            critical_paths.append(
                CriticalPath(
                    function_id=node_id,
                    importance_score=score,
                    call_count=call_count,
                    is_critical=is_critical,
                    suggestion=suggestion,
                )
            )

        # Sort by importance and return top N
        critical_paths.sort(key=lambda x: x.importance_score, reverse=True)
        return critical_paths[:top_n]

    def _calculate_importance_scores(self) -> Dict[str, float]:
        """Calculate importance score for each node using iterative algorithm."""
        scores = defaultdict(float)

        # Initialize all nodes with 1.0
        for node_id in self.graph.nodes:
            scores[node_id] = 1.0

        # Iterate to calculate scores
        for _ in range(5):  # 5 iterations of refinement
            new_scores = defaultdict(float)
            for node_id in self.graph.nodes:
                # Score increases based on incoming calls
                incoming = self.graph.get_edges_to(node_id, EdgeType.CALLS)
                new_scores[node_id] = 1.0 + sum(
                    scores[e.source_id] / 2 for e in incoming
                )

            scores = new_scores

        # Normalize to 0-1 range
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

        return scores

    def _get_suggestion(self, node_id: str, score: float, call_count: int) -> str:
        """Generate suggestion for critical function."""
        if score > 0.7 and call_count > 5:
            return "⚠️  Highly critical - has extensive call chain. Change with care."
        elif score > 0.5 and call_count > 3:
            return "📌 Important utility function. Monitor changes carefully."
        elif score > 0.3:
            return "ℹ️  Moderately used function. Good testing coverage recommended."
        else:
            return "📝 Low criticality function. Safe to refactor."


class CodeSmellDetector:
    """Detects code quality issues and anti-patterns."""

    def __init__(self, graph: CodeGraph):
        self.graph = graph

    def detect_all_smells(self) -> List[IssueNode]:
        """
        Run all code smell detection algorithms.

        Returns:
            List of detected issues
        """
        issues = []
        issues.extend(self._detect_god_classes())
        issues.extend(self._detect_circular_dependencies())
        issues.extend(self._detect_dead_code())
        issues.extend(self._detect_high_complexity())
        issues.extend(self._detect_tight_coupling())

        return issues

    def _detect_god_classes(self) -> List[IssueNode]:
        """Detect classes with too many responsibilities."""
        issues = []

        for node_id, node in self.graph.nodes.items():
            if node.element_type != CodeElementType.CLASS:
                continue

            # Count methods in class
            contained_methods = len(
                self.graph.get_edges_from(node_id, EdgeType.CONTAINS)
            )

            if contained_methods > 15:  # Threshold
                issue = IssueNode(
                    id=f"issue:god_class:{node_id}",
                    name=f"God Class: {node.name}",
                    element_type=CodeElementType.CLASS,
                    file_path=node.file_path,
                    line_number=node.line_number,
                    issue_type=IssueType.GOD_CLASS,
                    severity="warning",
                    description=f"Class {node.name} has {contained_methods} methods. Consider breaking into smaller classes.",
                    suggested_fix="Apply Single Responsibility Principle (SRP). Split into multiple focused classes.",
                    affected_nodes=[node_id],
                )
                issues.append(issue)

        return issues

    def _detect_circular_dependencies(self) -> List[IssueNode]:
        """Detect circular dependency chains."""
        issues = []

        analyzer = DependencyChainAnalyzer(self.graph)
        cycles = analyzer.detect_circular_dependencies()

        for cycle in cycles:
            if len(cycle.path) > 2:  # Only report real cycles
                issue = IssueNode(
                    id=f"issue:circular:{cycle.source_id}",
                    name=f"Circular Dependency",
                    element_type=CodeElementType.CLASS,
                    issue_type=IssueType.CIRCULAR_DEPENDENCY,
                    severity="critical",
                    description=f"Circular dependency detected: {' → '.join(cycle.path)}",
                    suggested_fix="Break the cycle by introducing a third module or restructuring dependencies.",
                    affected_nodes=cycle.path,
                )
                issues.append(issue)

        return issues

    def _detect_dead_code(self) -> List[IssueNode]:
        """Detect unreachable or unused functions."""
        issues = []

        for node_id, node in self.graph.nodes.items():
            if node.element_type != CodeElementType.FUNCTION:
                continue

            # Check if function has no incoming calls
            incoming_calls = self.graph.get_edges_to(node_id, EdgeType.CALLS)

            if not incoming_calls and node.is_public:  # Public but unused
                issue = IssueNode(
                    id=f"issue:dead_code:{node_id}",
                    name=f"Dead Code: {node.name}",
                    element_type=CodeElementType.FUNCTION,
                    file_path=node.file_path,
                    line_number=node.line_number,
                    issue_type=IssueType.DEAD_CODE,
                    severity="info",
                    description=f"Function {node.name} is not called anywhere.",
                    suggested_fix="Remove unused function or verify it's meant to be called externally.",
                    affected_nodes=[node_id],
                )
                issues.append(issue)

        return issues

    def _detect_high_complexity(self) -> List[IssueNode]:
        """Detect functions with high cyclomatic complexity."""
        issues = []

        for node_id, node in self.graph.nodes.items():
            if node.element_type != CodeElementType.FUNCTION:
                continue

            if node.complexity > 10:  # High complexity threshold
                issue = IssueNode(
                    id=f"issue:complexity:{node_id}",
                    name=f"High Complexity: {node.name}",
                    element_type=CodeElementType.FUNCTION,
                    file_path=node.file_path,
                    line_number=node.line_number,
                    issue_type=IssueType.HIGH_COMPLEXITY,
                    severity="warning",
                    description=f"Function {node.name} has complexity score {node.complexity}.",
                    suggested_fix="Break function into smaller, more focused functions. Consider extracting logic into helper methods.",
                    affected_nodes=[node_id],
                )
                issues.append(issue)

        return issues

    def _detect_tight_coupling(self) -> List[IssueNode]:
        """Detect tightly coupled modules/classes."""
        issues = []

        for node_id, node in self.graph.nodes.items():
            if node.element_type not in [CodeElementType.CLASS, CodeElementType.MODULE]:
                continue

            # Count outgoing dependencies
            dependencies = len(self.graph.get_edges_from(node_id, EdgeType.DEPENDS_ON))
            dependencies += len(self.graph.get_edges_from(node_id, EdgeType.IMPORTS))

            if dependencies > 10:  # High coupling threshold
                issue = IssueNode(
                    id=f"issue:coupling:{node_id}",
                    name=f"Tight Coupling: {node.name}",
                    element_type=node.element_type,
                    file_path=node.file_path,
                    issue_type=IssueType.TIGHT_COUPLING,
                    severity="warning",
                    description=f"{node.element_type.value} {node.name} depends on {dependencies} other modules.",
                    suggested_fix="Reduce dependencies using dependency injection or interface segregation.",
                    affected_nodes=[node_id],
                )
                issues.append(issue)

        return issues


from .impact_analyzer import ImpactAnalyzer


class CodeIntelligenceProvider:
    """
    High-level interface for code intelligence.
    Coordinates all analyzers and provides insights for agent decisions.
    """

    def __init__(self, graph: CodeGraph):
        self.graph = graph
        self.ripple_analyzer = RippleEffectAnalyzer(graph)
        self.dependency_analyzer = DependencyChainAnalyzer(graph)
        self.critical_analyzer = CriticalPathAnalyzer(graph)
        self.smell_detector = CodeSmellDetector(graph)
        # We need a Neo4j driver for the ImpactAnalyzer, but this class only has 'graph' (CodeGraph).
        # We'll assume the driver is available or injected later regarding actual coupling queries
        # if this class is used offline with just CodeGraph, we might not have the DB.
        # But for 'insights', the analyzer usually has a neo4j connection.

    def get_task_context(self, function_id: str) -> Dict:
        """
        Get comprehensive context for working on a specific function.
        Used to inject into agent prompts.

        Args:
            function_id: The function being worked on

        Returns:
            Dictionary with critical context
        """
        node = self.graph.get_node(function_id)
        if not node:
            return {}

        # Analyze ripple effect
        ripple = self.ripple_analyzer.analyze(function_id)

        # Find critical dependencies
        critical_funcs = self.critical_analyzer.analyze_criticality(top_n=5)
        critical_ids = {cp.function_id for cp in critical_funcs}

        # Get all issues
        all_issues = self.smell_detector.detect_all_smells()
        related_issues = [
            issue for issue in all_issues if function_id in issue.affected_nodes
        ]

        return {
            "function_id": function_id,
            "function_name": node.name,
            "file_path": node.file_path,
            "line_number": node.line_number,
            "signature": node.signature,
            "lines_of_code": node.lines_of_code,
            "complexity": node.complexity,
            "ripple_effect": {
                "affected_count": len(ripple.affected_functions),
                "severity": ripple.severity,
                "affected_functions": ripple.affected_functions[:5],  # Top 5
            },
            "is_critical": function_id in critical_ids,
            "related_issues": [
                {
                    "type": issue.issue_type.value,
                    "severity": issue.severity,
                    "description": issue.description,
                    "suggestion": issue.suggested_fix,
                }
                for issue in related_issues
            ],
        }

    def get_code_quality_report(self) -> Dict:
        """
        Generate code quality report for entire codebase.

        Returns:
            Dictionary with quality metrics
        """
        issues = self.smell_detector.detect_all_smells()
        critical_funcs = self.critical_analyzer.analyze_criticality(top_n=10)

        # New: Collect top complexity functions
        top_complexity = []
        for node_id, node in self.graph.nodes.items():
            if node.element_type == CodeElementType.FUNCTION:
                if hasattr(node, "complexity") and node.complexity > 5:
                    top_complexity.append(
                        {
                            "function_name": node.name,
                            "file_path": node.file_path,
                            "complexity": node.complexity,
                        }
                    )
        top_complexity = sorted(
            top_complexity, key=lambda x: x["complexity"], reverse=True
        )[:10]

        # New: Collect coupling data (Requires ImpactAnalyzer with live driver, but we are using CodeGraph here)
        # Limitation: ImpactAnalyzer needs Neo4j Driver, CodeGraph is in-memory representation.
        # Let's approximate coupling using in-memory graph
        coupling = []
        # TBD: Implement graph-based coupling if DB unavailable
        # Or better: DependencyChainAnalyzer already tracks dependencies

        return {
            "graph_stats": self.graph.get_stats(),
            "total_issues": len(issues),
            "issues_by_type": self._count_issues_by_type(issues),
            "issues_by_severity": self._count_issues_by_severity(issues),
            "critical_functions": [
                {
                    "id": cp.function_id,
                    "importance": cp.importance_score,
                    "call_count": cp.call_count,
                    "suggestion": cp.suggestion,
                }
                for cp in critical_funcs
            ],
            "top_complexity": top_complexity,
            "coupling": coupling,
            "recommendations": self._generate_recommendations(issues),
        }

    def _count_issues_by_type(self, issues: List[IssueNode]) -> Dict[str, int]:
        """Count issues by type."""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.issue_type.value] += 1
        return dict(counts)

    def _count_issues_by_severity(self, issues: List[IssueNode]) -> Dict[str, int]:
        """Count issues by severity."""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.severity] += 1
        return dict(counts)

    def _generate_recommendations(self, issues: List[IssueNode]) -> List[str]:
        """Generate prioritized recommendations based on issues."""
        recommendations = []

        critical_count = len([i for i in issues if i.severity == "critical"])
        if critical_count > 0:
            recommendations.append(
                f"🚨 Fix {critical_count} critical issues immediately (circular dependencies)."
            )

        god_classes = len([i for i in issues if i.issue_type == IssueType.GOD_CLASS])
        if god_classes > 0:
            recommendations.append(
                f"📦 Refactor {god_classes} god classes to improve maintainability."
            )

        dead_code = len([i for i in issues if i.issue_type == IssueType.DEAD_CODE])
        if dead_code > 0:
            recommendations.append(
                f"🗑️  Remove {dead_code} unused functions to reduce clutter."
            )

        high_complexity = len(
            [i for i in issues if i.issue_type == IssueType.HIGH_COMPLEXITY]
        )
        if high_complexity > 0:
            recommendations.append(
                f"⚡ Simplify {high_complexity} high-complexity functions."
            )

        if not recommendations:
            recommendations.append("✅ Codebase quality looks good!")

        return recommendations
