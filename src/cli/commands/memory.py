"""
Yaver Memory Commands
Manage chat sessions and context.
"""
import typer
from ..ui import console, print_title, print_success, print_error, create_table

app = typer.Typer(help="Manage chat sessions and context")


@app.command(name="list")
def list_sessions():
    """List all chat sessions."""
    from core.session_manager import get_session_manager

    mgr = get_session_manager()
    sessions = mgr.list_sessions()

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    table = create_table(["ID", "Name", "Tags", "Created"], "Chat Sessions")
    for s in sessions:
        table.add_row(
            s["id"][:8],
            s.get("name", "-"),
            ", ".join(s.get("tags", [])) or "-",
            s["created_at"][:10],
        )
    console.print(table)


@app.command()
def new(
    name: str = typer.Option(None, "--name", "-n", help="Session name"),
    tags: list[str] = typer.Option(None, "--tag", "-t", help="Tags"),
):
    """Create a new chat session."""
    from core.session_manager import get_session_manager

    mgr = get_session_manager()
    sid = mgr.create_session(name=name, tags=tags or [])
    print_success(f"Created session: {sid}")


@app.command()
def switch(
    session_id: str = typer.Argument(..., help="Session ID to switch to"),
):
    """Switch active session."""
    from core.session_manager import get_session_manager

    mgr = get_session_manager()
    if mgr.set_active_session(session_id):
        print_success(f"Switched to session: {session_id}")
    else:
        print_error(f"Session not found: {session_id}")


@app.command()
def delete(
    session_id: str = typer.Argument(..., help="Session ID to delete"),
):
    """Delete a chat session."""
    from core.session_manager import get_session_manager

    mgr = get_session_manager()
    mgr.delete_session(session_id)
    print_success(f"Deleted session: {session_id}")
