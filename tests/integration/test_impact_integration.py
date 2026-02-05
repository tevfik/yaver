import pytest
import os
import shutil
from pathlib import Path
from tools.code_analyzer.analyzer import CodeAnalyzer
from tools.code_analyzer.impact_analyzer import ImpactAnalyzer
from config.config import get_config

SAMPLE_REPO = Path("tests/data/sample_repo_impact")


@pytest.fixture(scope="module")
def setup_sample_repo():
    """Create a temporary sample repository with a call chain"""
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)
    SAMPLE_REPO.mkdir(parents=True)

    # db.py
    (SAMPLE_REPO / "db.py").write_text(
        """
def connect():
    print("Connecting to DB")
"""
    )

    # service.py
    (SAMPLE_REPO / "service.py").write_text(
        """
import db

def process_data():
    db.connect()
    print("Processing")
"""
    )

    # controller.py
    (SAMPLE_REPO / "controller.py").write_text(
        """
import service

def handle_request():
    service.process_data()
"""
    )

    # main.py
    (SAMPLE_REPO / "main.py").write_text(
        """
import controller

def main():
    controller.handle_request()

if __name__ == "__main__":
    main()
"""
    )

    yield SAMPLE_REPO

    # Cleanup
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)


@pytest.fixture(scope="module")
def graph_db_provider():
    config = get_config()
    provider = os.getenv("GRAPH_DB_PROVIDER", config.graph_db.provider)

    if provider == "neo4j":
        # Check connection
        try:
            from neo4j import GraphDatabase

            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            auth = (
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "password"),
            )
            driver = GraphDatabase.driver(uri, auth=auth)
            driver.verify_connectivity()

            # Clean DB
            with driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            driver.close()
            return "neo4j"
        except Exception:
            pytest.skip("Neo4j not available")

    return "networkx"


from config.config import reload_config


def test_impact_analysis_chain(setup_sample_repo, graph_db_provider):
    """
    Test Impact Analysis on a 4-level call chain:
    main -> controller -> process_data -> connect
    Target: connect
    """
    repo_path = setup_sample_repo
    session_id = "test_integration_1"

    # Force provider if needed based on fixture
    if graph_db_provider == "networkx":
        os.environ["GRAPH_DB_PROVIDER"] = "networkx"
        reload_config()

    # 1. Run Analysis (will use configured provider)
    analyzer = CodeAnalyzer(session_id, repo_path)

    try:
        analyzer.init_graph_db()
    except Exception as e:
        if graph_db_provider == "neo4j":
            pytest.skip(f"Could not connect to Neo4j: {e}")
        else:
            raise e

    analyzer.analyze_repository()

    # 2. Run Impact Analysis
    if graph_db_provider == "networkx":
        # For NetworkX, we can use the populated graph from analyzer
        adapter = analyzer.neo4j_adapter
        assert adapter.graph.number_of_nodes() > 0

        # Test basic graph connectivity
        connect_node = None
        for node, data in adapter.graph.nodes(data=True):
            if "connect" in str(node):
                connect_node = node
                break

        assert connect_node is not None, "Could not find 'connect' node"

        # Find callers (predecessors)
        callers = list(adapter.graph.predecessors(connect_node))
        caller_names = [str(c) for c in callers]

        # We expect process_data to call connect
        found = any("process_data" in c for c in caller_names)
        assert found, f"Expected process_data in {caller_names}"

        # Find transitive callers (two hops)
        transitive = []
        for caller in callers:
            transitive.extend(list(adapter.graph.predecessors(caller)))

        transitive_names = [str(c) for c in transitive]
        assert any(
            "handle_request" in c for c in transitive_names
        ), f"Expected handle_request in {transitive_names}"

    else:
        # Neo4j Path
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        auth = (
            os.getenv("NEO4J_USER", "neo4j"),
            os.getenv("NEO4J_PASSWORD", "password"),
        )

        impact_analyzer = ImpactAnalyzer(uri, auth)
        result = impact_analyzer.analyze_function_change(
            "connect", change_type="signature"
        )

        print(f"Impact Result: {result}")
        assert result["risk_score"] > 0

        direct_names = [c["name"] for c in result["direct_callers"]]
        assert "process_data" in direct_names

        transitive_names = [c["name"] for c in result["transitive_callers"]]
        assert "handle_request" in transitive_names

        impact_analyzer.close()

    analyzer.close()
