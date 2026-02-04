import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from tools.code_analyzer.analyzer import CodeAnalyzer
from tools.code_analyzer.models import FileAnalysis

SAMPLE_REPO = Path("tests/data/semantic_repo")

@pytest.fixture
def setup_semantic_repo():
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)
    SAMPLE_REPO.mkdir(parents=True, exist_ok=True)
    (SAMPLE_REPO / ".git").mkdir(exist_ok=True) # Mock git presence
    
    # Create a simple python file with a function and a class
    code = """
def my_func():
    '''Docstring for my_func'''
    pass

class MyClass:
    '''Docstring for MyClass'''
    def my_method(self):
        return True
"""
    (SAMPLE_REPO / "module.py").write_text(code, encoding="utf-8")
    
    yield SAMPLE_REPO
    
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)

@patch("tools.code_analyzer.analyzer.CodeEmbedder")
@patch("tools.code_analyzer.analyzer.QdrantAdapter")
@patch("tools.code_analyzer.analyzer.Neo4jAdapter")
@patch("tools.code_analyzer.analyzer.GitAnalyzer")
def test_semantic_analysis_flow(mock_git, mock_neo4j, mock_qdrant_cls, mock_embedder_cls, setup_semantic_repo):
    repo_path = setup_semantic_repo
    
    # Setup Mocks
    mock_embedder = mock_embedder_cls.return_value
    mock_qdrant = mock_qdrant_cls.return_value
    mock_git.return_value.get_current_commit.return_value = "abc1234"
    
    # Mock embedding return
    def fake_embed(items):
        for item in items:
            item['embedding'] = [0.1, 0.2, 0.3]
        return items
    mock_embedder.embed_code_batch.side_effect = fake_embed
    
    analyzer = CodeAnalyzer("test_semantic_session", repo_path)
    
    # Execute with usage_semantic=True
    analyzer.analyze_repository(use_semantic=True)
    
    # Verify Embedder init
    assert mock_embedder_cls.called
    assert mock_qdrant_cls.called
    
    # Verify embed_code_batch called
    assert mock_embedder.embed_code_batch.called
    call_args = mock_embedder.embed_code_batch.call_args[0][0]
    
    # Expecting 3 items: my_func, MyClass, MyClass.my_method
    assert len(call_args) >= 3
    
    names = [item['name'] for item in call_args]
    assert "my_func" in names
    assert "MyClass" in names
    
    # Check method existence
    methods = [item for item in call_args if item.get('type') == 'method']
    assert len(methods) > 0
    assert methods[0]['name'] == "my_method"
    assert methods[0]['class'] == "MyClass"
    
    # Check types
    types = [item['type'] for item in call_args]
    assert "function" in types
    assert "class" in types
    assert "method" in types
    
    # Verify Qdrant store called
    assert mock_qdrant.store_embeddings.called
    qdrant_args = mock_qdrant.store_embeddings.call_args[0][0]
    assert len(qdrant_args) == len(call_args)
    assert qdrant_args[0]['embedding'] == [0.1, 0.2, 0.3]
