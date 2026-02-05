#!/usr/bin/env python3
"""
Yaver AI - Command Line Interface
Main entry point that redirects to the new modern CLI.
"""
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.ERROR,  # Only show errors by default to keep UI clean
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Ensure the package can be imported from installed location
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    """Main entry point redirecting to new Typer CLI."""
    try:
        from cli.main import app

        app()
    except ImportError as e:
        print(f"❌ Error importing Yaver CLI: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
