# Yaver Language Capabilities

This file tracks the status of language supports in Yaver.

## Status Overview

| Language | Tree-Sitter Support | Static Analysis | Verification | Note |
| :--- | :---: | :---: | :---: | :--- |
| **Python** | ✅ | ✅ | ⚠️ | Only basic AST check. Need to add `python -m py_compile` |
| **C** | ✅ | ❌ | ❌ | Tree-sitter available. Parser uses regex fallback. |
| **C++** | ✅ | ❌ | ❌ | Tree-sitter available. Parser uses regex fallback. |
| **JavaScript** | ✅ | ❌ | ❌ | Tree-sitter available. |
| **TypeScript** | ✅ | ❌ | ❌ | Tree-sitter available. |
| **Java** | ✅ | ❌ | ❌ | Tree-sitter available. |
| **C#** | ✅ | ❌ | ❌ | Tree-sitter available. |

## Action Items

1.  **Refactor Parser**: Update `src/tools/analysis/parser.py` to use `tree_sitter_languages` instead of regex for C/C++.
2.  **Integrate Verification**: Add `gcc/clang` checks for C/C++ files in the verification phase.
