"""
Base Parser Interface
Defines the contract for language-specific parsers.
"""
from abc import ABC, abstractmethod
from typing import Optional, Union, Any
from pathlib import Path
from ..models import FileAnalysis

class BaseParser(ABC):
    """
    Abstract Base Class for Code Parsers.
    Implementations should handle specific languages (e.g., Python AST, Tree-sitter for C++).
    """

    @abstractmethod
    def parse(self, source_code: str, file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
        """
        Parse source code and return a FileAnalysis model.
        
        Args:
            source_code: Content of the file
            file_path: Absolute path to the file
            repo_root: Absolute path to the repository root
            
        Returns:
            FileAnalysis object if successful, None otherwise
        """
        pass
