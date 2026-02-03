"""
Call Graph Builder
Analyzes AST to extract function call relationships within the code.
"""
import ast
from typing import List, Dict, Set, Optional
from .models import FunctionInfo

class CallGraphBuilder(ast.NodeVisitor):
    def __init__(self):
        self.calls: List[Dict[str, str]] = []  # List of {caller, callee}
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None

    def build(self, tree: ast.AST) -> List[Dict[str, str]]:
        """
        Traverses AST and returns a list of calls found.
        Format: [{'caller': 'MyClass.method', 'callee': 'other_func', 'line': 10}]
        """
        self.calls = []
        self.visit(tree)
        return self.calls

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node)

    def _handle_function(self, node):
        prev_func = self.current_function
        
        func_name = node.name
        if self.current_class:
            func_name = f"{self.current_class}.{func_name}"
            
        self.current_function = func_name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node: ast.Call):
        if not self.current_function:
            # Call at module level
            caller = "<module>"
        else:
            caller = self.current_function
            
        callee_name, confidence, is_dynamic = self._get_func_name_info(node.func)
        
        if callee_name:
            self.calls.append({
                "caller": caller,
                "callee": callee_name,
                "line": node.lineno,
                "confidence": confidence,
                "is_dynamic": is_dynamic
            })
            
        self.generic_visit(node)

    def _get_func_name_info(self, node) -> tuple[Optional[str], float, bool]:
        """
        Convert AST node to dotted string name, confidence score, and dynamic flag.
        Returns: (name, confidence, is_dynamic)
        """
        if isinstance(node, ast.Name):
            return node.id, 1.0, False
        elif isinstance(node, ast.Attribute):
            # recursive for things like os.path.join
            value, conf, dyn = self._get_func_name_info(node.value)
            if value:
                return f"{value}.{node.attr}", conf, dyn
            return node.attr, 1.0, False
        
        # Dynamic handling start
        elif isinstance(node, ast.Call):
            # e.g. get_handler().process() - we can't be sure what get_handler returns
            # So we treat this as a lower confidence call if we can extract a partial name
            name, _, _ = self._get_func_name_info(node.func)
            if name:
                return f"{name}(...).Result", 0.5, True
        # Dynamic handling end
            
        return None, 0.0, False

    def _get_func_name(self, node) -> Optional[str]:
        # Legacy Wrapper
        name, _, _ = self._get_func_name_info(node)
        return name

