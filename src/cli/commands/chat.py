"""
Yaver Chat Command
Interactive AI chat session.
"""
import typer
import uuid
from ..ui import console, print_title, print_error, format_panel

app = typer.Typer(help="Start interactive AI chat session")


@app.callback(invoke_without_command=True)
def chat(
    ctx: typer.Context,
    project_id: str = typer.Option(
        None, "--project-id", "-p", help="Project ID context"
    ),
    session_id: str = typer.Option(
        None, "--session-id", "-s", help="Existing session ID"
    ),
):
    """Start interactive AI chat session."""
    if ctx.invoked_subcommand is not None:
        return

    print_title("Yaver AI Chat", "Interactive Coding Assistant")

    if project_id:
        console.print(f"[dim]Context: Project {project_id}[/dim]")
    if session_id:
        console.print(f"[dim]Session: {session_id}[/dim]")

    console.print("\nType [bold red]exit[/bold red] to quit.\n")

    agent = None
    try:
        from agents.agent_chat import ChatAgent

        # Use existing session or create new one
        chat_session_id = session_id or f"chat_{uuid.uuid4().hex[:8]}"

        # Initialize agent
        with console.status("[bold green]Initializing AI agent...[/bold green]"):
            agent = ChatAgent(session_id=chat_session_id, project_id=project_id)

        # Chat Loop
        while True:
            try:
                user_input = typer.prompt("You")
                if user_input.lower() in ["exit", "quit", "bye"]:
                    console.print("\n👋 Goodbye!")
                    break

                # Get AI response
                console.print()
                with console.status(
                    "[bold cyan]Thinking...[/bold cyan]", spinner="dots"
                ):
                    response = agent.chat(user_input)

                # Format response
                content = (
                    str(response.content)
                    if hasattr(response, "content")
                    else str(response)
                )
                # Clean up newlines if needed
                content = content.replace("\\\\n", "\n")

                console.print(format_panel(content, title="Yaver", border_style="cyan"))
                console.print()

            except KeyboardInterrupt:
                console.print("\n\n👋 Chat interrupted.")
                break

    except ImportError as e:
        print_error(f"AI features not available: {e}")
    except Exception as e:
        print_error(f"An error occurred: {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        if agent:
            # agent.close() # If applicable
            pass
