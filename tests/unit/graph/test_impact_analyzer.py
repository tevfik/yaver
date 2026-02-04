import pytest
from unittest.mock import MagicMock, patch
from tools.code_analyzer.impact_analyzer import ImpactAnalyzer


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value = session
    # Allow context manager usage for session
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    return driver


def test_analyze_function_change_simple(mock_driver):
    """Test simple impact analysis with one caller"""
    analyzer = ImpactAnalyzer(mock_driver)

    # Mock Neo4j result for finding target node
    mock_node_result = MagicMock()
    mock_node_record = MagicMock()
    mock_node_record.__getitem__.side_effect = lambda x: "found_id" if x == "id" else []
    mock_node_result.single.return_value = mock_node_record

    # Mock Neo4j result for callers
    mock_callers_result = MagicMock()
    mock_record = MagicMock()
    mock_record.__getitem__.side_effect = lambda x: {
        "id": "caller1",
        "name": "test_caller",
        "file": "/src/caller.py",
        "line": 10,
    }.get(x)
    mock_record.get.side_effect = lambda x, d=None: {"file": "/src/caller.py"}.get(x, d)
    mock_callers_result.__iter__.return_value = iter([mock_record])

    # Mock Transitive callers (empty for simple test)
    mock_transitive_result = MagicMock()
    mock_transitive_result.__iter__.return_value = iter([])

    # session.run is called 3 times: target, direct, transitive (if direct exists)
    mock_driver.session().run.side_effect = [
        mock_node_result,
        mock_callers_result,
        mock_transitive_result,
    ]

    result = analyzer.analyze_function_change("/src/target.py", "target_func")

    assert result["risk_score"] > 0
    assert len(result["direct_callers"]) == 1
    assert result["direct_callers"][0]["name"] == "test_caller"
    assert "/src/caller.py" in result["affected_files"]


def test_analyze_function_change_no_callers(mock_driver):
    """Test impact analysis with no callers"""
    analyzer = ImpactAnalyzer(mock_driver)

    # Mock Neo4j result for finding target node
    mock_node_result = MagicMock()
    mock_node_record = MagicMock()
    mock_node_record.__getitem__.side_effect = lambda x: "found_id" if x == "id" else []
    mock_node_result.single.return_value = mock_node_record

    # Empty result for callers
    mock_callers_result = MagicMock()
    mock_callers_result.__iter__.return_value = iter([])

    # If no direct callers, transitive query is skipped. So only 2 calls.
    mock_driver.session().run.side_effect = [mock_node_result, mock_callers_result]

    result = analyzer.analyze_function_change("/src/target.py", "lonely_func")

    assert result["risk_score"] == 0
    assert len(result["direct_callers"]) == 0
    assert len(result["affected_files"]) == 0
