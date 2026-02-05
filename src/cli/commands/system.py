"""
Yaver System Commands
Manage setup, status, and infrastructure.
"""
import typer
from ..ui import (
    console,
    print_title,
    print_success,
    print_error,
    print_info,
    create_table,
)

app = typer.Typer(help="System and infrastructure management")


@app.command()
def setup(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="Use defaults without prompting"
    )
):
    """Run the interactive setup wizard."""
    from config.onboarding import YaverSetupWizard

    print_title("System Setup", "Configure Yaver Environment")

    wizard = YaverSetupWizard()

    if non_interactive:
        # Default config for CI/CD
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
        print_success("Setup complete (non-interactive mode)!")
    else:
        wizard.run()
        print_success("Setup complete!")


@app.command()
def status():
    """Show system health and configuration status."""
    from config.config import get_config

    print_title("System Status")

    try:
        config = get_config()
        if config:
            table = create_table(["Component", "Status", "Details"])

            # Check components (mock check for display)
            table.add_row("Configuration", "✅ Loaded", "Found valid config")
            table.add_row("Ollama", "ℹ️  Configured", f"{config.ollama.base_url}")
            table.add_row("Vector DB", "ℹ️  Configured", config.vector_db.provider)
            table.add_row("Graph DB", "ℹ️  Configured", config.graph_db.provider)

            console.print(table)
        else:
            print_error("No configuration found. Run 'yaver system setup' first.")

    except Exception as e:
        print_error(f"Failed to check status: {e}")


# Docker Sub-app
docker_app = typer.Typer(help="Manage Docker services")
app.add_typer(docker_app, name="docker")


@docker_app.command("status")
def docker_status():
    """Check Docker services status."""
    from cli.docker_manager import DockerManager

    manager = DockerManager()
    manager.print_status()


@docker_app.command("start")
def docker_start():
    """Start Docker services."""
    from cli.docker_manager import DockerManager

    manager = DockerManager()
    success, msg = manager.start_services()
    if success:
        print_success(msg)
        manager.print_status()
    else:
        print_error(msg)


@docker_app.command("stop")
def docker_stop():
    """Stop Docker services."""
    from cli.docker_manager import DockerManager

    manager = DockerManager()
    success, msg = manager.stop_services()
    if success:
        print_success(msg)
    else:
        print_error(msg)
