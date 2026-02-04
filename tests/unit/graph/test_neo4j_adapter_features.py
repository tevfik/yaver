import pytest
from unittest.mock import MagicMock
from tools.code_analyzer.neo4j_adapter import Neo4jAdapter


def test_detect_circular_dependencies():
    """Test cycle detection cypher query execution"""
    # Mock driver
    mock_driver = MagicMock()
    adapter = Neo4jAdapter("bolt://localhost:7687", ("u", "p"))
    adapter.driver = mock_driver

    # Mock output
    mock_result = MagicMock()
    mock_result.__iter__.return_value = [{"cycle": ["funcA", "funcB", "funcA"]}]
    mock_driver.session.return_value.__enter__.return_value.run.return_value = (
        mock_result
    )

    cycles = adapter.detect_circular_dependencies()

    assert len(cycles) == 1
    assert cycles[0] == ["funcA", "funcB", "funcA"]

    # Verify Cypher query contained expected patterns
    args = mock_driver.session.return_value.__enter__.return_value.run.call_args[0][0]
    assert "MATCH path = (n:Function)-[:CALLS*2..5]->(n)" in args
    adapter = Neo4jAdapter("bolt://x", ("u", "p"))
    adapter.driver = mock_driver

    mock_analysis = MagicMock()
    mock_analysis.file_path = "test.py"
    mock_analysis.loc = 10
    mock_analysis.language = "python"
    mock_analysis.classes = []
    mock_analysis.functions = []
    mock_analysis.imports = []
    mock_analysis.calls = []

    adapter.store_analysis(mock_analysis, "repo1", commit_hash="a1b2c3d4")

    # Check if commit_hash was in params
    call_args = (
        mock_driver.session.return_value.__enter__.return_value.run.call_args_list
    )

    # Look for the file creation call
    found = False
    for call in call_args:
        args = call[0]
        if len(args) < 2:
            continue
        params = args[1]
        if params.get("commit") == "a1b2c3d4":
            found = True
            break

    assert found
