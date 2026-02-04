import pytest
from pathlib import Path
from src.tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser

class TestTreeSitterContext:

    def test_python_call_context(self):
        code = """
def parent_func():
    print("hello")
    
def other_func():
    obj.method()
"""
        parser = TreeSitterParser('python')
        analysis = parser.parse(code, Path("test.py"), Path("."))
        
        # Verify 'print' is called by 'parent_func'
        print_call = next(c for c in analysis.calls if c['callee'] == 'print')
        assert print_call['caller'] == 'parent_func'
        
        # Verify 'method' is called by 'other_func'
        method_call = next(c for c in analysis.calls if c['callee'] == 'method')
        assert method_call['caller'] == 'other_func'

    def test_global_call_context(self):
        code = """
print("global")

def my_func():
    pass
"""
        parser = TreeSitterParser('python')
        analysis = parser.parse(code, Path("test.py"), Path("."))
        
        call = next(c for c in analysis.calls if c['callee'] == 'print')
        assert call['caller'] == '<global>'
