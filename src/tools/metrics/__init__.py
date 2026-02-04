"""
Code Metrics Analyzer
Extracts code quality metrics from analyzed repository data.
"""

import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ComplexityMetric:
    """Cyclomatic complexity metric for a function"""
    function_id: str
    function_name: str
    file_path: str
    complexity_score: float
    loc: int
    parameters: int
    has_docstring: bool


@dataclass
class DeadCodeIssue:
    """Dead code detection result"""
    issue_type: str  # "unreachable_function", "unused_import", etc
    entity_id: str
    entity_name: str
    file_path: str
    line_number: int
    severity: str  # "low", "medium", "high"


@dataclass
class QualityScore:
    """Overall quality metrics for repository"""
    total_score: float  # 0-100
    complexity_score: float
    dead_code_score: float
    architecture_score: float
    maintainability_index: float  # 0-100


class MetricsAnalyzer:
    """Analyzes code quality metrics from Neo4j graph data"""
    
    def __init__(self, neo4j_adapter):
        """
        Initialize metrics analyzer
        
        Args:
            neo4j_adapter: Neo4j connection for querying
        """
        self.neo4j = neo4j_adapter
    
    def analyze_repository(self, repo_id: str) -> Dict[str, Any]:
        """
        Comprehensive repository analysis
        
        Returns:
            {
                "complexity_metrics": [ComplexityMetric],
                "dead_code": [DeadCodeIssue],
                "quality_score": QualityScore,
                "summary": {
                    "total_functions": int,
                    "high_complexity_functions": int,
                    "dead_code_count": int,
                    "health": str  # "healthy", "warning", "critical"
                }
            }
        """
        result = {
            "complexity_metrics": self._analyze_complexity(repo_id),
            "dead_code": self._detect_dead_code(repo_id),
            "circular_dependencies": self._detect_circular_deps(repo_id),
            "quality_score": None,
            "summary": {}
        }
        
        # Calculate overall quality score
        result["quality_score"] = self._calculate_quality_score(result)
        
        # Generate summary
        result["summary"] = self._generate_summary(result)
        
        return result
    
    def _analyze_complexity(self, repo_id: str) -> List[ComplexityMetric]:
        """Analyze cyclomatic complexity of functions"""
        # Query Neo4j for function metrics
        with self.neo4j.driver.session() as session:
            result = session.run("""
                MATCH (f:Function)-[:DEFINED_IN]->(file:File {repo_id: $repo_id})
                WITH f, file,
                     size([(f)-[:CALLS]->() | 1]) as call_count,
                     size([(f)-[:CALLS*1..2]->() | 1]) as max_depth
                RETURN f.id as function_id,
                       f.name as function_name,
                       file.path as file_path,
                       (1 + call_count) as complexity_score,
                       (f.end_line - f.start_line) as loc,
                       size(f.args) as parameters,
                       coalesce(f.has_docstring, false) as has_docstring
                ORDER BY complexity_score DESC
            """, {"repo_id": repo_id})
            
            metrics = []
            for record in result:
                metrics.append(ComplexityMetric(
                    function_id=record["function_id"],
                    function_name=record["function_name"],
                    file_path=record["file_path"],
                    complexity_score=float(record["complexity_score"]),
                    loc=record["loc"] or 0,
                    parameters=record["parameters"] or 0,
                    has_docstring=record["has_docstring"] or False
                ))
            
            return metrics
    
    def _detect_dead_code(self, repo_id: str) -> List[DeadCodeIssue]:
        """Detect dead code (unused functions, etc)"""
        issues = []
        
        # Find unreachable functions
        with self.neo4j.driver.session() as session:
            result = session.run("""
                MATCH (f:Function)-[:DEFINED_IN]->(file:File {repo_id: $repo_id})
                WHERE NOT (f)<-[:CALLS]-()
                  AND NOT f.name IN ['__init__', '__main__', 'main']
                WITH f, file, 0 as incoming_calls
                WHERE incoming_calls = 0
                RETURN f.id as function_id,
                       f.name as function_name,
                       file.path as file_path,
                       f.start_line as line_number
            """, {"repo_id": repo_id})
            
            for record in result:
                issues.append(DeadCodeIssue(
                    issue_type="unreachable_function",
                    entity_id=record["function_id"],
                    entity_name=record["function_name"],
                    file_path=record["file_path"],
                    line_number=record["line_number"],
                    severity="medium"
                ))
        
        return issues
    
    def _detect_circular_deps(self, repo_id: str) -> List[Dict[str, Any]]:
        """Detect circular dependencies"""
        with self.neo4j.driver.session() as session:
            cycles = self.neo4j.detect_circular_dependencies(repo_id)
            return [{"cycle": cycle, "length": len(cycle)} for cycle in cycles]
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> QualityScore:
        """Calculate overall quality score (0-100)"""
        
        complexity_metrics = analysis["complexity_metrics"]
        dead_code = analysis["dead_code"]
        circular_deps = analysis["circular_dependencies"]
        
        # Complexity score (lower is better, capped at 10)
        avg_complexity = sum(m.complexity_score for m in complexity_metrics) / max(len(complexity_metrics), 1)
        complexity_score = max(0, 100 - (avg_complexity * 5))  # Higher score is better
        
        # Dead code score (fewer issues = higher score)
        dead_code_score = max(0, 100 - (len(dead_code) * 5))
        
        # Architecture score (fewer circular deps = higher)
        architecture_score = max(0, 100 - (len(circular_deps) * 10))
        
        # Documentation score (functions with docstrings)
        if complexity_metrics:
            with_docs = sum(1 for m in complexity_metrics if m.has_docstring)
            doc_score = (with_docs / len(complexity_metrics)) * 100
        else:
            doc_score = 100
        
        # Overall score (weighted average)
        total_score = (
            complexity_score * 0.3 +
            dead_code_score * 0.25 +
            architecture_score * 0.25 +
            doc_score * 0.2
        )
        
        return QualityScore(
            total_score=round(total_score, 1),
            complexity_score=round(complexity_score, 1),
            dead_code_score=round(dead_code_score, 1),
            architecture_score=round(architecture_score, 1),
            maintainability_index=round(total_score, 1)
        )
    
    def _generate_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable summary"""
        
        complexity_metrics = analysis["complexity_metrics"]
        dead_code = analysis["dead_code"]
        circular_deps = analysis["circular_dependencies"]
        quality = analysis["quality_score"]
        
        # Find worst offenders
        high_complexity = [m for m in complexity_metrics if m.complexity_score > 8]
        
        # Health assessment
        if quality.total_score >= 80:
            health = "healthy"
        elif quality.total_score >= 60:
            health = "warning"
        else:
            health = "critical"
        
        return {
            "total_functions": len(complexity_metrics),
            "avg_complexity": round(sum(m.complexity_score for m in complexity_metrics) / max(len(complexity_metrics), 1), 1),
            "high_complexity_count": len(high_complexity),
            "dead_code_count": len(dead_code),
            "circular_deps_count": len(circular_deps),
            "health": health,
            "quality_score": quality.total_score,
            "top_issues": [
                {"type": "complexity", "count": len(high_complexity), "priority": 2 if len(high_complexity) > 5 else 3},
                {"type": "dead_code", "count": len(dead_code), "priority": 1 if len(dead_code) > 0 else 5},
                {"type": "circular_deps", "count": len(circular_deps), "priority": 1 if len(circular_deps) > 0 else 5},
            ]
        }
    
    def export_metrics(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Export metrics in standardized format"""
        return {
            "complexity_metrics": [asdict(m) for m in analysis["complexity_metrics"]],
            "dead_code": [asdict(m) for m in analysis["dead_code"]],
            "circular_dependencies": analysis["circular_dependencies"],
            "quality_score": asdict(analysis["quality_score"]),
            "summary": analysis["summary"]
        }
