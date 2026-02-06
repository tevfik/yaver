import pytest
from pathlib import Path
from src.tools.analysis.build_analyzer import BuildAnalyzer


@pytest.fixture
def sample_workspace(tmp_path):
    # Create a mock workspace
    (tmp_path / "Makefile").write_text(
        "all: main\n\nmain: main.c\n\tgcc -o main main.c\n", encoding="utf-8"
    )
    (tmp_path / "main.c").write_text("int main() { return 0; }", encoding="utf-8")
    (tmp_path / "go.mod").write_text("module example.com/foo", encoding="utf-8")
    (tmp_path / "app.go").write_text("package main", encoding="utf-8")
    return tmp_path


def test_detect_build_systems(sample_workspace):
    analyzer = BuildAnalyzer(str(sample_workspace))

    types = [sys["type"] for sys in analyzer.build_systems]
    assert "make" in types
    assert "go" in types
    assert "cmake" not in types


def test_get_build_context_makefile(sample_workspace):
    analyzer = BuildAnalyzer(str(sample_workspace))

    # Check context for main.c
    ctx = analyzer.get_build_context_for_file(str(sample_workspace / "main.c"))

    assert ctx["build_type"] == "make"
    # Our heuristic finds "main" because "main: main.c" match
    assert "make main" in ctx["commands"]


def test_get_build_context_go(sample_workspace):
    analyzer = BuildAnalyzer(str(sample_workspace))

    ctx = analyzer.get_build_context_for_file(str(sample_workspace / "app.go"))
    assert ctx["build_type"] == "go"
    assert "go test ./..." in ctx["commands"]
