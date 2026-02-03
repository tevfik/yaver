"""
Main Code Analyzer
Orchestrates the analysis process: Traversing directories, parsing files, caching, and storing results.
"""
from pathlib import Path
from typing import List, Generator, Dict
import logging
import ast
from rich.progress import Progress

from .ast_parser import ASTParser
from .neo4j_adapter import Neo4jAdapter
from .cache_manager import CachingManager
from .models import FileAnalysis
from .import_resolver import ImportResolver
from .call_graph import CallGraphBuilder
from .embeddings import CodeEmbedder
from .qdrant_adapter import QdrantAdapter
from .chunker import CodeChunker
from tools.git_analyzer import GitAnalyzer
from tools.rag.rag_service import RAGService
from core.analysis_session import AnalysisSession
import config.config as cfg 

logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """
    Main entry point for Deep Code Analysis.
    """
    
    def __init__(self, session_id: str, repo_path: Path):
        self.repo_path = repo_path.resolve()
        self.session_id = session_id
        
        # Components
        self.session = AnalysisSession(session_id)
        self.cache = CachingManager()
        self.parser = ASTParser()
        self.import_resolver = ImportResolver(self.repo_path)
        self.call_graph_builder = CallGraphBuilder()
        self.git_analyzer = GitAnalyzer(str(self.repo_path))
        
        # Semantic Components (Lazy load)
        self.code_embedder = None
        self.qdrant_adapter = None
        self.chunker = None
        
        # RAG Component
        self.rag_service = None
        
        # Initialize Neo4j (Lazy load or config based)
        self.neo4j_adapter = None  

    def connect_db(self, uri: str, auth: tuple):
        self.neo4j_adapter = Neo4jAdapter(uri, auth)
        self.neo4j_adapter.init_schema()
    
    def init_semantic(self):
        """Initialize semantic analysis components (Embeddings + Qdrant)"""
        if not self.code_embedder:
            self.code_embedder = CodeEmbedder()
        if not self.qdrant_adapter:
            self.qdrant_adapter = QdrantAdapter()
        if not self.chunker:
            self.chunker = CodeChunker()
            
    def init_rag(self):
        """Initialize RAG service"""
        self.init_semantic()
        if not self.rag_service:
            self.rag_service = RAGService(
                neo4j_adapter=self.neo4j_adapter,
                qdrant_adapter=self.qdrant_adapter,
                code_embedder=self.code_embedder
            )

    def find_similar_code(self, source_code: str, limit: int = 5, threshold: float = 0.7) -> List[Dict]:
        """
        Find code similar to the provided source code string using semantic search.
        
        Args:
            source_code: The code or natural language query to search for.
            limit: Max results.
            threshold: Similarity threshold (0-1).
            
        Returns:
            List of matching code chunks with metadata.
        """
        self.init_semantic()
        try:
            vector = self.code_embedder.embed_query(source_code)
            results = self.qdrant_adapter.search(vector, limit=limit, score_threshold=threshold)
            return results
        except Exception as e:
            logger.error(f"Error finding similar code: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.neo4j_adapter:
            self.neo4j_adapter.close()

    def analyze_repository(self, incremental: bool = False, use_semantic: bool = False):
        """
        Perform full analysis of the repository.
        
        Args:
            incremental: If True, use incremental strategies (git/cache).
            use_semantic: If True, generate embeddings and store in Vector DB.
        """
        self.session.log_progress(f"Starting analysis of {self.repo_path}")
        
        if use_semantic:
            self.init_semantic()
        
        # Get Current Commit Hash
        current_commit = self.git_analyzer.get_current_commit() or "HEAD"

        files = list(self._find_files())
        
        if incremental:
            # TODO: Better state tracking efficiently.
            pass

        total_files = len(files)
        
        self.session.update_plan(f"# Task Plan\n\n- [ ] Analyze {total_files} files in {self.repo_path.name}\n")
        self.session.log_progress(f"Found {total_files} files to analyze")
        
        processed_count = 0
        
        with Progress() as progress:
            task = progress.add_task("[green]Analyzing...", total=total_files)
            
            for file_path in files:
                try:
                    # 1. Check Cache
                    # This relies on content hash
                    analysis = self.cache.get_cached_analysis(file_path)
                    
                    if not analysis:
                        # 2. Parse (Cache Miss)
                        analysis = self.parser.parse_file(file_path, self.repo_path)
                        
                        # Phase 2: Enrich with Calls and Imports
                        if analysis:
                            # Parse AST for calls
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                                tree = ast.parse(content, filename=str(file_path))
                                analysis.calls = self.call_graph_builder.build(tree)
                            
                            # Resolve Imports
                            for imp in analysis.imports:
                                resolved = self.import_resolver.resolve_import(imp, file_path)
                                if resolved:
                                    imp_name = imp.module if imp.module else (imp.names[0] if imp.names else "")
                                    if imp_name:
                                        analysis.resolved_imports[imp_name] = str(resolved)

                            self.cache.save_analysis(file_path, analysis)
                    
                    # 3. Store in Neo4j (Nodes + Relationships)
                    if analysis and self.neo4j_adapter:
                        self.neo4j_adapter.store_analysis(analysis, self.repo_path.name, commit_hash=current_commit)
                    
                    # 4. Semantic Analysis (Embeddings)
                    if analysis and use_semantic and self.code_embedder and self.qdrant_adapter:
                        self._process_semantic_analysis(file_path, analysis)
                        
                    processed_count += 1
                    progress.advance(task)
                    
                except Exception as e:
                    self.session.log_error(f"Error processing {file_path}: {e}")
                    logger.error(f"Error processing {file_path}: {e}")

        self.session.log_progress(f"Completed analysis. Processed {processed_count}/{total_files} files.")
        
        # 5. Architecture Tagging
        if self.neo4j_adapter:
            self.session.log_progress("Auto-tagging architecture layers...")
            self.neo4j_adapter.auto_tag_layers(self.repo_path.name)
        
        self.session.log_finding("Analysis Complete", f"Successfully analyzed {processed_count} files.")
        
        if self.neo4j_adapter:
            self.neo4j_adapter.close()
            
    def _process_semantic_analysis(self, file_path: Path, analysis: FileAnalysis):
        """
        Generate embeddings for functions and classes in the file and store them.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            chunks = self.chunker.chunk_file(analysis, source_code)
            items_to_embed = []
            
            for chunk in chunks:
                # Prepare payload for Qdrant
                payload = {
                    "id": chunk.chunk_id,
                    "content": chunk.text_content, # The text used for embedding
                    "source": chunk.original_source, # The actual code (optional to store whole thing)
                }
                # Add metadata
                payload.update(chunk.metadata)
                
                items_to_embed.append(payload)
            
            if items_to_embed:
                # Generate embeddings (will use 'content' key by default in our embedder logic)
                embedded_items = self.code_embedder.embed_code_batch(items_to_embed)
                # Store in Qdrant
                self.qdrant_adapter.store_embeddings(embedded_items)
                
        except Exception as e:
            logger.error(f"Semantic analysis failed for {file_path}: {e}")

    def _find_files(self) -> Generator[Path, None, None]:
        """Yield python files in repo, respecting gitignore (simple version)"""
        # TODO: Implement proper gitignore parsing
        # For now, simple walk + exclude hidden/.git
        for p in self.repo_path.rglob("*.py"):
            parts = p.parts
            if any(part.startswith(".") for part in parts) or "venv" in parts or "__pycache__" in parts:
                continue
            yield p
