"""
Yaver Code Commands
Code analysis, visualization, and querying tools.
"""
import typer
import os
import time
from pathlib import Path
from ..ui import (
    console,
    print_title,
    print_success,
    print_error,
    print_info,
    create_table,
)

app = typer.Typer(help="Code analysis and intelligence tools")


@app.command()
def analyze(
    path: str = typer.Argument(".", help="Path to repository"),
    type: str = typer.Option(
        "overview", "--type", "-t", help="Analysis type: overview, deep, structure"
    ),
    incremental: bool = typer.Option(
        False, "--incremental", "-i", help="Only analyze changed files"
    ),
    project_id: str = typer.Option(
        None, "--project-id", "-p", help="Project ID for storage"
    ),
):
    """Analyze repository structure and code."""
    print_title(f"Analyzing: {path}", f"Type: {type}")

    try:
        if type == "deep":
            _run_deep_analysis(path, incremental, project_id)
            return

        # Basic Git Analysis
        from tools.git.client import GitClient

        analyzer = GitClient(path)
        status = analyzer.get_status()

        if status.get("error"):
            print_error(status["error"])
            return

        table = create_table(["Metric", "Value"], "Repository Overview")
        is_dirty = not status.get("is_clean", True)

        table.add_row("Status", "🔴 Dirty" if is_dirty else "✅ Clean")
        table.add_row("Branch", status.get("active_branch", "Unknown"))
        table.add_row("Files (Changed)", str(len(status.get("changed_files", []))))
        table.add_row("Staged", str(len(status.get("staged_files", []))))

        console.print(table)

    except Exception as e:
        print_error(f"Analysis failed: {e}")


def _run_deep_analysis(path: str, incremental: bool, project_id: str):
    """Run deep semantic analysis."""
    from tools.code_analyzer.analyzer import CodeAnalyzer
    import uuid

    session_id = project_id or f"cli_{uuid.uuid4().hex[:8]}"
    repo_path = Path(path)

    console.print(f"[dim]Session ID: {session_id}[/dim]")

    try:
        analyzer = CodeAnalyzer(session_id, repo_path)

        # Init Graph DB
        try:
            analyzer.init_graph_db()
            print_info("Connected to graph database")
        except Exception as e:
            print_error(f"Could not initialize graph database: {e}")
            print_info("Analysis will continue without graph storage")

        start_time = time.time()

        with console.status("[bold green]Running deep analysis...[/bold green]"):
            analyzer.analyze_repository(incremental=incremental, use_semantic=True)

            console.print("[dim]Extracting semantic facts...[/dim]")
            analyzer.extract_semantic_facts()

        duration = time.time() - start_time
        print_success(f"Analysis Complete ({duration:.2f}s)")

    except Exception as e:
        print_error(f"Deep analysis failed: {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")


@app.command()
def query(
    q: str = typer.Argument(..., help="Query string"),
    limit: int = typer.Option(5, "--limit", "-l", help="Max results"),
):
    """Semantic search in codebase."""
    # Placeholder for query logic
    print_info(f"Searching for: {q}")
