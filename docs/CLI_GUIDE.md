# CLI Command Reference

Complete reference for all Yaver commands (v1.2.0).

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

## Code Analysis

### `yaver code analyze`
Analyze repository structure and code.

```bash
yaver code analyze .                    # Quick overview
yaver code analyze . --type deep        # Full analysis (AST + Graph + Embeddings)
yaver code analyze . --type deep --project-id=myapp  # Store in project
yaver code analyze . --incremental      # Only analyze changed files
```

**Analysis Types:**
- `overview` - Basic stats (default)
- `deep` - Full analysis with AST, Graph, and Embeddings

---

### `yaver code query`
Semantic search across codebase.

```bash
yaver code query "authentication logic"
yaver code query "database connection" --limit 10
```

---

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
