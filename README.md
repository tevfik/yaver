# Yaver AI

AI-powered CLI development assistant built on Ollama. Provides intelligent code analysis, command suggestions, error fixes, and git repository analysis through a command-line interface.

## Documentation

- [Quick Start](docs/QUICK_START.md) - Get up and running in minutes
- [Installation Guide](docs/INSTALLATION.md) - Detailed installation instructions
- [CLI Reference](docs/CLI_REFERENCE.md) - Complete command reference
- [Architecture](docs/MEMORY_ARCH.md) - System architecture and memory design
- [Docker Integration](docs/DOCKER_INTEGRATION.md) - Using Yaver with Docker
- [Contributing](docs/CONTRIBUTING.md) - Guide for contributors
- [Deep Analysis Guide](docs/DEEP_ANALYSIS_GUIDE.md) - Understanding the analysis engine

## Features

- **Chat**: Interactive conversation about code
- **Commit Messages**: Generate professional commit messages
- **Code Explanation**: Understand shell commands and code snippets
- **Command Suggestions**: Get relevant commands based on intent
- **Code Editing**: AI-assisted code modifications
- **Error Analysis**: Debug errors from logs and stack traces
- **Git Analysis**: Repository intelligence and insights
- **Docker Support**: Container command assistance
- **Beautiful Output**: Rich terminal formatting with syntax highlighting
- **Local Processing**: Runs on Ollama, no cloud dependencies

## Key Specifications

- **44 Python modules** across 9,000+ lines of code
- **12 CLI commands** with full test coverage (20/20 passing)
- **Rich terminal UI** with markdown rendering and color support
- **Modular architecture** with pluggable agents and tools

## Installation

### Requirements

- Python 3.10 or higher
- Ollama with `nemotron-3-nano:30b` model
- Docker (optional, for container operations)

### Setup

```bash
# Clone repository
git clone https://github.com/tevfik/yaver.git
cd yaver

# Install via pipx (recommended)
pipx install -e .

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Configuration

```bash
yaver setup
```

Creates `~/.yaver/config.json` with:
- `OLLAMA_URL`: Ollama endpoint (default: http://localhost:11434)
- `OLLAMA_MODEL`: LLM model (default: nemotron-3-nano:30b)
- Docker configuration (optional)

## Commands

| Command | Description |
|---------|-------------|
| `yaver setup` | Initial configuration |
| `yaver chat` | Interactive chat |
| `yaver commit` | Generate commit messages |
| `yaver explain` | Explain commands and code |
| `yaver suggest` | Command suggestions |
| `yaver edit` | Code editing assistance |
| `yaver solve` | Problem solving |
| `yaver fix` | Error analysis and solutions |
| `yaver analyze` | Repository analysis |
| `yaver docker` | Docker command assistance |
| `yaver status` | System status check |

## Testing

```bash
# Run all tests
python3 test_cli.py
python3 test_modules.py

# Using make
make test-all
```

**Result**: 20/20 tests passing ✅

## Troubleshooting

### Connection Issues

**Error**: `Connection refused` or LLM not responding

1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Run setup again: `yaver setup`
3. Check config file: `cat ~/.yaver/config.json`

### Permission Errors

**Error**: `Permission denied` (Docker operations)

```bash
# Add user to docker group
sudo usermod -aG docker $USER
sudo systemctl restart docker
newgrp docker
```

### Import Errors

**Error**: `ImportError: No module named...`

1. Reinstall: `pip install -e .`
2. Use virtual environment
3. Verify Python 3.10+: `python3 --version`

### Configuration Errors

1. Run setup: `yaver setup`
2. Validate JSON: `python3 -m json.tool ~/.yaver/config.json`
3. Check file permissions

### System Package Conflicts

**Error**: `externally-managed-environment`

```bash
# Recommended: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Or use pipx
pipx install -e .
```

## Architecture

```
src/
  cli/           # CLI interface and commands
  config/        # Configuration management
  agents/        # AI agent implementations
  core/          # Core engine
  memory/        # Memory and context management
  tools/         # Git and system tools
  utils/         # Utilities and prompts
```

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines on bug reports, feature requests, and code contributions.

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

For issues and discussions, please use the [GitHub repository](https://github.com/tevfik/yaver).
