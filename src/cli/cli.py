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
    
    # Session command - Manage sessions
    session_parser = subparsers.add_parser(
        'session',
        help='Manage DevMind sessions with tags'
    )
    session_subparsers = session_parser.add_subparsers(
        dest='session_action',
        help='Session action'
    )
    
    # session new [--name NAME] [--tag TAG [TAG ...]]
    session_new = session_subparsers.add_parser('new', help='Create new session')
    session_new.add_argument('--name', help='Session name')
    session_new.add_argument('--tag', nargs='*', help='Tags for session')
    
    # session list
    session_subparsers.add_parser('list', help='List all sessions')
    
    # session current
    session_subparsers.add_parser('current', help='Show active session')
    
    # session set <session_id>
    session_set = session_subparsers.add_parser('set', help='Switch to session')
    session_set.add_argument('session_id', help='Session ID to switch to')
    
    # session tag <session_id> <tag>
    session_tag = session_subparsers.add_parser('tag', help='Add tag to session')
    session_tag.add_argument('session_id', help='Session ID')
    session_tag.add_argument('tag', help='Tag to add')
    
    # session delete <session_id>
    session_delete = session_subparsers.add_parser('delete', help='Delete session')
    session_delete.add_argument('session_id', help='Session ID to delete')
    
    session_parser.set_defaults(func=handle_session)
    
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
        choices=['overview', 'structure', 'impact', 'detailed', 'deep'],
        default='overview',
        help='Type of analysis'
    )
    analyze_parser.add_argument('--target', help='Target function/class for impact analysis')
    analyze_parser.add_argument('--incremental', action='store_true', help='Only analyze changed files')
    analyze_parser.set_defaults(func=handle_analyze)

    # Simulate command - Helper for impact analysis
    simulate_parser = subparsers.add_parser(
        'simulate',
        help='simulate impact analysis'
    )
    simulate_parser.add_argument('file', help='File to change')
    simulate_parser.add_argument('function', help='Function to change')
    simulate_parser.set_defaults(func=handle_simulate)
    
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
        help='Explain what a shell command does or analyze a file'
    )
    explain_parser.add_argument('command', nargs='?', help='Shell command to explain (or pipe from stdin)')
    explain_parser.add_argument('-f', '--file', help='Explain a specific file (path to file)')
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
    
    # Visualize command
    visualize_parser = subparsers.add_parser(
        'visualize',
        help='Visualize codebase structure'
    )
    visualize_parser.add_argument('path', help='Path to repository')
    visualize_parser.add_argument('--type', choices=['class', 'call-graph'], default='class', help='Visualization type')
    visualize_parser.add_argument('--function', '-f', help='Root function for call-graph')
    visualize_parser.add_argument('--output', '-o', help='Output file (e.g. diagram.md)', default='structure.md')
    visualize_parser.set_defaults(func=handle_visualize)
    
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


def handle_session(args):
    """Handle session management commands"""
    from core.session_manager import get_session_manager
    from rich.table import Table
    
    session_mgr = get_session_manager()
    
    if not args.session_action:
        print("❌ Error: Please specify a session action")
        print("   Try: devmind session --help")
        return
    
    # New session
    if args.session_action == "new":
        tags = args.tag if args.tag else []
        session_id = session_mgr.create_session(name=args.name, tags=tags)
        print(f"\n✅ Created session: {session_id}")
        if args.name:
            print(f"   Name: {args.name}")
        if tags:
            print(f"   Tags: {', '.join(tags)}")
        print(f"   Active: ✓\n")
    
    # List sessions
    elif args.session_action == "list":
        sessions = session_mgr.list_sessions()
        active = session_mgr.get_active_session()
        
        if not sessions:
            print("\n❌ No sessions found")
            print("   Create one: devmind session new\n")
            return
        
        table = Table(title="DevMind Sessions", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="green")
        table.add_column("Name", style="white")
        table.add_column("Tags", style="yellow")
        table.add_column("Created", style="dim")
        table.add_column("Active", style="bold")
        
        for session in sessions:
            is_active = "✓" if session["id"] == active else ""
            tags_str = ", ".join(session.get("tags", []))
            created = session["created_at"][:10]
            table.add_row(
                session["id"],
                session["name"],
                tags_str or "-",
                created,
                is_active
            )
        
        console.print(table)
        print()
    
    # Show current session
    elif args.session_action == "current":
        active = session_mgr.get_active_session()
        if not active:
            print("\n❌ No active session\n")
            return
        
        session = session_mgr.get_session(active)
        if session:
            print(f"\n🎯 Active Session:")
            print(f"   ID: {session['id']}")
            print(f"   Name: {session['name']}")
            print(f"   Tags: {', '.join(session.get('tags', [])) or '-'}")
            print(f"   Created: {session['created_at'][:10]}")
            print(f"   Last used: {session['last_used'][:10]}\n")
    
    # Switch session
    elif args.session_action == "set":
        if session_mgr.set_active_session(args.session_id):
            session = session_mgr.get_session(args.session_id)
            print(f"\n✅ Switched to session: {session['name']}")
            print(f"   ID: {args.session_id}\n")
        else:
            print(f"\n❌ Session not found: {args.session_id}\n")
    
    # Add tag
    elif args.session_action == "tag":
        if session_mgr.add_tag(args.session_id, args.tag):
            session = session_mgr.get_session(args.session_id)
            print(f"\n✅ Added tag '{args.tag}' to session: {session['name']}")
            print(f"   Tags: {', '.join(session.get('tags', []))}\n")
        else:
            print(f"\n❌ Session not found: {args.session_id}\n")
    
    # Delete session
    elif args.session_action == "delete":
        session = session_mgr.get_session(args.session_id)
        if not session:
            print(f"\n❌ Session not found: {args.session_id}\n")
            return
        
        session_mgr.delete_session(args.session_id)
        print(f"\n✅ Deleted session: {session['name']}\n")


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
    
    agent = None
    try:
        from agents.agent_chat import ChatAgent
        import uuid
        
        session_id = f"chat_{uuid.uuid4().hex[:8]}"
        agent = ChatAgent(session_id=session_id)
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Get AI response
                console.print("\n[cyan]DevMind:[/cyan]")
                with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                    response = agent.chat(user_input)
                
                format_response(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
    except ImportError as e:
        print(f"⚠️  AI features not available: {e}")
    except Exception as e:
        print(f"⚠️  An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if agent:
            agent.close()


def handle_analyze(args):
    """Handle repository analysis"""
    print(f"\n📊 Analyzing repository: {args.path}")
    print(f"   Analysis type: {args.type}\n")
    
    try:
        from tools.git_analyzer import GitAnalyzer
        from rich.table import Table
        from rich.panel import Panel
        import os
        
        analyzer = GitAnalyzer(args.path)
        status = analyzer.get_status()
        commits = analyzer.get_commits(50)
        
        if status.get('error'):
            print(f"⚠️  {status['error']}")
            return
        
        # Repository statistics
        total_files = len([f for f in os.walk(args.path)]) if os.path.isdir(args.path) else 0
        is_dirty = not status.get('is_clean', True)
        
        if args.type == 'deep':
            from tools.code_analyzer.analyzer import CodeAnalyzer
            from rich.console import Console
            from pathlib import Path
            import time
            import uuid
            
            console = Console()
            console.print(f"[bold cyan]🔍 Starting Deep Code Analysis...[/bold cyan]")
            
            # Create session ID
            session_id = f"cli_{uuid.uuid4().hex[:8]}"
            repo_path = Path(args.path)
            
            # Neo4j Config
            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
            
            try:
                analyzer = CodeAnalyzer(session_id, repo_path)
                
                # Attempt connection
                try:
                    analyzer.connect_db(neo4j_uri, (neo4j_user, neo4j_password))
                    console.print(f"[dim]Connected to Neo4j at {neo4j_uri}[/dim]")
                except Exception as db_err:
                    console.print(f"[yellow]⚠️  Could not connect to Neo4j: {db_err}[/yellow]")
                    console.print(f"[yellow]    Analysis will run but graph data won't be stored.[/yellow]")

                start_time = time.time()
                # Use incremental flag if passed (mapped from --incremental arg if we add it)
                # But CLI args don't have it yet. Let's assume standard analysis for now
                # or add argument in analyze_parser
                analyzer.analyze_repository(incremental=getattr(args, 'incremental', False))
                duration = time.time() - start_time
                
                console.print(f"[bold green]✅ Analysis Complete![/bold green]")
                console.print(f"   - Processing Duration: {duration:.2f}s")
                console.print(f"   - Session ID: {session_id}")
                
                # Report Cycles if possible
                if analyzer.neo4j_adapter:
                   cycles = analyzer.neo4j_adapter.detect_circular_dependencies()
                   if cycles:
                       console.print(f"\n[bold red]⚠️  Found {len(cycles)} Circular Dependencies:[/bold red]")
                       for cycle in cycles:
                           # cycle is a list of node IDs. Let's format nicely.
                           # id is like id:path/to/file::Class::method
                           simple_names = [uid.split("::")[-1] for uid in cycle]
                           console.print(f"   🔄 {' -> '.join(simple_names)}")
                
                # Clean up
                analyzer.close()

            except Exception as e:
                console.print(f"[bold red]❌ Analysis Failed:[/bold red] {str(e)}")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            
            return

        if args.type == 'overview':
            # Create overview table
            table = Table(title="Repository Overview", show_header=True, header_style="bold cyan")
            table.add_column("Metric", style="white")
            table.add_column("Value", style="green")
            
            table.add_row("Status", "🔴 Dirty" if is_dirty else "✅ Clean")
            table.add_row("Commits", str(len(commits)))
            table.add_row("Recent Activity", commits[0]['message'] if commits else "No commits")
            
            # Count file changes
            changes = status.get('changes', '').split('\n')
            modified = len([c for c in changes if c.strip().startswith('M ')])
            added = len([c for c in changes if c.strip().startswith('?? ')])
            deleted = len([c for c in changes if c.strip().startswith('D ')])
            
            table.add_row("Modified Files", str(modified))
            table.add_row("New Files", str(added))
            table.add_row("Deleted Files", str(deleted))
            
            console.print(table)
            
            # Recent commits
            if commits:
                print("\n📝 Recent Commits:")
                for commit in commits[:5]:
                    print(f"  • {commit['hash'][:7]} - {commit['message'][:60]}")
                    
        elif args.type == 'structure':
            # Project structure analysis
            lang_stats = {'Python': 0, 'Go': 0, 'C++': 0, 'JavaScript': 0, 'Other': 0}
            
            for root, dirs, files in os.walk(args.path):
                # Skip hidden and cache directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
                
                for file in files:
                    if file.endswith('.py'):
                        lang_stats['Python'] += 1
                    elif file.endswith('.go'):
                        lang_stats['Go'] += 1
                    elif file.endswith(('.cpp', '.cc', '.h', '.hpp')):
                        lang_stats['C++'] += 1
                    elif file.endswith(('.js', '.ts', '.jsx', '.tsx')):
                        lang_stats['JavaScript'] += 1
                    else:
                        lang_stats['Other'] += 1
            
            table = Table(title="Project Structure", show_header=True, header_style="bold cyan")
            table.add_column("Language", style="white")
            table.add_column("Files", style="green")
            
            for lang, count in lang_stats.items():
                if count > 0:
                    table.add_row(lang, str(count))
            
            console.print(table)
            
        elif args.type == 'detailed':
            # Detailed analysis with insights
            panel_text = f"""
🔍 **Repository Analysis**

**Status**: {'🔴 Has uncommitted changes' if is_dirty else '✅ Clean'}

**Commit History**:
  • Total commits: {len(commits)}
  • Latest: {commits[0]['message'] if commits else 'No commits'}
  • Last 5 commits:
"""
            for commit in commits[:5]:
                panel_text += f"    - {commit['hash'][:7]} {commit['message'][:50]}\n"
            
            # File statistics
            changes = status.get('changes', '').split('\n')
            modified = len([c for c in changes if c.strip().startswith('M ')])
            added = len([c for c in changes if c.strip().startswith('?? ')])
            deleted = len([c for c in changes if c.strip().startswith('D ')])
            
            panel_text += f"""
**Working Directory**:
  • Modified files: {modified}
  • New files: {added}
  • Deleted files: {deleted}
"""
            
            console.print(Panel(panel_text, title="Repository Details", border_style="cyan"))
            
        else:
            # Default: show basic info
            table = Table(title="Repository Info", show_header=True, header_style="bold cyan")
            table.add_column("Info", style="white")
            table.add_column("Details", style="green")
            
            table.add_row("Location", args.path)
            table.add_row("Status", "🔴 Dirty" if is_dirty else "✅ Clean")
            table.add_row("Commits", str(len(commits)))
            
            changes = status.get('changes', '').split('\n')
            table.add_row("Changes", str(len([c for c in changes if c.strip()])))
            
            console.print(table)
            
    except ImportError as ie:
        print(f"❌ Analysis failed: Module not found - {ie}")
        print("   Try: pip install -e . --upgrade")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")


def handle_simulate(args):
    """Handle impact simulation"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    import os
    from tools.code_analyzer.analyzer import CodeAnalyzer
    from tools.code_analyzer.impact_analyzer import ImpactAnalyzer
    from pathlib import Path
    
    console = Console()
    console.print(f"\n🧪 [bold cyan]Simulating impact of changing:[/bold cyan] {args.function} in {args.file}\n")
    
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        # We need a CodeAnalyzer just to get the DB connection easily.
        repo_path = Path.cwd()
        session_id = "simulation"
        
        analyzer = CodeAnalyzer(session_id, repo_path)
        analyzer.connect_db(neo4j_uri, (neo4j_user, neo4j_password))
        
        impact_analyzer = ImpactAnalyzer(analyzer.neo4j_adapter.driver)
        
        # Run analysis - search by function name
        # TODO: Use args.file to filter more precisely if needed
        report = impact_analyzer.analyze_function_change(args.function, change_type="signature")
        
        # Log to findings.md using current session
        analyzer.session.log_finding(
            title=f"Impact Simulation: {args.function}",
            description=f"Risk Score: {report['risk_score']}\nReasoning: {report['reasoning']}\nAffected files: {report['affected_files']}",
            severity="HIGH" if report['risk_score'] > 70 else ("MEDIUM" if report['risk_score'] > 30 else "LOW")
        )
        
        # Display Results
        risk_color = "green"
        if report['risk_score'] > 30: risk_color = "yellow"
        if report['risk_score'] > 70: risk_color = "red"
        
        console.print(Panel(
            f"Risk Score: [bold {risk_color}]{report['risk_score']}/100[/bold {risk_color}]\n"
            f"Direct Dependents: {len(report['direct_callers'])}\n"
            f"Affected Files: {len(report['affected_files'])}",
            title="Impact Summary",
            expand=False
        ))
        
        if report['direct_callers']:
            tree = Tree(f"[bold]Direct Callers ({len(report['direct_callers'])})[/bold]")
            for caller in report['direct_callers']:
                tree.add(f"[cyan]{caller['name']}[/cyan] in [dim]{caller['file']}[/dim]")
                
            console.print(tree)
            
        analyzer.neo4j_adapter.driver.close()
        
    except Exception as e:
        console.print(f"[bold red]❌ Simulation Failed:[/bold red] {str(e)}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def handle_visualize(args):
    """Handle visualization generation"""
    from tools.code_analyzer.visualizer import CodeVisualizer
    from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
    from rich.console import Console
    from pathlib import Path
    
    console = Console()
    console.print(f"[bold cyan]📊 Generating visualization for: {args.path}[/bold cyan]")
    
    repo_path = Path(args.path).resolve()
    
    # Optional: Connect to Neo4j if call-graph
    neo4j_adapter = None
    if args.type == 'call-graph':
        try:
            neo4j_adapter = Neo4jAdapter("bolt://localhost:7687", ("neo4j", "password"))
        except Exception:
            console.print("[yellow]Warning: Could not connect to Neo4j.[/yellow]")

    try:
        visualizer = CodeVisualizer(repo_path, neo4j_adapter)
        
        if args.type == 'call-graph':
            if not args.function:
                console.print("[red]Error: --function required for call-graph type[/red]")
                return
            mermaid_code = visualizer.generate_call_graph(args.function)
        else:
            mermaid_code = visualizer.generate_mermaid_class_diagram()
        
        output_path = repo_path / args.output
        
        content = f"# Codebase Structure ({args.type})\n\nGenerated by DevMind Deep Analysis.\n\n```mermaid\n{mermaid_code}\n```\n"
        
        output_path.write_text(content)
        console.print(f"[bold green]✅ Visualization saved to:[/bold green] {output_path}")
        
    except Exception as e:
        console.print(f"[bold red]❌ Visualization Failed:[/bold red] {str(e)}")
    finally:
        if neo4j_adapter:
            neo4j_adapter.close()


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
    """Handle shell command explanation or file analysis"""
    import sys
    from pathlib import Path
    
    # Check if file mode
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ File not found: {args.file}")
            return
        
        # Read file content
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return
        
        print(f"\n📖 Analyzing file: {args.file}\n")
        
        try:
            from agents.agent_base import create_llm
            from utils.prompts import FILE_ANALYZER_PROMPT
            
            llm = create_llm()
            
            # Use file analyzer prompt template
            prompt_input = {
                "file_name": args.file,
                "file_content": content
            }
            
            response = llm.invoke(FILE_ANALYZER_PROMPT.format(**prompt_input))
            format_response(response, title=f"📖 File Analysis: {args.file}")
            
        except ImportError:
            print("⚠️  AI features not available. Install required dependencies.")
        except Exception as e:
            print(f"❌ Error: {e}")
        return
    
    # Command explanation mode (existing logic)
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

