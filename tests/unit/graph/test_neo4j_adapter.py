import pytest
from unittest.mock import MagicMock, patch
from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
from tools.code_analyzer.models import FileAnalysis, ClassInfo, FunctionInfo

@pytest.fixture
def mock_driver():
    with patch("tools.code_analyzer.neo4j_adapter.GraphDatabase.driver") as mock:
        driver_instance = MagicMock()
        session_instance = MagicMock()
        driver_instance.session.return_value.__enter__.return_value = session_instance
        mock.return_value = driver_instance
        yield driver_instance, session_instance

def test_init_schema(mock_driver):
    driver, session = mock_driver
    adapter = Neo4jAdapter("bolt://localhost:7687", ("neo4j", "pass"))
    
    adapter.init_schema()
    
    # Check if session.run was called for constraints
    assert session.run.call_count >= 3 
    # At least 4 constraint/index queries

def test_store_analysis(mock_driver):
    driver, session = mock_driver
    adapter = Neo4jAdapter("bolt://localhost:7687", ("neo4j", "pass"))
    
    analysis = FileAnalysis(
        file_path="src/main.py",
        functions=[FunctionInfo(name="main", args=[], start_line=1, end_line=5, returns=None, docstring=None)],
        classes=[
            ClassInfo(name="MyClass", bases=[], start_line=10, end_line=20, docstring=None, methods=[
                FunctionInfo(name="method1", args=["self"], start_line=11, end_line=15, returns=None, docstring=None)
            ])
        ]
    )
    
    adapter.store_analysis(analysis, "test-repo")
    
    # Verify calls
    # 1. File node merge
    # 2. Class node merge + rel
    # 3. Method node merge + rel
    # 4. Function node merge + rel
    
    assert session.run.call_count >= 4
