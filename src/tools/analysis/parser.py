"""
Code Parser Module
Extracted from git_analysis.py
"""

import ast
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import re

# Attempt to import tree-sitter-languages
TREE_SITTER_AVAILABLE = False
try:
    from tree_sitter_languages import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    pass


class CodeParser:
    """Parses code to extract structural information (AST-based + Tree-Sitter + Regex fallback)."""

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a file to extract functions, classes, and calls."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        # Map extensions to tree-sitter languages
        # We prefer Python's built-in AST for Python as it's very reliable
        ts_lang_map = {
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".cc": "cpp",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cs": "c_sharp",
            ".rs": "rust",
            ".go": "go",
        }

        if suffix == ".py":
            return self._parse_python(path)

        # Try Tree-Sitter if available and language is supported
        if TREE_SITTER_AVAILABLE and suffix in ts_lang_map:
            try:
                lang_name = ts_lang_map[suffix]
                return self._parse_tree_sitter(path, lang_name)
            except Exception as e:
                # If tree-sitter fails (e.g. grammar not installed), log/pass and fall back
                pass

        # Fallback for known C-like extensions or failed TS
        if suffix in [
            ".c",
            ".cpp",
            ".cc",
            ".h",
            ".hpp",
            ".java",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".cs",
            ".php",
        ]:
            return self._parse_generic_regex(path)

        return {"error": "Unsupported file type", "details": f"No parser for {suffix}"}

    def _parse_python(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            tree = ast.parse(content)

            functions = [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
            ]
            classes = [
                node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            imports = [
                node.names[0].name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
            ]
            imports += [
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            ]

            # Extract calls
            calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    caller_name = node.name
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            func = child.func
                            callee_name = None
                            if isinstance(func, ast.Name):
                                callee_name = func.id
                            elif isinstance(func, ast.Attribute):
                                callee_name = func.attr

                            if callee_name:
                                calls.append(
                                    {"caller": caller_name, "callee": callee_name}
                                )

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(content.splitlines()),
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_tree_sitter(self, path: Path, lang_name: str) -> Dict[str, Any]:
        """Parse file using tree-sitter."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            language = get_language(lang_name)
            parser = get_parser(lang_name)
            tree = parser.parse(bytes(content, "utf8"))

            queries = self._get_ts_queries(lang_name)

            functions = []
            classes = []
            calls = []
            imports = []

            # Imports
            if "import" in queries:
                q = language.query(queries["import"])
                for node, _ in q.captures(tree.root_node):
                    imports.append(content[node.start_byte : node.end_byte])

            # Classes
            if "class" in queries:
                q = language.query(queries["class"])
                for node, _ in q.captures(tree.root_node):
                    classes.append(content[node.start_byte : node.end_byte])

            # Functions and Calls (Scoped)
            # If we generally support function scoping
            if "function_scope" in queries and "function_name" in queries:
                q_scope = language.query(queries["function_scope"])
                q_name = language.query(queries["function_name"])
                q_call = language.query(queries["call"]) if "call" in queries else None

                for node, name in q_scope.captures(tree.root_node):
                    if name == "def":
                        # Find function name within this definition
                        func_name = "unknown"
                        name_captures = q_name.captures(node)
                        if name_captures:
                            # Heuristic: The function name is usually one of the first identifiers
                            # in the declarator chain.
                            n_node, _ = name_captures[0]
                            func_name = content[n_node.start_byte : n_node.end_byte]

                        functions.append(func_name)

                        # Find calls inside this function
                        if q_call:
                            for c_node, _ in q_call.captures(node):
                                callee = content[c_node.start_byte : c_node.end_byte]
                                calls.append({"caller": func_name, "callee": callee})

            # Fallback for languages where we didn't define strict scope queries yet
            # just extract top level stuff if scope query missing
            elif "function" in queries:
                q = language.query(queries["function"])
                for node, _ in q.captures(tree.root_node):
                    functions.append(content[node.start_byte : node.end_byte])

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(content.splitlines()),
                "parser": f"tree-sitter:{lang_name}",
            }
        except Exception as e:
            # If tree-sitter parsing fails, the main parse_file will catch it
            # and attempt regex fallback
            raise e

    def _get_ts_queries(self, lang: str) -> Dict[str, str]:
        if lang == "cpp":
            return {
                "class": "(class_specifier name: (type_identifier) @name)",
                "import": "(preproc_include path: (_) @name)",
                "function_scope": "(function_definition) @def",
                "function_name": "(function_declarator declarator: (identifier) @name)",
                "call": "(call_expression function: (identifier) @name)",
            }
        if lang == "c":
            return {
                "import": "(preproc_include path: (_) @name)",
                "function_scope": "(function_definition) @def",
                "function_name": "(function_declarator declarator: (identifier) @name)",
                "call": "(call_expression function: (identifier) @name)",
            }
        if lang in ["javascript", "typescript", "tsx"]:
            return {
                "class": "(class_declaration name: (_) @name)",
                "import": "(import_statement source: (string) @name)",
                "function_scope": """
                    (function_declaration) @def
                    (method_definition) @def
                 """,
                "function_name": """
                    (function_declaration name: (identifier) @name)
                    (method_definition name: (property_identifier) @name)
                 """,
                "call": "(call_expression function: (identifier) @name)",
            }
        if lang in ["java", "c_sharp"]:
            return {
                "class": "(class_declaration name: (identifier) @name)",
                "function_scope": "(method_declaration) @def",
                "function_name": "(method_declaration name: (identifier) @name)",
                "call": "(method_invocation name: (identifier) @name)",
            }
        if lang == "go":
            return {
                "import": "(import_spec path: (interpreted_string_literal) @name)",
                "function_scope": """
                    (function_declaration) @def
                    (method_declaration) @def
                """,
                "function_name": """
                    (function_declaration name: (identifier) @name)
                    (method_declaration name: (field_identifier) @name)
                """,
                "call": "(call_expression function: (identifier) @name)",
            }
        return {}

    def _parse_generic_regex(self, path: Path) -> Dict[str, Any]:
        """Simple regex based parser for C-like languages."""

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Simple C-function regex: Type Name(Args) {
            # Limiting to common C patterns to avoid false positives
            # Improved regex to handle pointers and attributes better
            func_pattern = re.compile(r"^\s*(?:[\w\*]+\s+)+(\w+)\s*\(", re.MULTILINE)
            raw_functions = func_pattern.findall(content)

            # Filter out control structures that look like function definitions (e.g. "else if")
            # We allow 'main' because it's a critical entry point function
            blacklist = {
                "if",
                "while",
                "switch",
                "for",
                "catch",
                "return",
                "sizeof",
                "else",
                "define",
            }
            functions = [f for f in raw_functions if f not in blacklist]

            # Classes (for C++/Java)
            class_pattern = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
            classes = class_pattern.findall(content)

            # Includes/Imports
            imports = []
            include_pattern = re.compile(r'#include\s+[<"](.+)[>"]')
            imports.extend(include_pattern.findall(content))

            # Calls - this is hard with detailed scope parsing using just regex.
            calls = []
            current_func = None

            lines = content.splitlines()
            for line in lines:
                # Check for function start
                func_match = func_pattern.search(line)
                if func_match and "{" in line:  # Basic heuristics
                    current_func = func_match.group(1)
                    continue

                if current_func:
                    # Look for calls:  func_name(
                    call_matches = re.findall(r"(\w+)\s*\(", line)
                    for callee in call_matches:
                        if callee not in blacklist and callee != current_func:
                            calls.append({"caller": current_func, "callee": callee})

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(lines),
            }
        except Exception as e:
            return {"error": str(e)}
