import unittest
import ast
import sys
import os

# Add src to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src"))
)

from tools.code_analyzer.ast_parser import AnalysisVisitor


class TestComplexity(unittest.TestCase):
    def test_complexity_calculation(self):
        visitor = AnalysisVisitor()

        # Simple function
        code1 = """
def simple():
    print("hello")
"""
        node1 = ast.parse(code1).body[0]
        self.assertEqual(visitor._calculate_cyclomatic_complexity(node1), 1)

        # Branching
        code2 = """
def complex_one(x):
    if x > 0:
        return 1
    else:
        return 0
"""
        node2 = ast.parse(code2).body[0]
        self.assertEqual(visitor._calculate_cyclomatic_complexity(node2), 2)  # 1 + 1 if

        # Loops and Boolean Ops
        code3 = """
def loops_and_bools(items):
    for i in items: # +1
        if i and (x or y): # +1 (if), +1 (and), +1 (or) = +3
            print(i)
"""
        # Complexity breakdown:
        # Base: 1
        # For loop: +1
        # If: +1
        # BoolOp (and): +1 (implicit in syntax, strictly logic gate count?)
        # BoolOp (or): +1
        # Total: 1 + 1 + 1 + 2 = 5?

        # AST for `i and (x or y)` is a single BoolOp(op=And, values=[i, BoolOp(op=Or, values=[x, y])])
        # Outer BoolOp (And) has 2 values -> +1
        # Inner BoolOp (Or) has 2 values -> +1
        # Total added by bools: 2
        # Total expected: 1 (base) + 1 (for) + 1 (if) + 2 (bools) = 5

        node3 = ast.parse(code3).body[0]
        self.assertEqual(visitor._calculate_cyclomatic_complexity(node3), 5)


if __name__ == "__main__":
    unittest.main()
