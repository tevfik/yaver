"""
Neo4j Adapter for Code Graph
Handles efficient batch storage of code structure into Neo4j.
"""
from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional
import logging
from .models import FileAnalysis, ClassInfo, FunctionInfo

logger = logging.getLogger(__name__)

class Neo4jAdapter:
    """Manages connection and writing to Neo4j Graph DB"""
    
    def __init__(self, uri: str, auth: tuple):
        self.driver: Optional[Driver] = None
        try:
            self.driver = GraphDatabase.driver(uri, auth=auth)
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")

    def close(self):
        if self.driver:
            self.driver.close()
            
    def init_schema(self):
        """Create constraints and indexes"""
        if not self.driver:
            return

        constraints = [
            "CREATE CONSTRAINT unique_file_path IF NOT EXISTS FOR (f:File) REQUIRE f.id IS UNIQUE",
            "CREATE CONSTRAINT unique_class_id IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT unique_function_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
            "CREATE INDEX file_path_idx IF NOT EXISTS FOR (f:File) ON (f.path)"
        ]
        
        with self.driver.session() as session:
            for c in constraints:
                try:
                    session.run(c)
                except Exception as e:
                    logger.warning(f"Schema init warning: {e}")

    def store_analysis(self, analysis: FileAnalysis, repo_id: str):
        """Store a single file analysis result into the graph"""
        if not self.driver: 
            return

        with self.driver.session() as session:
            # 1. Create File Node
            file_id = f"{repo_id}:{analysis.file_path}"
            
            session.run("""
                MERGE (f:File {id: $id})
                SET f.path = $path, 
                    f.loc = $loc, 
                    f.language = $lang,
                    f.repo_id = $repo_id,
                    f.last_analyzed = timestamp()
            """, {
                "id": file_id,
                "path": analysis.file_path,
                "loc": analysis.loc,
                "lang": analysis.language,
                "repo_id": repo_id
            })
            
            # 2. Store Classes
            for cls in analysis.classes:
                class_id = f"{file_id}::{cls.name}"
                session.run("""
                    MERGE (c:Class {id: $id})
                    SET c.name = $name,
                        c.start_line = $start,
                        c.end_line = $end
                    
                    WITH c
                    MATCH (f:File {id: $file_id})
                    MERGE (f)-[:CONTAINS]->(c)
                """, {
                    "id": class_id, 
                    "name": cls.name, 
                    "start": cls.start_line, 
                    "end": cls.end_line,
                    "file_id": file_id
                })
                
                # Methods
                for method in cls.methods:
                    method_id = f"{class_id}::{method.name}"
                    self._store_function(session, method, method_id, parent_id=class_id, rel_type="DEFINES_METHOD")

            # 3. Store Top-Level Functions
            for func in analysis.functions:
                func_id = f"{file_id}::{func.name}"
                self._store_function(session, func, func_id, parent_id=file_id, rel_type="DEFINES_FUNCTION")

            # 4. Store Imports (Phase 2)
            for module_name, resolved_path in analysis.resolved_imports.items():
                target_file_id = f"{repo_id}:{resolved_path}"
                session.run("""
                    MATCH (f:File {id: $file_id})
                    MERGE (t:File {id: $target_id}) 
                    ON CREATE SET t.path = $target_path, t.repo_id = $repo_id
                    MERGE (f)-[:IMPORTS]->(t)
                """, {
                    "file_id": file_id,
                    "target_id": target_file_id,
                    "target_path": resolved_path,
                    "repo_id": repo_id
                })

            # Build a lookup of local methods for self-resolution
            local_methods = set()
            for cls in analysis.classes:
                 for method in cls.methods:
                      local_methods.add(f"{cls.name}.{method.name}")

            # 5. Store Calls (Phase 2)
            # Calls are tricky because we need to know the ID of the CALLEE
            # For now, we store them as a property or generic relationship if we can guess the ID
            # Better approach: Post-processing step to link calls after all nodes exist.
            # Here we just store basic intra-file calls or calls where we guessed the name.
            for call in analysis.calls:
                # Naive linking: If we have a caller function in THIS file
                caller_name = call['caller']
                callee_name = call['callee']
                
                # Construct IDs assuming caller is in this file
                # If caller is <module>, it's the file calling
                if caller_name == "<module>":
                    source_id = file_id
                    source_label = "File"
                elif "." in caller_name: # Method
                     # Try to find class
                     parts = caller_name.split(".")
                     cls_name = parts[0]
                     method_name = parts[1]
                     source_id = f"{file_id}::{cls_name}::{method_name}"
                     source_label = "Function"
                else: 
                     source_id = f"{file_id}::{caller_name}"
                     source_label = "Function"

                # Attempt to resolve target
                target_query_part = ""
                params = {
                    "source_id": source_id,
                    "callee_name": callee_name,
                    "line": call['line']
                }

                # Check for self calls resolving to local methods
                processed_callee = callee_name
                if callee_name.startswith("self.") and "." in caller_name:
                    potential_method = callee_name.replace("self.", f"{caller_name.split('.')[0]}.")
                    if potential_method.split(".")[-1] in [m.split(".")[-1] for m in local_methods]: 
                        # Ideally match full class but simple split ok for now
                         processed_callee = potential_method
                
                # If resolves to a local function (e.g. MyClass.method or my_func)
                # We need to distinguish between class methods and top level functions
                if processed_callee in local_methods:
                     # It's a method in this file
                     cls = processed_callee.split(".")[0]
                     met = processed_callee.split(".")[1]
                     target_id = f"{file_id}::{cls}::{met}"
                     params["target_id"] = target_id
                     target_query_part = "MERGE (target:Function {id: $target_id})"
                elif processed_callee in [f.name for f in analysis.functions]:
                     # It's a top level function
                     target_id = f"{file_id}::{processed_callee}"
                     params["target_id"] = target_id
                     target_query_part = "MERGE (target:Function {id: $target_id})"
                else:
                     # External or unknown
                     target_query_part = "MERGE (target:GhostFunction {name: $callee_name})"

                session.run(f"""
                    MATCH (s {{id: $source_id}})
                    {target_query_part}
                    MERGE (s)-[:CALLS {{line: $line}}]->(target)
                """, params)

    def _store_function(self, session, func: FunctionInfo, func_id: str, parent_id: str, rel_type: str):
        session.run(f"""
            MERGE (fn:Function {{id: $id}})
            SET fn.name = $name,
                fn.start_line = $start,
                fn.end_line = $end,
                fn.complexity = $complexity,
                fn.args = $args
            
            WITH fn
            MATCH (p {{id: $parent_id}})
            MERGE (p)-[:{rel_type}]->(fn)
        """, {
            "id": func_id,
            "name": func.name,
            "start": func.start_line,
            "end": func.end_line,
            "complexity": func.complexity,
            "args": func.args,
            "parent_id": parent_id
        })
