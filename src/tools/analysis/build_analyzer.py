"""
Build Analyzer Module
Identifies build systems and specific build contexts for files.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import re


class BuildAnalyzer:
    """Analyzes workspace to understand build environment"""

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.build_systems = []
        self._detect_build_systems()

    def _detect_build_systems(self):
        """Identify what build systems are present."""
        if (self.workspace_root / "Makefile").exists():
            self.build_systems.append({"type": "make", "file": "Makefile"})

        if (self.workspace_root / "CMakeLists.txt").exists():
            self.build_systems.append({"type": "cmake", "file": "CMakeLists.txt"})

        if (self.workspace_root / "go.mod").exists():
            self.build_systems.append({"type": "go", "file": "go.mod"})

        if (self.workspace_root / "package.json").exists():
            self.build_systems.append({"type": "npm", "file": "package.json"})

    def get_build_context_for_file(self, file_path: str) -> Dict[str, Any]:
        """
        Determines how a specific file is built (naively).
        """
        path = Path(file_path).absolute()
        rel_path = path.relative_to(self.workspace_root)

        context = {"build_type": "unknown", "commands": []}

        # 1. Makefile Heuristics
        makefile_info = next(
            (sys for sys in self.build_systems if sys["type"] == "make"), None
        )
        if makefile_info:
            targets = self._analyze_makefile(self.workspace_root / "Makefile", rel_path)
            if targets:
                context["build_type"] = "make"
                context["commands"] = [f"make {t}" for t in targets]
                return context

        # 2. Go Heuristics
        if path.suffix == ".go":
            context["build_type"] = "go"
            # In Go, we test the package usually
            context["commands"] = [f"go test ./...", "go build ./..."]
            return context

        return context

    def _analyze_makefile(
        self, makefile_path: Path, rel_source_path: Path
    ) -> List[str]:
        """
        Basic regex parsing of Makefile to find targets that might depend on the file.
        This is not a full parser, just heuristics.
        """
        try:
            with open(makefile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for targets that explicitly mention the file (e.g. main.o: main.c)
            # or generic patterns %.o: %.c

            targets = []

            # Simple direct match
            # target: ... dependency ...
            # We look for lines starting with 'target:' that contain the filename
            file_name = rel_source_path.name

            # Regex for target definitions
            target_pattern = re.compile(r"^(\w+):.*" + re.escape(file_name))

            for line in content.splitlines():
                match = target_pattern.match(line)
                if match:
                    targets.append(match.group(1))

            # Removed aggressive fallback to "all" to avoid false positives for unrelated files
            # if not targets and "all" in content:
            #      targets.append("all")

            return targets
        except Exception:
            return []
