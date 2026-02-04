# DevMind CLI Command Guide

Complete reference for all DevMind commands and their usage.

## ⚡ Quick Reference (Cheat Sheet)

### Session vs Project
| Concept | Purpose | Command |
|---------|---------|---------|
| **Session** | Chat conversation history | `devmind session ...` |
| **Project** | Group of learned repositories | `devmind project ...` |

### Top Commands
```bash
# Chat with project context
devmind chat --project-id=my-app

# Create chat session
devmind session new --name="Feature X"

# Learn repo into project (Deep Analysis)
devmind analyze ./backend --type deep --project-id=my-app

# Get autonomous code recommendations
devmind agent analyze my-app
```

## Table of Contents

- [Quick Start](#quick-start)
- [Core Commands](#core-commands)
- [Learning & Analysis](#learning--analysis)
- [Autonomous Agent](#autonomous-agent)
- [Session & Project Management](#session--project-management)
- [Code Assistance](#code-assistance)
- [Memory Operations](#memory-operations)
- [System & Status](#system--status)
- [Testing & Verification](#testing--verification)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# Learn a repository (Deep Analysis)
devmind analyze /path/to/repo --type deep

# Get autonomous recommendations
devmind agent analyze myproject

# Start interactive chat
devmind chat

# Get repository status
devmind status
```

---

## Core Commands

### `devmind chat`
Interactive AI chat for querying your codebase.

**Usage:**
```bash
devmind chat [OPTIONS]
```

**Options:**
- `--session-id <ID>` - Use specific chat session for conversation history
- `--project-id <ID>` - Limit code context to specific project (learned repo)

**Features:**
- Semantic search across learned repositories
- Natural language code queries
- Context-aware responses using RAG (Retrieval Augmented Generation)
- Multi-language support (English, Turkish, etc.)
- Session-based filtering for multi-repo projects

**Example 1: Chat with all learned repositories**
```bash
$ devmind chat
🤖 DevMind AI Chat (Type 'exit' to quit)
💡 Tip: Ask anything about your code, get AI assistance

You: How does authentication work?
DevMind: Based on the codebase, authentication uses JWT tokens...

You: Find code that validates emails
DevMind: Here are the relevant code snippets...
```

**Example 2: Chat within a specific project**
```bash
# Limit chat to 'my-saas-app' project only
$ devmind chat --project-id=my-saas-app
🤖 DevMind AI Chat - Project: my-saas-app

You: How does the payment flow work?
DevMind: [Searches only in backend, frontend, and auth repos from my-saas-app]
```

**Example 3: Use both project and chat session**
```bash
# Continue a previous conversation about a specific project
$ devmind chat --project-id=my-saas-app --session-id=payment-review
🤖 DevMind AI Chat - Project: my-saas-app, Session: payment-review

You: Continue from where we left off
DevMind: [Uses project context + previous conversation history]
```

**Tips:**
- Ask about code functionality: "How does X work?"
- Search for implementations: "Find code that does Y"
- Query architecture: "What is the project structure?"
- **Use `--project-id` to focus on specific project** (useful for multi-repo setups)
- **Use `--session-id` to continue previous conversations**

---

## Learning & Analysis

### `devmind analyze`
Unified command for repository analysis, from basic overview to deep learning.

**Usage:**
```bash
devmind analyze [PATH] [OPTIONS]
```

**Arguments:**
- `PATH` - Repository path (default: current directory)

**Options:**
- `--type <TYPE>` - Analysis type:
  - `overview`: basic stats (default)
  - `structure`: language & file breakdown
  - `deep`: **Deep Learning** (AST, Neo4j, Embeddings)
- `--project-id <ID>` - Project ID for deep analysis storage (use this to group repos)
- `--incremental` - Only analyze changed files (works for deep mode)
- `--target <FUNCTION/CLASS>` - Target for impact analysis

**Examples:**

**1. Basic Overview:**
```bash
$ devmind analyze .
📊 Analyzing repository: .
   Status: 🔴 Dirty
   Commits: 50+
   Modified Files: 3
```

**2. Deep Learning (Understand Codebase):**
> **Note:** This replaces the old `devmind learn` command.
```bash
# Deep learn repo and store in database
devmind analyze . --type deep --project-id my-project
```

**Mult-Repo Setup:**
```bash
# Learn multiple repos into one project context
devmind analyze ./backend --type deep --project-id my-saas
devmind analyze ./frontend --type deep --project-id my-saas
```

**INCREMENTAL ANALYSIS:**
```bash
# Only re-analyze changed files (much faster)
devmind analyze . --type deep --incremental
```

---

### `devmind learn` (DEPRECATED)
⚠️ **Deprecated:** Please use `devmind analyze --type deep` instead.
This command still works but redirects to the new analyze command.

---

## Autonomous Agent

### `devmind agent`
Your persistent autonomous AI developer assistant. The agent observes your code, analyzes quality, makes reasoned decisions, and learns from your feedback.

**Usage:**
```bash
devmind agent [SUBCOMMAND] [OPTIONS]
```

### `devmind agent analyze`
Run autonomous analysis on a project to generate smart recommendations.

**Usage:**
```bash
devmind agent analyze <PROJECT_ID> [--format table|json|chat]
```

**Features:**
- Detects **Dead Code** (unreachable functions)
- Identifies **High Complexity** code needing refactoring
- Finds **Circular Dependencies**
- Prioritizes issues (1-10 scale) based on risk and effort
- Estimates effort hours

**Example:**
```bash
$ devmind agent analyze my-saas
🤖 AUTONOMOUS AGENT ANALYSIS

⚠️  Issues Found:
[1] Remove dead code (Priority 9)
    Effort: 5 min | Risk: LOW
    
[2] Refactor complexity (Priority 7)
    Effort: 1-2 hrs | Risk: MEDIUM
```

---

### `devmind agent status`
View the agent's learning state and preferences for a project.

**Usage:**
```bash
devmind agent status <PROJECT_ID>
```

**Output:**
- Number of approved/rejected recommendations
- Learned user preferences (contracts, styles)
- Last analysis timestamp

---

### `devmind agent history`
View decision history and code quality trends over time.

**Usage:**
```bash
devmind agent history <PROJECT_ID> [--limit N]
```

**Output:**
- Chronological list of decisions
- Quality score trends
- Tracking of improvements

---

### `devmind agent feedback`
Teach the agent by providing feedback on its recommendations. The agent uses this to improve future suggestions.

**Usage:**
```bash
devmind agent feedback <PROJECT_ID> <REC_ID> --status <STATUS> [--note "TEXT"]
```

**Options:**
- `--status`: `approve`, `reject`, or `ignore`
- `--note`: Optional explanation for the agent

**Example:**
```bash
devmind agent feedback my-saas 1 --status approve --note "Good catch, removing this now"
```

---

### `devmind simulate`
Simulate impact analysis for code changes.

**Usage:**
```bash
devmind simulate <FILE> <FUNCTION>
```

**Example:**
```bash
devmind simulate src/auth.py login

# Output shows:
# - What depends on this function
# - Potential breaking changes
# - Test coverage impact
```

---

## Session & Project Management

### Understanding Sessions vs Projects

DevMind has **two distinct session types**:

1. **Chat Sessions** (via `devmind session`)
   - Stores **conversation history** for chat interactions
   - Tagged for organization and filtering
   - Supports switching between different conversation contexts
   - Example: "debugging-session", "feature-planning", "code-review"

2. **Projects** (via `devmind project`)
   - Groups multiple **learned repositories** together
   - Created with `devmind learn --project-id=PROJECT_NAME`
   - Used to organize multi-repo systems (microservices, monorepos)
   - Stores code graph, AST analysis, and embeddings
   - Example: "my-saas-app", "ml-pipeline", "legacy-system"

### Chat Session Commands

#### `devmind session new`
Create a new chat session to organize conversations.

**Usage:**
```bash
devmind session new [--name NAME] [--tag TAG ...]
```

**Options:**
- `--name <NAME>` - Give session a friendly name
- `--tag <TAGS>` - Add tags for organization

**Example:**
```bash
devmind session new --name="Feature Discussion" --tag=feature --tag=frontend
```

---

#### `devmind session list`
List all chat sessions with their tags.

**Usage:**
```bash
devmind session list
```

---

#### `devmind session set`
Switch to a different chat session.

**Usage:**
```bash
devmind session set <SESSION_ID>
```

---

#### `devmind session delete`
Delete a chat session and its history.

**Usage:**
```bash
devmind session delete <SESSION_ID> [--force]
```

---

### Project Commands (Learning Sessions)

#### `devmind project list`
List all learned projects with their repositories.

**Usage:**
```bash
devmind project list
```

**Output:**
```
📚 Learned Projects

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Project ID     ┃ Repositories           ┃ Last Used        ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ my-saas-app    │ backend, frontend,     │ 2026-02-03 17:35 │
│                │ auth                   │                  │
│ ml-pipeline    │ data-processor,        │ 2026-02-03 14:20 │
│                │ model-server           │                  │
│ legacy-system  │ monolith               │ 2026-02-01 09:15 │
└────────────────┴────────────────────────┴──────────────────┘

💡 Use 'devmind project show <project-id>' for details
```

---

#### `devmind project show`
Show detailed information about a specific project.

**Usage:**
```bash
devmind project show <PROJECT_ID>
```

**Example:**
```bash
devmind project show my-saas-app
```

**Output:**
```
📋 Project Details: my-saas-app

Repositories (3):
  • backend
  • frontend
  • auth

Statistics:
  • File: 234
  • Function: 1,245
  • Class: 156

Per-Repository Breakdown:
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┓
┃ Repository   ┃ Functions ┃ Classes ┃ Files ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━┩
│ backend      │       450 │      65 │    78 │
│ frontend     │       680 │      75 │   125 │
│ auth         │       115 │      16 │    31 │
└──────────────┴───────────┴─────────┴───────┘
```

---

#### `devmind project delete`
Delete a project and all its learned data from Neo4j.

**Usage:**
```bash
devmind project delete <PROJECT_ID> [--force]
```

**Options:**
- `--force, -f` - Skip confirmation prompt

**Example:**
```bash
# With confirmation
devmind project delete old-project

# Skip confirmation
devmind project delete old-project --force
```

**Output:**
```
⚠️  Delete project 'old-project' and all its learned data? [y/N]: y

✅ Deleted project 'old-project'
   Removed 1,234 nodes from Neo4j

💡 Note: Qdrant embeddings for this project remain.
   Use Qdrant console to delete if needed.
```

---

## Code Assistance

### `devmind fix`
Automatically fix code issues.

**Usage:**
```bash
devmind fix [FILE]
```

**Example:**
```bash
devmind fix src/buggy_code.py
```

---

### `devmind explain`
Get detailed explanation of code.

**Usage:**
```bash
devmind explain <FILE> [OPTIONS]
```

**Options:**
- `--function <NAME>` - Explain specific function
- `--class <NAME>` - Explain specific class

**Example:**
```bash
devmind explain src/auth.py --function=verify_token
```

---

### `devmind commit`
Generate commit messages from staged changes.

**Usage:**
```bash
devmind commit [OPTIONS]
```

**Options:**
- `--context, -c <TEXT>` - Additional context for commit message

**Example:**
```bash
# Stage your changes
git add .

# Generate commit message
devmind commit

# With context
devmind commit --context "Fixed authentication bug from issue #123"
```

**Output:**
```
✅ Generated Commit Message:

fix: Resolve JWT token validation issue

- Updated verify_token() to handle expired tokens correctly
- Added error logging for invalid signatures
- Fixes #123

Use this message? [Y/n]:
```

---

### `devmind suggest`
Get code improvement suggestions.

**Usage:**
```bash
devmind suggest <FILE>
```

**Example:**
```bash
devmind suggest src/utils/helpers.py
```

**Output:**
```
💡 Suggestions for helpers.py:

1. Performance: Use list comprehension instead of loop in process_data()
2. Security: Sanitize user input in validate_email()
3. Readability: Extract complex condition into named variable
4. Best Practice: Add type hints to function signatures
```

---

### `devmind edit`
AI-assisted code editing.

**Usage:**
```bash
devmind edit <FILE> --instruction "<INSTRUCTION>"
```

**Example:**
```bash
devmind edit src/api.py --instruction "Add rate limiting to all endpoints"
```

---

### `devmind solve`
Solve coding problems and challenges.

**Usage:**
```bash
devmind solve "<PROBLEM_DESCRIPTION>"
```

**Example:**
```bash
devmind solve "Write a function to validate credit card numbers using Luhn algorithm"
```

---

## Memory Operations

DevMind maintains a unified memory system for context and learning.

### `devmind remember`
Store information in DevMind's memory.

**Usage:**
```bash
devmind remember "<INFORMATION>"
```

**Example:**
```bash
devmind remember "The auth service uses Redis for session storage"
```

---

### `devmind recall`
Retrieve information from memory.

**Usage:**
```bash
devmind recall "<QUERY>"
```

**Example:**
```bash
devmind recall "How is session storage implemented?"
```

---

### `devmind reset-memory`
Clear DevMind's memory (use with caution).

**Usage:**
```bash
devmind reset-memory [--confirm]
```

**Example:**
```bash
devmind reset-memory --confirm
```

---

## System & Status

### `devmind status`
Show system status and configuration.

**Usage:**
```bash
devmind status
```

**Output:**
```
============================================================
DevMind System Status
============================================================

🔧 Configuration:
   Neo4j: bolt://localhost:7687 ✓
   Qdrant: localhost:6333 ✓
   Ollama: http://localhost:11434 ✓

📊 Database Status:
   Neo4j Nodes: 1,245
   Qdrant Vectors: 3,456
   Active Sessions: 3

🧠 Models:
   General: llama3.1:8b
   Embeddings: nomic-embed-text:latest

💾 Memory:
   Cache Size: 125 MB
   Last Cleanup: 2 hours ago
```

---

### `devmind query`
Query the codebase database directly.

**Usage:**
```bash
devmind query <CYPHER_QUERY>
```

**Example:**
```bash
devmind query "MATCH (f:Function) WHERE f.complexity > 10 RETURN f.name, f.complexity"
```

---

### `devmind inspect`
Inspect code structure and metrics.

**Usage:**
```bash
devmind inspect <FILE> [OPTIONS]
```

**Options:**
- `--metrics` - Show code metrics
- `--dependencies` - Show dependencies
- `--call-graph` - Show call graph

**Example:**
```bash
devmind inspect src/core/engine.py --metrics --call-graph
```

---

### `devmind insights`
Get insights about the codebase.

**Usage:**
```bash
devmind insights [OPTIONS]
```

**Options:**
- `--complexity` - Complexity analysis
- `--quality` - Code quality report
- `--architecture` - Architecture overview

**Example:**
```bash
devmind insights --complexity
```

**Output:**
```
📈 Codebase Insights

Complexity Analysis:
  • High Complexity Functions: 12
  • Average Complexity: 4.5
  • Most Complex: calculate_metrics() (complexity: 23)

Code Quality:
  • Code Coverage: 78%
  • Documentation: 65%
  • Type Hints: 82%

Architecture:
  • Layered Architecture Detected
  • 3 Circular Dependencies Found
  • Microservices Pattern
```

---

## Advanced Usage

### Multi-Repository Projects

Learn multiple related repositories under a single project:

```bash
# Microservices architecture
devmind learn ~/services/api-gateway --project-id=microservices
devmind learn ~/services/user-service --project-id=microservices
devmind learn ~/services/payment-service --project-id=microservices
devmind learn ~/services/notification-service --project-id=microservices

# Now query across all services
devmind chat --project-id=microservices
> "How does the payment flow work across services?"
```

**Why use project IDs?**
- **Focus queries**: Only search relevant repositories
- **Organize projects**: Keep different projects separate
- **Performance**: Faster searches with filtered context
- **Multi-tenancy**: Work on multiple projects simultaneously

**Example Workflow:**
```bash
# Learn your microservices
devmind learn ~/work/backend --project-id=work-project
devmind learn ~/work/frontend --project-id=work-project

# Learn your side project
devmind learn ~/hobby/game-engine --project-id=hobby-project

# Query work project only
devmind chat --project-id=work-project
> "How is user authentication implemented?"

# Query hobby project only  
devmind chat --project-id=hobby-project
> "How does the physics engine work?"

# List all sessions
devmind session list
```

### Incremental Learning

For large codebases, use incremental mode after initial learning:

```bash
# Initial learning (full scan)
devmind learn ~/large-project --project-id=main

# After code changes (only changed files)
devmind learn ~/large-project --project-id=main --incremental
```

### Session-Based Queries

Query specific sessions in chat mode:

```bash
# Set active session
devmind session set my-saas-app

# Chat will use this session's context
devmind chat
```

### Combining Commands

```bash
# Analyze, fix, and commit in one workflow
devmind analyze src/
devmind fix src/issues.py
git add src/issues.py
devmind commit --context "Fixed issues found in analysis"
```

---

## Environment Variables

Configure DevMind using environment variables:

```bash
# Neo4j Configuration
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"

# Qdrant Configuration
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"

# Ollama Configuration
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.1:8b"
```

---

## Configuration Files

DevMind looks for configuration in:
- `.env` in current directory
- `~/.devmind/config.yaml`
- Environment variables

**Example `.env`:**
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
QDRANT_HOST=localhost
QDRANT_PORT=6333
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Tips & Best Practices

### Learning Strategy

1. **Start with session IDs** for related projects
2. **Use descriptive session names** (e.g., `ecommerce-platform` not `project1`)
3. **Learn incrementally** after initial full scan
4. **Organize by domain** (frontend, backend, services)

### Query Optimization

1. **Be specific** in questions: "How does user authentication work?" vs "Tell me about auth"
2. **Use session context** for multi-repo queries
3. **Reference file paths** when available: "How does src/auth.py handle tokens?"

### Memory Management

1. **Regular cleanup**: Delete old sessions with `session delete`
2. **Check status**: Monitor database size with `devmind status`
3. **Incremental updates**: Don't re-learn entire repos unnecessarily

### Performance

1. **Limit session scope**: Don't include unrelated repos in same session
2. **Use filters**: Query specific repos when possible
3. **Incremental mode**: Faster than full re-analysis

---

## Testing & Verification

### Step-by-Step Test Plan

#### Test 1: Learn and Create a Project
```bash
# Learn a repository with a project ID
devmind learn /path/to/repo --project-id=test-project

# Or use current directory
cd /path/to/repo
devmind learn . --project-id=test-project
```

**Expected Output:**
```
🧠 Deep Learning Repository: repo-name
Project ID: test-project
✅ Connected to Neo4j
📊 Analyzing codebase...
✅ Analysis complete
✅ Repository Learning Complete!
```

#### Test 2: List Projects
```bash
devmind project list
```

**Expected Output:**
```
📚 Learned Projects

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Project ID     ┃ Repositories         ┃ Last Used       ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ test-project   │ repo-name            │ 2026-02-03 ...  │
└────────────────┴──────────────────────┴─────────────────┘
```

#### Test 3: Show Project Details
```bash
devmind project show test-project
```

**Expected Output:**
```
📋 Project Details: test-project

Repositories (1):
  • repo-name

Statistics:
  • File: N
  • Function: N
  • Class: N

Per-Repository Breakdown:
┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┓
┃ Repository  ┃ Functions ┃ Class ┃ Files ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━╇━━━━━━━┩
│ repo-name   │     ...   │  ...  │  ...  │
└─────────────┴───────────┴───────┴───────┘
```

#### Test 4: Create Chat Session
```bash
devmind session new --name="Test Session" --tag=testing
```

**Expected Output:**
```
✅ Created chat session: SESSION_ID
   Name: Test Session
   Tags: testing
   Active: ✓
```

#### Test 5: List Chat Sessions
```bash
devmind session list
```

**Expected Output:**
```
💬 Chat Sessions

┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Session ID    ┃ Name           ┃ Tags     ┃ Created   ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ sess_abc...   │ Test Session   │ testing  │ 2026-02-03┃
└───────────────┴────────────────┴──────────┴───────────┘
```

#### Test 6: Chat with Project Context Only
```bash
devmind chat --project-id=test-project
```

**Expected Output:**
```
🤖 DevMind AI Chat - Project: test-project
💡 Tip: Ask anything about your code, get AI assistance

You: How many functions are in this project?
DevMind: [Responds based on test-project context only]

You: exit
👋 Goodbye!
```

#### Test 7: Chat with Project and Session
```bash
# Get SESSION_ID from devmind session list
devmind chat --project-id=test-project --session-id=SESS_ID
```

**Expected Output:**
```
🤖 DevMind AI Chat - Project: test-project, Session: SESS_ID
```

#### Test 8: Delete Project
```bash
devmind project delete test-project
```

**Expected Confirmation:**
```
⚠️  Delete project 'test-project' and all its learned data? [y/N]: y

✅ Deleted project 'test-project'
   Removed N nodes from Neo4j
```

#### Test 9: Verify Deletion
```bash
devmind project list
```

**Expected Output:**
```
📚 Learned Projects

No projects found. Create one with:
  devmind learn <path> --project-id=<name>
```

### Verification Checklist

- [ ] Project creation works with `--project-id` parameter
- [ ] `devmind project list` shows all projects
- [ ] `devmind project show` displays correct statistics
- [ ] Chat with `--project-id` limits context to that project only
- [ ] Chat with both `--project-id` and `--session-id` works
- [ ] `devmind session list` shows all chat sessions (separate from projects)
- [ ] Project deletion removes all data from Neo4j
- [ ] Help text is accurate: `devmind chat --help`, `devmind project --help`, `devmind session --help`

### Troubleshooting Tests

**If projects don't appear in list:**
```bash
# Check Neo4j connection
devmind status

# Verify database is running
curl http://localhost:7687

# Check environment variables
env | grep NEO4J
```

**If chat doesn't filter by project:**
```bash
# Verify project exists first
devmind project show test-project

# Check RAG service is initialized
devmind chat --project-id=test-project
# Look for "Initializing Semantic Engine..." messages
```

---

## Troubleshooting

### Common Issues

**"Neo4j connection failed"**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Start Neo4j
docker start neo4j
```

**"Qdrant client not connected"**
```bash
# Check Qdrant status
curl http://localhost:6333/health

# Start Qdrant
docker start qdrant
```

**"No results in chat"**
```bash
# Re-learn the repository
devmind learn . --project-id=my-project

# Check project has data
devmind project show my-project
```

**"Session not found"**
```bash
# List all sessions
devmind session list

# Use correct session ID
devmind session show <correct-id>
```

---

## Getting Help

```bash
# General help
devmind --help

# Command-specific help
devmind chat --help
devmind learn --help
devmind session --help
```

---

## Version Information

Check DevMind version:
```bash
devmind --version
```

---

**Last Updated:** February 3, 2026  
**DevMind Version:** 1.0.0

For more information, visit the [DevMind Documentation](https://github.com/tevfik/devmind)
