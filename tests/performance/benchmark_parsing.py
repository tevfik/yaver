import os
import time
import shutil
import pytest
from pathlib import Path
from src.tools.code_analyzer.ast_parser import ASTParser


def generate_test_repo(path: Path, count: int = 1000):
    """Generate a test repo with many files"""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)

    # Template
    content = """
import os
import sys

class DataProcessor:
    def __init__(self, data):
        self.data = data

    def process(self):
        return [d * 2 for d in self.data]

def util_func(x):
    return x + 1

def main():
    p = DataProcessor([1, 2, 3])
    print(p.process())
"""

    for i in range(count):
        (path / f"module_{i}.py").write_text(content)


def test_parsing_performance():
    repo_path = Path("tests/data/bench_repo")
    try:
        # Generate
        print(f"Generating 1000 files in {repo_path}...")
        generate_test_repo(repo_path, 1000)

        parser = ASTParser()
        files = list(repo_path.glob("*.py"))

        start_time = time.time()
        count = 0
        for f in files:
            parser.parse_file(f, repo_root=repo_path)
            count += 1

        duration = time.time() - start_time
        print(f"\nTime to parse {count} files: {duration:.2f}s")
        print(f"Average: {duration/count*1000:.2f}ms per file")

        # Assertion: Should be under 15s
        assert duration < 15.0, f"Performance regression: Parsing took {duration}s"

    finally:
        # Cleanup
        if repo_path.exists():
            shutil.rmtree(repo_path)


if __name__ == "__main__":
    test_parsing_performance()
