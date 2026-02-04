"""
Import Resolver
Resolves Python import statements to actual file paths and module names within the repository.
"""
import os
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from .models import ImportInfo


class ImportResolver:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        # Map module paths to file paths for faster lookup
        self.module_map: Dict[str, Path] = {}
        self._build_module_map()

    def _build_module_map(self):
        """
        Scans the repo to map module names (e.g. 'tools.code_analyzer') to file paths.
        Pre-computes this to avoid disk I/O during analysis.
        """
        for root, _, files in os.walk(self.repo_root):
            for file in files:
                if file.endswith(".py"):
                    full_path = Path(root) / file
                    try:
                        rel_path = full_path.relative_to(self.repo_root)
                        # src/tools/analyzer.py -> src.tools.analyzer
                        # __init__.py files represent the parent package
                        parts = list(rel_path.with_suffix("").parts)

                        if parts[-1] == "__init__":
                            parts = parts[:-1]

                        module_name = ".".join(parts)
                        self.module_map[module_name] = rel_path
                    except ValueError:
                        continue

    def resolve_import(self, imp: ImportInfo, current_file: Path) -> Optional[Path]:
        """
        Resolves an import to a physical file path in the repo.
        Returns None if it's likely a standard library or external package.
        """
        # 1. Handle Relative Imports (e.g., from . import models)
        if imp.level > 0:
            return self._resolve_relative(imp, current_file)

        # 2. Handle Absolute Imports
        return self._resolve_absolute(imp.module)

    def _resolve_absolute(self, module_name: str) -> Optional[Path]:
        """
        Tries to find the module in the internal map.
        Handles partial matches (importing a package vs a module).
        """
        if not module_name:
            return None

        # Exact match
        if module_name in self.module_map:
            return self.module_map[module_name]

        # Check if it imports a class/function from a module
        # e.g. from tools.models import User -> tools.models might be the file
        parts = module_name.split(".")
        while parts:
            partial_name = ".".join(parts)
            if partial_name in self.module_map:
                return self.module_map[partial_name]
            parts.pop()

        return None

    def _resolve_relative(self, imp: ImportInfo, current_file: Path) -> Optional[Path]:
        """
        Resolves relative imports based on the current file's location.
        level 1 = ., level 2 = ..
        """
        try:
            # Current package path
            current_pkg = current_file.parent.relative_to(self.repo_root)

            # Go up (level - 1) times
            # from . import x -> level 1 -> stay in same dir
            # from .. import x -> level 2 -> go up 1 dir
            target_pkg = current_pkg
            for _ in range(imp.level - 1):
                target_pkg = target_pkg.parent

            # Consturct target module name
            if imp.module:
                target_module_parts = list(target_pkg.parts) + imp.module.split(".")
            else:
                # from . import something (module is None, names has "something")
                # This is tricky because "something" could be a file or a symbol.
                # Use _resolve_absolute logic on the path constructed so far
                target_module_parts = list(target_pkg.parts)

            target_module_name = ".".join(target_module_parts)

            # Check map
            if target_module_name in self.module_map:
                return self.module_map[target_module_name]

            # Try appending the first name from 'names' if module was None
            # e.g. from . import utils -> utils might be the file
            if not imp.module and imp.names:
                potential_name = f"{target_module_name}.{imp.names[0]}"
                if potential_name in self.module_map:
                    return self.module_map[potential_name]

            return None

        except ValueError:
            return None
