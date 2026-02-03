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

    def detect_circular_dependencies(self):
        """Find circular function calls in the graph"""
        if not self.driver:
            return []
            
        with self.driver.session() as session:
            result = session.run("""
                MATCH path = (n:Function)-[:CALLS*1..5]->(n)
                RETURN [x in nodes(path) | x.id] as cycle, length(path) as len
                ORDER BY len ASC
                LIMIT 10
            """)
            return [record["cycle"] for record in result]
            
    def get_call_graph(self, root_function_name: str, depth: int = 3) -> Dict:
        """
        Retrieve call graph starting from a function name.
        """
        if not self.driver:
            return {}
        
        query_pure = f"""
        MATCH path = (start:Function)-[:CALLS*0..{depth}]->(end)
        WHERE start.name CONTAINS $name
        RETURN path
        LIMIT 50
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query_pure, {"name": root_function_name})
                
                nodes = {}
                edges = []
                
                for record in result:
                    path = record["path"]
                    for node in path.nodes:
                        nodes[node["id"]] = {
                            "id": node["id"],
                            "name": node.get("name", "Unknown"),
                            "labels": list(node.labels)
                        }
                    for rel in path.relationships:
                        edges.append({
                            "from": rel.start_node["id"],
                            "to": rel.end_node["id"],
                            "type": rel.type
                        })
                
                return {"nodes": list(nodes.values()), "edges": edges}
        except Exception as e:
            logger.error(f"Error fetching call graph: {e}")
            return {}

    def store_analysis(self, analysis: FileAnalysis, repo_id: str, commit_hash: str = "HEAD"):
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
                    f.commit_hash = $commit,
                    f.last_analyzed = timestamp()
            """, {
                "id": file_id,
                "path": analysis.file_path,
                "loc": analysis.loc,
                "lang": analysis.language,
                "repo_id": repo_id,
                "commit": commit_hash
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
                confidence = call.get('confidence', 1.0)
                is_dynamic = call.get('is_dynamic', False)
                
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

                # Store call as a relationship with properties
                # We often can't resolve the target ID yet, so we create a 'Ghost Node' or just a property
                # But to support visualization, let's try to link if it's local
                
                target_id = None
                if callee_name in local_methods:
                     # It's a method in this file
                     parts = callee_name.split(".")
                     target_id = f"{file_id}::{parts[0]}::{parts[1]}"
                
                if target_id:
                    session.run(f"""
                        MATCH (s {{id: $source_id}})
                        MATCH (t {{id: $target_id}})
                        MERGE (s)-[r:CALLS]->(t)
                        SET r.line = $line, r.confidence = $confidence, r.dynamic = $dynamic
                    """, {
                        "source_id": source_id,
                        "target_id": target_id,
                        "line": call['line'],
                        "confidence": confidence,
                        "dynamic": is_dynamic
                    })
                else:
                    # Cannot resolve locally - store unresolved call info for post-processing
                    # Store as a pipe-separated string: "callee|line|confidence|dynamic"
                    import json
                    call_str = json.dumps({"callee": callee_name, "line": call['line'], "confidence": confidence, "dynamic": is_dynamic})
                    session.run("""
                        MATCH (s {id: $source_id})
                        SET s.unresolved_calls = COALESCE(s.unresolved_calls, []) + $call_str
                    """, {
                        "source_id": source_id,
                        "call_str": call_str
                    })



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

    def auto_tag_layers(self, repo_id: str):
        """
        Apply architecture layer labels based on heuristics.
        """
        if not self.driver:
            return

        queries = [
            # API Layer
            """
            MATCH (f:File) 
            WHERE f.repo_id = $repo_id AND (
                  f.path CONTAINS 'api/' OR 
                  f.path CONTAINS 'server/' OR 
                  f.path CONTAINS 'cli/' OR
                  f.path CONTAINS 'routes/' OR
                  f.path ENDS WITH 'main.py'
            )
            SET f:ApiLayer, f.layer = 'API'
            """,
            # Data Layer
            """
            MATCH (f:File) 
            WHERE f.repo_id = $repo_id AND (
                  f.path CONTAINS 'db/' OR 
                  f.path CONTAINS 'models/' OR 
                  f.path CONTAINS 'storage/' OR
                  f.path CONTAINS 'schema/' OR
                  f.path CONTAINS 'repository/'
            )
            SET f:DataLayer, f.layer = 'DATA'
            """,
            # Core/Business Logic Layer
            """
            MATCH (f:File) 
            WHERE f.repo_id = $repo_id AND (
                  f.path CONTAINS 'core/' OR 
                  f.path CONTAINS 'services/' OR 
                  f.path CONTAINS 'agents/' OR
                  f.path CONTAINS 'tools/' OR
                  f.path CONTAINS 'utils/'
            )
            AND NOT f:ApiLayer AND NOT f:DataLayer
            SET f:CoreLayer, f.layer = 'CORE'
            """
        ]

        with self.driver.session() as session:
            for q in queries:
                session.run(q, {"repo_id": repo_id})

    def link_unresolved_calls(self):
        """
        Second pass: Link CALLS relationships for cross-file calls.
        Processes nodes that have unresolved_calls property set during initial analysis.
        """
        import json
        
        with self.driver.session() as session:
            # Find all nodes with unresolved calls
            result = session.run("""
                MATCH (caller)
                WHERE caller.unresolved_calls IS NOT NULL
                RETURN caller.id as caller_id, caller.unresolved_calls as calls
            """)
            
            for rec in result:
                caller_id = rec["caller_id"]
                unresolved_list = rec["calls"]  # List of JSON strings
                
                for call_str in unresolved_list:
                    call_info = json.loads(call_str)
                    callee_name = call_info["callee"]
                    line = call_info["line"]
                    confidence = call_info["confidence"]
                    is_dynamic = call_info["dynamic"]
                    
                    # Extract simple name
                    simple_name = callee_name.split(".")[-1]
                    
                    # Find matching function
                    func_result = session.run("""
                        MATCH (t:Function)
                        WHERE t.name = $name OR t.id ENDS WITH ('::' + $name)
                        RETURN t.id as target_id
                        LIMIT 1
                    """, {"name": simple_name})
                    
                    func_record = func_result.single()
                    if func_record:
                        target_id = func_record["target_id"]
                        # Create the CALLS relationship
                        session.run("""
                            MATCH (s {id: $source_id})
                            MATCH (t {id: $target_id})
                            MERGE (s)-[r:CALLS]->(t)
                            SET r.line = $line, r.confidence = $confidence, r.dynamic = $dynamic
                        """, {
                            "source_id": caller_id,
                            "target_id": target_id,
                            "line": line,
                            "confidence": confidence,
                            "dynamic": is_dynamic
                        })
            
            # Clean up the temporary property
            session.run("""
                MATCH (n)
                WHERE n.unresolved_calls IS NOT NULL
                REMOVE n.unresolved_calls
            """)
