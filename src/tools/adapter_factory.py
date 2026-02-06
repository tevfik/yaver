"""
Adapter Factory Functions
Dynamic adapter selection based on configuration
"""

from typing import Union
from config.config import YaverConfig
from tools.graph.networkx_adapter import NetworkXAdapter
from utils.logger import get_logger

logger = get_logger(__name__)


def get_graph_adapter(config: YaverConfig) -> Union[NetworkXAdapter, any]:
    """
    Get graph database adapter based on configuration

    Args:
        config: Yaver configuration

    Returns:
        Graph adapter instance (NetworkX or Neo4j)
    """
    provider = config.graph_db.provider

    if provider == "networkx":
        logger.info(
            f"Using NetworkX graph database: {config.graph_db.networkx_persist_path}"
        )
        return NetworkXAdapter(config.graph_db.networkx_persist_path)

    elif provider == "neo4j":
        logger.info(f"Using Neo4j graph database: {config.neo4j.uri}")
        try:
            from neo4j import GraphDatabase

            # Create Neo4j adapter wrapper
            class Neo4jAdapter:
                def __init__(self, uri, user, password):
                    self.driver = GraphDatabase.driver(uri, auth=(user, password))
                    self.driver.verify_connectivity()

                def close(self):
                    self.driver.close()

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    self.close()

                def store_file_node(self, file_path, repo_name, language, loc):
                    query = """
                    MERGE (f:File {path: $path, repo_name: $repo_name})
                    SET f.language = $language,
                        f.loc = $loc,
                        f.last_updated = datetime()
                    """
                    with self.driver.session() as session:
                        session.run(
                            query,
                            path=file_path,
                            repo_name=repo_name,
                            language=language,
                            loc=loc,
                        )

                def store_code_structure(self, file_path, repo_name, structure):
                    with self.driver.session() as session:
                        # 1. Store Classes
                        for class_name in structure.get("classes", []):
                            query = """
                            MATCH (f:File {path: $path, repo_name: $repo_name})
                            MERGE (c:Class {name: $name, file_path: $path, repo_name: $repo_name})
                            MERGE (f)-[:CONTAINS]->(c)
                            """
                            session.run(
                                query,
                                path=file_path,
                                repo_name=repo_name,
                                name=class_name,
                            )

                        # 2. Store Functions
                        for func_name in structure.get("functions", []):
                            query = """
                            MATCH (f:File {path: $path, repo_name: $repo_name})
                            MERGE (fn:Function {name: $name, file_path: $path, repo_name: $repo_name})
                            MERGE (f)-[:CONTAINS]->(fn)
                            """
                            session.run(
                                query,
                                path=file_path,
                                repo_name=repo_name,
                                name=func_name,
                            )

                        # 3. Store Imports (File -> File Relationship)
                        # Tries to match imported file names with existing File nodes
                        # Note: This is a loose match (filename contains import name)
                        for imp in structure.get("imports", []):
                            query = """
                            MATCH (source:File {path: $path, repo_name: $repo_name})
                            MATCH (target:File {repo_name: $repo_name})
                            WHERE target.path ENDS WITH $imp OR target.path ENDS WITH $imp + '.h' OR target.path ENDS WITH $imp + '.py'
                            MERGE (source)-[:IMPORTS]->(target)
                            """
                            session.run(
                                query, path=file_path, repo_name=repo_name, imp=imp
                            )

                        # 4. Store Calls (Function -> Function Relationship)
                        # Currently we only link calls if both Caller and Callee are in the same file (local calls)
                        # or if we can uniquely identify the callee in the repo (global uniqueness assumption)
                        for call in structure.get("calls", []):
                            caller = call.get("caller")
                            callee = call.get("callee")
                            if caller and callee:
                                query = """
                                MATCH (f:File {path: $path, repo_name: $repo_name})
                                MATCH (caller_fn:Function {name: $caller, file_path: $path, repo_name: $repo_name})
                                MATCH (callee_fn:Function {name: $callee, repo_name: $repo_name})
                                MERGE (caller_fn)-[:CALLS]->(callee_fn)
                                """
                                session.run(
                                    query,
                                    path=file_path,
                                    repo_name=repo_name,
                                    caller=caller,
                                    callee=callee,
                                )

                def get_project_summary(self):
                    summary = "Project Graph Summary (Neo4j):\n"
                    query = "MATCH (n) RETURN labels(n) as label, count(n) as count"
                    with self.driver.session() as session:
                        results = session.run(query)
                        for record in results:
                            summary += f"- {record['label'][0]}s: {record['count']}\n"
                    return summary

                def get_context_for_file(self, file_path, repo_name):
                    context = []
                    with self.driver.session() as session:
                        # Imports
                        q_imp = """
                        MATCH (f:File {path: $path, repo_name: $repo_name})-[:IMPORTS]->(target:File)
                        RETURN target.path as path
                        """
                        res_imp = session.run(
                            q_imp, path=file_path, repo_name=repo_name
                        )
                        imports = [r["path"] for r in res_imp]
                        if imports:
                            context.append(f"Imports Files: {', '.join(imports)}")

                        # Calls
                        q_calls = """
                        MATCH (f:File {path: $path, repo_name: $repo_name})-[:CONTAINS]->(fn:Function)-[:CALLS]->(target:Function)
                        RETURN fn.name as caller, target.name as callee
                        """
                        res_calls = session.run(
                            q_calls, path=file_path, repo_name=repo_name
                        )
                        for r in res_calls:
                            context.append(
                                f"Function '{r['caller']}' calls '{r['callee']}'"
                            )

                    return (
                        "\n".join(context)
                        if context
                        else "No structural context found."
                    )

            return Neo4jAdapter(
                config.neo4j.uri, config.neo4j.user, config.neo4j.password
            )

        except ImportError:
            logger.error("neo4j package not installed. Install with: pip install neo4j")
            logger.warning("Falling back to NetworkX")
            return NetworkXAdapter(config.graph_db.networkx_persist_path)
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            logger.warning("Falling back to NetworkX")
            return NetworkXAdapter(config.graph_db.networkx_persist_path)

    else:
        logger.warning(f"Unknown graph provider: {provider}, using NetworkX")
        return NetworkXAdapter(config.graph_db.networkx_persist_path)


def get_vector_adapter(config: YaverConfig) -> Union[any, any]:
    """
    Get vector database adapter based on configuration

    Args:
        config: Yaver configuration

    Returns:
        Vector adapter instance (ChromaDB or Qdrant)
    """
    provider = config.vector_db.provider

    if provider == "chroma":
        logger.info(f"Using ChromaDB: {config.vector_db.chroma_persist_dir}")
        try:
            import chromadb
            from chromadb.config import Settings

            # Create ChromaDB client
            client = chromadb.Client(
                Settings(
                    persist_directory=config.vector_db.chroma_persist_dir,
                    anonymized_telemetry=False,
                )
            )

            return client

        except ImportError:
            logger.error(
                "chromadb package not installed. Install with: pip install chromadb"
            )
            logger.warning("Falling back to Qdrant")
            return _get_qdrant_adapter(config)
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            logger.warning("Falling back to Qdrant")
            return _get_qdrant_adapter(config)

    elif provider == "qdrant":
        return _get_qdrant_adapter(config)

    else:
        logger.warning(f"Unknown vector provider: {provider}, using ChromaDB")
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.Client(
                Settings(
                    persist_directory=config.vector_db.chroma_persist_dir,
                    anonymized_telemetry=False,
                )
            )
            return client
        except:
            return _get_qdrant_adapter(config)


def _get_qdrant_adapter(config: YaverConfig):
    """Internal helper to get Qdrant adapter"""
    logger.info(f"Using Qdrant: {config.qdrant.host}:{config.qdrant.port}")
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=config.qdrant.host, port=config.qdrant.port)
        return client

    except ImportError:
        logger.error(
            "qdrant-client package not installed. Install with: pip install qdrant-client"
        )
        raise
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise
