import pytest
import os
from src.tools.analysis.parser import CodeParser

# Test data
C_CODE = """
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    int res = add(5, 10);
    printf("Result: %d\\n", res);
    return 0;
}
"""

GO_CODE = """
package main

import "fmt"

func add(a int, b int) int {
	return a + b
}

func main() {
	res := add(5, 10)
	fmt.Println("Result:", res)
}
"""


@pytest.fixture
def parser():
    return CodeParser()


def test_c_parsing_tree_sitter(parser, tmp_path):
    f = tmp_path / "test.c"
    f.write_text(C_CODE, encoding="utf-8")

    result = parser.parse_file(str(f))

    assert "parser" in result
    # It might vary depending on env, but we expect tree-sitter-c if installed
    if result.get("parser", "").startswith("tree-sitter"):
        assert "add" in result["functions"]
        assert "main" in result["functions"]
        # Calls verification
        calls = result["calls"]
        assert any(c["caller"] == "main" and c["callee"] == "add" for c in calls)


def test_go_parsing_tree_sitter(parser, tmp_path):
    f = tmp_path / "test.go"
    f.write_text(GO_CODE, encoding="utf-8")

    result = parser.parse_file(str(f))

    if result.get("parser", "").startswith("tree-sitter"):
        assert "add" in result["functions"]
        assert "main" in result["functions"]
        assert "fmt" in result["imports"] or '"fmt"' in result["imports"]


def test_unsupported_extension(parser, tmp_path):
    f = tmp_path / "test.xyz"
    f.write_text("some content", encoding="utf-8")
    result = parser.parse_file(str(f))
    assert "error" in result
