#!/usr/bin/env python3
"""
Yaver AI - Command Line Interface
Full-featured CLI with all commands
"""

import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
        description="Yaver AI - Development Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  yaver setup              Run initial setup wizard
  yaver new myproject      Create a new Python project
  yaver new api --type fastapi  Create FastAPI project
  yaver docker status      Check Docker services
  yaver chat               Start interactive AI chat
  yaver analyze --type deep Deep learn repository (AST + embeddings)
  yaver commit             Generate commit message
  yaver explain "command"  Explain a shell command
  yaver --version          Show version
        """
    )
    
    # Version
    parser.add_argument(
        '--version',
        action='version',
        version='Yaver v1.1.0'
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
    # ========== SESSION MANAGEMENT (Chat History) ==========
    session_parser = subparsers.add_parser(
        'session',
        help='Manage Yaver chat sessions with tags'
    )
    session_subparsers = session_parser.add_subparsers(
        dest='session_action',
        help='Session action'
    )
    
    # session new [--name NAME] [--tag TAG [TAG ...]]
    session_new = session_subparsers.add_parser('new', help='Create new chat session')
    session_new.add_argument('--name', help='Session name')
    session_new.add_argument('--tag', nargs='*', help='Tags for session')
    
    # session list
    session_subparsers.add_parser('list', help='List all chat sessions')
    
    # session current
    session_subparsers.add_parser('current', help='Show active chat session')
    
    # session set <session_id>
    session_set = session_subparsers.add_parser('set', help='Switch to chat session')
    session_set.add_argument('session_id', help='Session ID to switch to')
    
    # session tag <session_id> <tag>
    session_tag = session_subparsers.add_parser('tag', help='Add tag to chat session')
    session_tag.add_argument('session_id', help='Session ID')
    session_tag.add_argument('tag', help='Tag to add')
    
    # session delete <session_id>
    session_delete = session_subparsers.add_parser('delete', help='Delete chat session')
    session_delete.add_argument('session_id', help='Session ID to delete')
    session_delete.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    # session show <session_id> - Show detailed session information
    session_show = session_subparsers.add_parser('show', help='Show detailed chat session information')
    session_show.add_argument('session_id', help='Session ID to show')
    
    session_parser.set_defaults(func=handle_session)
    
    # ========== PROJECT MANAGEMENT (Learning Sessions) ==========
    project_parser = subparsers.add_parser(
        'project',
        help='Manage Yaver projects (multi-repo learning)'
    )
    project_subparsers = project_parser.add_subparsers(
        dest='project_action',
        help='Project action'
    )
    
    # project list
    project_subparsers.add_parser('list', help='List all learned projects')
    
    # project show <project_id>
    project_show = project_subparsers.add_parser('show', help='Show project details')
    project_show.add_argument('project_id', help='Project ID to show')
    
    # project delete <project_id>
    project_delete = project_subparsers.add_parser('delete', help='Delete project')
    project_delete.add_argument('project_id', help='Project ID to delete')
    project_delete.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    # project history <project_id>
    project_history = project_subparsers.add_parser('history', help='Show analysis history for a project')
    project_history.add_argument('project_id', help='Project ID')
    project_history.add_argument('--limit', type=int, default=20, help='Number of records to show (default: 20)')
    
    # project cleanup <project_id>
    project_cleanup = project_subparsers.add_parser('cleanup', help='Clean old analyses for a project')
    project_cleanup.add_argument('project_id', help='Project ID')
    project_cleanup.add_argument('--keep-last', type=int, default=10, help='Keep last N analyses (default: 10)')
    project_cleanup.add_argument('--force', '-f', action='store_true', help='Skip confirmation')
    
    project_parser.set_defaults(func=handle_project)
    
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
    chat_parser.add_argument('--session-id', help='Use specific chat session for conversation history')
    chat_parser.add_argument('--project-id', help='Limit code context to specific project (learned repo)')
    chat_parser.set_defaults(func=handle_chat)
    
    # Analyze command - Repo analysis + Deep learning
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze repository (overview/deep learning with AST + embeddings)'
    )
    analyze_parser.add_argument('path', nargs='?', default='.', help='Path to repository (default: current dir)')
    analyze_parser.add_argument(
        '--type',
        choices=['overview', 'structure', 'impact', 'detailed', 'deep'],
        default='overview',
        help='Type of analysis'
    )
    analyze_parser.add_argument('--target', help='Target function/class for impact analysis')
    analyze_parser.add_argument('--incremental', action='store_true', help='Only analyze changed files')
    analyze_parser.add_argument('--project-id', help='Project ID for storage (deep mode)')
    analyze_parser.set_defaults(func=handle_analyze)

    # Agent command - Autonomous code quality agent
    agent_parser = subparsers.add_parser(
        'agent',
        help='Autonomous AI agent for code quality analysis'
    )
    agent_subparsers = agent_parser.add_subparsers(dest='agent_command', help='Agent subcommands')
    
    # Agent analyze subcommand
    agent_analyze_parser = agent_subparsers.add_parser(
        'analyze',
        help='Run autonomous analysis on a project'
    )
    agent_analyze_parser.add_argument('project_id', help='Project ID (learned repository)')
    agent_analyze_parser.add_argument('--format', choices=['table', 'json', 'chat'], default='table', help='Output format')
    agent_analyze_parser.set_defaults(func=handle_agent_analyze)
    
    # Agent status subcommand
    agent_status_parser = agent_subparsers.add_parser(
        'status',
        help='Show agent learning state'
    )
    agent_status_parser.add_argument('project_id', help='Project ID')
    agent_status_parser.set_defaults(func=handle_agent_status)
    
    # Agent history subcommand
    agent_history_parser = agent_subparsers.add_parser(
        'history',
        help='Show decision history and trends'
    )
    agent_history_parser.add_argument('project_id', help='Project ID')
    agent_history_parser.add_argument('--limit', type=int, default=10, help='Number of recent decisions to show')
    agent_history_parser.set_defaults(func=handle_agent_history)
    
    # Agent feedback subcommand
    agent_feedback_parser = agent_subparsers.add_parser(
        'feedback',
        help='Send feedback on recommendations'
    )
    agent_feedback_parser.add_argument('project_id', help='Project ID')
    agent_feedback_parser.add_argument('rec_id', help='Recommendation ID')
    agent_feedback_parser.add_argument('--status', choices=['approve', 'reject', 'ignore'], required=True, help='Feedback status')
    agent_feedback_parser.add_argument('--note', help='Optional note for feedback')
    agent_feedback_parser.set_defaults(func=handle_agent_feedback)

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
    from config.onboarding import YaverSetupWizard
    
    wizard = YaverSetupWizard()
    
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
            "CHROMA_PERSIST_DIR": ".yaver/chroma_db",
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
    """Handle chat session management commands (memory/history)"""
    from core.session_manager import get_session_manager
    from rich.table import Table
    
    session_mgr = get_session_manager()
    
    if not args.session_action:
        print("❌ Error: Please specify a session action")
        print("   Try: yaver session --help")
        return
    
    # New session
    if args.session_action == "new":
        tags = args.tag if args.tag else []
        session_id = session_mgr.create_session(name=args.name, tags=tags)
        print(f"\n✅ Created chat session: {session_id}")
        if args.name:
            print(f"   Name: {args.name}")
        if tags:
            print(f"   Tags: {', '.join(tags)}")
        print(f"   Active: ✓\n")
    
    # List sessions (memory sessions)
    elif args.session_action == "list":
        sessions = session_mgr.list_sessions()
        if not sessions:
            print("\n[yellow]No chat sessions found. Create one with:[/yellow]")
            print("[dim]  yaver session new --name=myproject[/dim]\n")
            return
        
        print(f"\n[bold cyan]💬 Chat Sessions[/bold cyan]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Tags", style="yellow")
        table.add_column("Created", style="dim")
        
        from rich.console import Console
        from rich.table import Table as RichTable
        console = Console()
        
        for session in sessions:
            table.add_row(
                session['id'][:8],
                session.get('name', '-'),
                ', '.join(session.get('tags', [])) or '-',
                session['created_at'][:10]
            )
        
        console.print(table)
        print()
    
    # Show current session
    elif args.session_action == "current":
        active = session_mgr.get_active_session()
        if not active:
            print("\n❌ No active chat session\n")
            return
        
        session = session_mgr.get_session(active)
        if session:
            print(f"\n🎯 Active Chat Session:")
            print(f"   ID: {session['id']}")
            print(f"   Name: {session['name']}")
            print(f"   Tags: {', '.join(session.get('tags', [])) or '-'}")
            print(f"   Created: {session['created_at'][:10]}")
            print(f"   Last used: {session['last_used'][:10]}\n")
    
    # Switch session
    elif args.session_action == "set":
        if session_mgr.set_active_session(args.session_id):
            session = session_mgr.get_session(args.session_id)
            print(f"\n✅ Switched to chat session: {session['name']}")
            print(f"   ID: {args.session_id}\n")
        else:
            print(f"\n❌ Chat session not found: {args.session_id}\n")
    
    # Add tag
    elif args.session_action == "tag":
        if session_mgr.add_tag(args.session_id, args.tag):
            session = session_mgr.get_session(args.session_id)
            print(f"\n✅ Added tag '{args.tag}' to chat session: {session['name']}")
            print(f"   Tags: {', '.join(session.get('tags', []))}\n")
        else:
            print(f"\n❌ Chat session not found: {args.session_id}\n")
    
    # Delete session
    elif args.session_action == "delete":
        session = session_mgr.get_session(args.session_id)
        if not session:
            print(f"\n❌ Chat session not found: {args.session_id}\n")
            return
        
        session_mgr.delete_session(args.session_id)
        print(f"\n✅ Deleted chat session: {session['name']}\n")
    
    # Show detailed session info
    elif args.session_action == "show":
        session = session_mgr.get_session(args.session_id)
        if not session:
            print(f"\n❌ Chat session not found: {args.session_id}\n")
            return
        
        print(f"\n[bold cyan]💬 Chat Session Details: {args.session_id}[/bold cyan]\n")
        print(f"[bold]ID:[/bold] {session['id']}")
        print(f"[bold]Name:[/bold] {session['name']}")
        print(f"[bold]Tags:[/bold] {', '.join(session.get('tags', [])) or '-'}")
        print(f"[bold]Created:[/bold] {session['created_at']}")
        print(f"[bold]Last used:[/bold] {session['last_used']}\n")


def handle_project(args):
    """Handle project management commands (learning sessions)"""
    if not args.project_action:
        print("❌ Error: Please specify a project action")
        print("   Try: yaver project --help")
        return
    
    # List projects
    if args.project_action == "list":
        handle_project_list(args)
    
    # Show project details
    elif args.project_action == "show":
        handle_project_show(args)
    
    # Delete project
    elif args.project_action == "delete":
        handle_project_delete(args)
    
    # Show analysis history
    elif args.project_action == "history":
        handle_project_history(args)
    
    # Cleanup old analyses
    elif args.project_action == "cleanup":
        handle_project_cleanup(args)


def handle_status(args):
    """Handle status command"""
    config = get_config()
    
    print("\n" + "="*60)
    print("Yaver System Status")
    print("="*60)
    
    if config:
        print("\n✅ Configuration found:")
        print(f"   Ollama: {config.get('OLLAMA_URL', 'not configured')}")
        print(f"   Qdrant: {config.get('QDRANT_URL', 'not configured')}")
        print(f"   Neo4j: {config.get('NEO4J_URI', 'not configured')}")
    else:
        print("\n⚠️  No configuration found. Run 'yaver setup' first.")
    
    print("\n" + "="*60)


def handle_chat(args):
    """Handle interactive AI chat"""
    project_id = getattr(args, 'project_id', None)
    session_id = getattr(args, 'session_id', None)
    
    if project_id and session_id:
        print(f"\n🤖 Yaver AI Chat - Project: {project_id}, Session: {session_id}")
    elif project_id:
        print(f"\n🤖 Yaver AI Chat - Project: {project_id}")
    elif session_id:
        print(f"\n🤖 Yaver AI Chat - Session: {session_id}")
    else:
        print("\n🤖 Yaver AI Chat (Type 'exit' to quit)")
    
    print("💡 Tip: Ask anything about your code, get AI assistance\n")
    
    agent = None
    try:
        from agents.agent_chat import ChatAgent
        import uuid
        
        chat_session_id = f"chat_{uuid.uuid4().hex[:8]}"
        agent = ChatAgent(
            session_id=chat_session_id,
            project_id=project_id
        )
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['exit', 'quit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Get AI response
                console.print("\n[cyan]Yaver:[/cyan]")
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
        from rich.console import Console
        import os
        
        console = Console()
        
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
            from pathlib import Path
            import time
            import uuid
            
            console.print(f"[bold cyan]🔍 Starting Deep Code Analysis...[/bold cyan]")
            
            # Create session ID (or use provided project_id)
            if hasattr(args, 'project_id') and args.project_id:
                session_id = args.project_id
                console.print(f"[dim]Using Project ID: {session_id}[/dim]")
            else:
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
                # Deep analysis includes semantic embeddings
                analyzer.analyze_repository(
                    incremental=getattr(args, 'incremental', False),
                    use_semantic=True  # Enable Qdrant embeddings for deep analysis
                )
                
                # Semantic fact extraction for knowledge graph
                console.print(f"[bold]🧠 Extracting Semantic Facts...[/bold]")
                analyzer.extract_semantic_facts()
                
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
        
        content = f"# Codebase Structure ({args.type})\n\nGenerated by Yaver Deep Analysis.\n\n```mermaid\n{mermaid_code}\n```\n"
        
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
        print(f"⚠️  Configuration error. Please run: yaver setup")
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
            print("❌ Error: No command provided. Usage: yaver explain <command>")
            return
    else:
        print("❌ Error: No command provided. Usage: yaver explain <command>")
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
            print("❌ Error: No prompt provided. Usage: yaver suggest <description>")
            return
    else:
        print("❌ Error: No prompt provided. Usage: yaver suggest <description>")
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
        print(f"⚠️  Configuration error. Please run: yaver setup")
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
        print("Usage: yaver new <project_name> [--type <type>]")
        print("\nExample:")
        print("  yaver new my_project")
        print("  yaver new api --type fastapi")
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
        print("  yaver new my_project")
        print("  yaver new my-project")
        print("  yaver new MyProject")
        print("  yaver new project_v2.0")
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
            print(f"   yaver chat  # Get AI help with your project\n")
            
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
            print(f"   yaver chat\n")
        
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

A Python project created with Yaver AI.

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

FastAPI application created with Yaver AI.

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
    (path / "README.md").write_text(f"# {name}\n\nFlask app created with Yaver AI.\n\n## Run\n\n```bash\npython run.py\n```\n")
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
    
    (path / "README.md").write_text(f"# {name}\n\nCLI tool created with Yaver AI.\n")
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

ML project created with Yaver AI.

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
    (path / "README.md").write_text(f"# {name}\n\nProject created with Yaver AI.\n")
    (path / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    
    print(f"   ✓ Created basic project structure")


def handle_project_list(args):
    """List all learned projects"""
    from rich.console import Console
    from rich.table import Table
    import os
    
    console = Console()
    
    # Neo4j Config
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
        adapter = Neo4jAdapter(neo4j_uri, (neo4j_user, neo4j_password))
        
        console.print("\n[bold cyan]📚 Learned Projects[/bold cyan]\n")
        
        with adapter.driver.session() as db_session:
            # Get all projects with their repositories
            result = db_session.run("""
                MATCH (n)
                WHERE n.session_id IS NOT NULL
                WITH n.session_id as project_id, collect(DISTINCT n.repo_id) as repos, 
                     max(n.last_analyzed) as last_used
                RETURN project_id, repos, last_used
                ORDER BY last_used DESC
            """)
            
            projects = list(result)
            
            if not projects:
                console.print("[yellow]No projects found. Create one with:[/yellow]")
                console.print("[dim]  yaver analyze --type deep <path> --project-id=<name>[/dim]\n")
                return
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Project ID", style="cyan", no_wrap=True)
            table.add_column("Repositories", style="green")
            table.add_column("Last Used", style="dim")
            
            for record in projects:
                project_id = record["project_id"]
                repos = [r for r in record["repos"] if r]  # Filter out None
                last_used = record["last_used"]
                
                # Format timestamp
                if last_used:
                    from datetime import datetime
                    last_used_dt = datetime.fromtimestamp(last_used / 1000)  # Neo4j timestamp is in milliseconds
                    last_used_str = last_used_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    last_used_str = "Unknown"
                
                repos_str = ", ".join(repos) if repos else "No repos"
                
                table.add_row(project_id, repos_str, last_used_str)
            
            console.print(table)
            console.print(f"\n[dim]💡 Use 'yaver project show <project-id>' for details[/dim]\n")
        
        adapter.close()
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()


def handle_project_show(args):
    """Show detailed information about a project"""
    from rich.console import Console
    from rich.table import Table
    import os
    
    console = Console()
    project_id = args.project_id
    
    # Neo4j Config
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
        adapter = Neo4jAdapter(neo4j_uri, (neo4j_user, neo4j_password))
        
        console.print(f"\n[bold cyan]📋 Project Details: {project_id}[/bold cyan]\n")
        
        with adapter.driver.session() as db_session:
            # Get repositories in this project
            repos_result = db_session.run("""
                MATCH (n {session_id: $project_id})
                RETURN DISTINCT n.repo_id as repo_id
                ORDER BY repo_id
            """, {"project_id": project_id})
            
            repos = [r["repo_id"] for r in repos_result if r["repo_id"]]
            
            if not repos:
                console.print(f"[yellow]Project '{project_id}' not found or has no data.[/yellow]\n")
                return
            
            console.print(f"[bold]Repositories ({len(repos)}):[/bold]")
            for repo in repos:
                console.print(f"  • {repo}")
            
            console.print(f"\n[bold]Statistics:[/bold]")
            
            # Get node counts by type for this project
            stats_result = db_session.run("""
                MATCH (n {session_id: $project_id})
                RETURN labels(n)[0] as type, count(n) as count
                ORDER BY type
            """, {"project_id": project_id})
            
            for record in stats_result:
                node_type = record["type"] or "Unknown"
                count = record["count"]
                console.print(f"  • {node_type}: {count}")
            
            # Per-repository breakdown
            console.print(f"\n[bold]Per-Repository Breakdown:[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Repository", style="cyan")
            table.add_column("Functions", justify="right", style="green")
            table.add_column("Classes", justify="right", style="blue")
            table.add_column("Files", justify="right", style="yellow")
            
            for repo in repos:
                counts_result = db_session.run("""
                    MATCH (n {session_id: $project_id, repo_id: $repo_id})
                    RETURN labels(n)[0] as type, count(n) as count
                """, {"project_id": project_id, "repo_id": repo})
                
                counts = {r["type"]: r["count"] for r in counts_result}
                
                table.add_row(
                    repo,
                    str(counts.get("Function", 0)),
                    str(counts.get("Class", 0)),
                    str(counts.get("File", 0))
                )
            
            console.print(table)
            console.print()
        
        adapter.close()
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()


def handle_project_delete(args):
    """Delete a project and all its learned data"""
    from rich.console import Console
    from rich.prompt import Confirm
    import os
    
    console = Console()
    project_id = args.project_id
    
    # Confirmation
    if not args.force:
        confirmed = Confirm.ask(
            f"[yellow]⚠️  Delete project '{project_id}' and all its learned data?[/yellow]",
            default=False
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            return
    
    # Neo4j Config
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
        adapter = Neo4jAdapter(neo4j_uri, (neo4j_user, neo4j_password))
        
        with adapter.driver.session() as db_session:
            # Count nodes to be deleted
            count_result = db_session.run("""
                MATCH (n {session_id: $project_id})
                RETURN count(n) as count
            """, {"project_id": project_id})
            
            node_count = count_result.single()["count"]
            
            if node_count == 0:
                console.print(f"[yellow]Project '{project_id}' not found or already empty.[/yellow]\n")
                return
            
            # Delete all nodes and relationships for this project
            db_session.run("""
                MATCH (n {session_id: $project_id})
                DETACH DELETE n
            """, {"project_id": project_id})
            
            console.print(f"\n[bold green]✅ Deleted project '{project_id}'[/bold green]")
            console.print(f"[dim]   Removed {node_count} nodes from Neo4j[/dim]")
        
        adapter.close()
        
        # Delete embeddings
        try:
            from config.config import MemoryConfig
            mem_config = MemoryConfig()
            
            if mem_config.memory_type == "leann":
                from tools.code_analyzer.leann_adapter import LeannAdapter
                # LeannAdapter uses session_id to determine storage path
                leann_adapter = LeannAdapter(session_id=project_id)
                leann_adapter.delete_collection()
                console.print(f"[dim]   Removed Leann index for project[/dim]\n")
            elif mem_config.memory_type == "chroma":
                from tools.code_analyzer.chroma_adapter import ChromaAdapter
                chroma_adapter = ChromaAdapter()
                chroma_adapter.delete_by_filter(filter_key="session_id", filter_value=project_id)
                console.print(f"[dim]   Removed embeddings from ChromaDB[/dim]\n")
            else:
                from tools.code_analyzer.qdrant_adapter import QdrantAdapter
                qdrant_adapter = QdrantAdapter()
                qdrant_adapter.delete_by_filter(filter_key="session_id", filter_value=project_id)
                console.print(f"[dim]   Removed embeddings from Qdrant[/dim]\n")
                
        except Exception as e:
            console.print(f"\n[dim]⚠️  Could not delete embeddings: {e}[/dim]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {str(e)}")
        import traceback
        traceback.print_exc()


def handle_project_history(args):
    """Show analysis history for a project"""
    from rich.console import Console
    from rich.table import Table
    from pathlib import Path
    
    console = Console()
    project_id = args.project_id
    limit = args.limit
    
    try:
        from core.project_history import ProjectHistoryManager
        
        history_mgr = ProjectHistoryManager()
        history = history_mgr.get_history(project_id, limit=limit)
        
        if not history:
            console.print(f"\n[yellow]No analysis history found for project '{project_id}'[/yellow]\n")
            return
        
        # Create table
        table = Table(title=f"📊 Analysis History: {project_id}", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim")
        table.add_column("Commit", style="cyan", no_wrap=True)
        table.add_column("Type", style="green")
        table.add_column("Files", style="yellow")
        table.add_column("Duration", style="magenta")
        table.add_column("Timestamp", style="dim")
        
        for i, record in enumerate(history, 1):
            commit_short = record['commit_hash'][:8] if record['commit_hash'] else "N/A"
            duration = f"{record['duration_seconds']:.1f}s" if record['duration_seconds'] else "N/A"
            
            table.add_row(
                str(i),
                commit_short,
                record['analysis_type'],
                str(record['files_analyzed'] or record['files_count'] or 0),
                duration,
                record['analysis_timestamp'][:10]
            )
        
        console.print(f"")
        console.print(table)
        console.print(f"\n[dim]Showing {len(history)} of {limit} records[/dim]\n")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}\n")
        import traceback
        traceback.print_exc()


def handle_project_cleanup(args):
    """Clean old analyses for a project"""
    from rich.console import Console
    from rich.prompt import Confirm
    
    console = Console()
    project_id = args.project_id
    keep_last = args.keep_last
    
    # Confirmation
    if not args.force:
        confirmed = Confirm.ask(
            f"[yellow]Keep last {keep_last} analyses for '{project_id}', delete older ones?[/yellow]",
            default=False
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            return
    
    try:
        from core.project_history import ProjectHistoryManager
        
        history_mgr = ProjectHistoryManager()
        deleted_count = history_mgr.cleanup_old_analyses(project_id, keep_last=keep_last)
        
        if deleted_count > 0:
            console.print(f"\n[bold green]✅ Cleanup Complete[/bold green]")
            console.print(f"[dim]   Deleted {deleted_count} old analyses for '{project_id}'[/dim]")
            console.print(f"[dim]   Kept last {keep_last} analyses[/dim]\n")
        else:
            console.print(f"\n[yellow]No old analyses to delete. Project has {keep_last} or fewer analyses.[/yellow]\n")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {str(e)}\n")
        import traceback
        traceback.print_exc()


# ========== AGENT HANDLERS ==========

def handle_agent_analyze(args):
    """Handle autonomous agent analysis"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from pathlib import Path
    import os
    
    console = Console()
    
    try:
        from agents.code_quality_agent import CodeQualityAgent
        from tools.metrics import MetricsAnalyzer
        from tools.code_analyzer.neo4j_adapter import Neo4jAdapter
        from agents.agent_base import create_llm
        
        console.print(f"\n[bold cyan]🤖 AUTONOMOUS AGENT ANALYSIS[/bold cyan]")
        console.print(f"[dim]Project: {args.project_id}[/dim]\n")
        
        # Find project path (using sessions storage)
        project_root = Path(os.path.expanduser("~/.yaver/sessions")) / args.project_id
        if not project_root.exists():
            # Fallback to projects for backward compatibility or if using different structure
            project_root_alt = Path(os.path.expanduser("~/.yaver/projects")) / args.project_id
            if project_root_alt.exists():
                project_root = project_root_alt
            else:
                console.print(f"[bold red]❌ Error:[/bold red] Project '{args.project_id}' not found in sessions")
                console.print(f"[dim]   Try: yaver analyze <repo> --type deep --project-id {args.project_id}[/dim]\n")
                return
        
        # Get original repo path from project metadata (if available)
        # For now, we'll use the project root itself
        repo_path = project_root
        
        # Initialize dependencies
        username = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        neo4j_adapter = Neo4jAdapter(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(username, password)
        )
        
        class AgentWrapper:
            def __init__(self):
                # Import here to avoid circular dependencies if any
                pass
                
            def query_llm(self, prompt, model_type="general"):
                # Lazy load LLM to avoid overhead if not needed immediately
                llm = create_llm(model_type)
                response = llm.invoke(prompt)
                return response.content

        agent_base = AgentWrapper()
        
        # Initialize agent
        agent = CodeQualityAgent(args.project_id, neo4j_adapter, agent_base)
        
        # Run analysis
        console.print(f"[dim]Observing changes and analyzing code...[/dim]")
        report = agent.analyze_repository()
        
        if not report:
            console.print(f"[yellow]No issues detected or analysis skipped.[/yellow]\n")
            return
        
        # Format output
        if args.format == 'json':
            import json
            console.print(json.dumps(report, indent=2))
        
        elif args.format == 'chat':
            # Friendly chat-like format
            console.print(f"\n[bold green]Analysis Results[/bold green]")
            
            issues = report.get('issues', [])
            if issues:
                console.print(f"\n[cyan]Found {len(issues)} issues:[/cyan]\n")
                for i, issue in enumerate(issues, 1):
                    priority = issue.get('priority', 5)
                    effort = issue.get('effort_hours', 0)
                    risk = issue.get('risk_level', 'unknown')
                    
                    icon = "🔴" if priority >= 8 else "🟠" if priority >= 5 else "🟡"
                    console.print(f"{icon} [{i}] {issue.get('type', 'Unknown')}")
                    console.print(f"    {issue.get('description', '')}")
                    console.print(f"    Priority: {priority}/10 | Effort: ~{effort}h | Risk: {risk}\n")
        
        else:  # table format (default)
            issues = report.get('issues', [])
            if not issues:
                console.print(f"[green]✅ No issues detected![/green]\n")
                return
            
            table = Table(title="Code Quality Issues", show_header=True, header_style="bold cyan")
            table.add_column("Priority", style="red", width=8)
            table.add_column("Type", style="cyan", width=15)
            table.add_column("Description", style="white")
            table.add_column("Effort", style="yellow", width=8)
            table.add_column("Risk", style="magenta", width=8)
            
            for issue in issues:
                priority = issue.get('priority', 5)
                priority_str = f"{priority}/10"
                issue_type = issue.get('type', 'Unknown')
                desc = issue.get('description', '')[:50]
                effort = f"{issue.get('effort_hours', 0)}h"
                risk = issue.get('risk_level', '?')
                
                table.add_row(priority_str, issue_type, desc, effort, risk)
            
            console.print(table)
        
        console.print(f"\n[dim]💡 Use 'yaver agent feedback <id> --status approve' to approve recommendations[/dim]\n")
        
    except ImportError as e:
        console.print(f"[bold red]❌ Agent not available:[/bold red] {e}\n")
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}\n")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


def handle_agent_status(args):
    """Show agent learning state"""
    from rich.console import Console
    from rich.panel import Panel
    from pathlib import Path
    import os
    import json
    
    console = Console()
    
    try:
        agent_state_path = Path(os.path.expanduser("~/.yaver/projects")) / args.project_id / "agent" / "state.json"
        
        if not agent_state_path.exists():
            console.print(f"\n[yellow]No agent state found for project '{args.project_id}'[/yellow]")
            console.print(f"[dim]   Try: yaver agent analyze {args.project_id}[/dim]\n")
            return
        
        with open(agent_state_path) as f:
            state = json.load(f)
        
        console.print(f"\n[bold cyan]🤖 AGENT STATE: {args.project_id}[/bold cyan]\n")
        
        approved = len(state.get('user_feedback', {}).get('approved', []))
        rejected = len(state.get('user_feedback', {}).get('rejected', []))
        
        info = f"""
[bold]Learning Progress:[/bold]
  • Decisions made: {len(state.get('decision_history', []))}
  • Recommendations approved: {approved}
  • Recommendations rejected: {rejected}
  • Last analysis: {state.get('last_analysis_timestamp', 'Never')}

[bold]Learned Preferences:[/bold]
"""
        for pref, value in state.get('learned_preferences', {}).items():
            info += f"  • {pref}: {value}\n"
        
        console.print(Panel(info, title="Agent State", border_style="cyan"))
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}\n")


def handle_agent_history(args):
    """Show decision history and trends"""
    from rich.console import Console
    from rich.table import Table
    from pathlib import Path
    import os
    import json
    
    console = Console()
    
    try:
        agent_state_path = Path(os.path.expanduser("~/.yaver/projects")) / args.project_id / "agent" / "state.json"
        
        if not agent_state_path.exists():
            console.print(f"\n[yellow]No history found for project '{args.project_id}'[/yellow]\n")
            return
        
        with open(agent_state_path) as f:
            state = json.load(f)
        
        history = state.get('decision_history', [])
        if not history:
            console.print(f"\n[dim]No decision history yet.[/dim]\n")
            return
        
        console.print(f"\n[bold cyan]📊 DECISION HISTORY: {args.project_id}[/bold cyan]\n")
        
        table = Table(title="Recent Decisions", show_header=True, header_style="bold cyan")
        table.add_column("Timestamp", style="dim", width=20)
        table.add_column("Issue Type", style="cyan")
        table.add_column("Action", style="green")
        table.add_column("Priority", style="red", width=8)
        
        for entry in history[-args.limit:]:
            timestamp = entry.get('timestamp', 'unknown')[:10]
            issue_type = entry.get('issue_type', 'Unknown')
            action = entry.get('action', 'none')
            priority = entry.get('priority', 5)
            
            table.add_row(timestamp, issue_type, action, f"{priority}/10")
        
        console.print(table)
        console.print(f"\n[dim]Showing last {args.limit} decisions[/dim]\n")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}\n")


def handle_agent_feedback(args):
    """Record user feedback on recommendations"""
    from rich.console import Console
    from pathlib import Path
    import os
    import json
    
    console = Console()
    
    try:
        agent_state_path = Path(os.path.expanduser("~/.yaver/projects")) / args.project_id / "agent" / "state.json"
        
        if not agent_state_path.exists():
            console.print(f"\n[bold red]❌ Error:[/bold red] Project state not found\n")
            return
        
        with open(agent_state_path) as f:
            state = json.load(f)
        
        # Record feedback
        feedback_category = args.status  # approve/reject/ignore
        if 'user_feedback' not in state:
            state['user_feedback'] = {'approved': [], 'rejected': [], 'ignored': []}
        
        if feedback_category not in state['user_feedback']:
            state['user_feedback'][feedback_category] = []
        
        feedback_entry = {
            'rec_id': args.rec_id,
            'status': args.status,
            'note': args.note or '',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }
        
        state['user_feedback'][feedback_category].append(feedback_entry)
        
        # Save updated state
        with open(agent_state_path, 'w') as f:
            json.dump(state, f, indent=2)
        
        console.print(f"\n[bold green]✅ Feedback recorded[/bold green]")
        console.print(f"[dim]   Recommendation {args.rec_id}: {args.status}[/dim]")
        if args.note:
            console.print(f"[dim]   Note: {args.note}[/dim]")
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}\n")


if __name__ == "__main__":
    main()

