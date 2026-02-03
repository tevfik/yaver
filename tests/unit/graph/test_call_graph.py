import ast
import pytest
from tools.code_analyzer.call_graph import CallGraphBuilder

CODE_SAMPLE = """
class MyClass:
    def method_a(self):
        self.method_b()
        other_func()

    def method_b(self):
        print("B")

def other_func():
    MyClass().method_b()
    nested_call(helper())
"""

def test_call_graph_builder():
    tree = ast.parse(CODE_SAMPLE)
    visited = CallGraphBuilder().build(tree)
    
    # helper to find calls
    def find_calls(caller):
        return [c['callee'] for c in visited if c['caller'] == caller]

    # method_a calls method_b and other_func
    calls_a = find_calls("MyClass.method_a")
    # _get_func_name captures full attribute path "self.method_b"
    assert "self.method_b" in calls_a 
    assert "other_func" in calls_a
    
    # other_func calls MyClass, method_b, nested_call, helper
    calls_other = find_calls("other_func")
    assert "MyClass" in calls_other
    # MyClass().method_b() -> now parsed as dynamic pattern 'MyClass(...).Result.method_b'
    # Check that we captured the call pattern
    dynamic_calls = [c for c in calls_other if "method_b" in c]
    assert len(dynamic_calls) > 0, f"Expected method_b call, got: {calls_other}"
    assert "nested_call" in calls_other
    assert "helper" in calls_other


def test_nested_calls():
    code = "fn(a(b()))"
    tree = ast.parse(code)
    calls = CallGraphBuilder().build(tree)
    
    callees = [c['callee'] for c in calls]
    assert "fn" in callees
    assert "a" in callees
    assert "b" in callees
