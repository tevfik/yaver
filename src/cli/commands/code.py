import typer
import os
import time
from pathlib import Path
from enum import Enum
from typing import List
from ..ui import (
    console,
    print_title,
    print_success,
    print_error,
    print_info,
    create_table,
)

app = typer.Typer(help="Code analysis and intelligence tools")


class AnalysisType(str, Enum):
    overview = "overview"
    deep = "deep"
    structure = "structure"


def complete_path(ctx: typer.Context, incomplete: str) -> List[str]:
    """Autocomplete for directories."""
    path = Path(incomplete)
    if not path.exists() or not path.is_dir():
        # If incomplete is empty or not a dir, start from current dir
        base_dir = Path(".")
    else:
        base_dir = path

    # If user typed part of a name (e.g., "src/to"), we need "src/" as base
    # and "to" as pattern.
    # Typer/Click logic is a bit raw here, keeping it simple:
    # Just list directories in the current working directory or partial match

    # Simple approach: standard shell expansion logic is hard to replicate perfectly
    # without os-specifics, but basic directory completion:
    return [str(p) for p in Path(".").glob(f"{incomplete}*") if p.is_dir()]


@app.command()
def analyze(
    path: str = typer.Argument(
        ".", help="Path to repository", autocompletion=complete_path
    ),
    type: AnalysisType = typer.Option(
        AnalysisType.overview,
        "--type",
        "-t",
        help="Analysis type",
        case_sensitive=False,
    ),
    incremental: bool = typer.Option(
        False, "--incremental", "-i", help="Only analyze changed files"
    ),
    project_id: str = typer.Option(
        None, "--project-id", "-p", help="Project ID for storage"
    ),
):
    """Analyze repository structure and code."""
    print_title(f"Analyzing: {path}", f"Type: {type.value}")

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
        total_files = len(analyzer.list_files())

        table.add_row("Status", "🔴 Dirty" if is_dirty else "✅ Clean")
        table.add_row("Branch", status.get("active_branch", "Unknown"))
        table.add_row("Files (Total)", str(total_files))
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
def architect(
    path: str = typer.Argument(
        ".", help="Path to repository", autocompletion=complete_path
    ),
    output: str = typer.Option("report.md", "--output", "-o", help="Output filename"),
):
    """Generate a detailed architecture report."""
    print_title(f"Architecting: {path}", f"Output: {output}")

    from tools.code_analyzer.analyzer import CodeAnalyzer
    from agents.agent_git_analyzer import git_analyzer_node
    from agents.agent_base import YaverState

    repo_path = Path(path).resolve()

    try:
        with console.status("[bold green]Analyzing repository...[/bold green]"):
            analyzer = CodeAnalyzer(session_id="cli_architect", repo_path=repo_path)
            # Perform deep analysis if not already done (simplified for CLI)
            analyzer.analyze_repository(incremental=True, use_semantic=False)
            repo_info = analyzer.analyze_structure()

            state = YaverState(
                repo_path=str(repo_path),
                repo_info=repo_info,
                user_request="Generate a detailed architecture report.",
            )

            # Run the specialized Git Analyzer Agent
            results = git_analyzer_node(state)

            arch_analysis = results.get("architecture_analysis")
            if arch_analysis and arch_analysis.documentation:
                report_content = arch_analysis.documentation

                # Prepend some metadata
                full_report = f"# Architecture Report: {repo_path.name}\n\n"
                full_report += (
                    f"- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                full_report += (
                    f"- **Files Analyzed**: {len(results.get('file_analyses', []))}\n"
                )
                full_report += f"- **Quality Score**: {results.get('code_quality_score', 'N/A')}\n\n"
                full_report += report_content

                with open(output, "w", encoding="utf-8") as f:
                    f.write(full_report)

                print_success(f"Report generated successfully: {output}")
            else:
                print_error("Failed to generate architecture documentation.")

    except Exception as e:
        print_error(f"Architecture analysis failed: {e}")
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
