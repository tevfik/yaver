import typer
import logging
import os
import sys
from rich.console import Console
from tools.forge.tool import ForgeTool

app = typer.Typer(help="Verification and Testing Commands")
console = Console()
logger = logging.getLogger("yaver")


@app.command("social-live")
def verify_social_live(
    repo_path: str = typer.Option(
        os.path.expanduser("~/nextcloud/WORKSPACE/git_github/tevfik/yaver_test"),
        help="Path to the test repository",
    ),
    create_issue: bool = typer.Option(True, help="Create a fresh test issue to solve"),
):
    """
    Verify Social Developer Flow (Live).
    1. Connects to test repo.
    2. Creates a test issue (optional).
    3. Triggers the social developer agent loop.
    """
    from agents.agent_task_manager import social_developer_node, YaverState

    console.print(f"[bold blue]🔬 Starting Social Developer Verification...[/bold blue]")

    if not os.path.exists(repo_path):
        console.print(f"[bold red]❌ Test repo not found at {repo_path}[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"Using test repo at: {repo_path}")

    # Initialize Tool
    try:
        forge_tool = ForgeTool(repo_path=repo_path)
        if not forge_tool.provider:
            console.print(
                "[bold red]❌ Failed to initialize Forge provider. Check config/credentials.[/bold red]"
            )
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]❌ Initialization error: {e}[/bold red]")
        raise typer.Exit(code=1)

    # Create Issue
    if create_issue:
        console.print("📝 Creating test issue...")
        issue_title = "Social Dev Test: Verify CLI Integration"
        issue_body = "Automated test triggered by 'yaver verify social-live'. Please resolve this."
        try:
            issue = forge_tool.run("create_issue", title=issue_title, body=issue_body)
            if isinstance(issue, dict) and "number" in issue:
                console.print(
                    f"[green]✅ Created issue #{issue['number']}: {issue['title']}[/green]"
                )
            else:
                console.print(
                    f"[yellow]⚠️  Issue creation response ambiguous: {issue}[/yellow]"
                )
        except Exception as e:
            console.print(f"[red]❌ Error creating issue: {e}[/red]")
            # Continue anyway

    # Run Agent
    console.print("\n[bold purple]🤖 Running Social Developer Node...[/bold purple]")
    state = {"user_request": "", "log": [], "errors": []}

    try:
        # We need to ensure the agent looks at our specific repo if possible,
        # but social_developer_node is designed to loop over ALL assignments.
        # This acts as a true integration test of the "monitoring" capability.
        updated_state = social_developer_node(state)

        console.print("\n[bold]Execution Log:[/bold]")
        for entry in updated_state.get("log", []):
            console.print(f" - {entry}")

    except Exception as e:
        console.print(f"[bold red]❌ Agent execution failed: {e}[/bold red]")
        raise typer.Exit(code=1)


@app.command("social-clean")
def verify_social_clean(
    sandbox_dir: str = typer.Option(
        os.path.expanduser("~/.yaver/sandbox"), help="Sandbox directory for clean test"
    ),
    repo_url: str = typer.Option(
        "https://git.bezg.in/tevfik/yaver_test.git", help="Git repository URL to clone"
    ),
):
    """
    Verify Social Developer Flow (Clean Sandbox).
    1. Clones repo to sandbox.
    2. Runs agent in isolated environment.
    """
    import shutil
    import git
    from agents.agent_task_manager import social_developer_node, YaverState

    console.print(f"[bold blue]🧹 Setting up sandbox at {sandbox_dir}...[/bold blue]")
    if os.path.exists(sandbox_dir):
        shutil.rmtree(sandbox_dir)
    os.makedirs(sandbox_dir, exist_ok=True)

    local_repo_path = os.path.join(sandbox_dir, "yaver_test")

    console.print(f"📥 Cloning {repo_url}...")
    try:
        git.Repo.clone_from(repo_url, local_repo_path)
        console.print("[green]✅ Clone successful.[/green]")
    except Exception as e:
        console.print(f"[bold red]❌ Failed to clone: {e}[/bold red]")
        # Assuming credentials might be needed, but sticking to basic for now
        raise typer.Exit(code=1)

    console.print("\n[bold purple]🤖 Running Social Developer Node...[/bold purple]")

    # Switch CWD to sandbox so ForgeTool picks it up as current repo context if needed
    original_cwd = os.getcwd()
    os.chdir(local_repo_path)

    try:
        # Inject context for finding the repo
        state = {"log": [], "errors": []}

        # We invoke the node. It should detect the git repo in CWD via ForgeTool default behavior
        updated_state = social_developer_node(state)

        console.print("\n[bold]Execution Log:[/bold]")
        for entry in updated_state.get("log", []):
            console.print(f" - {entry}")

    except Exception as e:
        console.print(f"[bold red]❌ Agent execution failed: {e}[/bold red]")
    finally:
        os.chdir(original_cwd)
