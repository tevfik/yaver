# DevMind - Quick Start Guide

## TL;DR - Start in 30 Seconds

```bash
# 1. Clone
git clone https://github.com/tevfik/devmind.git
cd devmind

# 2. Install (with all integrations: Qdrant, Neo4j, Ollama, LangChain, etc.)
bash docs/QUICK_INSTALL.sh

# 3. Use
devmind chat
```

Done. Everything works.

---

## What Is This?

DevMind is a fully functional AI development assistant:
- 🤖 LLM integration (Ollama, LangChain)
- 🧠 Vector database (Qdrant)
- 📊 Code graph analysis (Neo4j)
- 🔍 Git analysis
- 💻 Code quality control
- 🎨 Beautiful terminal UI

**Single install**: `pip install -e .`
**Everything included**: Qdrant, Neo4j, Ollama, etc.
**Run immediately**: `devmind chat`

---

## Installation

### Option 1: Automatic Script
```bash
bash docs/QUICK_INSTALL.sh
```

Automatically:
- Creates virtual environment
- Installs all dependencies
- Ready to use

### Option 2: Manual
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install
pip install -e .

# Run
devmind chat
```

---

## Commands

```bash
# Deep Learn Repository (Recommended first step)
devmind analyze . --type deep --project-id my-project

# Autonomous Agent (Get recommendations)
devmind agent analyze my-project

# Interactive chat
devmind chat

# Lite Analysis (Overview)
devmind analyze .

# Generate commit message
devmind commit

# Solve task (automatic branch, edit, PR)
devmind solve "Add authentication"

# Edit file
devmind edit "Add type hints" --file src/app.py

# Explain shell commands
devmind explain "grep -r pattern ."

# Suggest shell command
devmind suggest "Find all python files"
```

---

## First Use

```bash
devmind chat
```

After running this command:
- Repository is automatically analyzed
- Ask questions
- AI assists

Example questions:
```
> Analyze src/auth.py
> What functions call login()?
> Suggest improvements for error handling
> Add type hints to this file
```

---

## Optional: Start Services

DevMind works, but for better results:

### 1. Ollama (Local LLM)
```bash
# Download and install from https://ollama.ai
ollama serve

# In another terminal:
ollama pull llama2
```

### 2. Qdrant (Vector Search)
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Neo4j (Code Graph)
```bash
docker run \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

## .env File (Optional)

Create `.env` in the project folder:

```bash
# Ollama settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Qdrant settings
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-key

# Neo4j settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

---

## Troubleshooting

### "devmind: command not found"
```bash
# Is virtual environment active?
source venv/bin/activate

# If not, reinstall:
pip install -e .
```

### "ImportError: No module named 'qdrant_client'"
Normal. Will be installed later. DevMind continues working.

### "Ollama not found"
```bash
# Download from https://ollama.ai
# Or: brew install ollama (Mac)
```

### Qdrant connection error
```bash
# Is Docker running?
docker ps | grep qdrant

# If not, start it:
docker run -p 6333:6333 qdrant/qdrant
```

---

## Performance

Typical repository analysis:
- 1000 files: ~2 seconds
- Semantic search: ~200ms
- LLM analysis: 5-30 seconds (depends on model)

Memory usage:
- Startup: ~150 MB
- With Qdrant: +100-500 MB
- With Neo4j: +200-800 MB
- Fully loaded: 500 MB - 1.5 GB

---

## Architecture

```
DevMind
├── AI Agent (LangChain)
│   ├── Query Analyzer
│   ├── Task Planner
│   └── Executor
├── Memory
│   ├── Vector DB (Qdrant) - Semantic search
│   ├── Episodic (Chromadb) - History
│   └── Knowledge (Neo4j) - Code relationships
├── Tools
│   ├── Git
│   ├── Code Analysis
│   └── Shell
└── UI
    ├── Terminal (Rich)
    └── Web (Gradio)
```

---

## What's Included

All integrations included:

✅ LangChain - Orchestration
✅ LanGraph - Multi-step flows
✅ Ollama - Local LLM
✅ Qdrant - Vector database
✅ Neo4j - Graph database
✅ ChromaDB - Memory
✅ FastAPI - API server
✅ GitPython - Git operations
✅ Radon - Code metrics
✅ Bandit - Security analysis
✅ Pylint - Code quality
✅ Rich - Terminal UI
✅ Gradio - Web UI

Nothing missing.

---

## Development

### Run tests
```bash
pytest tests/
```

### Contribute
```bash
# Fork
# Create branch
# Make changes
# Write tests
# Submit PR
```

---

## License

MIT - Use, modify, share

---

## Support

- Issues: GitHub Issues
- Questions: GitHub Discussions
- Documentation: README.md and INSTALLATION.md

---

## Summary

| Task | Command | Time |
|------|---------|------|
| Install | `bash QUICK_INSTALL.sh` | 2-5 minutes |
| Start | `devmind chat` | 1 second |
| Analyze | `devmind analyze .` | 2-5 seconds |
| Use LLM | Start Ollama | 1 minute |

**DevMind: Single install, full power, works immediately.**
