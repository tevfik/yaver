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
