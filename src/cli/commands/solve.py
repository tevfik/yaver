"""
Yaver Solve Command
Agentic workflow: Plan -> Code -> Review
"""
import typer
import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

app = typer.Typer(help="Agentic solver with Planning + Coding phases")
console = Console()


@app.command()
def file(
    task: str = typer.Argument(..., help="Modification description"),
    file_path: str = typer.Argument(..., help="Target file to modify"),
    iterations: int = typer.Option(3, help="Max retry iterations"),
):
    """
    Solve a coding task on a specific file using Plan -> Code -> Review loop.
    """
    # Lazy imports to prevent slow startup
    from agents.agent_coder import CoderAgent
    from agents.agent_planner import PlannerAgent
    from agents.agent_reviewer import ReviewerAgent
    from tools.git.ops import GitOps
    from cli.cli_edit import extract_code_block

    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' does not exist.")
        raise typer.Exit(code=1)

    # 1. Initialize GitOps
    try:
        git_ops = GitOps(os.getcwd())
        if not git_ops.repo:
            console.print(
                "[yellow]Warning:[/yellow] Not a git repository. Branching disabled."
            )
            git_ops = None
    except Exception:
        git_ops = None

    console.print(
        Panel(
            f"[bold blue]Task:[/bold blue] {task}\n[bold blue]Target File:[/bold blue] {file_path}",
            title="Yaver Solver",
        )
    )

    # 2. Create Branch
    if git_ops:
        with console.status(f"[bold green]Creating branch for task..."):
            branch_name = git_ops.create_pr_branch(task)
            if branch_name:
                console.print(f"[green]✔ Switched to branch: {branch_name}[/green]")
            else:
                console.print(
                    "[red]Failed to create branch, continuing on current branch.[/red]"
                )

    # Initialize Agents
    planner = PlannerAgent()
    coder_agent = CoderAgent()
    reviewer = ReviewerAgent()

    # Read original content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            original_content = f.read()
    except Exception as e:
        console.print(f"[bold red]Error reading file:[/bold red] {e}")
        return

    outer_loop_count = 0
    feedback_for_planner = ""

    final_content = original_content
    final_plan = ""
    success = False

    while outer_loop_count < iterations:
        outer_loop_count += 1
        console.print(
            f"\n[bold magenta]🚀 MAJOR ITERATION {outer_loop_count}/{iterations}[/bold magenta]"
        )

        # 3. PHASE 1: PLANNING
        console.print("\n[bold cyan]Phase 1: Planning...[/bold cyan]")
        with console.status("[bold yellow]Generating execution plan..."):
            plan_context = f"File to edit: {file_path}"
            if feedback_for_planner:
                plan_context += (
                    "\n\nCRITICAL CONTEXT - PREVIOUS FAILED PLANNING/CODING ATTEMPTS:\n"
                    + feedback_for_planner
                )

            plan = planner.create_plan(task, plan_context)
            final_plan = plan

        console.print(
            Panel(
                Markdown(plan),
                title="Implementation Plan",
                border_style="cyan",
            )
        )

        # In a real interactive CLI, we might ask for confirmation here.
        # confirm = typer.confirm("Proceed with this plan?")
        # if not confirm: raise typer.Abort()

        # 4. PHASE 2: CODING
        console.print("\n[bold cyan]Phase 2: Coding...[/bold cyan]")
        with console.status("[bold yellow]Writing code..."):
            instructions = f"Task: {task}\n\nImplementation Plan:\n{final_plan}"
            new_content = coder_agent.edit_file_content(
                file_content=original_content,
                instructions=instructions,
                file_path=file_path,
            )

        if not new_content or new_content.strip() == original_content.strip():
            console.print("[bold red]Coder agent produced no changes.[/bold red]")
            feedback_for_planner = "Coder agent did not produce any changes. The plan might be too vague or the file content too complex."
            continue

        # Extract useful code from potential markdown
        cleaned_content = extract_code_block(new_content)
        if not cleaned_content:
            # Fallback if extraction failed (maybe it wasn't valid markdown)
            cleaned_content = new_content

        # 5. PHASE 3: REVIEWING
        console.print("\n[bold cyan]Phase 3: Reviewing...[/bold cyan]")
        with console.status("[bold yellow]Reviewing changes..."):
            review_result = reviewer.review_code(
                code=cleaned_content, requirements=task, file_path=file_path
            )

        console.print(Markdown(review_result))

        if "APPROVED" in review_result:
            console.print("[bold green]✔ Changes Approved![/bold green]")
            final_content = cleaned_content
            success = True
            break
        else:
            console.print("[bold red]❌ Changes Rejected. Retrying...[/bold red]")
            feedback_for_planner = (
                f"Reviewer rejected the code. Feedback: {review_result}"
            )

    if success:
        # Save file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        console.print(
            f"[bold green]File {file_path} updated successfully![/bold green]"
        )

        # Git Commit
        if git_ops:
            git_ops.commit_changes(file_path, f"feat: {task}")
            console.print("[bold green]Changes committed.[/bold green]")
    else:
        console.print(
            "[bold red]Failed to solve the task after max retries.[/bold red]"
        )
