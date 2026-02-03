# Deep Code Analysis System - Architecture & Implementation Plan

**Status:** Planning & Design Phase  
**Target Branch:** `feature/deep-code-analysis`  
**Estimated Duration:** 4 weeks (4 phases)  
**Started:** 2026-02-03

---

## 1. VISION & GOALS

### Primary Goal
Build a Google Codebase AI / Jules-like system that:
- **Learns** repositories deeply (AST parsing, call graphs, dependencies)
- **Stores** structural and semantic information in dual databases
- **Reasons** about code changes and their impact
- **Advises** on architecture, refactoring, and safety of modifications

### Key Capabilities
```
User asks: "Can I safely change auth.py's authenticate() method?"

System:
├─ Queries Neo4j: "What calls authenticate()?" → 12 functions
├─ Analyzes graph: "Do any depend on signature?" → 5 functions
├─ Queries Qdrant: "Security-related code?" → Checks token handling
├─ LLM reasoning: "Potential breaking changes?"
└─ Response: "HIGH RISK - 5 callers expect strict type validation"
```

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Data Model

#### Neo4j Graph (Structural Knowledge)
```
Nodes:
├─ File (name, path, language, lines_of_code)
├─ Module (name, layer: "api"|"core"|"data")
├─ Class (name, methods, properties, lines)
├─ Function (name, params, returns, complexity, lines)
└─ Architecture (layer, description)

Relationships:
├─ FILE_CONTAINS_CLASS
├─ CLASS_DEFINES_METHOD
├─ FUNCTION_CALLS_FUNCTION (weight: call_count)
├─ MODULE_IMPORTS_MODULE (weight: import_count)
├─ FUNCTION_USES_CLASS
├─ IN_LAYER (file/module → layer)
├─ CIRCULAR_DEPENDENCY (A ↔ B)
└─ TIGHT_COUPLING (high_interconnection)

Properties:
├─ last_analyzed: timestamp
├─ repository_id: uuid
├─ language: "python" | "go" | "javascript"
└─ metrics: {complexity, maintainability, test_coverage}
```

#### Qdrant Vectors (Semantic Knowledge)
```
Collection: "repository_code"
├─ code_snippet (text)
├─ embedding (768d vector)
└─ metadata:
   ├─ file_path
   ├─ function_name
   ├─ type: "implementation" | "docstring" | "test" | "pattern"
   ├─ language
   ├─ module_layer: "api" | "core" | "data"
   ├─ repository_id
   └─ timestamp

Collection: "architecture_insights"
├─ description (text)
├─ embedding
└─ metadata:
   ├─ scope: "file" | "module" | "layer" | "system"
   ├─ type: "pattern" | "issue" | "opportunity"
   ├─ repository_id
   └─ auto_generated: bool
```

---

## 3. IMPLEMENTATION PHASES

### PHASE 1: Deep Code Analyzer (Week 1)

**Goal:** Extract code structure from repositories

**New Modules:**
```
src/tools/code_analyzer/
├── __init__.py
├── ast_parser.py          # Multi-language AST parsing
├── call_graph.py          # Build call graphs
├── dependency_mapper.py    # Map module dependencies
├── code_embedder.py       # Create embeddings for code
└── models.py              # Data classes for analysis results
```

**Key Functions:**

`ast_parser.py`:
```python
class CodeAnalyzer:
    def analyze_directory(path: str) -> AnalysisResult
    def parse_python_files(path: str) -> List[PythonFile]
    def extract_classes(tree: ast.AST) -> List[ClassDef]
    def extract_functions(tree: ast.AST) -> List[FunctionDef]
    def extract_imports(tree: ast.AST) -> List[ImportDef]
```

`call_graph.py`:
```python
class CallGraphBuilder:
    def build_call_graph(analysis: AnalysisResult) -> CallGraph
    def find_callers(func_id: str) -> List[FunctionDef]
    def trace_call_chain(func_id: str) -> CallChain
    def detect_circular_calls() -> List[CircularDep]
```

`dependency_mapper.py`:
```python
class DependencyMapper:
    def map_file_dependencies(path: str) -> DependencyGraph
    def detect_circular_imports() -> List[CircularImport]
    def find_entry_points() -> List[Function]
    def calculate_coupling_metrics() -> CouplingMetrics
```

**Output:** `AnalysisResult` object with all extracted data (not yet in DB)

---

### PHASE 2: Repository Learning & Storage (Week 2)

**Goal:** Save analyzed data to Neo4j + Qdrant

**New Features:**
```
devmind learn <repo_path> [--name "ProjectName"] [--language python]

Process:
1. Call Phase 1 analyzer
2. Generate embeddings for code blocks
3. Detect architecture layers
4. Create Neo4j nodes + relationships
5. Store embeddings in Qdrant
6. Tag in session memory
7. Return learning summary
```

**New Commands:**
```bash
devmind learn .                           # Learn current repo
devmind learn /path/to/repo --name "API" # Named project
devmind knowledge list                    # Show learned repos
devmind knowledge remove <repo_id>        # Delete knowledge
```

---

### PHASE 3: RAG-based Querying (Week 3)

**Goal:** Answer questions about learned repositories using graph + vectors

**Integration Points:**
```
agent_base.py - retrieve_relevant_context():
├─ Neo4j query: Structural questions
├─ Qdrant search: Semantic context
└─ Combine + enhance with LLM

New prompts:
├─ CALL_GRAPH_ANALYZER_PROMPT
├─ IMPACT_ANALYZER_PROMPT
└─ ARCHITECTURE_QUESTIONER_PROMPT
```

**Example Queries:**
```python
# What calls this function?
graph.query_callers("src/auth.py::authenticate")
# → Returns 12 callers with locations

# What will break if I change this?
analyzer.analyze_impact("src/auth.py::authenticate", change_type="signature")
# → Returns affected functions, confidence, recommendations

# Show me the auth flow
graph.trace_call_chain("src/api.py::handle_login")
# → Returns sequence diagram data
```

---

### PHASE 4: Intelligent Chat (Week 4)

**Goal:** Natural language understanding of codebase

**Example Interactions:**
```
Q: "I want to add caching to get_user(). What breaks?"
A: [Analyzes Neo4j for side effects]
   [Checks Qdrant for similar patterns]
   "Found 3 callers expecting immediate consistency:
    - login() at line 234
    - refresh_token() at line 456  
    - get_profile() at line 789
    Risk: MEDIUM - Use TTL-based cache"

Q: "Show database layer"
A: [Filters Neo4j by IN_LAYER relationship]
   "Database Layer (12 modules):
    ├─ models/
    ├─ migrations/
    ├─ queries/
    └─ transactions/"

Q: "Extract API schema"
A: [Finds decorators @api, @route in Neo4j]
   [Generates OpenAPI spec]
```

---

## 4. TECHNOLOGY CHOICES

### Code Parsing
- **Python:** Built-in `ast` module (most accurate)
- **Go:** `go/parser` if available, else regex-based
- **JavaScript:** `ast` via `esprima` or similar

### Initial Support: **Python only** (Week 1-2)
Then expand to Go if needed.

### Embeddings
- Use existing Ollama embeddings (768-dim, nomic-embed-text)
- Chunk code: max 500 tokens per embedding
- Include context: function name, class name, docstring

### Graph Database
- Neo4j (already in setup)
- Query language: Cypher
- Update strategy: Append-only + versioning

---

## 5. DETAILED DESIGN DECISIONS

### 5.1 When to Learn vs. On-demand Analysis

**Learn (Store):**
- When explicitly asked: `devmind learn <repo>`
- Time cost: ~1-2 minutes for large repos
- Benefit: Instant queries, context in future chats
- Storage: Per-repository

**On-demand (Temporary):**
- When analyzing unknown repo: `devmind analyze <repo> --deep`
- Time cost: ~30-60 seconds
- Benefit: No storage overhead
- Storage: Session memory only

### 5.2 Architecture Detection

**Heuristics:**
```
API Layer:
├─ Contains: cli/, api/, server/, routes/
├─ Files: *_handler.py, *_endpoint.py, main.py
└─ Pattern: HTTP decorators, CLI commands

Core Layer:
├─ Contains: agents/, tools/, core/, services/
├─ Pattern: Business logic, no external I/O
└─ Metrics: Most internal dependencies

Data Layer:
├─ Contains: models/, db/, storage/, memory/
├─ Pattern: Database models, ORM, storage
└─ Characteristics: Lowest-level imports
```

### 5.3 Impact Analysis Algorithm

```
Function Change: change_function_signature()

Step 1: Find all direct callers (Neo4j)
   callers = query("MATCH (c)-[:CALLS]->(f) WHERE f=target")

Step 2: For each caller, check:
   - Does it pass arguments? (signature sensitive?)
   - Does it use return value? (return type sensitive?)
   - Are there tests? (coverage?)

Step 3: Transitively affected:
   affected = find_transitive_callers(callers)

Step 4: Score risk:
   risk = (direct_callers × 0.5) + (transitive × 0.2) + (test_coverage × -0.3)

Step 5: LLM reasoning:
   "Given {code_context}, this change has {risk_level} impact because..."
```

---

## 6. DATABASE SCHEMA DETAILS

### Neo4j Constraints
```cypher
CREATE CONSTRAINT unique_function_id
  ON (f:Function) ASSERT f.id IS UNIQUE;

CREATE CONSTRAINT unique_file_path
  ON (f:File) ASSERT f.repository_id + f.path IS UNIQUE;

CREATE INDEX file_language
  ON (f:File) FOR (f.language);

CREATE INDEX repo_timestamp
  ON (f:File) FOR (f.last_analyzed);
```

### Qdrant Collection Schema
```json
{
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "payload_schema": {
    "file_path": {"type": "keyword"},
    "function_name": {"type": "keyword"},
    "type": {"type": "keyword"},
    "language": {"type": "keyword"},
    "module_layer": {"type": "keyword"},
    "repository_id": {"type": "keyword"},
    "timestamp": {"type": "datetime"}
  }
}
```

---

## 7. BRANCH STRATEGY

```
main/master
├─ feature/deep-code-analysis (THIS BRANCH)
│  ├─ phase-1/code-analyzer (Week 1)
│  ├─ phase-2/repository-learning (Week 2)
│  ├─ phase-3/rag-queries (Week 3)
│  └─ phase-4/intelligent-chat (Week 4)
│     └─ → MERGE to master when complete
```

**Workflow:**
```bash
# Start feature branch
git checkout -b feature/deep-code-analysis

# Each phase is a commit
git commit -m "feat: Phase 1 - Deep code analyzer module"
git commit -m "feat: Phase 2 - Repository learning system"
# ... etc

# Final PR to master with all phases
```

---

## 8. TESTING STRATEGY

### Unit Tests
```python
tests/
├── test_ast_parser.py
│   ├── test_extract_functions()
│   ├── test_extract_classes()
│   └── test_extract_imports()
├── test_call_graph.py
│   ├── test_build_call_graph()
│   ├── test_find_callers()
│   └── test_detect_circular_calls()
└── test_impact_analyzer.py
    ├── test_impact_score()
    └── test_ripple_effect()
```

### Integration Tests
```
Test Repositories: (small test projects)
├── simple_app/ (100 lines)
├── medium_project/ (1000 lines)
└── complex_system/ (10000 lines)

Test Scenarios:
├─ Parse correctly?
├─ Neo4j storage works?
├─ Qdrant embeddings generated?
├─ Queries return correct results?
└─ Impact analysis accurate?
```

---

## 9. PERFORMANCE TARGETS

| Operation | Target Time | Repo Size |
|-----------|------------|-----------|
| Parse Python files | < 5 sec | 1000 files |
| Build call graph | < 10 sec | 1000 files |
| Generate embeddings | < 30 sec | 1000 files |
| Store to Neo4j | < 5 sec | 1000 functions |
| Store to Qdrant | < 10 sec | 1000 embeddings |
| Query impact | < 1 sec | Any |
| Semantic search | < 2 sec | Any |

---

## 10. DOCUMENTATION NEEDED

In `docs/` folder:
- [x] `DEEP_ANALYSIS_GUIDE.md` - User guide
- [x] `GRAPH_SCHEMA.md` - Neo4j structure
- [x] `PHASE4_COMPLETION.md` - Phase 4 completion summary

---

## 11. NEXT STEPS (COMPLETED)

### Implementation Status:
- ✅ All Phase 1-4 features implemented
- ✅ 19/19 tests passing
- ✅ Performance benchmark exceeded (0.14s for 1000 files vs 15s target)
- ✅ Documentation complete

### Optional Future Enhancements:
- Consider Go language support (Python-first validated)
- Additional visualization types (sequence diagrams, dependency matrices)
- ML-based dynamic call confidence scoring
3. Implement `call_graph.py`
4. Implement `dependency_mapper.py`
5. Write unit tests
6. Commit: "feat: Phase 1 - Deep code analyzer"

---

## 12. RISK MITIGATION

| Risk | Mitigation |
|------|-----------|
| Large repos slow | Implement caching, incremental analysis |
| AST parsing fails | Fallback to regex-based parsing |
| Neo4j connection issues | Queue operations, retry logic |
| Embeddings expensive | Batch operations, lazy generation |
| Memory leaks during parsing | Use generators, explicit cleanup |

---

## 14. STATE MANAGEMENT & OBSERVABILITY (The "Manus" Pattern)

Inspired by [planning-with-files](https://github.com/OthmanAdi/planning-with-files), we will implement a file-based state management system for long-running analysis tasks. This treats the file system as "Persistent Memory" and the LLM Context as "RAM".

### The 3-File Pattern
For every deep analysis session (e.g., `devmind analyze --deep`), the system will maintain three live Markdown files in `.devmind/sessions/<session_id>/`:

#### 1. `task_plan.md` (The Strategy)
- **Purpose**: Prevents goal drift.
- **Content**:
  - High-level phases (e.g., "1. Parse AST", "2. Build Graph", "3. Identify Risks").
  - Current active step.
  - Acceptance criteria.
- **Mechanism**: The Agent must read this file before starting a new major step.

#### 2. `findings.md` (The Knowledge)
- **Purpose**: Persist insights without context stuffing.
- **Content**:
  - Discovered architecture patterns.
  - Potential bugs or risks found.
  - Key dependencies identified.
- **Mechanism**: Appended to as analysis progresses. Indexed by RAG later.

#### 3. `progress.md` (The Log)
- **Purpose**: Execution history and error tracking.
- **Content**:
  - Chronological log of tool executions.
  - Error logs (to avoid repeating mistakes).
  - Test results.

### Implementation Integration
```python
class AnalysisSession:
    def __init__(self, session_id):
        self.state_dir = f".devmind/sessions/{session_id}"
        self.plan_file = self.state_dir / "task_plan.md"
        self.findings_file = self.state_dir / "findings.md"
        self.progress_file = self.state_dir / "progress.md"

    def update_phase(self, phase_name, status="in-progress"):
        # Updates task_plan.md checkboxes
        pass
    
    def log_finding(self, finding):
        # Appends to findings.md
        pass
```

---

## 15. DETAILED TESTING INFRASTRUCTURE

To ensure robustness, we will establish a dedicated test suite reflecting the modular architecture.

### Directory Structure (`tests/`)
```
tests/
├── __init__.py
├── conftest.py                 # Global fixtures (Neo4j/Qdrant mocks)
├── data/                       # Test data assets
│   ├── sample_python_repo/     # Real code for integration tests
│   └── broken_syntax_repo/     # For robustness testing
├── unit/
│   ├── analyzer/
│   │   ├── test_ast_parser.py
│   │   ├── test_import_resolver.py
│   │   └── test_complexity_metrics.py
│   ├── graph/
│   │   ├── test_neo4j_adapter.py
│   │   └── test_call_graph.py
│   └── semantic/
│       ├── test_code_embedder.py
│       └── test_chunking_strategy.py
└── integration/
    ├── test_full_analysis_flow.py
    ├── test_incremental_learning.py
    └── test_state_persistence.py  # Verify markdown file updates
```

### Key Test Fixtures (`conftest.py`)
- `mock_neo4j`: Uses `neo4j-experimental` or a Docker container wrapper to prevent writing to the real DB during unit tests.
- `mock_qdrant`: Uses Qdrant's in-memory mode.
- `temp_repo`: Generates a temporary Python project on the fly for parsing tests.

---

## 16. REVISED TODO LIST (With Test & State Tasks)

### ✅ Phase 1: Foundation (Code Analyzer + Structural Storage) [Week 1]
**Goal:** Parse code, visualize structure in Neo4j, and handle caching.

- [x] **Infrastructure Setup**
    - [x] Create `src/tools/code_analyzer/` structure.
    - [x] **[TEST]** Create `tests/` structure and `tests/data/sample_python_repo`.
    - [x] **[STATE]** Implement `AnalysisSession` class (The 3-File Pattern manager).
    - [x] Implement `CachingManager` (File hash → Cached AST/Result).
    - [x] Define Neo4j Constraints & Indexes (Schema).

- [x] **AST Parsing (Static Analysis)**
    - [x] Implement `ASTParser` using Python `ast` module.
    - [x] **[TEST]** Write `tests/unit/analyzer/test_ast_parser.py`.
    - [x] **Optimization:** Use Generator pattern for memory-efficient directory traversal.
    - [x] Implement `ClassExtractor` & `FunctionExtractor`.

- [x] **Graph Storage (Neo4j)**
    - [x] Implement `Neo4jAdapter` class.
    - [x] **[TEST]** Write `tests/unit/graph/test_neo4j_adapter.py` with mock driver.
    - [x] Implement `batch_insert_nodes()` (Files, Classes, Functions).
    - [x] Implement `batch_insert_relationships()` (CONTAINS, DEFINES).
    - [x] **Feature:** Add `commit_hash` and `version` properties to all nodes.

- [x] **CLI & Visualization**
    - [x] Add `devmind analyze --deep` command.
    - [x] **[STATE]** Ensure CLI initializes `task_plan.md` at start.
    - [x] Add `devmind visualize <file>` (Output basic Mermaid Class Diagram).

### 🚀 Phase 2: Relationships & Impact Analysis [Week 2]
**Goal:** Connect the dots (Call Graphs) and calculate change risks.

- [x] **Deep Relationship Mapping**
    - [x] Implement `CallGraphBuilder` (Static calls).
    - [x] **[TEST]** Test call graph with `tests/unit/graph/test_call_graph.py`.
    - [x] Implement `ImportResolver` (Map imports to actual files/modules).
    - [x] **Feature:** Circular Dependency Detection logic.

- [x] **Incremental Learning Engine**
    - [x] Add `devmind analyze --incremental` flag.
    - [x] Logic: Get `git diff` -> identify changed files -> re-parse ONLY those.
    - [x] **[TEST]** `tests/integration/test_incremental_learning.py`.

- [x] **Impact Analysis & Simulation**
    - [x] Implement `ImpactAnalyzer` algorithm.
    - [x] **[STATE]** Log risk findings to `findings.md`.
    - [x] Add `devmind simulate "change signature of X"` command.

### 🧠 Phase 3: Semantic Understanding & RAG [Week 3]
**Goal:** Understand what the code *means* using Vector DB.

- [x] **Semantic Engine**
    - [x] Implement `CodeEmbedder`.
    - [x] **Enhancement:** Context-Aware Chunking strategy:
        - [x] Chunk = `Docstring` + `Signature` + `Body subset` + `Context Tags`.
    - [x] **[TEST]** Verify chunking logic in `tests/unit/semantic/test_chunking.py`.

- [x] **Vector Storage (Qdrant)**
    - [x] Implement `QdrantAdapter` for `repository_code` collection.
    - [x] Implement "Code Clone Detection" logic (Cosine Similarity).

- [x] **Hybrid Query Engine**
    - [x] Create `RAGService` combining Neo4j (Structure) + Qdrant (Meaning).
    - [x] Implement prompts: `CONCEPT_EXPLAINER`, `SIMILAR_CODE_FINDER`.

### 🤖 Phase 4: Intelligence, Chat & Polish [Week 4]
**Goal:** Natural Language Interface and Production Readiness.

- [x] **Intelligent Agent Integration**
    - [x] Integrate deeper tools into `ChatAgent`.
    - [x] Add "Dynamic Logic" confidence score (Static heuristic-based detection).

- [x] **Advanced Features**
    - [x] **Visualization:** `devmind visualize call-graph <func>` (Mermaid Flowchart).
    - [x] **Architecture:** Auto-tagging layers (API/Core/Data) based on heuristics.
    - [x] **[STATE]** Finalize `progress.md` with complete session stats.

- [x] **Performance & Documentation**
    - [x] Benchmark: Ensure 1000 files parse < 15s (achieved 0.14s for 1000 files).
    - [x] Write `docs/DEEP_ANALYSIS_GUIDE.md`.
    - [x] Write `docs/GRAPH_SCHEMA.md`.

---

## NOTES & ASSUMPTIONS

- Python support is priority (Go optional in Phase 2)
- Neo4j is already running (from setup)
- Qdrant is already running (from setup)
- Using Ollama embeddings we configured
- Session-based memory system works (just added)

---

**Document Created:** 2026-02-03  
**Author:** DevMind Team  
**Status:** Ready for Implementation

