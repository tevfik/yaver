"""
Yaver AI - Command Line Interface (Typer)

Entry point for the modern, modular CLI.
"""
import typer
from .ui import console, print_title
from .commands import chat, code, system, agent, memory, social, verify, solve

app = typer.Typer(
    name="yaver",
    help="Yaver AI - Your Autonomous Development Assistant",
    add_completion=True,
    rich_markup_mode="rich",
)

# Register sub-commands
app.add_typer(chat.app, name="chat")
app.add_typer(code.app, name="code")
app.add_typer(system.app, name="system")
app.add_typer(agent.app, name="agent")
app.add_typer(memory.app, name="memory")
app.add_typer(social.app, name="social")
app.add_typer(verify.app, name="verify")
app.add_typer(solve.app, name="solve")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", help="Show version", is_eager=True
    ),
):
    """
    [bold cyan]Yaver AI[/bold cyan] - Full-featured AI development assistant.

    Use [bold]yaver --help[/bold] to see available commands.
    """
    if version:
        console.print("[bold cyan]Yaver AI[/bold cyan] v1.2.0")
        raise typer.Exit()

    # If no command, show help
    if ctx.invoked_subcommand is None:
        print_title("Yaver AI", "Your Autonomous Development Assistant")
        console.print(
            "Use [bold green]yaver --help[/bold green] to see available commands."
        )


if __name__ == "__main__":
    app()
