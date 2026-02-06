"""
Yaver Agent Commands
Manage autonomous agents and their learning.
"""
import typer
from pathlib import Path
from ..ui import (
    console,
    print_title,
    print_success,
    print_error,
    print_warning,
    create_table,
    print_section_header,
)
from config.config import get_config

app = typer.Typer(help="Manage autonomous agent learning")


@app.command()
def work(
    request: str = typer.Argument(..., help="Task description for the agent"),
    path: str = typer.Option(".", "--path", "-p", help="Repository path"),
    iterations: int = typer.Option(None, "--iterations", "-i", help="Max iterations"),
):
    """Execute a task autonomously."""
    from tools.code_analyzer.analyzer import CodeAnalyzer
    from agents.agent_base import YaverState, ConfigWrapper
    from agents.agent_task_manager import task_manager_node, run_iteration_cycle

    print_section_header("Autonomous Agent Worker", "🤖")
    console.print(f"\n[bold]Task:[/bold] {request}")

    repo_path = Path(path).resolve()
    console.print(f"[dim]Initializing context from {repo_path}...[/dim]")

    # 1. Analyze Repo
    analyzer = CodeAnalyzer(session_id="cli_work", repo_path=repo_path)
    repo_info_dict = analyzer.analyze_structure()
    # Wrap in ConfigWrapper for attribute access
    repo_info = ConfigWrapper(repo_info_dict)

    # 2. Init State
    state = YaverState(
        user_request=request,
        repo_path=str(repo_path),
        repo_info=repo_info,
        iteration_count=0,
        tasks=[],
        log=[],
        errors=[],
    )

    # 3. Initial Planning (Decomposition)
    console.print("\n[bold]🤔 Planning...[/bold]")
    state = task_manager_node(state)

    if state.get("errors"):
        for err in state["errors"]:
            print_error(err)
        return

    tasks = state.get("tasks", [])
    console.print(f"[green]✅ {len(tasks)} tasks created[/green]")

    # 4. Execution Loop
    console.print("\n[bold]⚙️  Executing...[/bold]")
    config = get_config()
    max_iters = iterations or config.task.max_iterations

    should_continue = True
    while should_continue and state.get("iteration_count", 0) < max_iters:
        state = run_iteration_cycle(state)
        should_continue = state.get("should_continue", False)

        # Check for immediate errors in state update
        if not should_continue and not any(
            t.status == "completed" for t in state.get("tasks", [])
        ):
            if state.get("errors"):
                for err in state["errors"]:
                    print_error(err)
                break

    # 5. Summary
    completed = [t for t in state.get("tasks", []) if t.status.value == "completed"]
    total = len(state.get("tasks", []))

    if completed:
        print_success(f"\n✅ Completed {len(completed)}/{total} tasks.")
    else:
        print_warning(f"\n⚠️  Completed {len(completed)}/{total} tasks.")
