# Yaver Development Scratchpad & Roadmap

> **NOTE:** This file is a living document (scratchpad). It is updated, wiped, and rewritten during every development phase. It serves as the current state of truth, backlog, and architectural vision.

## 🎯 Strategic Vision (The "Long Road")

Yaver is evolving from a simple Python coding assistant into a **Polyglot Autonomous Developer** with a strong focus on **Systems Programming (C/C++)** and **Logical Reasoning**.

### Core Capabilities Targeted:
1.  **Systems Engineering Focus**: Transition from Python scripts to handling C/C++ build systems (Make, CMake, Ninja), memory management, and compilation errors.
2.  **Cognitive Architecture**: Moving beyond simple "Prompt -> Code" to "Memory + graph RAG + Reasoning Model -> Plan -> Code".
3.  **Active Intelligence Gathering**: The "Social" aspect is not just about replying to PRs; it is about autonomously gathering context, scraping documentation, understanding dependencies, and building a knowledge graph of the ecosystem.

---

## 🟢 Phase 1: Stability & Verification (Current)
*Target: Stop "blind commits" and ensure basic reliability.*

- [x] **Conflict Handling**: Basic merge/rebase (Implemented).
- [ ] **Language Architecture Analysis**:
    - [x] Verify Tree-sitter availability (Implemented: `scripts/check_languages.py`).
    - [x] **Refactor Parser**: Switch `src/tools/analysis/parser.py` from regex to tree-sitter for robust C/C++ parsing.
    - [x] **Build Verification**:
        - [x] `SyntaxChecker` module with Tool -> LLM fallback.
        - [x] **Output Feedback Loop**: Integrated into `AgentTaskManager`. If `SyntaxChecker` fails, it triggers `CoderAgent.fix_code()` automatically.
        - [x] **Verify Tests**: Created `tests/integration/test_parser_real.py` and `tests/integration/test_syntax_real.py`.

## 🟡 Phase 2: Enhanced Context & Reasoning (Current)
*Target: "Think before you code."*

### Architecture Upgrade
- [x] **Build System Awareness**:
    - Created `BuildAnalyzer` to parse Makefile/Go/CMake.
    - Integrated into `agent_task_manager.py` prompt.
    - **Implementation**: Updated `tools/memory_ops.py` to ingest build targets using `BuildAnalyzer`.
- [x] **Logic & Reasoning Integration**:
    - **Planner Awareness**: `PlannerAgent` now scans `ToolRegistry` to understand available capabilities dynamically.
    - **Self-Correction Loop**: Implemented `yaver solve` command causing a `Plan -> Code -> Review -> Retry` loop.
    - **Fact Extraction**: Preserved and integrated into `MemoryQueryOrchestrator`.
    - **Reasoning System**: `Query Orchestrator` now implements Hybrid Search (Vector + Structural).
    - **Graph Integration**: `NetworkX Adapter` upgraded with storage for imports/calls and deduplication fixes.
- [x] **Live Execution & Sandbox**:
    - **Sandbox Integration**: `ChatAgent` can now execute Python code in a secure sandbox (`python:execute` blocks).
    - **Tool Call Support**: Fixed `agent_chat.py` to handle both standard Markdown blocks and LLM Tool Calls (JSON) for robust execution.
    - **Context Fixes**: Refactored chat history management to ensure context is passed correctly without confusing the model.
- [x] **Context-Aware Reviewer**:
    - **Reviewer Upgrade**: `ReviewerAgent` now fetches RAG context (definitions, dependencies) before reviewing code.
    - **Prompt Update**: Updated `reviewer_user.md` to include injected context.
    - **Integration**: `yaver solve` pipeline now passes file path to reviewer for context lookup.
- **Hybrid RAG**: Combine Vector Search (Semantic) with Knowledge Graph (Structural - e.g., Call Graphs, Header Dependencies).

### C/C++ Specialization
- **Build System Awareness**: Agent must understand `Makefile` targets and `CMakeLists.txt` structures.
- **Header Analysis**: RAG must retrieve relevant `.h` files when modifying `.c` files to prevent signature mismatches.

## 🔴 Phase 3: The "Social Researcher"
*Target: Autonomous data gathering and ecosystem understanding.*

- **Dependency Intelligence**: When working on a repo, traverse its dependencies/submodules to understand the broader system.
- **Documentation Crawler**: Scrape and index project documentation/wikis into the Vector Store (`Chroma`/`Qdrant`) to answer "How do I use API X?" correctly.
- **Self-Evaluation (Low Priority)**: Analyze human reactions (emojis, comments) to its own PRs.

---

## 📝 Session Summary (Feb 06, 2026)
*Use this context to resume work in future sessions.*

### 🚀 Recent Achievements
1.  **Performance Fix**: Refactored CLI to use **Lazy Loading**, fixing startup crashes and enabling fast autocompletion.
2.  **Planner Upgrade**: `PlannerAgent` is now "Self-Aware". It knows exactly which tools (Git, File, Shell) are available in the runtime and adjusts its plan accordingly.
3.  **New Command**: Added `yaver solve <task> <file>` which orchestrates:
    -   *Planner*: Generates a markdown plan.
    -   *Coder*: Writes code.
    -   *Reviewer*: Audits code. (If rejected, loops back to Planner/Coder).
4.  **Legacy Cleanup**: Removed `autonomous_worker.py` and old API layers; `MemoryQueryOrchestrator` is now the single source of truth.
5.  **Reviewer Intelligence**:
    -   Added DORA Metrics awareness (Failure Rate, Lead Time).
    -   Enable Context-Aware reviews (RAG integration).
    -   Added E2E verification script `scripts/verify_reviewer_dora.py`.
6.  **Social/Forge Integration**:
    -   Added `list_review_requests` to Forge Tool (GitHub/Gitea).
    -   Updated `social_developer_node` to auto-review PRs where the user is requested.
    -   Updated `GitClient` to support fetching/checkout of PR refs (`refs/pull/ID/head`).

### 🐛 Identified TODOs & Technical Debt
-   **Policy**: DO NOT DELETE functional verification scripts (e.g., `verify_reviewer_dora.py`). They serve as regression tests.
-   **Tree-sitter Parser**: `src/tools/code_analyzer/parsers/tree_sitter_parser.py` needs better argument and method extraction.
-   **Large File Handling**: `src/tools/code_analyzer/chunker.py` needs sliding window logic for files > token limit.
-   **GitLab Adapter**: `src/tools/forge/adapters/gitlab.py` needs proper mention support (currently hacking `todos` endpoint).
-   **Reviewer Language Detection**: `yaver solve` currently hardcodes "python" for the reviewer; needs auto-detection from file extension.

---

## 🗑️ Legacy Cleanup Log (Archived)
*The following components were removed to simplify the architecture (Feb 2024)*

1.  **Autonomous Execution Worker (`core/autonomous_worker.py`)**: Replaced by direct `TaskGraph` + `Orchestrator` execution. The old infinite loop worker was unreliable.
2.  **Legacy API Layer (`core/api.py`, `mcp/*`)**: The FastAPI backend was duplicative. We now invoke agents directly via CLI or potentially a simpler new API if needed later.
3.  **Legacy RAG Service (`tools/rag/rag_service.py`)**: This was a thin wrapper around ChromaDB. Now fully integrated into `MemoryQueryOrchestrator` which handles both Vector and Graph logic.
4.  **Old Fact Extractor Integration**: The capabilities were preserved, but the direct dependency was refactored into the Orchestrator.
    - *Goal*: "The user thumbs-downed my last 3 refactors; I should change my strategy or ask for clarification."
    - *Mechanism*: Sentiment analysis on PR comments -> Update internal "Persona" or "Strategy" memory.

## 🛑 Technical Debt / Known Issues
1.  **Python-Centric**: Current prompt templates and verification steps assume Python.
2.  **Blind Execution**: Agent runs `git push` without verifying if the build passes locally.
3.  **Single-Pass Logic**: Complex tasks are attempted in one go; need better "Chain of Thought" decomposition.
4.  **Policy**: DO NOT DELETE functional verification scripts (e.g., `verify_reviewer_dora.py`). They serve as regression tests.
5.  **Documentation**: Whenever a new feature is implemented, you MUST update `docs/FEATURE_LIST.md` to reflect the new capabilities.
