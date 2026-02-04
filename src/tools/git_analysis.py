"""
Unified Git Repository Analyzer Tool
Adapted from IntelligentAgent project for YaverAI.
"""

import os
import ast
import shutil
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

try:
    from config.config import Neo4jConfig
except ImportError:
    # Fallback for development
    try:
        from yaver_cli.config import Neo4jConfig
    except ImportError:
        Neo4jConfig = None

# Configure logging
logger = logging.getLogger("tools.git_analysis")

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

class GraphIndexer:
    """Indexes code structure into Neo4j."""
    
    def __init__(self):
        self.config = Neo4jConfig()
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    self.config.uri, 
                    auth=(self.config.username, self.config.password),
                    encrypted=False
                )
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
        else:
            logger.warning("neo4j package not found")
            
    def close(self):
        if self.driver:
            self.driver.close()
            
    def index_repo(self, structure: List[Dict[str, Any]]):
        """Push parsed structure to Graph DB."""
        if not self.driver:
            return {"error": "No Neo4j connection"}
            
        with self.driver.session() as session:
            # Create constraints (optional but good)
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.name IS UNIQUE")
            
            count = 0
            for file_info in structure:
                session.execute_write(self._create_file_nodes, file_info)
                count += 1
                
        return {"indexed_files": count}

    @staticmethod
    def _create_file_nodes(tx, file_info):
        # Create File Node
        query_file = """
        MERGE (f:File {name: $name})
        SET f.loc = $loc
        """
        tx.run(query_file, name=file_info["file"], loc=file_info.get("loc", 0))
        
        # Create Functions and Relationships
        for func in file_info.get("functions", []):
            query_func = """
            MERGE (fn:Function {name: $func_name, file: $file_name})
            MERGE (f:File {name: $file_name})
            MERGE (f)-[:DEFINES]->(fn)
            """
            tx.run(query_func, func_name=func, file_name=file_info["file"])
            
        # Create Classes
        for cls in file_info.get("classes", []):
            query_cls = """
            MERGE (c:Class {name: $cls_name, file: $file_name})
            MERGE (f:File {name: $file_name})
            MERGE (f)-[:DEFINES]->(c)
            """
            tx.run(query_cls, cls_name=cls, file_name=file_info["file"])

        # Create Imports (Simple dependency)
        for imp in file_info.get("imports", []):
            query_imp = """
            MERGE (f:File {name: $file_name})
            MERGE (i:Module {name: $imp_name})
            MERGE (f)-[:IMPORTS]->(i)
            """
            tx.run(query_imp, file_name=file_info["file"], imp_name=imp)

        # Create Calls
        for call in file_info.get("calls", []):
            query_call = """
            MATCH (caller:Function {name: $caller_name, file: $file_name})
            MERGE (callee {name: $callee_name})
            MERGE (caller)-[:CALLS]->(callee)
            """
            tx.run(query_call, caller_name=call["caller"], callee_name=call["callee"], file_name=file_info["file"])

class RepoManager:
    """Manages Git repository operations with caching."""
    
    def __init__(self, cache_dir: str = "./cache/git_repos", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_repo(self, repo_source: str) -> Dict[str, Any]:
        """Get repository (clone or usage local)."""
        if os.path.exists(repo_source):
            return {"path": str(Path(repo_source).resolve()), "type": "local"}
            
        # Remote repo logic
        repo_hash = hashlib.md5(repo_source.encode()).hexdigest()
        target_path = self.cache_dir / repo_hash
        
        if target_path.exists():
            # In a real app, check TTL here
            logger.info(f"Using cached repo at {target_path}")
            return {"path": str(target_path), "type": "cached"}
            
        logger.info(f"Cloning {repo_source} to {target_path}...")
        # Use simple git clone for now
        os.system(f"git clone {repo_source} {target_path}")
        return {"path": str(target_path), "type": "cloned"}

class CodeParser:
    """Parses code to extract structural information (AST-based + Regex fallback)."""
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a file to extract functions, classes, and calls."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix == '.py':
            return self._parse_python(path)
        elif suffix in ['.c', '.cpp', '.cc', '.h', '.hpp', '.java', '.js', '.ts', '.jsx', '.tsx']:
            return self._parse_generic_regex(path)
        else:
            return {"error": "Unsupported file type"}

    def _parse_python(self, path: Path) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
            imports += [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
            
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
                                calls.append({"caller": caller_name, "callee": callee_name})

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(content.splitlines())
            }
        except Exception as e:
            return {"error": str(e)}

    def _parse_generic_regex(self, path: Path) -> Dict[str, Any]:
        """Simple regex based parser for C-like languages."""
        import re
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Simple C-function regex: Type Name(Args) {
            # Limiting to common C patterns to avoid false positives
            # Improved regex to handle pointers and attributes better
            func_pattern = re.compile(r'^\s*(?:[\w\*]+\s+)+(\w+)\s*\(', re.MULTILINE)
            raw_functions = func_pattern.findall(content)
            
            # Filter out control structures that look like function definitions (e.g. "else if")
            # We allow 'main' because it's a critical entry point function
            blacklist = {'if', 'while', 'switch', 'for', 'catch', 'return', 'sizeof', 'else', 'define'}
            functions = [f for f in raw_functions if f not in blacklist]
            
            # Classes (for C++/Java)
            class_pattern = re.compile(r'^\s*class\s+(\w+)', re.MULTILINE)
            classes = class_pattern.findall(content)
            
            # Includes/Imports
            imports = []
            include_pattern = re.compile(r'#include\s+[<"](.+)[>"]')
            imports.extend(include_pattern.findall(content))
            
            # Calls - this is hard with detailed scope parsing using just regex.
            # We will try a heuristic: line-by-line check inside "suspected" function blocks.
            # Or simplified: Check all "Name(" occurrences and assume they are calls if they overlap with known functions.
            
            # Better approach for calls: just find all "tokens that look like function calls"
            # and map them to the last seen function definition (very rough approximation).
            calls = []
            current_func = None
            
            lines = content.splitlines()
            for line in lines:
                # Check for function start
                func_match = func_pattern.search(line)
                if func_match and '{' in line: # Basic heuristics
                     current_func = func_match.group(1)
                     continue
                
                if current_func:
                    # Look for calls:  func_name(
                    call_matches = re.findall(r'(\w+)\s*\(', line)
                    for callee in call_matches:
                        if callee not in blacklist and callee != current_func:
                             calls.append({"caller": current_func, "callee": callee})

            return {
                "file": path.name,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "calls": calls,
                "loc": len(lines)
            }
        except Exception as e:
            return {"error": str(e)}

class ImpactAnalyzer:
    """Analyzes change impact using Neo4j Graph."""
    
    def __init__(self):
        self.config = Neo4jConfig()
        self.driver = None
        if GraphDatabase:
            try:
                self.driver = GraphDatabase.driver(
                    self.config.uri, 
                    auth=(self.config.username, self.config.password),
                    encrypted=False
                )
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j for Impact Analysis: {e}")

    def generate_call_graph(self, repo_name: Optional[str] = None, limit: int = 200) -> Dict[str, str]:
        """Generates a mermaid chart of the call graph."""
        if not self.driver:
            return {"error": "Neo4j connection missing"}
            
        with self.driver.session() as session:
            if repo_name:
                query = f"""
                MATCH (caller:Function {{repo_name: $repo_name}})-[:CALLS]->(callee:Function)
                RETURN caller.name as source, callee.name as target
                LIMIT {limit}
                """
                params = {'repo_name': repo_name}
            else:
                query = f"""
                MATCH (caller:Function)-[:CALLS]->(callee:Function)
                RETURN caller.name as source, callee.name as target
                LIMIT {limit}
                """
                params = {}
                
            results = session.run(query, parameters=params).data()  # type: ignore
            
            mermaid = ["graph TD"]
            for r in results:
                # Sanitization for mermaid
                src = r['source'].replace(' ', '_').replace('.', '_')
                tgt = r['target'].replace(' ', '_').replace('.', '_')
                mermaid.append(f"    {src} --> {tgt}")
                
            return {"mermaid": "\n".join(mermaid)}
                
    def analyze(self, target_name: str, depth: int = 2) -> Dict[str, Any]:
        """Find what depends on target_name."""
        if not self.driver:
            return {"error": "Neo4j connection missing"}
            
        with self.driver.session() as session:
            # 1. Direct callers (Functions calling target)
            query_direct = """
            MATCH (caller:Function)-[:DEFINES|CALLS]->(target {name: $name})
            RETURN caller.name as caller, caller.file as file
            """
            direct_deps = session.run(query_direct, name=target_name).data()  # type: ignore
            
            # 2. Files importing target (if target is a module/file concept)
            query_imports = """
            MATCH (f:File)-[:IMPORTS]->(m:Module {name: $name})
            RETURN f.name as file
            """
            import_deps = session.run(query_imports, name=target_name).data()  # type: ignore
            
            # 3. Transitive impact (simplified)
            # Find chains: (Something) -> ... -> (Target)
            query_transitive = f"""
            MATCH path = (source)-[:CALLS*1..{depth}]->(target {{name: $name}})
            RETURN source.name as source, length(path) as hops
            """
            transitive_deps = session.run(query_transitive, name=target_name).data()  # type: ignore
            
            affected_files = set()
            for d in direct_deps: affected_files.add(d['file'])
            for i in import_deps: affected_files.add(i['file'])
            
            return {
                "target": target_name,
                "direct_dependents": direct_deps,
                "importers": import_deps,
                "transitive_count": len(transitive_deps),
                "affected_files": list(affected_files),
                "risk_level": "High" if len(affected_files) > 5 else "Low"
            }

class GitRepoAnalyzer:
    """Main analyzer tool facade."""
    
    def __init__(self):
        self.repo_manager = RepoManager()
        self.parser = CodeParser()
        self.graph_indexer = GraphIndexer()
        self.impact_analyzer = ImpactAnalyzer()
        
    def analyze(self, repo_source: str, analysis_type: str = "overview", target: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform analysis on a repository.
        analysis_type: 'overview', 'structure', 'search', 'graph_index', 'impact'
        """
        repo_info = self.repo_manager.get_repo(repo_source)
        repo_path = Path(repo_info["path"])
        
        if not repo_path.exists():
            return {"error": f"Repository not found at {repo_path}"}
            
        if analysis_type == "overview":
            return self._generate_overview(repo_path)
        elif analysis_type == "structure":
            return self._generate_structure(repo_path)
        elif analysis_type == "graph_index":
            structure = self._generate_structure(repo_path).get("structure", [])
            return self.graph_indexer.index_repo(structure)
        elif analysis_type == "impact":
            if not target:
                return {"error": "Target parameter required for impact analysis"}
            return self.impact_analyzer.analyze(target)
        elif analysis_type == "callgraph":
             return self.impact_analyzer.generate_call_graph()
        
        return {"error": "Unknown analysis type"}
        
    def _generate_overview(self, path: Path) -> Dict[str, Any]:
        file_counts = {}
        total_files = 0
        total_size = 0
        
        for root, _, files in os.walk(path):
            if ".git" in root: continue
            for file in files:
                total_files += 1
                ext = Path(file).suffix
                file_counts[ext] = file_counts.get(ext, 0) + 1
                total_size += (Path(root) / file).stat().st_size
                
        return {
            "summary": "Repository Overview",
            "files": total_files,
            "size_kb": total_size / 1024,
            "languages": file_counts
        }
        
    def _generate_structure(self, path: Path) -> Dict[str, Any]:
        structure = []
        # Same list as in agent_git_analyzer, should ideally be shared constant.
        supported_ext = {'.py', '.c', '.cpp', '.cc', '.h', '.hpp', '.java', '.js', '.ts', '.jsx', '.tsx'}
        for root, _, files in os.walk(path):
            if ".git" in root: continue
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in supported_ext:
                    full_path = Path(root) / file
                    analysis = self.parser.parse_file(str(full_path))
                    structure.append(analysis)
        return {"structure": structure}
