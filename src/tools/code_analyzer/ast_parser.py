"""
AST Parser for Python
Parses Python source code into structured Analysis Models.
"""
import ast
from pathlib import Path
from typing import List, Optional, Union
import logging

from .models import FileAnalysis, ClassInfo, FunctionInfo, ImportInfo
from .parsers.base import BaseParser

logger = logging.getLogger(__name__)

class ASTParser(BaseParser):
    """Parses Python code to extract structural information"""

    def parse(self, source_code: str, file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
        """
        Parse Python source code.
        """
        try:
            tree = ast.parse(source_code)
            
            rel_path = file_path.relative_to(repo_root).as_posix()
            
            analysis = FileAnalysis(
                file_path=rel_path,
                loc=len(source_code.splitlines()),
                content_hash="" 
            )
            
            # Visitor pass
            visitor = AnalysisVisitor()
            visitor.visit(tree)
            
            analysis.classes = visitor.classes
            analysis.functions = visitor.functions
            analysis.imports = visitor.imports
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def parse_file(self, file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
        """
        Parse a single Python file.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.parse(content, file_path, repo_root)
        except Exception as e:
            logger.error(f"Failed to read/parse {file_path}: {e}")
            return None


class AnalysisVisitor(ast.NodeVisitor):
    """AST Visitor to extract info"""
    
    def __init__(self):
        self.classes: List[ClassInfo] = []
        self.functions: List[FunctionInfo] = []
        self.imports: List[ImportInfo] = []
        self.current_class: Optional[ClassInfo] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportInfo(
                module=alias.name,
                names=[],
                alias=alias.asname
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        names = [n.name for n in node.names]
        self.imports.append(ImportInfo(
            module=module,
            names=names,
            level=node.level
        ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Extract bases
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if isinstance(base.value, ast.Name) else "Unknown")
        
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        class_info = ClassInfo(
            name=node.name,
            bases=bases,
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            decorators=decorators
        )
        
        # Recurse into body handling methods
        prev_class = self.current_class
        self.current_class = class_info
        
        self.generic_visit(node)
        
        self.classes.append(class_info)
        self.current_class = prev_class

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def _handle_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], is_async: bool):
        args = [a.arg for a in node.args.args]
        
        returns = None
        if node.returns:
             if isinstance(node.returns, ast.Name):
                 returns = node.returns.id
             elif isinstance(node.returns, ast.Constant) and node.returns.value is None:
                 returns = "None"
        
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        func_info = FunctionInfo(
            name=node.name,
            args=args,
            returns=returns,
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            decorators=decorators,
            is_async=is_async,
            complexity=1 # TODO: McCabe
        )
        
        if self.current_class:
            self.current_class.methods.append(func_info)
        elif not self.current_class: # Only add top-level functions to global list, nested funcs inside logic?
            # For now, simplistic: if not in class, it's top level. 
            # Note: This logic misses nested functions inside functions.
            self.functions.append(func_info)
            
        self.generic_visit(node)

    def _get_decorator_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "complex_decorator"
