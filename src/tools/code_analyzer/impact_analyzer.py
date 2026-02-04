"""
Impact Analyzer
Analyzes the potential impact of code changes by traversing the Neo4j dependency graph.
"""
from typing import List, Dict, Any, Optional
from neo4j import Driver, GraphDatabase
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImpactResult:
    target_node: str
    affected_nodes: List[Dict[str, Any]]
    risk_score: float
    reasoning: str


class ImpactAnalyzer:
    def __init__(self, driver_or_uri: Any, neo4j_auth: tuple = None):
        if isinstance(driver_or_uri, str):
            self.driver = GraphDatabase.driver(driver_or_uri, auth=neo4j_auth)
            self.owns_driver = True
        else:
            self.driver = driver_or_uri
            self.owns_driver = False

    def close(self):
        if self.owns_driver and self.driver:
            self.driver.close()

    def analyze_function_change(
        self, function_name: str, change_type: str = "signature"
    ) -> Dict[str, Any]:
        """
        Analyzes impact of changing a specific function.

        Args:
            function_name: Fully qualified name (e.g. 'src/main.py::MyClass::my_method') or partial name.
            change_type: 'signature', 'logic', 'rename'
        """
        with self.driver.session() as session:
            # 1. Find the Target Node
            result = session.run(
                """
                MATCH (f) WHERE f.id ENDS WITH $name AND (f:Function OR f:GhostFunction)
                RETURN f.id as id, labels(f) as labels LIMIT 1
            """,
                {"name": function_name},
            )

            record = result.single()
            if not record:
                return {
                    "target_node": function_name,
                    "risk_score": 0.0,
                    "direct_callers": [],
                    "transitive_callers": [],
                    "affected_files": [],
                    "reasoning": "Target function not found in graph.",
                }

            target_id = record["id"]

            # Extract simple name from ID for fuzzy matching of Ghosts
            # IDs are like file::Class::method or file::function
            simple_name = target_id.split("::")[-1]

            # 2. Find Direct Callers
            # MATCH (caller)-[:CALLS]->(target)
            direct_callers_res = session.run(
                """
                MATCH (caller)-[r:CALLS]->(target)
                WHERE target.id = $id
                   OR (target:GhostFunction AND target.name ENDS WITH '.' + $simple_name)
                   OR (target:GhostFunction AND target.name = $simple_name)
                RETURN caller.id as id, caller.name as name, caller.file as file, r.line as line
            """,
                {"id": target_id, "simple_name": simple_name},
            )

            direct_callers = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "file": r.get("file", "unknown"),
                    "line": r["line"],
                    "depth": 1,
                }
                for r in direct_callers_res
            ]

            # 3. Find Transitive Callers (Depth 2 for now)
            transitive_callers = []
            if direct_callers:
                for direct in direct_callers:
                    direct_id = direct["id"]
                    simple_direct_name = direct_id.split("::")[-1]

                    trans_res = session.run(
                        """
                        MATCH (caller)-[r:CALLS]->(middle)
                        WHERE middle.id = $id
                           OR (middle:GhostFunction AND middle.name ENDS WITH '.' + $simple_name)
                           OR (middle:GhostFunction AND middle.name = $simple_name)
                        RETURN caller.id as id, caller.name as name, caller.file as file, middle.id as via
                     """,
                        {"id": direct_id, "simple_name": simple_direct_name},
                    )

                    for r in trans_res:
                        transitive_callers.append(
                            {
                                "id": r["id"],
                                "name": r["name"],
                                "file": r.get("file", "unknown"),
                                "via": r["via"],
                                "depth": 2,
                            }
                        )

            # Deduplicate transitive callers
            unique_transitive = []
            seen_transitive = set()
            for t in transitive_callers:
                if t["id"] not in seen_transitive:
                    unique_transitive.append(t)
                    seen_transitive.add(t["id"])
            transitive_callers = unique_transitive

            all_affected = direct_callers + transitive_callers
            affected_files = list(set([c["file"] for c in all_affected if c["file"]]))

            # 4. Calculate Risk Score
            # Simple heuristic: Direct * 10 + Transitive * 5
            score = (len(direct_callers) * 10) + (len(transitive_callers) * 5)

            # Adjust based on change type
            if change_type == "signature":
                score *= 1.5  # High risk: breaks compilation/runtime
            elif change_type == "rename":
                score *= 2.0  # Very high risk: breaks everything not refactored

            reasoning = (
                f"Changing '{function_name}' ({change_type}) directly affects {len(direct_callers)} functions "
                f"and indirectly affects {len(transitive_callers)} others.\n"
                f"Total Risk Score: {score}"
            )

            return {
                "target_node": target_id,
                "risk_score": score,
                "direct_callers": direct_callers,
                "transitive_callers": transitive_callers,
                "affected_files": affected_files,
                "reasoning": reasoning,
            }

    def find_highly_coupled_modules(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Find modules (files) that are highly coupled (reference each other frequently).

        Args:
           threshold: Minimum number of cross-file calls/imports to consider 'high coupling'

        Returns:
           List of dicts describing the coupling
        """
        if not self.driver:
            return []

        with self.driver.session() as session:
            # Query for files calling/importing other files
            # Determine coupling by counting relationships between different files
            query = """
            MATCH (f1:File)-[:CONTAINS]->(func1:Function)-[:CALLS]->(func2:Function)<-[:CONTAINS]-(f2:File)
            WHERE f1.id <> f2.id
            WITH f1, f2, count(*) as weight
            WHERE weight > $threshold
            RETURN f1.path as source, f2.path as target, weight
            ORDER BY weight DESC
            LIMIT 20
            """

            result = session.run(query, {"threshold": threshold})

            coupling_data = []
            for record in result:
                coupling_data.append(
                    {
                        "source_module": record["source"],
                        "target_module": record["target"],
                        "coupling_strength": record["weight"],
                        "type": "functional_coupling",  # Based on function calls
                    }
                )

            return coupling_data
