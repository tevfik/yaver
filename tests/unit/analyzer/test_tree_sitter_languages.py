import pytest
from pathlib import Path
from src.tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser

class TestTreeSitterLanguages:

    def test_parse_python(self):
        code = """
class MyClass:
    def my_method(self):
        pass

def global_func():
    return 1
"""
        parser = TreeSitterParser('python')
        analysis = parser.parse(code, Path("test.py"), Path("."))
        
        assert analysis is not None
        assert analysis.language == 'python'
        
        # Verify classes
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == 'MyClass'
        assert analysis.classes[0].start_line == 2
        
        # Verify functions
        func_names = [f.name for f in analysis.functions]
        # order is not guaranteed by captures? usually document order.
        assert 'my_method' in func_names
        assert 'global_func' in func_names
        
        # Check specific details for global_func
        gf = next(f for f in analysis.functions if f.name == 'global_func')
        assert gf.start_line == 6

    def test_parse_go(self):
        code = """
package main

type MyStruct struct {
    Field int
}

func GlobalFunc() {
}

func (m *MyStruct) Method() {
}
"""
        parser = TreeSitterParser('go')
        analysis = parser.parse(code, Path("test.go"), Path("."))
        
        assert analysis is not None
        assert analysis.language == 'go'
        
        # Verify types (Classes)
        assert len(analysis.classes) == 1
        assert analysis.classes[0].name == 'MyStruct'
        assert analysis.classes[0].start_line == 4
        
        # Verify functions and methods
        func_names = [f.name for f in analysis.functions]
        assert 'GlobalFunc' in func_names
        assert 'Method' in func_names
        
        # Check details
        method = next(f for f in analysis.functions if f.name == 'Method')
        assert method.start_line == 11
