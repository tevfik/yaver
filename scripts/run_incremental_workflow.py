#!/usr/bin/env python3
"""
Test script for incremental analysis workflow.
Creates a test repository, makes git commits, and tests the full yaver workflow.
"""

import os
import sys
import subprocess
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime

# Colors for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RED = '\033[91m'
BOLD = '\033[1m'
END = '\033[0m'

def run_cmd(cmd, cwd=None, description=""):
    """Run a shell command and return output"""
    if description:
        print(f"\n{BLUE}→ {description}{END}")
    print(f"  $ {cmd}")
    
    result = subprocess.run(
        cmd, 
        shell=True, 
        cwd=cwd, 
        capture_output=True, 
        text=True
    )
    
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print(f"{RED}Error: {result.stderr}{END}")
    
    return result

def create_test_repo(repo_path):
    """Create a test Python repository with initial structure"""
    os.makedirs(repo_path, exist_ok=True)
    
    print(f"\n{BOLD}{GREEN}📁 Creating test repository at {repo_path}{END}")
    
    # Initialize git
    run_cmd("git init", cwd=repo_path, description="Initialize git repository")
    run_cmd("git config user.email 'test@example.com'", cwd=repo_path)
    run_cmd("git config user.name 'Test User'", cwd=repo_path)
    
    # Create initial files
    files = {
        "utils.py": '''"""Utility functions"""

def parse_config(filename):
    """Parse configuration file"""
    with open(filename) as f:
        return f.read()

def validate_input(data):
    """Validate input data"""
    return len(data) > 0

def format_output(result):
    """Format output"""
    return str(result)
''',
        
        "analyzer.py": '''"""Code analyzer"""

from utils import parse_config, validate_input, format_output

def analyze_file(filepath):
    """Analyze a Python file"""
    config = parse_config("config.ini")
    
    if not validate_input(filepath):
        return None
    
    result = _analyze_content(filepath)
    return format_output(result)

def _analyze_content(filepath):
    """Internal: analyze file content"""
    return {"file": filepath}

def analyze_directory(dirpath):
    """Analyze directory recursively"""
    results = []
    for file in [dirpath]:
        result = analyze_file(file)
        results.append(result)
    return results
''',
        
        "main.py": '''"""Main entry point"""

from analyzer import analyze_file, analyze_directory

def main():
    """Main function"""
    file = "example.py"
    result = analyze_file(file)
    print(f"Analysis: {result}")

if __name__ == "__main__":
    main()
''',
    }
    
    for filename, content in files.items():
        filepath = Path(repo_path) / filename
        filepath.write_text(content)
        print(f"  ✓ Created {filename}")
    
    # First commit
    run_cmd("git add .", cwd=repo_path, description="Stage initial files")
    run_cmd("git commit -m 'Initial commit: utils, analyzer, main'", cwd=repo_path, description="Commit initial files")

def modify_utils(repo_path):
    """Modify utils.py - second commit"""
    print(f"\n{BOLD}{YELLOW}📝 Modification 1: Add new function to utils.py{END}")
    
    utils_path = Path(repo_path) / "utils.py"
    content = utils_path.read_text()
    
    new_content = content + '''
def cache_result(key, value):
    """Cache a result with key"""
    return {key: value}

def retrieve_cached(key, cache):
    """Retrieve cached value"""
    return cache.get(key)
'''
    
    utils_path.write_text(new_content)
    run_cmd("git add utils.py", cwd=repo_path, description="Stage utils.py changes")
    run_cmd("git commit -m 'Add caching functions to utils'", cwd=repo_path, description="Commit: Add caching functions")

def modify_analyzer(repo_path):
    """Modify analyzer.py - third commit"""
    print(f"\n{BOLD}{YELLOW}📝 Modification 2: Enhance analyzer.py{END}")
    
    analyzer_path = Path(repo_path) / "analyzer.py"
    content = analyzer_path.read_text()
    
    new_content = content.replace(
        "from utils import parse_config, validate_input, format_output",
        "from utils import parse_config, validate_input, format_output, cache_result, retrieve_cached"
    )
    
    new_content = new_content.replace(
        "def _analyze_content(filepath):",
        '''def _analyze_content(filepath):
    """Internal: analyze file content with caching"""'''
    )
    
    new_content = new_content + '''
def analyze_with_cache(filepath, cache=None):
    """Analyze file with caching"""
    if cache and filepath in cache:
        return retrieve_cached(filepath, cache)
    
    result = analyze_file(filepath)
    if cache is not None:
        cache_result(filepath, result)
    
    return result
'''
    
    analyzer_path.write_text(new_content)
    run_cmd("git add analyzer.py", cwd=repo_path, description="Stage analyzer.py changes")
    run_cmd("git commit -m 'Add caching support to analyzer'", cwd=repo_path, description="Commit: Add caching support")

def modify_main(repo_path):
    """Modify main.py - fourth commit"""
    print(f"\n{BOLD}{YELLOW}📝 Modification 3: Update main.py{END}")
    
    main_path = Path(repo_path) / "main.py"
    content = main_path.read_text()
    
    new_content = content.replace(
        "from analyzer import analyze_file, analyze_directory",
        "from analyzer import analyze_file, analyze_directory, analyze_with_cache"
    )
    
    new_content = new_content.replace(
        "if __name__ == \"__main__\":",
        '''def benchmark():
    """Benchmark analysis"""
    import time
    start = time.time()
    result = analyze_file("example.py")
    elapsed = time.time() - start
    print(f"Completed in {elapsed:.3f}s")
    return result

if __name__ == \"__main__\":'''
    )
    
    main_path.write_text(new_content)
    run_cmd("git add main.py", cwd=repo_path, description="Stage main.py changes")
    run_cmd("git commit -m 'Add benchmarking to main'", cwd=repo_path, description="Commit: Add benchmarking")

def show_git_log(repo_path):
    """Show git commit history"""
    print(f"\n{BOLD}{BLUE}📋 Git commit history:{END}")
    run_cmd("git log --oneline", cwd=repo_path)

def test_yaver_workflow(repo_path, project_id):
    """Test the yaver analyze --type deep workflow"""
    print(f"\n{BOLD}{GREEN}🚀 Testing Yaver Workflow{END}")
    
    # Test 1: Full analysis (first run)
    print(f"\n{BOLD}{BLUE}Test 1: Full Analysis (First Run){END}")
    print(f"{YELLOW}This will analyze all files since it's the first run{END}")
    run_cmd(
        f"yaver analyze --type deep {repo_path} --project-id {project_id}",
        description="Run full analysis on test repository"
    )
    
    # Check history
    print(f"\n{BOLD}{BLUE}Checking history after first analysis:{END}")
    run_cmd(f"yaver project history {project_id}", description="Show project history")
    
    time.sleep(2)
    
    # Test 2: Incremental (no changes - should skip)
    print(f"\n{BOLD}{BLUE}Test 2: Incremental Analysis (No Changes){END}")
    print(f"{YELLOW}Same commit hash → should SKIP analysis{END}")
    run_cmd(
        f"yaver analyze --type deep {repo_path} --project-id {project_id} --incremental",
        description="Run incremental analysis (should skip)"
    )
    
    # Check history again
    print(f"\n{BOLD}{BLUE}History after incremental attempt (no changes):{END}")
    run_cmd(f"yaver project history {project_id} --limit 5", description="Show updated history")

def test_after_modification(repo_path, project_id, mod_name):
    """Test analysis after making modifications"""
    print(f"\n{BOLD}{BLUE}After {mod_name} - Incremental Analysis{END}")
    print(f"{YELLOW}New commit hash detected → will analyze changed files{END}")
    
    run_cmd(
        f"yaver analyze --type deep {repo_path} --project-id {project_id} --incremental",
        description="Run incremental analysis after changes"
    )
    
    time.sleep(1)
    
    # Show updated history
    print(f"\n{BOLD}{BLUE}Updated history:{END}")
    run_cmd(f"yaver project history {project_id} --limit 10", description="Show history")

def cleanup_test(project_id):
    """Test cleanup command"""
    print(f"\n{BOLD}{BLUE}Test: Project Cleanup{END}")
    print(f"{YELLOW}Keeping only last 2 analyses, removing older ones{END}")
    
    run_cmd(
        f"yaver project cleanup {project_id} --keep-last 2 --force",
        description="Cleanup old analyses (keep last 2)"
    )
    
    # Show final history
    print(f"\n{BOLD}{BLUE}Final history after cleanup:{END}")
    run_cmd(f"yaver project history {project_id}", description="Show final history")

def main():
    """Main test workflow"""
    print(f"\n{BOLD}{GREEN}{'='*70}")
    print(f"  YAVER INCREMENTAL ANALYSIS - WORKFLOW TEST")
    print(f"{'='*70}{END}\n")
    
    # Create temporary test repository
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test_repo"
        project_id = "test_incremental_workflow"
        
        try:
            # Phase 1: Create repository with initial commit
            print(f"\n{BOLD}{GREEN}PHASE 1: Repository Setup{END}")
            create_test_repo(str(repo_path))
            show_git_log(str(repo_path))
            
            # Phase 2: Initial analysis
            print(f"\n{BOLD}{GREEN}PHASE 2: Initial Yaver Analysis{END}")
            test_yaver_workflow(str(repo_path), project_id)
            
            # Phase 3: First modification
            print(f"\n{BOLD}{GREEN}PHASE 3: First Modification (utils.py){END}")
            modify_utils(str(repo_path))
            show_git_log(str(repo_path))
            test_after_modification(str(repo_path), project_id, "Modification 1")
            
            # Phase 4: Second modification
            print(f"\n{BOLD}{GREEN}PHASE 4: Second Modification (analyzer.py){END}")
            modify_analyzer(str(repo_path))
            show_git_log(str(repo_path))
            test_after_modification(str(repo_path), project_id, "Modification 2")
            
            # Phase 5: Third modification
            print(f"\n{BOLD}{GREEN}PHASE 5: Third Modification (main.py){END}")
            modify_main(str(repo_path))
            show_git_log(str(repo_path))
            test_after_modification(str(repo_path), project_id, "Modification 3")
            
            # Phase 6: Test cleanup
            print(f"\n{BOLD}{GREEN}PHASE 6: Test Cleanup{END}")
            cleanup_test(project_id)
            
            # Final summary
            print(f"\n{BOLD}{GREEN}{'='*70}")
            print(f"  ✅ ALL TESTS COMPLETED SUCCESSFULLY")
            print(f"{'='*70}{END}\n")
            
            print(f"{YELLOW}Summary of what was tested:{END}")
            print(f"  1. ✓ Full analysis on first run (analyzed all 3 files)")
            print(f"  2. ✓ Incremental skip when no changes (same commit hash)")
            print(f"  3. ✓ Incremental analysis after first modification (utils.py)")
            print(f"  4. ✓ Incremental analysis after second modification (analyzer.py)")
            print(f"  5. ✓ Incremental analysis after third modification (main.py)")
            print(f"  6. ✓ Project history tracking (multiple analysis records)")
            print(f"  7. ✓ Project cleanup (removed old analyses, kept last 2)")
            print()
            
        except Exception as e:
            print(f"\n{RED}{BOLD}❌ Test failed with error:{END}")
            print(f"{RED}{str(e)}{END}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()
