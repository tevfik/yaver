# Contributing to Yaver

Contributions are welcome! Here's how to get started.

## Setting Up Development Environment

```bash
# Clone and setup
git clone https://github.com/tevfik/yaver.git
cd yaver

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
make test-all
```

## Making Changes

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Run tests: `make test-all`
4. Commit with clear messages: `git commit -m "type: description"`
5. Push and create a pull request

## Commit Message Format

```
type: description

Details about the change (optional)

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Testing

```bash
# Run all tests
make test-all

# Run specific tests
python3 test_cli.py
python3 test_modules.py

# Check code style (if applicable)
python3 -m flake8 src/
```

## Code Style

- Use type hints where possible
- Follow PEP 8
- Document public functions
- Keep it simple and readable

## Questions?

Open an issue or discussion if you have questions.

Thanks for contributing!
