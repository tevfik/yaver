from typing import List, Dict
from pathlib import Path
from .models import FileAnalysis, ClassInfo
from .cache_manager import CachingManager

class CodeVisualizer:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.cache = CachingManager()
        
    def generate_mermaid_class_diagram(self) -> str:
        """
        Scans cached analysis results and generates a Mermaid class diagram.
        """
        mermaid_lines = ["classDiagram"]
        files = self._find_files()
        
        classes_found = False
        
        for file_path in files:
            analysis = self.cache.get_cached_analysis(file_path)
            if not analysis:
                continue
                
            for cls in analysis.classes:
                classes_found = True
                safe_name = self._sanitize_name(cls.name)
                mermaid_lines.append(f"    class {safe_name}")
                
                # Add methods
                for method in cls.methods:
                    mermaid_lines.append(f"    {safe_name} : +{method.name}()")
                
                # Add inheritance
                for base in cls.bases:
                    safe_base = self._sanitize_name(base)
                    # Only map inheritance if base is likely internal or well-known
                    # For now map all
                    mermaid_lines.append(f"    {safe_base} <|-- {safe_name}")
                    
        if not classes_found:
            return "No classes found to visualize."
            
        return "\n".join(mermaid_lines)

    def _find_files(self) -> List[Path]:
        """Simple file finder similar to analyzer"""
        files = []
        for p in self.repo_path.rglob("*.py"):
            parts = p.parts
            if any(part.startswith(".") for part in parts) or "venv" in parts or "__pycache__" in parts:
                continue
            files.append(p)
        return files
        
    def _sanitize_name(self, name: str) -> str:
        """Sanitize class names for Mermaid"""
        return name.replace(".", "_").replace(" ", "")
