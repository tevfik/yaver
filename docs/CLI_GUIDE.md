# CLI Command Reference

Complete reference for all Yaver commands (v1.2.0).

## 🚀 Quick Start Workflow

1.  **Ingest Codebase** (Learn):
    ```bash
    yaver code analyze . --type deep --project-id my-cool-app
    ```
2.  **Start Chatting** (Context-Aware):
    ```bash
    yaver chat --project-id my-cool-app
    ```
3.  **Solve a Task** (Agentic Mode):
    ```bash
    yaver solve file "Refactor this class to use Singleton pattern" src/utils/logger.py
    ```

---

## Core Commands

### `yaver chat`
Interactive AI chat with codebase context.

```bash
yaver chat                              # Chat with all learned code
yaver chat --project-id=myapp           # Limit to specific project
yaver chat --session-id=debug-session   # Continue previous conversation
```

**Features:**
- Semantic search across codebase
- Natural language queries
- Context-aware responses using RAG
- Session-based conversation history

---

## Agentic Solver (New)

### `yaver solve file`
Autonomous Plan -> Code -> Review loop for specific files.

```bash
yaver solve file <task_description> <file_path> [options]
```

**Examples:**
```bash
yaver solve file "Add error handling to network calls" src/api/client.py
yaver solve file "Fix syntax error in line 42" tests/test_api.py --iterations 5
```

**Workflow:**
1.  **Plan**: Agent analyzes the file and available tools to create a step-by-step plan.
2.  **Code**: Coder agent executes the plan.
3.  **Review**: Reviewer agent audits the changes. If rejected, it loops back to fix it.

---

## Code Analysis & Learning

### `yaver code analyze`
Deep learn repository structure and code to build the Knowledge Graph.

```bash
yaver code analyze . --type deep --project-id=myapp  # Store in project context
yaver code analyze . --incremental      # Only analyze changed files
```

**Analysis Types:**
- `overview` - Basic stats (default)
- `deep` - Full analysis with AST, Graph, and Embeddings (Required for RAG)

---

### `yaver code query`
Semantic search across codebase.

```bash
yaver code query "authentication logic"
yaver code query "database connection" --limit 10
```

---

## Social & Verification

### `yaver verify`
System health and agent capability testing.

```bash
yaver verify social-live      # Test social agent against live repo
yaver verify social-clean     # Test in clean sandbox
```


## System Management

### `yaver system status`
Check system health and configuration.

```bash
yaver system status
```

Shows:
- Ollama connection and models
- Vector DB status (Qdrant/ChromaDB)
- Graph DB status (NetworkX/Neo4j)
- Configuration validity

---

### `yaver system setup`
Run configuration wizard.

```bash
yaver system setup
```

Interactive wizard to configure:
- Ollama URL and models
- Database providers
- Forge integration

---

### `yaver system docker`
Manage Docker services (if used).

```bash
yaver system docker start      # Start all services
yaver system docker stop       # Stop all services
yaver system docker status     # Check service status
yaver system docker logs       # View real-time logs
```

---

## Agent Management

### `yaver agent status`
View agent learning state.

```bash
yaver agent status <project-id>
```

---

### `yaver agent history`
View decision history.

```bash
yaver agent history <project-id>
yaver agent history <project-id> --limit=20
```

---

### `yaver agent teach`
Provide feedback to the agent.

```bash
yaver agent teach <project-id> <rec-id> --status=approve
```

---

## Memory & Sessions

### `yaver memory list`
List all chat sessions.

```bash
yaver memory list
```

---

### `yaver memory switch`
Switch to different chat session.

```bash
yaver memory switch <session-id>
```

---

### `yaver memory new`
Create new chat session.

```bash
yaver memory new --name="Feature Planning"
yaver memory new --name="Debug Session" --tag=debug
```

---

### `yaver memory delete`
Delete a chat session.

```bash
yaver memory delete <session-id>
```

---

## Configuration

### Environment Variables

Create `.env` in project root or `~/.yaver/.env`:

```bash
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERAL=llama3.1:8b
OLLAMA_MODEL_CODE=codellama:13b
OLLAMA_MODEL_EMBEDDING=nomic-embed-text

# Graph Database
GRAPH_DB_PROVIDER=networkx  # or 'neo4j'

# Vector Database
VECTOR_DB_PROVIDER=qdrant   # or 'chroma'
QDRANT_URL=http://localhost:6333
```

---

## Getting Help

```bash
yaver --help                    # General help
yaver <command> --help          # Command-specific help
```
