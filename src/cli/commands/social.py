"""
Yaver Social Developer Commands
Autonomous agent for monitoring and responding to GitHub/Gitea issues and PRs.
"""
import typer
from ..ui import (
    console,
    print_section_header,
    print_success,
    print_error,
)

app = typer.Typer(help="Social developer agent for autonomous issue/PR handling")


@app.command()
def run(
    repo: str = typer.Option(
        None, "--repo", "-r", help="Specific repository to monitor (owner/repo)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    daemon: bool = typer.Option(
        False, "--daemon", "-d", help="Run as daemon (continuous monitoring)"
    ),
    interval: int = typer.Option(
        300, "--interval", "-i", help="Daemon check interval in seconds"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force run on issues even if they are marked as in-progress",
    ),
):
    """Run the social developer agent to monitor and handle issues/PRs."""
    from agents.agent_task_manager import social_developer_node
    from agents.agent_base import YaverState
    import time
    import os

    if force:
        os.environ["YAVER_FORCE_RUN"] = "1"

    print_section_header("Social Developer Agent", "👥")

    if repo:
        console.print(f"[dim]Monitoring repository: {repo}[/dim]")
    else:
        console.print("[dim]Monitoring all assigned issues and PRs[/dim]")

    def run_once():
        """Execute one iteration of the social developer agent."""
        try:
            state = YaverState(
                log=[],
                errors=[],
                user_request="",
            )

            updated_state = social_developer_node(state)

            if updated_state.get("errors"):
                for error in updated_state["errors"]:
                    print_error(f"Error: {error}")
            else:
                print_success("Social developer agent completed successfully")

            return True

        except Exception as e:
            print_error(f"Agent execution failed: {e}")
            if verbose:
                import traceback

                console.print(traceback.format_exc())
            return False

    if daemon:
        console.print(
            f"[yellow]Running in daemon mode (checking every {interval}s)[/yellow]"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        try:
            while True:
                run_once()
                console.print(f"\n[dim]Waiting {interval}s until next check...[/dim]")
                time.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Daemon stopped by user[/yellow]")
    else:
        run_once()


@app.callback()
def callback():
    """
    Social Developer Agent - Autonomous issue and PR handler.

    Monitors assigned issues and open PRs, automatically creates branches,
    writes code, commits changes, and responds to feedback.
    """
    pass
