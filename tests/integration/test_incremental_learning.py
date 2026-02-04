import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from tools.code_analyzer.analyzer import CodeAnalyzer
from tools.code_analyzer.cache_manager import CachingManager
from tools.git_analyzer import GitAnalyzer

SAMPLE_REPO = Path("tests/data/incremental_repo")


@pytest.fixture
def setup_incremental_repo():
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)
    SAMPLE_REPO.mkdir(parents=True)
    (SAMPLE_REPO / ".git").mkdir()  # Fake git repo

    # Create file 1
    (SAMPLE_REPO / "file1.py").write_text("def func1(): pass")

    yield SAMPLE_REPO

    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)


@patch("tools.code_analyzer.analyzer.GitAnalyzer")
@patch("tools.code_analyzer.analyzer.Neo4jAdapter")
def test_incremental_analysis(mock_neo4j, mock_git_cls, setup_incremental_repo):
    """
    Test that incremental analysis relies on cache and doesn't crash.
    """
    repo_path = setup_incremental_repo

    # Mock Git
    mock_git = mock_git_cls.return_value
    mock_git.get_current_commit.return_value = "commit_1"

    # Mock Cache to simulate HIT for file1 on second run
    # For this test, we just verifying workflow execution not actua filesystem cache logic which is tested elsewhere

    analyzer = CodeAnalyzer("test_session", repo_path)
    # Mock driver
    analyzer.neo4j_adapter = mock_neo4j.return_value
    analyzer.neo4j_adapter.driver = MagicMock()

    # First Run
    analyzer.analyze_repository(incremental=False)

    assert mock_neo4j.return_value.store_analysis.call_count == 1

    # Second Run - Incremental
    # Here we simulate that cache returns an analysis object, so parsing is skipped
    analyzer.cache = MagicMock()
    mock_analysis = MagicMock()
    mock_analysis.file_path = "file1.py"
    analyzer.cache.get_cached_analysis.return_value = mock_analysis

    analyzer.analyze_repository(incremental=True)

    # Logic: Even if cache hit, we currently store to Neo4j to update timestamp/commit info
    # So call count should increment
    assert mock_neo4j.return_value.store_analysis.call_count == 2
    # Verify commit hash passed
    analyzer.neo4j_adapter.store_analysis.assert_called_with(
        mock_analysis,
        "incremental_repo",
        commit_hash="commit_1",
        session_id="test_session",
    )
