"""
Main Code Analyzer
Orchestrates the analysis process: Traversing directories, parsing files, caching, and storing results.
"""
from pathlib import Path
from typing import List, Generator, Dict
import logging
import ast
from rich.progress import Progress
from concurrent.futures import ThreadPoolExecutor, as_completed

from .ast_parser import ASTParser
from .parsers.tree_sitter_parser import TreeSitterParser
from .neo4j_adapter import Neo4jAdapter
from .cache_manager import CachingManager
from .models import FileAnalysis
from .import_resolver import ImportResolver
from .call_graph import CallGraphBuilder
from .embeddings import CodeEmbedder
from .chunker import CodeChunker
from .qdrant_adapter import QdrantAdapter
from .leann_adapter import LeannAdapter
from .chroma_adapter import ChromaAdapter
from tools.git_analyzer import GitAnalyzer
from tools.rag.rag_service import RAGService
from tools.rag.fact_extractor import FactExtractor
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
        self.parser = ASTParser() # Keep as default python parser
        self.import_resolver = ImportResolver(self.repo_path)
        self.call_graph_builder = CallGraphBuilder()
        self.git_analyzer = GitAnalyzer(str(self.repo_path))
        self.memory_config = cfg.MemoryConfig()
        
        # Parsers
        self.parsers = {}
        self._init_parsers()
        
        # Semantic Components (Lazy load)
        self.code_embedder = None
        self.qdrant_adapter = None
        self.chroma_adapter = None
        self.leann_adapter = None
        self.chunker = None
        
        # RAG Component
        self.rag_service = None
        
        # Initialize Neo4j (Lazy load or config based)
        self.neo4j_adapter = None  

    def _init_parsers(self):
        """Initialize language parsers"""
        self.parsers['python'] = self.parser
        
        # Initialize Tree-sitter parsers
        for lang in ['cpp', 'c', 'java', 'go', 'javascript', 'typescript']:
            try:
                self.parsers[lang] = TreeSitterParser(lang)
            except Exception as e:
                logger.debug(f"Parser for {lang} not available: {e}")

    def get_parser(self, file_path: Path):
        """Get appropriate parser for file"""
        ext = file_path.suffix.lower()
        if ext in ['.py']:
            return self.parsers.get('python')
        elif ext in ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.ino']:
            return self.parsers.get('cpp')
        elif ext in ['.c', '.h']:
            return self.parsers.get('c') or self.parsers.get('cpp')
        elif ext in ['.java']:
            return self.parsers.get('java')
        elif ext in ['.go']:
            return self.parsers.get('go')
        elif ext in ['.js', '.jsx']:
            return self.parsers.get('javascript')
        elif ext in ['.ts', '.tsx']:
             return self.parsers.get('typescript')
        return None

    def connect_db(self, uri: str, auth: tuple):

        self.neo4j_adapter = Neo4jAdapter(uri, auth)
        self.neo4j_adapter.init_schema()
    
    def init_semantic(self):
        """Initialize semantic analysis components (Embeddings + Vector DB)"""
        if self.memory_config.memory_type == "leann":
            if not self.leann_adapter:
                self.leann_adapter = LeannAdapter(self.session_id)
        elif self.memory_config.memory_type == "chroma":
            if not self.code_embedder:
                self.code_embedder = CodeEmbedder()
            if not self.chroma_adapter:
                self.chroma_adapter = ChromaAdapter()
        else:
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
            if self.memory_config.memory_type == "leann":
                # Leann uses text query
                return self.leann_adapter.search(
                    source_code, 
                    limit=limit, 
                    score_threshold=threshold,
                    # We might pass default filters if needed, but session is handled by adapter path
                    query_filter={"session_id": self.session_id} 
                )
            elif self.memory_config.memory_type == "chroma":
                vector = self.code_embedder.embed_query(source_code)
                # Chroma uses 'where' filter
                return self.chroma_adapter.search(
                    vector, 
                    limit=limit, 
                    score_threshold=threshold,
                    query_filter={"session_id": self.session_id}
                )
            else:
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
                        parser = self.get_parser(file_path)
                        
                        if parser:
                            # Structural Analysis via Parser (Python, C++, etc.)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                
                                analysis = parser.parse(content, file_path, self.repo_path)
                                
                                # Python Specific Enrichment (Call Graph & Resolve Imports)
                                # TODO: Move this logic into ASTParser or LanguageSpecific Enrichers
                                if analysis and isinstance(parser, ASTParser):
                                    try:
                                        # Parse AST for calls
                                        tree = ast.parse(content, filename=str(file_path))
                                        analysis.calls = self.call_graph_builder.build(tree)
                                        
                                        # Resolve Imports
                                        for imp in analysis.imports:
                                            resolved = self.import_resolver.resolve_import(imp, file_path)
                                            if resolved:
                                                imp_name = imp.module if imp.module else (imp.names[0] if imp.names else "")
                                                if imp_name:
                                                    analysis.resolved_imports[imp_name] = str(resolved)
                                    except Exception as e:
                                        logger.warning(f"AST enrichment failed for {file_path}: {e}")
                                        
                            except Exception as e:
                                logger.warning(f"Structural parsing failed for {file_path}: {e}")
                                analysis = None

                        if not analysis:
                            # Fallback: Generic text parsing
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                
                                rel_path = file_path.relative_to(self.repo_path).as_posix()
                                analysis = FileAnalysis(
                                    file_path=rel_path,
                                    language=file_path.suffix.lstrip('.') or "text",
                                    loc=len(content.splitlines())
                                )
                            except UnicodeDecodeError:
                                # logger.warning(f"Skipping binary/encoding error: {file_path}")
                                continue
                            except Exception as e:
                                logger.warning(f"Generic parse failed for {file_path}: {e}")
                                continue

                        if analysis:
                            self.cache.save_analysis(file_path, analysis)
                    
                    # 3. Store in Neo4j (Nodes + Relationships)
                    if analysis and self.neo4j_adapter:
                        self.neo4j_adapter.store_analysis(
                            analysis, 
                            self.repo_path.name, 
                            commit_hash=current_commit,
                            session_id=self.session_id
                        )
                    
                    # 4. Semantic Analysis (Embeddings)
                    if analysis and use_semantic and self.code_embedder and self.qdrant_adapter:
                        self._process_semantic_analysis(file_path, analysis)
                        
                    processed_count += 1
                    progress.advance(task)
                    
                except Exception as e:
                    self.session.log_error(f"Error processing {file_path}: {e}")
                    logger.error(f"Error processing {file_path}: {e}")

        self.session.log_progress(f"Completed analysis. Processed {processed_count}/{total_files} files.")
        
        # 5. Link Cross-File Calls (Second Pass)
        if self.neo4j_adapter:
            self.session.log_progress("Linking cross-file call relationships...")
            self.neo4j_adapter.link_unresolved_calls()
        
        # 6. Architecture Tagging
        if self.neo4j_adapter:
            self.session.log_progress("Auto-tagging architecture layers...")
            self.neo4j_adapter.auto_tag_layers(self.repo_path.name)
        
        self.session.log_finding("Analysis Complete", f"Successfully analyzed {processed_count} files.")
        
        # Log Final Stats
        import time
        stats = {
            "files_processed": processed_count,
            "total_files": total_files,
            "error_count": total_files - processed_count,
            "duration_seconds": 0  # To be filled by CLI or wrapper, but we can't easily measure here without start time passed in
        }
        # In a real implementation we would track detailed node counts from adapter
        self.session.finalize_report(stats)
        
        # Record analysis in history
        try:
            project_id = self.session.session_id
            commit_hash = current_commit
            
            from core.project_history import ProjectHistoryManager
            history_mgr = ProjectHistoryManager()
            history_mgr.record_analysis(
                project_id=project_id,
                repo_path=str(self.repo_path),
                commit_hash=commit_hash,
                analysis_type="deep" if use_semantic else "full",
                files_count=total_files,
                files_analyzed=processed_count,
                duration_seconds=0  # Timing would need to be passed in
            )
        except Exception as e:
            logger.warning(f"Failed to record analysis history: {e}")

        # Connection should be closed by the caller using analyzer.close()
        # if self.neo4j_adapter:
        #    self.neo4j_adapter.close()
            
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
                # Add session_id for multi-repo querying
                payload["session_id"] = self.session_id
                
                items_to_embed.append(payload)
            
            if items_to_embed:
                if self.memory_config.memory_type == "leann":
                    self.leann_adapter.store_embeddings(items_to_embed)
                else:
                    # Generate embeddings (will use 'content' key by default in our embedder logic)
                    embedded_items = self.code_embedder.embed_code_batch(items_to_embed)
                    # Store in Qdrant
                    self.qdrant_adapter.store_embeddings(embedded_items)
                
        except Exception as e:
            logger.error(f"Semantic analysis failed for {file_path}: {e}")

    def _find_files(self) -> Generator[Path, None, None]:
        """Yield files in repo, respecting gitignore (simple filtering)"""
        # Supported extensions for text/code analysis
        SUPPORTED_EXTENSIONS = {
            # Python
            '.py', '.pyi', '.pyx', '.ipy',
            # JavaScript/Web
            '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.vue', '.svelte', '.astro',
            '.html', '.htm', '.css', '.scss', '.sass', '.less', '.styl',
            '.json', '.json5', '.xml', '.yaml', '.yml', '.toml', '.graphql', '.gql',
            # C/C++
            '.c', '.cpp', '.cxx', '.cc', '.cp', '.h', '.hpp', '.hxx', '.hh', '.inl', '.m', '.mm', '.ino',
            # JVM
            '.java', '.kt', '.kts', '.scala', '.groovy', '.clj', '.cljs',
            # .NET
            '.cs', '.fs', '.vb',
            # Go/Rust
            '.go', '.rs',
            # Shell/Scripting
            '.sh', '.bash', '.zsh', '.fish', '.bat', '.ps1', '.cmd', '.awk', '.sed',
            '.rb', '.php', '.pl', '.pm', '.lua', '.r', '.dart', '.el', '.vim',
            # Config/Data
            '.ini', '.conf', '.cfg', '.properties', '.env', '.env.example', '.csv', '.tsv', '.sql',
            '.dockerfile', '.editorconfig', '.gitignore', '.gitattributes',
            # Docs
            '.md', '.markdown', '.rst', '.txt', '.tex', '.asc', '.adoc'
        }
        
        # For now, simple walk + exclude hidden/.gits
        for p in self.repo_path.rglob("*"):
            if not p.is_file():
                continue
                
            # Filter excluded dirs
            parts = p.parts
            if any(part.startswith(".") and part != "." and part != ".." for part in parts) or \
               "venv" in parts or "__pycache__" in parts or "node_modules" in parts or "dist" in parts or "build" in parts:
                continue

            # Filter by extension (simple binary exclusion)
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield p
            elif p.name in ['Dockerfile', 'Makefile', 'LICENSE', 'Gemfile', 'Rakefile']:
                 yield p

    def extract_semantic_facts(self, file_paths: List[Path] = None):
        """
        Run LLM-based fact extraction on specified files (or all source files) 
        and store the resulting RDF-style triples in Neo4j.
        Uses parallel processing to speed up LLM extraction.
        """
        if not self.neo4j_adapter:
            logger.warning("Neo4j adapter not connected. Cannot store facts.")
            return

        # Lazy init extractor
        if not hasattr(self, 'fact_extractor') or self.fact_extractor is None:
            try:
                self.fact_extractor = FactExtractor()
            except Exception as e:
                logger.error(f"Failed to initialize FactExtractor: {e}")
                return
            
        targets = file_paths if file_paths else list(self._find_files())
        
        logger.info(f"Starting Semantic Fact Extraction on {len(targets)} files...")
        
        # Parallel extraction using ThreadPoolExecutor
        max_workers = 4  # Balance between speed and API rate limits
        
        with Progress() as progress:
            task = progress.add_task("[magenta]Extracting Facts...", total=len(targets))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_file = {}
                for fp in targets:
                    future = executor.submit(self._extract_and_store_facts, fp)
                    future_to_file[future] = fp
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    fp = future_to_file[future]
                    try:
                        future.result()  # Will raise if extraction failed
                    except Exception as e:
                        logger.debug(f"Fact extraction skipped for {fp.name}: {e}")
                    
                    progress.advance(task)
                
        logger.info("Semantic Fact Extraction completed.")

    def _extract_and_store_facts(self, file_path: Path):
        """
        Extract facts from a single file and store in Neo4j.
        This runs in a separate thread.
        """
        try:
            # Read content (with size limit)
            content = file_path.read_text(errors='ignore')
            if not content.strip():
                return
                
            if len(content) > 20000:
                # Take head and tail for context
                content = content[:15000] + "\n...[truncated]...\n" + content[-5000:]
            
            # LLM Extraction (this is what makes it slow)
            facts = self.fact_extractor.extract_facts(content)
            
            # Store in Neo4j
            if facts and self.neo4j_adapter:
                self.neo4j_adapter.store_facts(facts, repo_id=str(self.repo_path))
                    
        except Exception as e:
            logger.debug(f"Error in _extract_and_store_facts for {file_path}: {e}")
            raise

