"""
Syntax Checker Module
Provides a unified interface for checking code syntax using local tools (gcc, clang, etc.)
with a fallback to LLM-based verification.
"""

import subprocess
import shutil
import os
import ast
import tempfile
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger("yaver.tools.syntax")


@dataclass
class SyntaxCheckResult:
    valid: bool
    error_message: Optional[str] = None
    tool_used: str = "unknown"
    is_fallback: bool = False


class SyntaxChecker:
    """
    Checks syntax of code files using best available method:
    1. Local Compiler/Linter (Ground Truth)
    2. LLM Analysis (Fallback)
    """

    def __init__(self):
        self.supported_extensions = {
            ".c": ["gcc", "clang"],
            ".cpp": ["g++", "clang++", "gcc"],
            ".cc": ["g++", "clang++", "gcc"],
            ".h": ["gcc", "clang"],  # Headers are tricky, often need context
            ".hpp": ["g++", "clang++"],
            ".py": ["python"],
            ".go": ["go"],
            ".js": ["node"],
            ".ts": ["tsc"],
        }

    def check(self, file_path: str) -> SyntaxCheckResult:
        """
        Check syntax of the given file.
        """
        path = Path(file_path)
        if not path.exists():
            return SyntaxCheckResult(False, f"File not found: {file_path}", "fs")

        ext = path.suffix.lower()

        # 1. Try Local Tools
        if ext in self.supported_extensions:
            candidates = self.supported_extensions[ext]
            for tool in candidates:
                if tool == "python":
                    return self._check_python(path)

                tool_path = shutil.which(tool)
                if tool_path:
                    logger.info(f"Checking {path.name} using local tool: {tool}")
                    return self._check_with_tool(tool, path)

        # 2. Fallback to LLM
        return self._check_with_llm(path)

    def _check_python(self, path: Path) -> SyntaxCheckResult:
        """Check Python syntax using built-in ast module."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            ast.parse(content)
            return SyntaxCheckResult(True, tool_used="ast.parse")
        except SyntaxError as e:
            return SyntaxCheckResult(
                False, f"Line {e.lineno}: {e.msg}", tool_used="ast.parse"
            )
        except Exception as e:
            return SyntaxCheckResult(False, str(e), tool_used="ast.parse")

    def _check_with_tool(self, tool_name: str, path: Path) -> SyntaxCheckResult:
        """Run external command to check syntax."""
        cmd = []

        # Define commands for each tool (syntax-only modes)
        if tool_name in ["gcc", "g++", "clang", "clang++"]:
            # -fsyntax-only: Check for syntax errors, but don't emit code
            # -x: Explicitly specify language if needed (optional usually)
            cmd = [tool_name, "-fsyntax-only", str(path)]

            # For C++, we might need to suppress linker errors or include issues if we just want syntax
            # But -fsyntax-only usually handles this well for single files.

        elif tool_name == "go":
            # 'go vet' works on packages. 'go tool compile' is lower level.
            # 'go fmt' is a weak check.
            # 'go build' with -o /dev/null is robust.
            cmd = ["go", "build", "-o", os.devnull, str(path)]

        elif tool_name == "node":
            # node --check (since Node 10)
            cmd = ["node", "--check", str(path)]

        elif tool_name == "tsc":
            # tsc --noEmit
            cmd = ["tsc", "--noEmit", str(path)]

        if not cmd:
            return SyntaxCheckResult(
                False,
                f"Tool configuration missing for {tool_name}",
                tool_used=tool_name,
            )

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode == 0:
                return SyntaxCheckResult(True, tool_used=tool_name)
            else:
                # Combine stdout and stderr
                msg = (result.stderr + "\n" + result.stdout).strip()
                return SyntaxCheckResult(False, msg, tool_used=tool_name)

        except Exception as e:
            return SyntaxCheckResult(
                False, f"Tool execution failed: {str(e)}", tool_used=tool_name
            )

    def _check_with_llm(self, path: Path) -> SyntaxCheckResult:
        """Fallback to LLM for syntax checking."""
        logger.warning(
            f"No local tool found for {path.suffix}. Falling back to LLM analysis."
        )

        try:
            # Lazy import to avoid circular dependencies
            from src.agents.agent_base import create_llm
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = create_llm("code")  # Use code specialized model

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            prompt = f"""
            You are a strict code compiler/linter.
            Analyze the following code for SYNTAX ERRORS only.
            Do not complain about style, imports, or logic bugs unless they prevent compilation/parsing.

            Filename: {path.name}
            Language (inferred): {path.suffix}

            CODE:
            ```
            {content}
            ```

            Response Format:
            If valid: "VALID"
            If invalid: "INVALID: <concise error message with line number>"
            """

            response = llm.invoke(
                [
                    SystemMessage(
                        content="You are a syntax check tool. Output only VALID or INVALID status."
                    ),
                    HumanMessage(content=prompt),
                ]
            )

            result_text = response.content.strip()

            if result_text.startswith("VALID"):
                return SyntaxCheckResult(
                    True, tool_used="llm-fallback", is_fallback=True
                )
            else:
                error_msg = result_text.replace("INVALID:", "").strip()
                return SyntaxCheckResult(
                    False, error_msg, tool_used="llm-fallback", is_fallback=True
                )

        except Exception as e:
            return SyntaxCheckResult(
                False,
                f"LLM Fallback failed: {str(e)}",
                tool_used="llm-fallback-error",
                is_fallback=True,
            )
