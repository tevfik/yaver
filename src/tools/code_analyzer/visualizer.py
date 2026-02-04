from typing import List, Dict, Optional
from pathlib import Path
from .models import FileAnalysis, ClassInfo
from .cache_manager import CachingManager
from .neo4j_adapter import Neo4jAdapter

class CodeVisualizer:
    def __init__(self, repo_path: Path, neo4j_adapter: Optional[Neo4jAdapter] = None):
        self.repo_path = repo_path
        self.cache = CachingManager()
        self.neo4j = neo4j_adapter
        
    def generate_call_graph(self, function_name: str, depth: int = 3) -> str:
        """
        Generate Mermaid flowchart for a call graph.
        Requires Neo4j connection.
        """
        if not self.neo4j:
            return "Error: Neo4j connection required for call graph visualization."
            
        data = self.neo4j.get_call_graph(function_name, depth)
        if not data or not data.get("nodes"):
            return f"No call graph found for {function_name}"
            
        mermaid_lines = ["graph TD"]
        
        # ID mapping to safe mermaid ids
        id_map = {}
        for i, node in enumerate(data["nodes"]):
            safe_id = f"node_{i}"
            id_map[node["id"]] = safe_id
            
            # Format label: File::Function -> Function
            label = node["name"]
            if "::" in label:
                label = label.split("::")[-1]
                
            mermaid_lines.append(f"    {safe_id}[\"{label}\"]")
            
        for edge in data["edges"]:
            src = id_map.get(edge["from"])
            dst = id_map.get(edge["to"])
            if src and dst:
                mermaid_lines.append(f"    {src} --> {dst}")
                
        return "\n".join(mermaid_lines)

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
