# Deep Code Analysis Guide

Yaver Deep Analysis is a powerful engine that indexes your codebase into a Graph Database (Neo4j) and a Vector Database (Qdrant) to enable semantic understanding, impact analysis, and visual exploration.

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have the required databases running. If you used `yaver setup`, this should be handled (Docker).

```bash
docker ps
# Should show: yaver-neo4j, yaver-qdrant
```

### 2. Learn a Repository
To enable deep features, you must first "teach" Yaver your code.

```bash
# Deep Learning (AST + Graph + Embeddings)
yaver analyze . --type deep --project-id my-project
```

*Note: The first run takes time (generating embeddings). Subsequent runs use caching.*

## 🔍 Features

### 1. Visualization
Generate diagrams to understand the code structure.

**Class Diagram:**
```bash
yaver visualize . --type class --output classes.md
```

**Call Graph:**
Trace who calls a specific function.
```bash
yaver visualize . --type call-graph -f "my_function_name" -o flow.md
```
*Output is MermaidJS format, viewable in GitHub or compatible editors.*

### 2. Impact Simulation
Predict what breaks if you change a function.

```bash
yaver simulate "Change signature of process_data"
```
*Generates a risk report (findings.md) detailing affected files and call chains.*

### 3. Intelligent Chat (RAG)
Ask questions about your codebase in natural language.

```bash
yaver chat
```

**Example Queries:**
- "How does the authentication middleware work?"
- "Show me the class hierarchy for AgentBase"
- "Where is the database connection initialized?"
- "What happens if I remove the cache_manager.py file?"

### 4. Architecture Discovery
The system automatically tags files into layers:
- **API**: Endpoints, CLI handlers
- **CORE**: Business logic, Services
- **DATA**: Database models, Repositories

You can query these in Neo4j (Cypher) or ask the Chat Agent.

## 🛠️ Troubleshooting

**Reset Databases:**
If data gets corrupted or you want a fresh start:
```bash
# Reset Graph
python src/utils/reset_graph_db.py

# Reset Vectors
# Delete the ./chroma_db or ./qdrant_data folder
```

**Logs:**
Check `~/.yaver/logs/yaver.log` for analysis errors.
