#!/usr/bin/env python3
"""
DevMind AI - Command Line Interface
Full-featured CLI with all commands
"""

import sys
import argparse
from pathlib import Path

# Ensure the package can be imported from installed location
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    # Try absolute imports first (for installed package)
    from config.onboarding import check_and_setup_if_needed, get_config
    from cli.docker_manager import DockerManager
except ImportError:
    # Fallback for development
    from config.onboarding import check_and_setup_if_needed, get_config
    from cli.docker_manager import DockerManager

# Rich for beautiful terminal output
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


def format_response(response, title=None):
    """
    Format LLM response for terminal output with rich styling.
    Renders markdown with colors, tables, code blocks, etc.
    
    Args:
        response: AIMessage object or string
        title: Optional title for the response panel
    """
    # Extract content if response is an object
    if hasattr(response, 'content'):
        content = response.content
    else:
        content = str(response)
    
    # Handle escaped newlines
    content = content.replace('\\\\n', '\n')
    content = content.replace('\\\\t', '\t')
    
    # Render as markdown with rich
    md = Markdown(content)
    
    if title:
        console.print(Panel(md, title=title, expand=False, border_style="blue"))
    else:
        console.print(md)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DevMind AI - Development Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  devmind setup              Run initial setup wizard
  devmind new myproject      Create a new Python project
  devmind new api --type fastapi  Create FastAPI project
  devmind docker status      Check Docker services
  devmind chat               Start interactive AI chat
  devmind commit             Generate commit message
  devmind explain "command"  Explain a shell command
  devmind --version          Show version
        """
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='DevMind v1.0.0'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # ========== CORE COMMANDS ==========
    
    # Setup command
    setup_parser = subparsers.add_parser(
        'setup',
        help='Run initial setup wizard'
    )
    setup_parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Use defaults without prompting'
    )
    setup_parser.set_defaults(func=handle_setup)
    
    # Docker command
    docker_parser = subparsers.add_parser(
        'docker',
        help='Manage Docker services'
    )
    docker_subparsers = docker_parser.add_subparsers(
        dest='docker_action',
        help='Docker action'
    )
    docker_subparsers.add_parser('start', help='Start services')
    docker_subparsers.add_parser('stop', help='Stop services')
    docker_subparsers.add_parser('status', help='Check status')
    docker_subparsers.add_parser('logs', help='View logs')
    docker_subparsers.add_parser('restart', help='Restart services')
    docker_parser.set_defaults(func=handle_docker)
    
    # Status command
    status_parser = subparsers.add_parser(
        'status',
        help='Show system status'
    )
    status_parser.set_defaults(func=handle_status)
    
    # ========== AI COMMANDS ==========
    
    # Chat command - Interactive AI
    chat_parser = subparsers.add_parser(
        'chat',
        help='Start interactive AI chat session'
    )
    chat_parser.set_defaults(func=handle_chat)
    
    # Analyze command - Repo analysis
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a git repository'
    )
    analyze_parser.add_argument('path', help='Path to repository')
    analyze_parser.add_argument(
        '--type',
        choices=['overview', 'structure', 'impact', 'detailed'],
        default='overview',
        help='Type of analysis'
    )
    analyze_parser.add_argument('--target', help='Target function/class for impact analysis')
    analyze_parser.set_defaults(func=handle_analyze)
    
    # Commit command - Generate commit message
    commit_parser = subparsers.add_parser(
        'commit',
        help='Generate commit message from staged changes'
    )
    commit_parser.add_argument(
        '--context', '-c',
        help='Additional context for the commit message'
    )
    commit_parser.set_defaults(func=handle_commit)
    
    # Explain command - Explain shell command
    explain_parser = subparsers.add_parser(
        'explain',
        help='Explain what a shell command does'
    )
    explain_parser.add_argument('command', nargs='?', help='Shell command to explain (or pipe from stdin)')
    explain_parser.set_defaults(func=handle_explain)
    
    # Edit command - Edit files with AI
    edit_parser = subparsers.add_parser(
        'edit',
        help='Edit a file using AI instructions'
    )
    edit_parser.add_argument('request', help='Instructions for editing')
    edit_parser.add_argument('--file', '-f', required=True, help='File to edit')
    edit_parser.set_defaults(func=handle_edit)
    
    # Solve command - Full workflow
    solve_parser = subparsers.add_parser(
        'solve',
        help='End-to-end task solver (Branch -> Edit -> Commit)'
    )
    solve_parser.add_argument('task', help='Task description')
    solve_parser.add_argument('--file', '-f', help='Target file to modify')
    solve_parser.set_defaults(func=handle_solve)
    
    # Fix command - Analyze and fix logs
    fix_parser = subparsers.add_parser(
        'fix',
        help='Analyze logs and suggest fixes'
    )
    fix_parser.add_argument('cmd_args', nargs=argparse.REMAINDER, help='Command to execute')
    fix_parser.set_defaults(func=handle_fix)
    
    # Suggest command - Generate shell command
    suggest_parser = subparsers.add_parser(
        'suggest',
        help='Generate shell command from natural language'
    )
    suggest_parser.add_argument('prompt', nargs='?', help='Description of what you want to do (or pipe from stdin)')
    suggest_parser.set_defaults(func=handle_suggest)
    
    # New command - Create new project
    new_parser = subparsers.add_parser(
        'new',
        help='Create a new project with scaffolding'
    )
    new_parser.add_argument('name', help='Project name')
    new_parser.add_argument(
        '--type', '-t',
        choices=['python', 'fastapi', 'flask', 'cli', 'ml', 'basic'],
        default='python',
        help='Project type (default: python)'
    )
    new_parser.add_argument(
        '--path', '-p',
        help='Path where to create project (default: current directory)'
    )
    new_parser.set_defaults(func=handle_new)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Auto setup on first run (if running any command except setup/help/version)
    if args.command and args.command not in ['setup']:
        check_and_setup_if_needed()
    
    # Execute command
    if hasattr(args, 'func'):
        try:
            args.func(args)
        except ModuleNotFoundError as e:
            print(f"❌ Error: Module not found: {e}")
            print("   This may indicate an installation issue.")
            print("   Try running: pip install -e . --upgrade")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


def handle_setup(args):
    """Handle setup command"""
    from config.onboarding import DevMindSetupWizard
    
    wizard = DevMindSetupWizard()
    
    # Check if non-interactive mode (for CI/CD)
    if hasattr(args, 'non_interactive') and args.non_interactive:
        # Use defaults
        config = {
            "OLLAMA_URL": "http://localhost:11434",
            "OLLAMA_MODEL": "mistral",
            "QDRANT_URL": "http://localhost:6333",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "CHROMA_PERSIST_DIR": ".devmind/chroma_db",
        }
        wizard.save_env_file(config)
        print("✅ Setup complete (non-interactive mode)!")
    else:
        config = wizard.run()
        print("✅ Setup complete!")


def handle_docker(args):
    """Handle docker commands"""
    manager = DockerManager()
    
    if not args.docker_action:
        # Show interactive menu
        from cli.docker_manager import manage_docker_interactive
        manage_docker_interactive()
    else:
        if args.docker_action == "start":
            success, msg = manager.start_services()
            print(f"\n{msg}")
            if success:
                manager.print_status()
        
        elif args.docker_action == "stop":
            success, msg = manager.stop_services()
            print(f"\n{msg}")
        
        elif args.docker_action == "status":
            manager.print_status()
        
        elif args.docker_action == "logs":
            import subprocess
            try:
                compose_cmd = manager.get_compose_command()
                subprocess.run(
                    compose_cmd + ["-f", str(manager.compose_file), "logs", "-f", "--tail=50"],
                    cwd=str(manager.docker_dir)
                )
            except KeyboardInterrupt:
                print("\n\nLogs stopped.\n")
        
        elif args.docker_action == "restart":
            print("\n🔄 Restarting services...")
            manager.stop_services(verbose=False)
            import time
            time.sleep(2)
            success, msg = manager.start_services()
            print(f"\n{msg}")
            if success:
                manager.print_status()


def handle_status(args):
    """Handle status command"""
    config = get_config()
    
    print("\n" + "="*60)
    print("DevMind System Status")
    print("="*60)
    
    if config:
        print("\n✅ Configuration found:")
        print(f"   Ollama: {config.get('OLLAMA_URL', 'not configured')}")
        print(f"   Qdrant: {config.get('QDRANT_URL', 'not configured')}")
        print(f"   Neo4j: {config.get('NEO4J_URI', 'not configured')}")
    else:
        print("\n⚠️  No configuration found. Run 'devmind setup' first.")
    
    print("\n" + "="*60)


def handle_chat(args):
    """Handle interactive AI chat"""
    print("\n🤖 DevMind AI Chat (Type 'exit' to quit)\n")
    print("💡 Tip: Ask anything about your code, get AI assistance\n")
    
    try:
        from agents.agent_base import create_llm
        
        llm = create_llm()
        chat_history = []
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Add to history
                chat_history.append({"role": "user", "content": user_input})
                
                # Get AI response
                response = llm.invoke(user_input)
                
                console.print("\n[cyan]Assistant:[/cyan]")
                format_response(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
    except ImportError as e:
        print(f"⚠️  AI features not available: {e}")
    except AttributeError:
        print("⚠️  Configuration error. Please run: devmind setup")
        print("   Please run: pip install -e .[full]")


def handle_analyze(args):
    """Handle repository analysis"""
    print(f"\n📊 Analyzing repository: {args.path}")
    print(f"   Analysis type: {args.type}\n")
    
    try:
        # Try to import GitAnalyzer (the actual class that exists)
        from tools.git_analyzer import GitAnalyzer
        
        analyzer = GitAnalyzer(args.path)
        
        if args.type == 'overview':
            status = analyzer.get_status()
            commits = analyzer.get_commits()
            print(f"Status: {status}")
            print(f"Recent commits: {commits[:5]}")
        elif args.type == 'structure':
            # Get files in repository
            files = analyzer.get_files() if hasattr(analyzer, 'get_files') else []
            print(f"Repository structure loaded: {len(files)} files")
        elif args.type == 'impact' and args.target:
            # Analyze impact of changes
            print(f"Analyzing impact on: {args.target}")
        elif args.type == 'detailed':
            # Detailed analysis
            status = analyzer.get_status()
            commits = analyzer.get_commits(50)
            print(f"Status: {status}")
            print(f"Recent commits (50): {len(commits)} entries")
        else:
            # Default overview
            status = analyzer.get_status()
            print(f"Repository status: {status}")
            
    except ImportError as ie:
        print(f"❌ Analysis failed: Module not found - {ie}")
        print("   Try: pip install -e . --upgrade")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")


def handle_commit(args):
    """Handle commit message generation with structured prompt"""
    print("\n📝 Generating commit message from staged changes...\n")
    
    try:
        import subprocess
        from agents.agent_base import create_llm
        from utils.prompts import COMMIT_MESSAGE_PROMPT
        
        # Get staged changes
        result = subprocess.run(
            ['git', 'diff', '--staged'],
            capture_output=True,
            text=True,
            check=True
        )
        
        diff = result.stdout
        if not diff:
            print("⚠️  No staged changes found.")
            return
        
        llm = create_llm()
        
        # Use structured prompt
        prompt_input = {
            "diff": diff,
            "context": args.context if args.context else "None provided"
        }
        
        response = llm.invoke(COMMIT_MESSAGE_PROMPT.format(**prompt_input))
        format_response(response, title="📝 Suggested Commit Message")
        
    except subprocess.CalledProcessError:
        print("❌ Not a git repository or no git installed.")
    except ImportError as e:
        print(f"⚠️  AI features not available: {e}")
    except AttributeError:
        print(f"⚠️  Configuration error. Please run: devmind setup")
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_explain(args):
    """Handle shell command explanation with structured prompt"""
    import sys
    
    # Get command from argument or stdin
    if args.command:
        command = args.command
    elif not sys.stdin.isatty():
        command = sys.stdin.read().strip()
        if not command:
            print("❌ Error: No command provided. Usage: devmind explain <command>")
            return
    else:
        print("❌ Error: No command provided. Usage: devmind explain <command>")
        return
    
    print(f"\n📖 Explaining command: {command}\n")
    
    try:
        from agents.agent_base import create_llm
        from utils.prompts import SHELL_EXPLAINER_PROMPT
        
        llm = create_llm()
        
        # Use structured prompt
        prompt_input = {
            "command": command
        }
        
        response = llm.invoke(SHELL_EXPLAINER_PROMPT.format(**prompt_input))
        format_response(response, title=f"📖 Command Explanation: {command}")
        
    except ImportError:
        print("⚠️  AI features not available. Install required dependencies.")
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_edit(args):
    """Handle file editing with AI"""
    print(f"\n✏️  Editing: {args.file}")
    print(f"   Request: {args.request}\n")
    
    try:
        from pathlib import Path
        from agents.agent_base import create_llm
        
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}")
            return
        
        # Read current file
        with open(file_path) as f:
            current_content = f.read()
        
        llm = create_llm()
        
        prompt = f"""Edit this file according to the request:

File: {args.file}
Request: {args.request}

Current content:
```
{current_content}
```

Provide the edited content only, no explanation."""
        
        response = llm.invoke(prompt)
        
        format_response(response, title="✏️ Proposed Changes")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_solve(args):
    """Handle end-to-end task solving"""
    print(f"\n🚀 Solving task: {args.task}\n")
    
    if args.file:
        print(f"   Target file: {args.file}")
    
    print("   This is a full workflow task solver.\n")
    
    try:
        from agents.agent_base import create_llm
        
        llm = create_llm()
        
        prompt = f"""Solve this development task:

Task: {args.task}
Target file: {args.file if args.file else 'Not specified'}

Provide a step-by-step solution including:
1. Analysis of the problem
2. Proposed solution
3. Code changes needed
4. Testing approach"""
        
        response = llm.invoke(prompt)
        format_response(response, title="🚀 Task Solution")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_fix(args):
    """Handle log analysis and fixing with structured prompt"""
    print("\n🔧 Analyzing logs and suggesting fixes...\n")
    
    try:
        import subprocess
        from agents.agent_base import create_llm
        from utils.prompts import ERROR_FIXER_PROMPT
        
        # Run the command
        cmd = args.cmd_args if args.cmd_args else ['echo', 'No command provided']
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        output = result.stdout + result.stderr
        
        if result.returncode != 0:
            llm = create_llm()
            
            # Use structured prompt
            prompt_input = {
                "command": ' '.join(cmd),
                "exit_code": result.returncode,
                "output": result.stdout if result.stdout else "No stdout",
                "stderr": result.stderr if result.stderr else "No stderr"
            }
            
            response = llm.invoke(ERROR_FIXER_PROMPT.format(**prompt_input))
            format_response(response, title="🔧 Error Analysis & Fixes")
        else:
            print("✅ Command succeeded (no errors to fix)")
            
    except ImportError:
        print("⚠️  AI features not available. Install required dependencies.")
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_suggest(args):
    """Handle shell command suggestion with structured prompt"""
    import sys
    
    # Get prompt from argument or stdin
    if args.prompt:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
        if not prompt:
            print("❌ Error: No prompt provided. Usage: devmind suggest <description>")
            return
    else:
        print("❌ Error: No prompt provided. Usage: devmind suggest <description>")
        return
    
    print(f"\n💡 Suggesting command for: {prompt}\n")
    
    try:
        from agents.agent_base import create_llm
        from utils.prompts import SHELL_SUGGESTER_PROMPT
        
        llm = create_llm()
        
        # Use structured prompt
        prompt_input = {
            "task": prompt
        }
        
        response = llm.invoke(SHELL_SUGGESTER_PROMPT.format(**prompt_input))
        format_response(response, title="💡 Command Suggestion")
        
    except ImportError as e:
        print(f"⚠️  AI features not available: {e}")
    except AttributeError as e:
        print(f"⚠️  Configuration error. Please run: devmind setup")
    except Exception as e:
        print(f"❌ Error: {e}")


def handle_new(args):
    """Handle new project creation with AI"""
    import json
    import re
    
    project_name = args.name.strip()
    project_type = args.type
    base_path = Path(args.path) if args.path else Path.cwd()
    project_path = base_path / project_name
    
    # Validate project name
    if not project_name:
        print("❌ Error: Project name cannot be empty!")
        print("Usage: devmind new <project_name> [--type <type>]")
        print("\nExample:")
        print("  devmind new my_project")
        print("  devmind new api --type fastapi")
        return
    
    # Project name must be valid for filesystem
    if len(project_name) > 255:
        print("❌ Error: Project name too long (max 255 characters)")
        return
    
    # Allow alphanumeric, dash, underscore, dot
    if not re.match(r'^[a-zA-Z0-9._-]+$', project_name):
        print("❌ Error: Invalid project name!")
        print("   Project names can only contain: letters, numbers, dash (-), underscore (_), dot (.)")
        print("\nValid examples:")
        print("  devmind new my_project")
        print("  devmind new my-project")
        print("  devmind new MyProject")
        print("  devmind new project_v2.0")
        return
    
    # Cannot start with dash or dot
    if project_name[0] in '-.':
        print("❌ Error: Project name cannot start with dash (-) or dot (.)")
        return
    
    # Check if directory already exists
    if project_path.exists():
        print(f"❌ Error: Directory '{project_name}' already exists!")
        return
    
    print(f"\n🤖 Creating new {project_type} project: {project_name}")
    print(f"   Location: {project_path}")
    print(f"   Using AI to generate optimal project structure...\n")
    
    try:
        # Use AI to generate project structure
        from agents.agent_base import create_llm
        from utils.prompts import PROJECT_SCAFFOLDER_PROMPT
        
        llm = create_llm()
        
        # Build prompt with project details
        prompt_input = {
            "project_name": project_name,
            "project_type": project_type,
            "requirements": "",
            "context": f"Generate a complete {project_type} project structure with all necessary files and best practices."
        }
        
        print("   🧠 AI is designing your project structure...")
        response = llm.invoke(PROJECT_SCAFFOLDER_PROMPT.format(**prompt_input))
        
        # Try to parse JSON response
        try:
            # Extract JSON from response (may have markdown wrapper)
            response_text = str(response) if not isinstance(response, str) else response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text
            
            structure = json.loads(json_text)
            
            # Create project from AI-generated structure
            create_project_from_ai_structure(project_path, structure)
            
            print(f"\n✅ Project '{project_name}' created successfully with AI-generated structure!")
            
            # Show next steps if provided
            if "next_steps" in structure:
                print(f"\n📂 Next steps:")
                for step in structure["next_steps"]:
                    print(f"   • {step}")
            print(f"\n   cd {project_name}")
            print(f"   devmind chat  # Get AI help with your project\n")
            
        except json.JSONDecodeError:
            # Fallback to template-based generation if AI response can't be parsed
            print("   ⚠️  Using template-based generation (AI response format issue)")
            if project_type == 'python':
                create_python_project(project_path, project_name)
            elif project_type == 'fastapi':
                create_fastapi_project(project_path, project_name)
            elif project_type == 'flask':
                create_flask_project(project_path, project_name)
            elif project_type == 'cli':
                create_cli_project(project_path, project_name)
            elif project_type == 'ml':
                create_ml_project(project_path, project_name)
            else:
                create_basic_project(project_path, project_name)
            
            print(f"\n✅ Project '{project_name}' created successfully!")
            print(f"\n📂 Next steps:")
            print(f"   cd {project_name}")
            print(f"   git init")
            print(f"   pip install -e .")
            print(f"   devmind chat\n")
        
    except ImportError:
        # If AI dependencies not available, use templates
        print("   ⚠️  AI features not available, using templates")
        project_path.mkdir(parents=True, exist_ok=True)
        
        if project_type == 'python':
            create_python_project(project_path, project_name)
        elif project_type == 'fastapi':
            create_fastapi_project(project_path, project_name)
        elif project_type == 'flask':
            create_flask_project(project_path, project_name)
        elif project_type == 'cli':
            create_cli_project(project_path, project_name)
        elif project_type == 'ml':
            create_ml_project(project_path, project_name)
        else:
            create_basic_project(project_path, project_name)
        
        print(f"\n✅ Project '{project_name}' created!")
        
    except Exception as e:
        print(f"❌ Error creating project: {e}")
        # Cleanup on error
        if project_path.exists():
            import shutil
            shutil.rmtree(project_path)


def create_project_from_ai_structure(path: Path, structure: dict):
    """Create project from AI-generated structure"""
    # Create directories
    if "structure" in structure and "directories" in structure["structure"]:
        for dir_path in structure["structure"]["directories"]:
            (path / dir_path).mkdir(parents=True, exist_ok=True)
            print(f"   ✓ Created directory: {dir_path}")
    
    # Create files
    if "structure" in structure and "files" in structure["structure"]:
        for file_info in structure["structure"]["files"]:
            file_path = path / file_info["path"]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(file_info["content"])
            print(f"   ✓ Created file: {file_info['path']}")
    
    print(f"   ✓ Project structure complete")


def create_python_project(path: Path, name: str):
    """Create a standard Python project"""
    # Create directory structure
    (path / name).mkdir()
    (path / "tests").mkdir()
    (path / "docs").mkdir()
    
    # Create __init__.py
    (path / name / "__init__.py").write_text(f'"""{name}"""\n\n__version__ = "0.1.0"\n')
    
    # Create main.py
    (path / name / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main module\"\"\"


def main():
    \"\"\"Main entry point\"\"\"
    print("Hello from {name}!")


if __name__ == "__main__":
    main()
""".replace("{name}", name))
    
    # Create setup.py
    (path / "setup.py").write_text(f"""from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={{
        "console_scripts": [
            "{name}={name}.main:main",
        ],
    }},
    python_requires=">=3.8",
)
""")
    
    # Create requirements.txt
    (path / "requirements.txt").write_text("# Add your dependencies here\n")
    
    # Create README.md
    (path / "README.md").write_text(f"""# {name}

A Python project created with DevMind AI.

## Installation

```bash
pip install -e .
```

## Usage

```bash
{name}
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/
```
""")
    
    # Create .gitignore
    (path / ".gitignore").write_text("""__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
.coverage
htmlcov/
.DS_Store
""")
    
    # Create test file
    (path / "tests" / "__init__.py").write_text("")
    (path / "tests" / f"test_{name}.py").write_text(f"""import pytest
from {name}.main import main


def test_main():
    \"\"\"Test main function\"\"\"
    main()  # Should not raise
""")
    
    print(f"   ✓ Created Python project structure")


def create_fastapi_project(path: Path, name: str):
    """Create a FastAPI project"""
    (path / "app").mkdir()
    (path / "tests").mkdir()
    
    # Create FastAPI app
    (path / "app" / "__init__.py").write_text("")
    (path / "app" / "main.py").write_text("""from fastapi import FastAPI

app = FastAPI(title="My API", version="0.1.0")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}
""")
    
    # Create requirements.txt
    (path / "requirements.txt").write_text("""fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.5.0
""")
    
    # Create README
    (path / "README.md").write_text(f"""# {name}

FastAPI application created with DevMind AI.

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
""")
    
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\nvenv/\n.env\n")
    
    print(f"   ✓ Created FastAPI project structure")


def create_flask_project(path: Path, name: str):
    """Create a Flask project"""
    (path / "app").mkdir()
    (path / "templates").mkdir()
    (path / "static").mkdir()
    
    (path / "app" / "__init__.py").write_text("""from flask import Flask

def create_app():
    app = Flask(__name__)
    
    @app.route('/')
    def index():
        return {"message": "Hello from Flask!"}
    
    return app
""")
    
    (path / "run.py").write_text("""from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
""")
    
    (path / "requirements.txt").write_text("Flask>=3.0.0\n")
    (path / "README.md").write_text(f"# {name}\n\nFlask app created with DevMind AI.\n\n## Run\n\n```bash\npython run.py\n```\n")
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\nvenv/\n")
    
    print(f"   ✓ Created Flask project structure")


def create_cli_project(path: Path, name: str):
    """Create a CLI tool project"""
    (path / name).mkdir()
    
    (path / name / "__init__.py").write_text(f'__version__ = "0.1.0"\n')
    (path / name / "cli.py").write_text("""import argparse

def main():
    parser = argparse.ArgumentParser(description="CLI tool")
    parser.add_argument('--version', action='version', version='0.1.0')
    args = parser.parse_args()
    
    print("CLI tool running!")

if __name__ == '__main__':
    main()
""")
    
    (path / "setup.py").write_text(f"""from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(),
    entry_points={{
        'console_scripts': [
            '{name}={name}.cli:main',
        ],
    }},
)
""")
    
    (path / "README.md").write_text(f"# {name}\n\nCLI tool created with DevMind AI.\n")
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    
    print(f"   ✓ Created CLI tool project structure")


def create_ml_project(path: Path, name: str):
    """Create a Machine Learning project"""
    (path / "data").mkdir()
    (path / "notebooks").mkdir()
    (path / "models").mkdir()
    (path / "src").mkdir()
    
    (path / "src" / "__init__.py").write_text("")
    (path / "requirements.txt").write_text("""numpy>=1.24.0
pandas>=2.0.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
jupyter>=1.0.0
""")
    
    (path / "README.md").write_text(f"""# {name}

ML project created with DevMind AI.

## Structure

- `data/`: Dataset files
- `notebooks/`: Jupyter notebooks
- `models/`: Trained models
- `src/`: Source code
""")
    
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\ndata/*.csv\nmodels/*.pkl\n.ipynb_checkpoints/\n")
    
    print(f"   ✓ Created ML project structure")


def create_basic_project(path: Path, name: str):
    """Create a basic project"""
    (path / "README.md").write_text(f"# {name}\n\nProject created with DevMind AI.\n")
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    
    print(f"   ✓ Created basic project structure")


if __name__ == "__main__":
    main()

