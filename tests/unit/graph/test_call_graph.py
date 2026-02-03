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
    # MyClass().method_b() -> parsed as chain
    # It might come out as 'MyClass().method_b' or similar depending on implementation
    # Let's check what we got if failure persists, but based on recursive implementation:
    # MyClass() is a Call, not Name/Attribute, so _get_func_name might return None for the base if it's complex
    # Let's see what the builder actually produced for this line: MyClass().method_b()
    assert "method_b" in calls_other
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
