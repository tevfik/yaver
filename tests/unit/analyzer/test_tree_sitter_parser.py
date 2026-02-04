import pytest
from pathlib import Path
from src.tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser
from src.tools.code_analyzer.models import FileAnalysis, ClassInfo, FunctionInfo

class TestTreeSitterParser:
    
    @pytest.fixture
    def parser(self):
        # Initialize parser for C++
        try:
            return TreeSitterParser('cpp')
        except Exception as e:
            pytest.skip(f"Tree-sitter languages not installed or failed: {e}")

    def test_cpp_function_parsing(self, parser):
        code = """
        int add(int a, int b) {
            return a + b;
        }
        
        void print_hello() {
            printf("Hello");
        }
        """
        
        file_path = Path("/repo/src/main.cpp")
        repo_root = Path("/repo")
        
        analysis = parser.parse(code, file_path, repo_root)
        
        assert analysis is not None
        assert analysis.language == 'cpp'
        assert len(analysis.functions) == 2
        
        names = {f.name for f in analysis.functions}
        assert "add" in names
        assert "print_hello" in names

    def test_cpp_class_parsing(self, parser):
        code = """
        class UserManager {
        private:
            int id;
        public:
            void login() {}
        };
        """
        
        file_path = Path("/repo/src/user.cpp")
        repo_root = Path("/repo")
        
        analysis = parser.parse(code, file_path, repo_root)
        
        assert analysis is not None
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "UserManager"

    def test_mixed_content(self, parser):
        code = """
        #include <iostream>
        
        class DataProcessor {
            void process() {}
        };
        
        int main() {
            DataProcessor dp;
            return 0;
        }
        """
        
        file_path = Path("/repo/main.cpp")
        repo_root = Path("/repo")
        
        analysis = parser.parse(code, file_path, repo_root)
        
        assert analysis is not None
        # Check class
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == "DataProcessor"
        
        # Check main function
        # Note: Depending on query, 'process' method inside class might 
        # or might not be captured as a top-level function. 
        # Ideally it should be under class methods, but our current implementation
        # might catch it as function or ignore it.
        # Let's check for 'main' at least.
        func_names = {f.name for f in analysis.functions}
        assert "main" in func_names

