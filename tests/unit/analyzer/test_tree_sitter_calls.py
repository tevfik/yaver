import pytest
from pathlib import Path
from src.tools.code_analyzer.parsers.tree_sitter_parser import TreeSitterParser

class TestTreeSitterCalls:

    def test_parse_python_calls(self):
        code = """
def main():
    print("hello")
    obj.method()
"""
        parser = TreeSitterParser('python')
        analysis = parser.parse(code, Path("test.py"), Path("."))
        
        calls = [c['callee'] for c in analysis.calls]
        assert 'print' in calls
        assert 'method' in calls

    def test_parse_go_calls(self):
        code = """
func main() {
    fmt.Println("hello")
    myFunc()
}
"""
        parser = TreeSitterParser('go')
        analysis = parser.parse(code, Path("test.go"), Path("."))
        
        calls = [c['callee'] for c in analysis.calls]
        assert 'Println' in calls
        assert 'myFunc' in calls

    def test_parse_cpp_calls(self):
        code = """
int main() {
    std::cout << "hello";
    my_func();
    obj.method();
    return 0;
}
"""
        parser = TreeSitterParser('cpp')
        analysis = parser.parse(code, Path("test.cpp"), Path("."))
        
        calls = [c['callee'] for c in analysis.calls]
        assert 'my_func' in calls
        assert 'method' in calls
