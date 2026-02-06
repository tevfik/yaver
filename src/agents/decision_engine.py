"""
Code Quality Decision Engine
Uses LLM to reason about code issues and generate recommendations.
"""

import json
import logging
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Single agent decision"""

    issue_id: str
    issue_type: str
    severity: str  # low, medium, high
    priority: int  # 1-10 (10 = highest)
    title: str
    description: str
    reasoning: str
    recommended_action: str
    effort_estimate: str  # "5 min", "1-2 hours", etc
    risk_level: str  # low, medium, high
    can_autofix: bool


class DecisionEngine:
    """LLM-powered reasoning about code quality issues"""

    def __init__(self, agent_base):
        """
        Initialize decision engine

        Args:
            agent_base: Yaver agent with LLM access
        """
        self.agent = agent_base

    def reason_about_issues(self, metrics: Dict[str, Any]) -> List[Decision]:
        """
        Use LLM to reason about detected issues and generate decisions

        Args:
            metrics: Output from MetricsAnalyzer

        Returns:
            List of prioritized decisions
        """

        decisions = []

        # Process each metric category
        if metrics.get("dead_code"):
            decisions.extend(self._reason_dead_code(metrics["dead_code"]))

        if metrics.get("complexity_metrics"):
            decisions.extend(self._reason_complexity(metrics["complexity_metrics"]))

        if metrics.get("circular_dependencies"):
            decisions.extend(
                self._reason_circular_deps(metrics["circular_dependencies"])
            )

        # Prioritize and rank
        decisions = self._prioritize_decisions(decisions, metrics.get("quality_score"))

        return decisions

    def _reason_dead_code(self, dead_code_issues: List) -> List[Decision]:
        """Generate decisions for dead code"""
        decisions = []

        prompt = f"""
        Analyze these dead code findings and provide assessment:
        {json.dumps([{
            'type': issue.issue_type,
            'name': issue.entity_name,
            'file': issue.file_path,
            'severity': issue.severity
        } for issue in dead_code_issues], indent=2)}

        For each, provide JSON with:
        {{
            "entity_name": "function name",
            "reasoning": "Why this is dead code",
            "action": "What to do about it",
            "priority": 1-10,
            "risk": "low|medium|high",
            "can_autofix": true/false
        }}
        """

        try:
            response = self.agent.query_llm(prompt, model_type="reasoning")

            # Parse JSON responses
            import re

            json_matches = re.findall(r"\{.*?\}", response, re.DOTALL)

            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    decisions.append(
                        Decision(
                            issue_id=data.get("entity_name", "unknown"),
                            issue_type="dead_code",
                            severity="medium",
                            priority=int(data.get("priority", 5)),
                            title=f"Remove {data.get('entity_name', 'unused code')}",
                            description=f"Found unused: {data.get('entity_name')}",
                            reasoning=data.get("reasoning", ""),
                            recommended_action=data.get("action", "Remove"),
                            effort_estimate="5-15 min",
                            risk_level=data.get("risk", "low"),
                            can_autofix=data.get("can_autofix", False),
                        )
                    )
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.warning(f"Error reasoning about dead code: {e}")

        return decisions

    def _reason_complexity(self, complexity_metrics: List) -> List[Decision]:
        """Generate decisions for high complexity functions"""
        decisions = []

        # Focus on high complexity
        high_complexity = [m for m in complexity_metrics if m.complexity_score > 8]

        if not high_complexity:
            return decisions

        prompt = f"""
        Analyze these complex functions:
        {json.dumps([{
            'name': m.function_name,
            'file': m.file_path,
            'complexity': m.complexity_score,
            'loc': m.loc,
            'parameters': m.parameters
        } for m in high_complexity[:5]], indent=2)}

        For each, suggest refactoring strategy. Respond with JSON:
        {{
            "function_name": "name",
            "strategy": "How to refactor this",
            "priority": 1-10,
            "risk": "low|medium|high",
            "effort": "30 min|1 hour|2 hours"
        }}
        """

        try:
            response = self.agent.query_llm(prompt, model_type="reasoning")

            import re

            json_matches = re.findall(r"\{.*?\}", response, re.DOTALL)

            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    decisions.append(
                        Decision(
                            issue_id=data.get("function_name", "unknown"),
                            issue_type="complexity",
                            severity="medium",
                            priority=int(data.get("priority", 5)),
                            title=f"Refactor {data.get('function_name')} (complexity)",
                            description=f"High complexity function needs refactoring",
                            reasoning=data.get("strategy", ""),
                            recommended_action="Consider extracting helper functions",
                            effort_estimate=data.get("effort", "1 hour"),
                            risk_level=data.get("risk", "medium"),
                            can_autofix=False,
                        )
                    )
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.warning(f"Error reasoning about complexity: {e}")

        return decisions

    def _reason_circular_deps(self, circular_deps: List[Dict]) -> List[Decision]:
        """Generate decisions for circular dependencies"""
        decisions = []

        if not circular_deps:
            return decisions

        for i, dep_info in enumerate(circular_deps[:3]):  # Top 3 cycles
            cycle = dep_info.get("cycle", [])
            cycle_str = " → ".join([c.split("::")[-1] for c in cycle])

            decisions.append(
                Decision(
                    issue_id=f"circular_dep_{i}",
                    issue_type="circular_dependency",
                    severity="high",
                    priority=9,
                    title=f"Resolve circular dependency: {cycle_str}",
                    description=f"Circular import detected: {cycle_str}",
                    reasoning="Circular dependencies make code hard to test and maintain",
                    recommended_action="Extract shared types or reorganize modules",
                    effort_estimate="1-2 hours",
                    risk_level="medium",
                    can_autofix=False,
                )
            )

        return decisions

    def _prioritize_decisions(
        self, decisions: List[Decision], quality_score=None
    ) -> List[Decision]:
        """
        Prioritize decisions using:
        - Issue severity
        - Quality score (worse = more urgent)
        - Effort/benefit ratio
        """

        # Adjust priority based on quality
        if quality_score and quality_score.total_score < 60:
            # Critical quality - boost all priorities
            for d in decisions:
                d.priority = min(10, d.priority + 2)

        # Dead code removal gets priority (low effort, high impact)
        for d in decisions:
            if d.issue_type == "dead_code":
                d.priority = min(10, d.priority + 1)

        # Circular deps also high priority (architectural issue)
        for d in decisions:
            if d.issue_type == "circular_dependency":
                d.priority = min(10, d.priority + 1)

        # Sort by priority (descending)
        return sorted(decisions, key=lambda d: (-d.priority, d.issue_type))
