import pytest
import os
import shutil
from pathlib import Path
from neo4j import GraphDatabase
from tools.code_analyzer.analyzer import CodeAnalyzer
from tools.code_analyzer.impact_analyzer import ImpactAnalyzer

SAMPLE_REPO = Path("tests/data/sample_repo_impact")

@pytest.fixture(scope="module")
def setup_sample_repo():
    """Create a temporary sample repository with a call chain"""
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)
    SAMPLE_REPO.mkdir(parents=True)
    
    # db.py
    (SAMPLE_REPO / "db.py").write_text("""
def connect():
    print("Connecting to DB")
""")

    # service.py
    (SAMPLE_REPO / "service.py").write_text("""
import db

def process_data():
    db.connect()
    print("Processing")
""")

    # controller.py
    (SAMPLE_REPO / "controller.py").write_text("""
import service

def handle_request():
    service.process_data()
""")

    # main.py
    (SAMPLE_REPO / "main.py").write_text("""
import controller

def main():
    controller.handle_request()

if __name__ == "__main__":
    main()
""")

    yield SAMPLE_REPO
    
    # Cleanup
    if SAMPLE_REPO.exists():
        shutil.rmtree(SAMPLE_REPO)

@pytest.fixture(scope="module")
def clean_db():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    auth = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
    driver = GraphDatabase.driver(uri, auth=auth)
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()
    return uri, auth

def test_impact_analysis_chain(setup_sample_repo, clean_db):
    """
    Test Impact Analysis on a 4-level call chain:
    main -> controller -> process_data -> connect
    Target: connect
    Expected: 
      - Direct: process_data
      - Transitive: handle_request (via process_data)
      # Note: My current depth limit is 2, so main might not show up if depth is hardcoded to 2.
    """
    uri, auth = clean_db
    repo_path = setup_sample_repo
    session_id = "test_integration_1"
    
    # 1. Run Analysis
    analyzer = CodeAnalyzer(session_id, repo_path)
    analyzer.connect_db(uri, auth)
    analyzer.analyze_repository()
    analyzer.close()
    
    # 2. Run Impact Analysis
    # We need a new driver or reusing the one from analyzer (but we closed it)
    impact_analyzer = ImpactAnalyzer(uri, auth)
    
    # Analyze 'connect' in 'db.py'
    # The ID construction in analyzer is usually 'file_path::function_name'
    # But files are relative or absolute? Analyzer uses relative to repo root usually or absolute.
    # Let's see how analyzer stores IDs. It uses file_id which is repo_name:rel_path usually.
    # In my previous code, I saw file_id = f"{repo_id}:{rel_path}"
    # And function_id = f"{file_id}::{func_name}"
    
    # So we search by function name "connect" which ends with "connect"
    
    result = impact_analyzer.analyze_function_change("connect", change_type="signature")
    
    print(f"Impact Result: {result}")
    
    assert result['risk_score'] > 0, "Risk score should be positive"
    
    # Check Direct Callers
    direct_names = [c['name'] for c in result['direct_callers']]
    assert "process_data" in direct_names
    
    # Check Transitive Callers
    transitive_names = [c['name'] for c in result['transitive_callers']]
    # handle_request calls process_data, so it should be transitive
    assert "handle_request" in transitive_names
    
    impact_analyzer.close()
