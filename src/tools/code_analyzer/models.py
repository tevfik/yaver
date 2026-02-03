"""
Data Models for Code Analysis
Defines the structures used to represent code elements.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class FunctionInfo:
    """Represents a function or method definition"""
    name: str
    args: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    start_line: int
    end_line: int
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    complexity: int = 1
    body_summary: str = ""  # Hash or short snippet

@dataclass
class ClassInfo:
    """Represents a class definition"""
    name: str
    bases: List[str]
    docstring: Optional[str]
    start_line: int
    end_line: int
    methods: List[FunctionInfo] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

@dataclass
class ImportInfo:
    """Represents an import statement"""
    module: str
    names: List[str]  # e.g., ["Item", "Optional"]
    alias: Optional[str] = None
    level: int = 0  # 0=absolute, 1=., 2=..

@dataclass
class FileAnalysis:
    """Complete analysis result for a single file"""
    file_path: str  # Relative to repo root
    language: str = "python"
    classes: List[ClassInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)  # Top-level functions
    imports: List[ImportInfo] = field(default_factory=list)
    loc: int = 0
    last_modified: float = 0.0
    content_hash: str = ""
    # Phase 2 Additions
    calls: List[Dict[str, Any]] = field(default_factory=list)  # [{'caller': 'x', 'callee': 'y', 'line': 1}]
    resolved_imports: Dict[str, str] = field(default_factory=dict) # {'models': 'src/tools/models.py'}
