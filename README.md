# Yaver AI

**AI-powered development assistant with autonomous capabilities**

Yaver is a CLI tool that combines deep code analysis, semantic search, and autonomous task execution to help you understand and improve your codebase.

## ✨ Features

- 💬 **Interactive Code Chat** - Ask questions about your codebase in natural language
- 🔍 **Deep Code Analysis** - AST parsing + Graph database + Semantic embeddings
- 🧠 **Multi-Backend Memory** - Qdrant (primary) or ChromaDB for vector storage
- 🕸️ **Graph-Based Code Intelligence** - NetworkX (default) or Neo4j
- 🤖 **Agent Learning** - Feedback loop for autonomous behaviors

## 🚀 Quick Start

```bash
# 1. Install
pip install -e .

# 2. Setup (interactive wizard)
yaver system setup

# 3. Use
yaver chat                          # Interactive chat
yaver code analyze .                # Deep analysis
```

## 📋 Commands

### Core
- `yaver chat` - Interactive AI chat with codebase context

### Code Analysis
- `yaver code analyze [--type deep]` - Analyze repository (AST + Graph + Embeddings)
- `yaver code query <question>` - Semantic search across codebase

### System Management
- `yaver system status` - Check all services
- `yaver system setup` - Run configuration wizard
- `yaver system docker` - Manage Docker services

### Agent & Memory
- `yaver agent status` - View agent learning state
- `yaver agent history` - Decision history
- `yaver memory [list|switch|new|delete]` - Session management

## 📚 Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Get running in 5 minutes
- [Installation Guide](docs/INSTALLATION.md) - Detailed setup instructions
- [CLI Reference](docs/CLI_GUIDE.md) - Complete command reference (v1.2.0)
- [Architecture](docs/ARCHITECTURE.md) - System design and components

## 🏗️ Architecture

```
Yaver AI
├── CLI (Typer + Rich)
├── RAG Service (NetworkX/Neo4j + Qdrant/ChromaDB)
├── Memory Manager (Mem0)
└── Tool Registry
```

**Supported Backends:**
- **LLM**: Ollama (local)
- **Vector DB**: Qdrant (primary), ChromaDB (fallback)
- **Graph DB**: NetworkX (default, file-based), Neo4j (optional)

## 🧪 Testing

```bash
pytest                    # Run all tests
```

**Status**: ✅ All tests passing

## 🔧 Requirements

- Python 3.10+
- Git
- Ollama (for LLM backend)

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/tevfik/yaver.git
cd yaver

# Install with virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## ⚙️ Configuration

Run the interactive setup wizard:

```bash
yaver system setup
```

This creates `~/.yaver/config.json`. Alternatively, use `.env` file.

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

**Version**: 1.2.0 | **Status**: Production Ready ✅
