.PHONY: help install test clean docker-start docker-stop docker-status test-modules test-all

help:
	@echo "Yaver AI - Makefile Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install          Install Yaver (pipx)"
	@echo "  make install-dev      Install in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run CLI test suite (14 tests)"
	@echo "  make test-modules     Run comprehensive module tests (20 tests)"
	@echo "  make test-all         Run all tests (CLI + modules)"
	@echo "  make test-verbose     Run tests with verbose output"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-start     Start Docker services"
	@echo "  make docker-stop      Stop Docker services"
	@echo "  make docker-status    Check Docker services"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove temporary files"
	@echo "  make uninstall        Uninstall Yaver"

install:
	@echo "🚀 Installing Yaver with pipx..."
	pipx install -e . --force
	@echo "✅ Installation complete! Run 'yaver --help' to get started."

install-dev:
	@echo "🔧 Installing Yaver in development mode..."
	pip install -e .
	pip install pre-commit
	pre-commit install
	@echo "✅ Development installation complete! Pre-commit hooks installed."

setup-hooks:
	@echo "🪝 Setting up pre-commit hooks..."
	pip install pre-commit
	pre-commit install
	@echo "✅ Hooks installed!"

test:
	@echo "🧪 Running unit tests..."
	@pytest tests/unit

test-integration:
	@echo "🔗 Running integration tests..."
	@pytest tests/integration

test-all:
	@echo "🔬 Running all tests..."
	@pytest tests/

docker-start:
	@yaver docker start

docker-stop:
	@yaver docker stop

docker-status:
	@yaver docker status

clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"

uninstall:
	@echo "🗑️  Uninstalling Yaver..."
	pipx uninstall yaver
	@echo "✅ Yaver uninstalled!"
