# Yaver AI - High-Level Feature Overview

Yaver AI is an autonomous, polyglot software development assistant that integrates deeply with your local environment, Git history, and remote forges. It moves beyond simple "chat-with-code" by maintaining persistent memory, understanding project structure via knowledge graphs, and proactively managing development tasks.

## 🧠 Core Intelligence
*   **Local-First AI**: Built on **Ollama**, ensuring code privacy and offline capability.
*   **Hybrid RAG Architecture**:
    *   **Vector Memory**: Uses **Qdrant/ChromaDB** for semantic search (e.g., "Find logic related to auth").
    *   **Knowledge Graph**: Uses **Neo4j/NetworkX** to map structural dependencies (Call Graphs, Import hierarchies).
*   **Persistent Memory**: Remembers past user interactions, project decisions, and architectural analyses across sessions.

## 🤖 Autonomous Agents ecosystem
*   **Task Manager Agent**: Orchestrates complex workflows, decomposes high-level goals into subtasks, and assigns them to specialized agents.
*   **Social Agent (The "Bot" Mode)**:
    *   **Auto-Review**: Monitors Pull Requests on GitHub/Gitea.
    *   **Interaction**: Responds to mentions (`@yaver`) and comments.
    *   **DORA Metrics**: Evaluates PRs for DevOps health indicators.
*   **Reviewer Agent**:
    *   **Iterative Deep Review**: Analyzes code file-by-file with specific context.
    *   **Impact Analysis**: Identifies "ripple effects" of changes using the dependency graph.
    *   **Hard Verification**: Runs real compilers/linters (GCC, Clang, Python AST) to verify syntax before reviewing.
*   **Coder Agent**: Autonomous coding capability that can read files, apply edits, and verify syntax.
*   **Planner Agent**: Generates architectural plans and implementation steps before coding begins.

## 🛠️ Deep Code Analysis
*   **Language Agnostic Parsing**: Uses **Tree-sitter** for robust parsing of C, C++, Python, Go, JS/TS, and more.
*   **Static Analysis Integration**: Built-in support for tools like `Radon` (complexity), `Bandit` (security), and `Lizard` (metrics).
*   **Dependency Mapping**: Automatically extracts and indexes import chains and function calls to build a project map.

## 🔌 Interactions & Integrations
*   **Multi-Forge Support**: Seamlessly works with **GitHub**, **Gitea**, and **GitLab**.
*   **Smart Git Operations**:
    *   Handles remote branches, PR refs (`refs/pull/...`), and detached HEAD states.
    *   Automatic context switching between repositories.
*   **Modern CLI**:
    *   Interactive chat mode with rich terminal UI.
    *   Command-line tools for verifying system health and agent capabilities.
    *   Daemon mode for background monitoring.

## 🏗️ Architecture & Deployment
*   **Docker Ready**: Sandbox environments for safe code execution.
*   **Modular Tooling**: Extensible tool system allowing agents to acquire new capabilities (e.g., File System access, Terminal execution).
*   **FastAPI Backend**: Optional server mode for integration with other tools or IDE plugins.
