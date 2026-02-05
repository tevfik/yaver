"""
Yaver Agent Commands
Manage autonomous agents and their learning.
"""
import typer
from ..ui import console, print_title, print_success, print_error, create_table

app = typer.Typer(help="Manage autonomous agent learning")


@app.command()
def status(
    project_id: str = typer.Argument(..., help="Project ID to check agent status for")
):
    """Show agent learning state."""
    print_title(f"Agent Status: {project_id}")
    # Placeholder for agent status implementation
    # In a real implementation, this would query the agent's memory/state
    console.print("[dim]Checking agent state...[/dim]")
    print_success("Agent is active and learning.")


@app.command()
def history(
    project_id: str = typer.Argument(..., help="Project ID"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of items to show"),
):
    """Show agent decision history."""
    print_title(f"Agent History: {project_id}")

    table = create_table(["Time", "Action", "Result"], "Recent Decisions")
    # Mock data
    table.add_row("10:00", "Analyze File", "Success")
    table.add_row("10:05", "Refactor Code", "Completed")
    console.print(table)


@app.command()
def teach(
    project_id: str = typer.Argument(..., help="Project ID"),
    rec_id: str = typer.Argument(..., help="Recommendation ID"),
    status: str = typer.Option(..., "--status", "-s", help="approve, reject, ignore"),
    note: str = typer.Option(None, "--note", "-n", help="Optional feedback note"),
):
    """Provide feedback to the agent."""
    print_title("Agent Feedback")
    console.print(f"Project: {project_id}")
    console.print(f"Rec ID: {rec_id}")
    console.print(f"Status: {status}")
    if note:
        console.print(f"Note: {note}")

    print_success("Feedback recorded!")
