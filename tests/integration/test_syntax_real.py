import pytest
import shutil
import os
from src.tools.analysis.syntax import SyntaxChecker


# Helper to check if tool exists
def has_tool(name):
    return shutil.which(name) is not None


@pytest.fixture
def checker():
    return SyntaxChecker()


def test_python_syntax_valid(checker, tmp_path):
    f = tmp_path / "valid.py"
    f.write_text("def foo():\n    pass", encoding="utf-8")
    result = checker.check(str(f))
    assert result.valid is True
    assert result.tool_used == "ast.parse"


def test_python_syntax_invalid(checker, tmp_path):
    f = tmp_path / "invalid.py"
    f.write_text("def foo(\n    pass", encoding="utf-8")
    result = checker.check(str(f))
    assert result.valid is False
    assert "Line 1" in result.error_message


@pytest.mark.skipif(not has_tool("gcc"), reason="GCC not installed")
def test_c_syntax_gcc(checker, tmp_path):
    f = tmp_path / "test.c"
    # Valid C
    f.write_text("int main() { return 0; }", encoding="utf-8")
    result = checker.check(str(f))
    assert result.valid is True
    assert result.tool_used == "gcc"

    # Invalid C
    f = tmp_path / "test_invalid.c"
    f.write_text("int main() { return 0", encoding="utf-8")
    result = checker.check(str(f))
    assert result.valid is False
    assert result.tool_used == "gcc"
    assert "error" in result.error_message.lower()


# We can mock the LLM fallback or assume it won't run in CI without keys
# For integration test, we might skip the actual LLM call if no KEY, or mock it.
# Here we will just verify that it attempts fallback if tool is missing.


def test_fallback_trigger_mechanism(checker, tmp_path):
    """
    Manipulate internal supported_extensions to force fallback logic
    without actually calling the LLM (to save costs/avoid auth errors in test).
    Or we can mock the _check_with_llm method.
    """
    f = tmp_path / "fallback.c"
    f.write_text("int main() {}", encoding="utf-8")

    # Sabotage
    original_c = checker.supported_extensions.get(".c")
    checker.supported_extensions[".c"] = ["non_existent_tool_xyz"]

    # Mock _check_with_llm to avoid network call
    def mock_llm_check(path):
        from src.tools.analysis.syntax import SyntaxCheckResult

        return SyntaxCheckResult(True, tool_used="mock-llm", is_fallback=True)

    # Monkeypatch
    checker._check_with_llm = mock_llm_check

    result = checker.check(str(f))

    # Restore
    if original_c:
        checker.supported_extensions[".c"] = original_c

    assert result.is_fallback is True
    assert result.tool_used == "mock-llm"
