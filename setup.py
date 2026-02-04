#!/usr/bin/env python3
"""
Yaver AI - Fully Functional Development Assistant

Single install: pip install -e .
Then use: yaver chat

All integrations included:
- Qdrant vector database for semantic search
- Neo4j for code graph analysis
- Ollama for local LLM (multiple specialized models)
- LangChain for orchestration
- ChromaDB for memory
- FastAPI for API server
- Rich for beautiful terminal UI

Configuration via ~/.yaver/.env:
  OLLAMA_BASE_URL=https://ollama.bezg.in
  OLLAMA_MODEL_GENERAL=nemotron-3-nano:30b (Chat, general queries)
  OLLAMA_MODEL_CODE=deepseek-coder-v2:16b (Code analysis)
  OLLAMA_MODEL_EXTRACTION=qwen2.5-coder:7b (Fact extraction - faster)
  OLLAMA_MODEL_EMBEDDING=nomic-embed-text (Vector embeddings)
  OLLAMA_USERNAME=admin (Optional: For remote Ollama)
  OLLAMA_PASSWORD=password (Optional: For remote Ollama)
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding="utf-8")

# Read requirements from requirements file
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []

if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f.readlines()
            if line.strip() and not line.startswith("#")
        ]
else:
    # Complete requirements with ALL integrations
    requirements = [
        # Core Framework
        "langchain>=0.3.0",
        "langchain-community>=0.3.0",
        "langchain-core>=0.3.0",
        "langchain-ollama>=0.2.0",
        "langgraph>=0.2.0",
        # LLM & Embeddings
        "ollama>=0.4.0",
        # Data Validation & Parsing
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        # Git Operations
        "gitpython>=3.1.40",
        "pygit2>=1.13.0",
        # Code Analysis & Quality
        "radon>=6.0.1",
        "lizard>=1.17.10",
        "bandit>=1.7.5",
        "pylint>=3.0.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "mypy>=1.7.0",
        # File Processing
        "tree-sitter>=0.20.0",
        "tree-sitter-python>=0.20.0",
        "tree-sitter-javascript>=0.20.0",
        # Vector Database & Memory
        "chromadb>=0.4.0",
        "qdrant-client>=1.9.1",
        "sentence-transformers>=2.2.0",
        "mem0ai>=0.1.0",
        # Web & API
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-multipart>=0.0.6",
        "gradio>=4.0.0",
        "requests>=2.31.0",
        # Graph Database (Neo4j)
        "neo4j>=5.0.0",
        # Terminal UI
        "rich>=13.0.0",
        "typer>=0.9.0",
        # Async
        "aiohttp>=3.9.0",
    ]

setup(
    name="yaver",
    version="1.1.0",
    author="tevfik.kadioglu",
    author_email="tevfik.kadioglu@gmail.com",
    description="Fully functional AI-powered development assistant with Qdrant, Neo4j, Ollama, LangChain",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tevfik/yaver",
    project_urls={
        "Bug Tracker": "https://github.com/tevfik/yaver/issues",
        "Documentation": "https://github.com/tevfik/yaver",
        "Source Code": "https://github.com/tevfik/yaver",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "yaver=cli.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "ai",
        "development",
        "git",
        "code-analysis",
        "llm",
        "langchain",
        "qdrant",
        "neo4j",
        "ollama",
        "assistant",
    ],
    zip_safe=False,
)
