"""
Graph Database Manager for Yaver AI
Handles code graph storage and retrieval using Neo4j.
"""

from typing import Dict, List, Any, Optional
from neo4j import GraphDatabase
import logging
from .config import get_config

logger = logging.getLogger("yaver_cli")


class GraphManager:
    """
    Manages interactions with Neo4j graph database.
    Stores code structure (Files, Classes, Functions) and their relationships.
    """

    def __init__(self):
        config = get_config()
        self.uri = config.neo4j.uri
        self.username = config.neo4j.username
        self.password = config.neo4j.password

        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.username, self.password)
            )
            self.verify_connection()
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def verify_connection(self):
        """Check if Neo4j is reachable"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record and record["num"] == 1:
                    logger.info(f"✅ Connected to Neo4j at {self.uri}")
                else:
                    logger.warning(f"⚠️ Neo4j connection test failed")
        except Exception as e:
            logger.error(f"❌ Neo4j connection error: {e}")
            self.driver = None

    def store_file_node(self, file_path: str, repo_name: str, language: str, loc: int):
        """Create or update a File node"""
        if not self.driver:
            return

        query = """
        MERGE (f:File {path: $path, repo_name: $repo_name})
        SET f.language = $language,
            f.loc = $loc,
            f.last_updated = datetime()
        """
        try:
            with self.driver.session() as session:
                session.run(
                    query,
                    path=file_path,
                    repo_name=repo_name,
                    language=language,
                    loc=loc,
                )
        except Exception as e:
            logger.error(f"Failed to store file node {file_path}: {e}")

    def store_code_structure(
        self, file_path: str, repo_name: str, structure: Dict[str, Any]
    ):
        """
        Store classes and functions found in a file and link them.
        structure expects: {'classes': ['ClassName'], 'functions': ['func_name']}
        """
        if not self.driver:
            return

        # Store Classes
        for class_name in structure.get("classes", []):
            query = """
            MATCH (f:File {path: $path, repo_name: $repo_name})
            MERGE (c:Class {name: $name, file_path: $path, repo_name: $repo_name})
            MERGE (f)-[:CONTAINS]->(c)
            """
            try:
                with self.driver.session() as session:
                    session.run(
                        query, path=file_path, repo_name=repo_name, name=class_name
                    )
            except Exception as e:
                logger.error(f"Failed to store class {class_name}: {e}")

        # Store Functions
        for func_name in structure.get("functions", []):
            query = """
            MATCH (f:File {path: $path, repo_name: $repo_name})
            MERGE (fn:Function {name: $name, file_path: $path, repo_name: $repo_name})
            MERGE (f)-[:CONTAINS]->(fn)
            """
            try:
                with self.driver.session() as session:
                    session.run(
                        query, path=file_path, repo_name=repo_name, name=func_name
                    )
            except Exception as e:
                logger.error(f"Failed to store function {func_name}: {e}")

        # Store Calls
        for call in structure.get("calls", []):
            # We only create the relationship if the caller function is known (already stored)
            # The callee might not be defined in this file, so we merge it as a Function node
            # (possibly a stub if we haven't parsed its file yet, but we attach repo_name)
            query = """
            MATCH (caller:Function {name: $caller_name, file_path: $path, repo_name: $repo_name})
            MERGE (callee:Function {name: $callee_name, repo_name: $repo_name})
            MERGE (caller)-[:CALLS]->(callee)
            """
            try:
                with self.driver.session() as session:
                    session.run(
                        query,
                        caller_name=call["caller"],
                        callee_name=call["callee"],
                        path=file_path,
                        repo_name=repo_name,
                    )
            except Exception as e:
                # Common to fail if caller node doesn't exist (e.g. blacklisted keyword)
                pass

    def get_project_summary(self) -> str:
        """
        Retrieve a summary of the project structure from the Graph.
        Returns a text description suitable for LLM context.
        """
        if not self.driver:
            return "Graph database not available."

        summary = "Project Graph Summary (from Neo4j):\n"

        # Count nodes
        query_stats = """
        MATCH (n)
        RETURN labels(n) as label, count(n) as count
        """
        try:
            with self.driver.session() as session:
                results = session.run(query_stats)
                for record in results:
                    summary += f"- {record['label'][0]}s: {record['count']}\n"
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")

        return summary
