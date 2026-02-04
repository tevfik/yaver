import pytest
from pathlib import Path
from unittest.mock import MagicMock
from tools.code_analyzer.analyzer import CodeAnalyzer
from core.analysis_session import AnalysisSession

def test_full_analysis_flow(sample_repo_path, temp_workspace, mock_session_id):
    """
    Integration test:
    Run CodeAnalyzer on sample_repo.
    Verify:
    1. Parsing happens.
    2. Caching happens.
    3. Neo4j storage is called.
    4. Session state is updated.
    """
    
    # Setup Analyzer
    analyzer = CodeAnalyzer(mock_session_id, sample_repo_path)
    
    # Mock Neo4j
    mock_adapter = MagicMock()
    analyzer.neo4j_adapter = mock_adapter
    
    # Override session dir to temp to avoid writing to user home during test
    analyzer.session = AnalysisSession(mock_session_id, base_dir=temp_workspace)
    # Also override cache dir
    analyzer.cache.base_dir = temp_workspace / "cache"
    analyzer.cache.base_dir.mkdir(parents=True)
    
    # Execute
    analyzer.analyze_repository()
    
    # Verifications
    
    # 1. Parsing/Storage Calls
    # sample_repo has 1 main.py. Should be called once.
    assert mock_adapter.store_analysis.call_count == 1
    call_args = mock_adapter.store_analysis.call_args[0]
    analysis_obj = call_args[0]
    assert analysis_obj.file_path == "main.py"
    assert len(analysis_obj.functions) == 1
    
    # 2. Caching
    # Hashes should exist in cache directory
    assert any(analyzer.cache.base_dir.rglob("*.pkl"))
    
    # 3. Session State
    plan_content = analyzer.session.read_plan()
    assert "Analyze 1 files" in plan_content
    
    progress_content = analyzer.session.progress_file.read_text()
    assert "Completed analysis" in progress_content
    
    findings_content = analyzer.session.findings_file.read_text()
    assert "Analysis Complete" in findings_content
