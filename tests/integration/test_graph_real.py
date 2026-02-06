import pytest
import os
import shutil
from src.tools.graph.networkx_adapter import NetworkXAdapter


class TestGraphReal:
    def setup_method(self):
        self.db_path = "/tmp/test_context_graph.pkl"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_local_call_linking(self):
        # Test linking within same file
        adapter = NetworkXAdapter(self.db_path)
        repo = "test_repo"
        file = "math.py"

        # 1. Store File Node
        adapter.store_file_node(file, repo, "python", 20)

        # 2. Store Structure with Calls
        structure = {
            "functions": ["compute", "add"],
            "calls": [{"caller": "compute", "callee": "add"}],
        }

        adapter.store_code_structure(file, repo, structure)

        # 3. Verify Context
        context = adapter.get_context_for_file(file, repo)

        # Expectation: "compute" calls "add" should be visible
        assert "Defines: compute, add" in context
        assert "calls 'add'" in context

    def test_cross_file_linking_simulated(self):
        adapter = NetworkXAdapter(self.db_path)
        repo = "test_repo"
        file = "main.py"

        adapter.store_file_node(file, repo, "python", 50)

        structure = {
            "functions": ["main"],
            "imports": ["utils", "math"],
            "calls": [],  # Cross-file calls would be here in real scenario
        }
        adapter.store_code_structure(file, repo, structure)

        context = adapter.get_context_for_file(file, repo)

        assert "Imports: utils, math" in context
        assert "Defines: main" in context
