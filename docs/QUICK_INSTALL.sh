#!/bin/bash
# Yaver - One Script Installation & Setup

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Yaver AI - Full Installation                   ║"
echo "║     All integrations (Qdrant, Neo4j, Ollama, etc)        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION detected"

if [[ ! "$PYTHON_VERSION" == "3."* ]] || [[ "$PYTHON_VERSION" < "3.11" ]]; then
    echo "✗ Python 3.11+ required"
    exit 1
fi

# Check Git
if ! command -v git &> /dev/null; then
    echo "✗ Git not found"
    exit 1
fi
echo "✓ Git found"

# Optional: Check/setup virtual environment
if [[ ! -d "venv" ]]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate

echo ""
echo "Installing Yaver with all integrations..."
echo "This includes: LangChain, Qdrant, Neo4j, Ollama, LanGraph, FastAPI, etc."
echo ""

# Install in development mode
pip install --upgrade pip setuptools wheel
pip install -e .

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                ✅ Installation Complete!                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Yaver Chat:"
echo "   yaver chat"
echo ""
echo "2. Analyze a repository:"
echo "   yaver analyze ."
echo ""
echo "3. Optional: Start Ollama for local LLM"
echo "   ollama serve"
echo ""
echo "4. Optional: Start Qdrant (Docker)"
echo "   docker run -p 6333:6333 qdrant/qdrant"
echo ""
echo "5. Optional: Start Neo4j (Docker)"
echo "   docker run -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j"
echo ""
echo "For more information, see INSTALLATION.md"
echo ""
