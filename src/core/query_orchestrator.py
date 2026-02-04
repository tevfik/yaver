"""
Unified query orchestration system.

Routes different query types to appropriate backends:
- Semantic queries → Qdrant vector search
- Structural queries → Neo4j graph analysis
- Temporal queries → SQLite episodic memory
- Analytical queries → Neo4j analyzers

Provides multi-source fusion for complex queries.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import logging
import json
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries based on intent."""

    SEMANTIC = "semantic"  # "Where is the authentication code?"
    STRUCTURAL = "structural"  # "What calls this function?"
    TEMPORAL = "temporal"  # "Did we solve this before?"
    ANALYTICAL = "analytical"  # "Code quality analysis"
    COMBINED = "combined"  # Multiple types


@dataclass
class QueryResult:
    """Result from a single source."""

    source: str  # "qdrant", "neo4j", "sqlite", "code_smell", "ripple_effect"
    query_type: QueryType
    results: List[Dict[str, Any]]
    confidence: float  # 0.0 to 1.0
    explanation: str
    metadata: Dict[str, Any] = None


@dataclass
class FusedResult:
    """Result fused from multiple sources."""

    query: str
    query_type: QueryType
    sources: List[QueryResult]
    fused_results: List[Dict[str, Any]]
    overall_confidence: float
    recommendations: List[str]
    execution_time_ms: float


class QueryClassifier:
    """Classify user queries to determine query type."""

    # Keywords for each query type
    SEMANTIC_KEYWORDS = {
        "where",
        "find",
        "locate",
        "search",
        "show",
        "list",
        "get",
        "how",
        "count",
        "contains",
        "has",
        "includes",
    }

    STRUCTURAL_KEYWORDS = {
        "call",
        "called",
        "depend",
        "dependency",
        "chain",
        "path",
        "impact",
        "affect",
        "ripple",
        "break",
        "circular",
        "import",
        "usage",
        "reference",
        "hierarchy",
        "relation",
    }

    TEMPORAL_KEYWORDS = {
        "before",
        "did",
        "history",
        "previous",
        "last",
        "past",
        "solved",
        "tried",
        "attempt",
        "remember",
        "encounter",
    }

    ANALYTICAL_KEYWORDS = {
        "quality",
        "complexity",
        "issue",
        "smell",
        "critical",
        "important",
        "report",
        "analyze",
        "metric",
        "insight",
    }

    @staticmethod
    def classify(query: str) -> QueryType:
        """Classify query to determine query type."""
        query_lower = query.lower()
        words = set(query_lower.split())

        # Count keyword matches
        semantic_score = len(words & QueryClassifier.SEMANTIC_KEYWORDS)
        structural_score = len(words & QueryClassifier.STRUCTURAL_KEYWORDS)
        temporal_score = len(words & QueryClassifier.TEMPORAL_KEYWORDS)
        analytical_score = len(words & QueryClassifier.ANALYTICAL_KEYWORDS)

        scores = {
            QueryType.SEMANTIC: semantic_score,
            QueryType.STRUCTURAL: structural_score,
            QueryType.TEMPORAL: temporal_score,
            QueryType.ANALYTICAL: analytical_score,
        }

        # If multiple types matched equally, use combined
        max_score = max(scores.values()) if scores.values() else 0
        matched_types = [
            qtype for qtype, score in scores.items() if score == max_score and score > 0
        ]

        if len(matched_types) > 1:
            return QueryType.COMBINED
        elif matched_types:
            return matched_types[0]
        else:
            return QueryType.SEMANTIC  # Default


class MemoryQueryOrchestrator:
    """
    High-level query orchestrator that routes queries to appropriate backends
    and fuses results.
    """

    def __init__(self, project_name: str = "default"):
        self.project_name = project_name
        self.classifier = QueryClassifier()
        self.query_history: List[Dict] = []

    def execute_query(self, query: str, context: Optional[Dict] = None) -> FusedResult:
        """
        Execute a query against all available memory sources.

        Args:
            query: User query string
            context: Optional context dict (repo_id, file_path, etc.)

        Returns:
            FusedResult with results from all applicable sources
        """
        import time

        start_time = time.time()

        # Classify query
        query_type = self.classifier.classify(query)
        logger.info(f"Query classified as: {query_type.value}")

        # Route to appropriate sources
        results = []

        if query_type in [QueryType.SEMANTIC, QueryType.COMBINED]:
            qdrant_result = self._query_qdrant(query, context)
            if qdrant_result:
                results.append(qdrant_result)

        if query_type in [
            QueryType.STRUCTURAL,
            QueryType.ANALYTICAL,
            QueryType.COMBINED,
        ]:
            neo4j_result = self._query_neo4j(query, context)
            if neo4j_result:
                results.append(neo4j_result)

        if query_type in [QueryType.TEMPORAL, QueryType.COMBINED]:
            sqlite_result = self._query_sqlite(query, context)
            if sqlite_result:
                results.append(sqlite_result)

        # Fuse results
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        fused = self._fuse_results(query, query_type, results, execution_time)

        # Log query
        self._log_query(query, query_type, fused)

        return fused

    def _query_qdrant(
        self, query: str, context: Optional[Dict] = None
    ) -> Optional[QueryResult]:
        """Query Qdrant for semantic search (stub - would connect to actual Qdrant)."""
        logger.debug(f"Querying Qdrant: {query}")

        # This is a stub - in production would call actual Qdrant client
        # For now, return example structure
        return QueryResult(
            source="qdrant",
            query_type=QueryType.SEMANTIC,
            results=[
                {
                    "file": "auth/login.py",
                    "line": 42,
                    "snippet": "def authenticate(username, password):",
                    "relevance_score": 0.92,
                }
            ],
            confidence=0.92,
            explanation="Found via semantic search in code memory",
        )

    def _query_neo4j(
        self, query: str, context: Optional[Dict] = None
    ) -> Optional[QueryResult]:
        """Query Neo4j for structural analysis (stub)."""
        logger.debug(f"Querying Neo4j: {query}")

        # This is a stub - in production would call actual Neo4j driver
        return QueryResult(
            source="neo4j",
            query_type=QueryType.STRUCTURAL,
            results=[
                {
                    "function": "process_login",
                    "calls": ["validate_credentials", "create_session"],
                    "callers": ["handle_request"],
                    "complexity": 5,
                }
            ],
            confidence=0.85,
            explanation="Found via graph analysis of code structure",
        )

    def _query_sqlite(
        self, query: str, context: Optional[Dict] = None
    ) -> Optional[QueryResult]:
        """Query SQLite for episodic memory (stub)."""
        logger.debug(f"Querying SQLite: {query}")

        # This is a stub - in production would call actual SQLite
        return QueryResult(
            source="sqlite",
            query_type=QueryType.TEMPORAL,
            results=[
                {
                    "interaction_id": "int_20240601_001",
                    "timestamp": "2024-06-01T14:30:00Z",
                    "task": "Fix authentication bug in login.py",
                    "solution": "Added password validation",
                    "success": True,
                }
            ],
            confidence=0.78,
            explanation="Found via episodic memory of previous interactions",
        )

    def _fuse_results(
        self,
        query: str,
        query_type: QueryType,
        results: List[QueryResult],
        execution_time: float,
    ) -> FusedResult:
        """Fuse results from multiple sources."""

        # Calculate overall confidence (average)
        overall_confidence = (
            sum(r.confidence for r in results) / len(results) if results else 0.0
        )

        # Merge result lists
        fused_results = []
        source_map = {}

        for result in results:
            for item in result.results:
                item["source"] = result.source
                item["confidence"] = result.confidence
                fused_results.append(item)
            source_map[result.source] = result

        # Sort by confidence
        fused_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            query, fused_results, source_map
        )

        return FusedResult(
            query=query,
            query_type=query_type,
            sources=results,
            fused_results=fused_results,
            overall_confidence=overall_confidence,
            recommendations=recommendations,
            execution_time_ms=execution_time,
        )

    def _generate_recommendations(
        self, query: str, results: List[Dict], source_map: Dict[str, QueryResult]
    ) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        if not results:
            recommendations.append(
                "No results found. Try a more specific query or different keywords."
            )
            return recommendations

        # If only one source, suggest checking others
        if len(source_map) == 1:
            source = list(source_map.keys())[0]
            if source == "qdrant":
                recommendations.append(
                    "💡 Consider structural analysis (Neo4j) to understand call chains."
                )
            elif source == "neo4j":
                recommendations.append(
                    "💡 Consider semantic search (Qdrant) for related code patterns."
                )
            elif source == "sqlite":
                recommendations.append(
                    "💡 Check if this is documented in code structure (Neo4j)."
                )

        # If low confidence, suggest refining
        avg_confidence = (
            sum(r.get("confidence", 0) for r in results) / len(results)
            if results
            else 0
        )
        if avg_confidence < 0.6:
            recommendations.append(
                "⚠️  Low confidence results. Try refining your query."
            )

        # If high confidence, suggest next steps
        if avg_confidence > 0.8:
            recommendations.append(
                "✅ High confidence results. Ready to implement or analyze further."
            )

        return recommendations

    def _log_query(
        self, query: str, query_type: QueryType, result: FusedResult
    ) -> None:
        """Log query for future reference (episodic memory)."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "query_type": query_type.value,
            "result_count": len(result.fused_results),
            "overall_confidence": result.overall_confidence,
            "execution_time_ms": result.execution_time_ms,
        }
        self.query_history.append(log_entry)


class AnalyticsQueryExecutor:
    """Execute analytics queries for code quality insights."""

    def __init__(self, code_intelligence_provider=None):
        """
        Initialize with CodeIntelligenceProvider.

        Args:
            code_intelligence_provider: CodeIntelligenceProvider instance
        """
        self.provider = code_intelligence_provider

    def get_code_quality_insights(self) -> Dict:
        """Get comprehensive code quality report."""
        if not self.provider:
            # Fallback if provider is not initialized (e.g. if graph not loaded)
            return {"error": "Code intelligence provider not initialized"}

        # New: Use the enhanced provider to request full analysis
        # which now includes complexity and coupling from Neo4j/ImpactAnalyzer
        report = self.provider.get_code_quality_report()

        return {
            "type": "code_quality",
            "timestamp": datetime.now().isoformat(),
            "statistics": report["graph_stats"],
            "issues": {
                "total": report["total_issues"],
                "by_type": report["issues_by_type"],
                "by_severity": report["issues_by_severity"],
            },
            "recommendations": report["recommendations"],
            "critical_functions": report["critical_functions"][:10],  # Top 10
            "coupling": report.get("coupling", []),  # New: Coupling Data
            "top_complexity": report.get("top_complexity", []),  # New: Complexity Data
        }

    def analyze_function(self, function_id: str) -> Dict:
        """Analyze a specific function for insights."""
        if not self.provider:
            return {"error": "Code intelligence provider not initialized"}

        context = self.provider.get_task_context(function_id)
        return {
            "type": "function_analysis",
            "timestamp": datetime.now().isoformat(),
            "function": context.get("function_name"),
            "file": context.get("file_path"),
            "metrics": {
                "lines_of_code": context.get("lines_of_code"),
                "complexity": context.get("complexity"),
                "is_critical": context.get("is_critical"),
            },
            "ripple_effect": context.get("ripple_effect"),
            "related_issues": context.get("related_issues"),
        }


class CombinedMemoryInterface:
    """
    High-level interface combining all memory backends.

    Used by agents to query combined memory with single interface.
    """

    def __init__(self, repo_id: str):
        self.repo_id = repo_id
        self.orchestrator = MemoryQueryOrchestrator(repo_id)
        self.analytics = AnalyticsQueryExecutor()

    def query(self, question: str) -> Dict:
        """
        User-facing query method.

        Args:
            question: Natural language question

        Returns:
            Dictionary with fused results and recommendations
        """
        result = self.orchestrator.execute_query(question)

        return {
            "question": question,
            "query_type": result.query_type.value,
            "results": result.fused_results[:10],  # Top 10
            "overall_confidence": result.overall_confidence,
            "recommendations": result.recommendations,
            "sources": [s.source for s in result.sources],
            "execution_time_ms": result.execution_time_ms,
        }

    def get_insights(self) -> Dict:
        """Get code quality insights."""
        return self.analytics.get_code_quality_insights()

    def analyze_task_context(self, function_id: str) -> Dict:
        """Get context for working on a specific function."""
        return self.analytics.analyze_function(function_id)

    def solve_problem(self, problem_description: str) -> Dict:
        """
        Comprehensive problem solving flow.

        1. Query: Find related code
        2. Analyze: Check code quality
        3. Recommend: Suggest solution

        Args:
            problem_description: Description of problem to solve

        Returns:
            Structured problem-solving context
        """
        # Step 1: Find related code
        query_result = self.query(problem_description)

        # Step 2: Get quality insights
        insights = self.get_insights()

        # Step 3: Build recommendations
        recommendations = []
        if query_result["overall_confidence"] > 0.7:
            recommendations.append(
                "✅ High confidence matches found. Ready to implement solution."
            )
        else:
            recommendations.append(
                "⚠️  Low confidence. May need to gather more context."
            )

        return {
            "problem": problem_description,
            "related_code": query_result["results"][:5],
            "code_quality_context": insights,
            "recommended_approach": recommendations,
            "next_steps": [
                "1. Review related code",
                "2. Check for existing patterns",
                "3. Test solution thoroughly",
            ],
        }
