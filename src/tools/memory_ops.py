"""
Memory Operations Module
Orchestrates data flow between Git Analyzer, Vector DB (Qdrant), and Graph DB (Neo4j).
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from agents.agent_base import FileAnalysis, logger
from agents.agent_memory import MemoryManager, MemoryType
from agents.agent_graph import GraphManager
from tools.analysis.build_analyzer import BuildAnalyzer


def ingest_repository(
    repo_name: str,
    repo_path: str,
    file_analyses: List[FileAnalysis],
    code_structure: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ingest repository metadata and structure into both Memory Systems.

    1. Vector DB (Qdrant): Stores semantic embeddings of files and functions.
    2. Graph DB (Neo4j): Stores structural relationships (File -> Class -> Function).
    """
    stats = {"qdrant": 0, "neo4j": 0, "errors": []}

    # 1. Initialize Managers
    try:
        mem_mgr = MemoryManager()
        graph_mgr = GraphManager()
    except Exception as e:
        logger.error(f"Failed to initialize memory managers: {e}")
        return stats

    # 2. Graph Ingestion (Structure)
    logger.info("Starting Graph Ingestion (Neo4j)...")
    if graph_mgr.driver:
        try:
            # A. Store Code Structure (Classes/Functions)
            for item in code_structure:
                # 'item' comes from CodeParser.parse_file
                # expected keys: file, classes=[], functions=[]
                file_path = item.get("file")
                if file_path:
                    # Sync with file analysis to get LOC/Lang if possible,
                    # but CodeParser might not have it. GraphManager.store_file_node
                    # is usually better called with full analysis data.
                    graph_mgr.store_code_structure(file_path, repo_name, item)
                    stats["neo4j"] += 1

            # B. Store File Nodes (Metadata)
            for file in file_analyses:
                graph_mgr.store_file_node(
                    file_path=file.file_path,
                    repo_name=repo_name,
                    language=file.language,
                    loc=file.lines_of_code,
                )
        except Exception as e:
            msg = f"Graph ingestion error: {e}"
            logger.error(msg)
            stats["errors"].append(msg)
    else:
        stats["errors"].append("Neo4j driver not available")

    # 2.5 Build System Ingestion (Graph)
    logger.info("Ingesting Build Analysis...")
    try:
        build_analyzer = BuildAnalyzer(repo_path)
        for file in file_analyses:
            ctx = build_analyzer.get_build_context_for_file(file.file_path)
            for cmd in ctx.get("commands", []):
                # We treat the command itself as the target name for uniqueness
                # e.g. "make test" -> target="test"
                target_name = (
                    cmd.split(" ")[1] if "make" in cmd and len(cmd.split()) > 1 else cmd
                )

                graph_mgr.store_build_target(
                    name=target_name,
                    build_type=ctx.get("build_type", "unknown"),
                    cmd=cmd,
                    dependent_files=[file.file_path],
                    repo_name=repo_name,
                )
        stats["neo4j"] += 1  # Count generic build update
    except Exception as e:
        msg = f"Build Analysis ingestion error: {e}"
        logger.error(msg)
        stats["errors"].append(msg)

    # 3. Vector Ingestion (Semantics)
    logger.info("Starting Vector Ingestion (Qdrant)...")
    try:
        for file in file_analyses:
            # Create a rich semantic summary for the file
            content_snippet = f"""
            File: {file.file_path}
            Language: {file.language}
            Lines of Code: {file.lines_of_code}
            Complexity: {file.complexity}
            Security Issues: {len(file.security_issues)}
            """

            # Add to Qdrant
            mem_mgr.add_memory(
                content=content_snippet,
                memory_type=MemoryType.CODE_PATTERN,
                metadata={
                    "repo": repo_name,
                    "path": file.file_path,
                    "type": "file_summary",
                },
            )
            stats["qdrant"] += 1

    except Exception as e:
        msg = f"Vector ingestion error: {e}"
        logger.error(msg)
        stats["errors"].append(msg)

    # 4. Cleanup
    graph_mgr.close()

    return stats


def retrieve_project_insights(repo_name: str) -> str:
    """
    Retrieve architectural insights from Memory Systems (RAG).

    1. Neo4j: Find 'God Classes' (Hubs) and central components.
    2. Qdrant: Find complex or critical code patterns.
    """
    insights = ["\n[Memory Augmented Insights]"]

    # 1. Graph Insights (Neo4j)
    graph_mgr = GraphManager()
    if graph_mgr.driver:
        try:
            with graph_mgr.driver.session() as session:
                # A. Find Central Hubs (Nodes with most relationships)
                # Filter by repo_name using path matching or explicit property if added.
                # Since we added repo_name property to Function and Class nodes, we can use it.
                # Fallback to path check if repo_name is missing (for older nodes)
                query = """
                MATCH (n)
                WHERE n.repo_name = $repo_name
                WITH n
                MATCH (n)-[r]-()
                RETURN coalesce(n.path, n.file_path) as file, n.name as symbol, labels(n)[0] as type, count(r) as degree
                ORDER BY degree DESC
                LIMIT 5
                """
                result = session.run(query, repo_name=repo_name)
                hubs = []
                for r in result:
                    identifier = r["symbol"] if r["symbol"] else r["file"]
                    if identifier:
                        hubs.append(
                            f"- {r['type']} '{identifier}': {r['degree']} connections (Central Component)"
                        )

                if hubs:
                    insights.append("\n**Structural Hubs (GraphDB):**")
                    insights.extend(hubs)
                else:
                    insights.append(
                        "\n**Structural Hubs:** None detected (Graph might be sparse)."
                    )

        except Exception as e:
            logger.error(f"Graph retrieval failed: {e}")
            insights.append(f"\nGraph Retrieval Error: {e}")
        finally:
            graph_mgr.close()

    # 2. Vector Insights (Qdrant)
    # Ideally we would search for "security vulnerability" or "complex logic"
    # For now, let's just show that we can fetch context.
    try:
        mem_mgr = MemoryManager()
        # Search for high complexity or security issues generically
        # Filter by repo_name in metadata filter
        filter_criteria = {"repo": repo_name}
        results = mem_mgr.search_memories(
            query="high complexity security vulnerability",
            memory_type=MemoryType.CODE_PATTERN,
            limit=3,
            metadata_filter=filter_criteria,
        )

        if results:
            insights.append("\n**Semantic Hotspots (VectorDB):**")
            for res in results:
                # We extract the path from metadata if available
                path = res.get("metadata", {}).get("path", "unknown")
                insights.append(f"- {path} (Matches query 'complexity/security')")

    except Exception as e:
        logger.error(f"Vector retrieval failed: {e}")

    return "\n".join(insights)
