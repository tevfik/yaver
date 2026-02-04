"""
Code Chunking Strategy

This module handles the logic of preparing code entities (functions, classes)
for embedding. It optimizes the text representation to improve retrieval quality.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import logging

from .models import FileAnalysis, FunctionInfo, ClassInfo

logger = logging.getLogger(__name__)

@dataclass
class CodeChunk:
    """Represents a prepared chunk of code for embedding"""
    chunk_id: str
    text_content: str  # The optimized text to be embedded
    metadata: Dict[str, Any]
    original_source: str # The actual code

class CodeChunker:
    """
    Splits file analysis results into semantic chunks.
    Uses context-aware strategies:
    - Include docstrings and signatures prominently.
    - Tag with file path and type.
    """

    def __init__(self, max_tokens: int = 500):
        self.max_tokens = max_tokens

    def chunk_file(self, file_analysis: FileAnalysis, source_code: str) -> List[CodeChunk]:
        """
        Generate chunks from a file analysis object and its source.
        """
        chunks = []
        lines = source_code.splitlines()
        rel_path = file_analysis.file_path

        # 1. Chunk Functions
        for func in file_analysis.functions:
            chunk = self._create_function_chunk(func, lines, rel_path)
            if chunk:
                chunks.append(chunk)

        # 2. Chunk Classes (and their methods)
        for cls in file_analysis.classes:
            # Create a chunk for the class definition itself (docstring + init?)
            class_chunk = self._create_class_chunk(cls, lines, rel_path)
            if class_chunk:
                chunks.append(class_chunk)
            
            # Chunk methods
            for method in cls.methods:
                method_chunk = self._create_method_chunk(method, cls.name, lines, rel_path)
                if method_chunk:
                    chunks.append(method_chunk)
                    
        # 3. If no structural chunks found (e.g., non-Python or flat script)
        # Create a generic file chunk
        if not chunks and source_code.strip():
            # Simple content truncation for now
            # TODO: Implement sliding window for large files
            description = f"Content of file {rel_path}"
            
            # Reduce fallback chunk size to 600 chars to avoid NaN issues with some embedding models
            # on large blocks of text (especially repetitive ones like config files)
            safe_content = source_code[:600]
            
            chunks.append(CodeChunk(
                chunk_id=f"{rel_path}::whole",
                text_content=f"File: {rel_path}\nType: File Content\nLanguage: {file_analysis.language}\n\n{safe_content}",
                metadata={
                    "id": f"{rel_path}::whole",
                    "file_path": rel_path,
                    "type": "file",
                    "name": rel_path.split("/")[-1],
                    "language": file_analysis.language
                },
                original_source=source_code[:3000]
            ))
                    
        return chunks

    def _extract_source(self, start: int, end: int, lines: List[str]) -> str:
        """Extract lines 1-based inclusive"""
        if 0 < start <= len(lines) and 0 < end <= len(lines):
            return "\n".join(lines[start-1:end])
        return ""

    def _create_function_chunk(self, func: FunctionInfo, lines: List[str], file_path: str) -> Optional[CodeChunk]:
        source = self._extract_source(func.start_line, func.end_line, lines)
        if not source.strip():
            return None
            
        # Construct optimized text representation
        # Format:
        # File: path/to/file.py
        # Type: Function
        # Name: my_func
        # Signature: def my_func(a, b) -> int
        # Docstring: ...
        # Code: ...
        
        signature = f"def {func.name}({', '.join(func.args)})"
        if func.returns:
            signature += f" -> {func.returns}"
            
        doc_part = f"\nDocstring: {func.docstring}" if func.docstring else ""
        
        # Limit code body length for embedding (keep start)
        # Aggressive truncation to avoid NaN errors from embedding model
        truncated_code = source[:800] # Reduced to avoid problematic patterns
        
        text_content = (
            f"File: {file_path}\n"
            f"Type: Function\n"
            f"Name: {func.name}\n"
            f"Signature: {signature}"
            f"{doc_part}\n"
            f"Code:\n{truncated_code}"
        )
        
        return CodeChunk(
            chunk_id=f"{file_path}::{func.name}",
            text_content=text_content,
            metadata={
                "type": "function",
                "name": func.name,
                "file_path": file_path,
                "start_line": func.start_line,
                "end_line": func.end_line,
                "complexity": func.complexity
            },
            original_source=source
        )

    def _create_class_chunk(self, cls: ClassInfo, lines: List[str], file_path: str) -> Optional[CodeChunk]:
        # For class, we extract definition but not ALL methods code, just signatures maybe?
        # Or just the class docstring and top level items.
        
        # Actually, let's just take the whole class text but verify size?
        # If class is huge, extracting just the top part (definition + docstring) is better.
        # Let's extract from start_line until first method start if possible, or just arbitrary.
        
        # For now, let takes the whole source but rely on 'text_content' formulation to focus on high level.
        source = self._extract_source(cls.start_line, cls.end_line, lines)
        if not source.strip():
            return None

        text_content = (
            f"File: {file_path}\n"
            f"Type: Class\n"
            f"Name: {cls.name}\n"
            f"Docstring: {cls.docstring or ''}\n"
            f"Bases: {', '.join(cls.bases)}\n"
        )
        
        return CodeChunk(
            chunk_id=f"{file_path}::{cls.name}",
            text_content=text_content,
            metadata={
                "type": "class",
                "name": cls.name,
                "file_path": file_path,
                "start_line": cls.start_line,
                "end_line": cls.end_line
            },
            original_source=source
        )

    def _create_method_chunk(self, method: FunctionInfo, class_name: str, lines: List[str], file_path: str) -> Optional[CodeChunk]:
        source = self._extract_source(method.start_line, method.end_line, lines)
        if not source.strip():
            return None
            
        signature = f"def {method.name}({', '.join(method.args)})"
        doc_part = f"\nDocstring: {method.docstring}" if method.docstring else ""
        truncated_code = source[:2000]

        text_content = (
            f"File: {file_path}\n"
            f"Type: Method\n"
            f"Class: {class_name}\n"
            f"Name: {method.name}\n"
            f"Signature: {signature}"
            f"{doc_part}\n"
            f"Code:\n{truncated_code}"
        )
        
        return CodeChunk(
            chunk_id=f"{file_path}::{class_name}.{method.name}",
            text_content=text_content,
            metadata={
                "type": "method",
                "class": class_name,
                "name": method.name,
                "file_path": file_path,
                "start_line": method.start_line,
                "end_line": method.end_line
            },
            original_source=source
        )
