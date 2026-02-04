# Installation Guide

**One install. Full power. Ready to use.**

```bash
pip install -e .
yaver chat
```

That's it. Everything works out of the box.

## What's Included

✅ **AI Agent Framework** - LangChain + LanGraph orchestration
✅ **Local LLM** - Ollama integration (bring your own model)
✅ **Semantic Search** - Qdrant vector database  
✅ **Code Graph Analysis** - Neo4j for dependency mapping
✅ **Memory System** - Chromadb + Mem0 for context retention
✅ **Git Analysis** - GitPython integration
✅ **Code Quality** - Radon, Bandit, Pylint, MyPy
✅ **Terminal UI** - Rich formatting + Gradio web interface
✅ **API Server** - FastAPI for external integration

## Available Commands

```bash
# Start interactive chat
yaver chat

# Analyze a repository
yaver analyze <repo_path>

# Generate git commit message
yaver commit

# Solve tasks end-to-end
yaver solve "Fix bug in auth module"

# Edit files with AI
yaver edit "Add type hints" --file src/app.py

# Explain shell commands
yaver explain "grep -r pattern ."

# Generate shell commands
yaver suggest "find all python files"

# Query repository
yaver query status
yaver query graph <repo>
```

## Installation Options

### Option 1: From Source (Full Control)
```bash
cd yaver
pip install -e .
```

### Option 2: From GitHub (Latest)
```bash
pip install git+https://github.com/tevfik/yaver.git
```

### Option 3: PyPI (When available)
```bash
pip install yaver
```

## Requirements

- **Python 3.10+**
- **Git** (for repository analysis)
- **Ollama** (optional, for local LLM)
  - Download: https://ollama.ai
  - Pull model: `ollama pull nemotron-3-nano:30b`

## First Run

```bash
yaver chat
```

This starts an interactive session where you can:
- Analyze your current repository
- Ask questions about your codebase
- Get AI-powered suggestions
- Solve tasks step-by-step

## Configuration

Create `.env` in your project root:

```bash
# LLM Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nemotron-3-nano:30b

# Qdrant Settings
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-key

# Neo4j Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# API Settings
YAVER_API_PORT=8000
```

## Quick Examples

### Example 1: Analyze Your Repository
```bash
yaver analyze .
```

Output shows:
- Repository structure
- Detected frameworks
- Code metrics
- Key files

### Example 2: Get AI Help with Code
```bash
yaver chat
> Analyze src/auth.py and suggest improvements
```

Yaver will:
1. Read the file
2. Analyze using AI
3. Suggest improvements with code snippets

### Example 3: Generate Commit Message
```bash
git add .
yaver commit
```

Automatically generates meaningful commit message from staged changes.

### Example 4: End-to-End Task Solving
```bash
yaver solve "Add authentication to the API" --file src/api.py
```

Yaver will:
1. Create a feature branch
2. Analyze the code
3. Implement the feature
4. Run tests
5. Create a PR

## Troubleshooting

### "ollama not found"
```bash
# Install Ollama
# Mac: brew install ollama
# Linux: Follow https://ollama.ai
# Then start: ollama serve
```

### "Qdrant connection refused"
```bash
# Start Qdrant locally (Docker)
docker run -p 6333:6333 qdrant/qdrant

# Or connect to remote Qdrant
export QDRANT_URL=http://your-server:6333
```

### "Neo4j connection error"
```bash
# Start Neo4j locally (Docker)
docker run \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Update .env with credentials
```

### Memory issues on large repos
Yaver handles large repositories efficiently by:
- Chunking code into semantic units
- Using vector search instead of full search
- Building incremental code graphs

For very large repos (>100k files), use:
```bash
yaver analyze . --sampling=0.1  # Analyze 10% of files
```

## What Each Component Does

### 🤖 Agent Framework (LangChain)
- Multi-step reasoning
- Tool orchestration
- Memory management
- Agent workflows

### 🧠 Memory System (Qdrant + Chromadb)
- Semantic search on codebase
- Episode memory (previous interactions)
- Context retention across sessions
- Fast similarity search

### 📊 Code Analysis (Neo4j)
- Build code dependency graph
- Find impact of changes
- Trace function calls
- Visualize architecture

### 🔍 Git Analysis (GitPython)
- Repository structure analysis
- Commit history analysis
- Branch management
- File change tracking

### 💻 Code Quality (Radon, Bandit, Pylint)
- Complexity metrics
- Security analysis
- Code quality scores
- Type checking

### 🎨 Terminal UI (Rich, Gradio)
- Beautiful formatted output
- Interactive web interface
- Progress indicators
- Syntax highlighting

## Architecture

```
Yaver
├── Agent Framework (LangChain)
│   ├── Query Analyzer
│   ├── Task Planner
│   └── Execution Engine
│
├── Memory System
│   ├── Code Memory (Qdrant) - Semantic search
│   ├── Episodic Memory (Chromadb) - Interaction history
│   └── Knowledge Base (Neo4j) - Code relationships
│
├── Tools
│   ├── Git Operations (GitPython)
│   ├── Code Analysis (Radon, Bandit, Pylint)
│   ├── File Processing (Tree-sitter)
│   └── Shell Execution (subprocess)
│
├── UI Layer
│   ├── CLI (Rich, Typer)
│   ├── Web (Gradio)
│   └── API (FastAPI)
│
└── LLM Integration
    └── Ollama (local) or API (remote)
```

## Performance

Typical latencies on 1000-file repository:
- Repo analysis: ~2 seconds
- Semantic search: ~200ms (after indexing)
- Code quality analysis: ~1 second
- LLM analysis: ~5-30 seconds (depends on model)

Memory usage:
- Startup: ~150 MB
- With Qdrant indexed: +100-500 MB
- With Neo4j graph: +200-800 MB
- Full loaded: 500 MB - 1.5 GB

## Development

### Running Tests
```bash
pytest tests/
```

### Building Documentation
```bash
sphinx-build -b html docs/ docs/_build/
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## License

MIT License - Feel free to use and modify

## Support

- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
- Documentation: Read the wiki

---

**Yaver: Your AI development assistant - one install, everything works.**
