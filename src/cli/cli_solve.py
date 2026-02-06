import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.markdown import Markdown
from pathlib import Path

from agents.agent_coder import CoderAgent
from agents.agent_planner import PlannerAgent
from agents.agent_reviewer import ReviewerAgent
from agents.git_ops import GitOps
from agents.cli_edit import extract_code_block

console = Console()


def handle_solve(args):
    """
    Handles the 'solve' command: Branch -> Plan -> Edit -> Review -> Commit -> Push -> PR
    """
    task = args.task
    file_path = args.file

    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' does not exist.")
        return

    # 1. Initialize GitOps
    git_ops = GitOps(os.getcwd())
    if not git_ops.repo:
        console.print("[bold red]Error:[/bold red] Not a git repository.")
        return

    console.print(
        Panel(
            f"[bold blue]Task:[/bold blue] {task}\n[bold blue]Target File:[/bold blue] {file_path}",
            title="Yaver Autonomous Agent",
        )
    )

    # 2. Create Branch
    with console.status(f"[bold green]Creating branch for task..."):
        branch_name = git_ops.create_pr_branch(task)
        if not branch_name:
            console.print("[bold red]Failed to create branch.[/bold red]")
            return
        console.print(f"[green]✔ Switched to branch: {branch_name}[/green]")

    # 2. Create Branch
    with console.status(f"[bold green]Creating branch for task..."):
        branch_name = git_ops.create_pr_branch(task)
        if not branch_name:
            console.print("[bold red]Failed to create branch.[/bold red]")
            return
        console.print(f"[green]✔ Switched to branch: {branch_name}[/green]")

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

    MAX_OUTER_LOOP = 3
    outer_loop_count = 0
    feedback_for_planner = ""
    success = False

    final_content = original_content
    final_plan = ""

    while outer_loop_count < MAX_OUTER_LOOP:
        outer_loop_count += 1
        console.print(
            f"\n[bold magenta]🚀 MAJOR ITERATION {outer_loop_count}/{MAX_OUTER_LOOP}[/bold magenta]"
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
                title=f"Execution Plan (Attempt {outer_loop_count})",
                border_style="cyan",
            )
        )

        if not Confirm.ask("\n[bold]Does this plan look good?[/bold]"):
            if Confirm.ask("Do you want to retry planning?"):
                feedback_for_planner += "\nUser rejected the previous plan. Please try a different approach."
                continue
            else:
                console.print("[red]Plan rejected. Aborting.[/red]")
                return

        # 4. PHASE 2: EXECUTION (CODING)
        console.print("\n[bold cyan]Phase 2: Execution...[/bold cyan]")
        with console.status("[bold yellow]AI is coding..."):
            # Pass the plan to the coder for better context
            coding_instructions = f"Task: {task}\n\nFollow this Plan:\n{plan}"
            # Always start from original content to avoid getting stuck in a local optimum of bad code
            result = coder_agent.edit_file_content(
                original_content, coding_instructions, file_path
            )
            # But wait, result might be a full file or just a block. extract_code_block handles it.
            new_content = extract_code_block(result)

        # 5. PHASE 3: REVIEW & REFINEMENT LOOP
        console.print("\n[bold cyan]Phase 3: Review & Refinement Loop...[/bold cyan]")

        if new_content == original_content:
            console.print(
                "[yellow]AI made no changes to the file. Skipping review.[/yellow]"
            )
            # If no changes, maybe the plan was bad?
            feedback_for_planner += (
                f"\nAttempt {outer_loop_count}: Coder made no changes to the file."
            )
            continue

        max_inner_retries = 3
        inner_try = 0
        feedbacks_history = []
        inner_success = False

        while inner_try < max_inner_retries:
            with console.status(
                f"[bold yellow]Reviewing code changes (Iteration {inner_try + 1}/{max_inner_retries})..."
            ):
                review_result = reviewer.review_code(new_content, task)

            console.print(
                Panel(
                    Markdown(review_result),
                    title=f"Code Review (Iter {outer_loop_count}.{inner_try+1})",
                    border_style="magenta",
                )
            )

            # Check pass conditions
            if "APPROVED" in review_result or "No issues found" in review_result:
                console.print("[bold green]✔ Code passed review.[/bold green]")
                inner_success = True
                break

            # If issues found, store feedback
            feedbacks_history.append(review_result)

            # If issues found, ask to fix
            inner_try += 1
            if inner_try >= max_inner_retries:
                console.print(
                    "[bold red]❌ Maximum review retries reached for this cycle.[/bold red]"
                )
                break

            if Confirm.ask(
                "[bold yellow]Issues found. Attempt auto-fix?[/bold yellow]"
            ):
                with console.status(
                    f"[bold yellow]Fixing code (Attempt {inner_try})..."
                ):
                    fix_result = coder_agent.fix_code(
                        new_content, review_result, feedbacks_history[:-1]
                    )
                    new_content = extract_code_block(fix_result)
                    console.print("[green]✔ Fix applied. Re-reviewing...[/green]")
            else:
                console.print("[yellow]Auto-fix skipped by user.[/yellow]")
                break

        if inner_success:
            final_content = new_content
            success = True
            break
        else:
            # Aggregate feedback for the next outer loop
            summary_feedback = "\n".join(
                [
                    f"Review Iteration {i+1}: {fb}"
                    for i, fb in enumerate(feedbacks_history)
                ]
            )
            feedback_for_planner += f"\n\nMajor Attempt {outer_loop_count} Failed. The code failed the review loop.\nSummary of failures:\n{summary_feedback}"
            if outer_loop_count < MAX_OUTER_LOOP:
                console.print(
                    "[bold yellow]Plan failed to produce valid code. Restarting with a new plan...[/bold yellow]"
                )

    if not success:
        console.print(
            Panel(
                "[bold red]All attempts failed to produce valid code.[/bold red]\nSee output for details.",
                title="Mission Failed",
                border_style="red",
            )
        )
        return

    # 6. Apply Changes
    console.print("\n[bold cyan]Phase 4: Finalization...[/bold cyan]")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        console.print(f"[green]✔ Applied changes to {file_path}[/green]")
    except Exception as e:
        console.print(f"[bold red]Error writing file:[/bold red] {e}")
        return

    # 7. Commit, Push, PR
    if Confirm.ask(
        f"\n[bold green]Proceed to Commit & Push '{branch_name}'?[/bold green]"
    ):
        commit_msg = f"fix: {task}"
        git_ops.commit_changes(file_path, commit_msg)

        if git_ops.push_changes(branch_name):
            console.print(f"[green]✔ Pushed to origin/{branch_name}[/green]")

            if Confirm.ask("[bold green]Create Pull Request now?[/bold green]"):
                with console.status("[bold green]Creating PR..."):
                    pr_url = git_ops.create_pull_request(
                        branch_name=branch_name,
                        title=f"Fix: {task}",
                        body=f"Automated PR by Yaver AI.\n\nTask: {task}\nFile: {file_path}\n\n## Final Plan\n{final_plan}",
                    )

                if pr_url:
                    console.print(
                        Panel(
                            f"[bold]PR Created Successfully![/bold]\n\n[link={pr_url}]{pr_url}[/link]",
                            title="🚀 Mission Complete",
                            border_style="green",
                        )
                    )
                else:
                    console.print(
                        "[bold red]Failed to create PR (Check GITHUB_TOKEN).[/bold red]"
                    )
        else:
            console.print("[bold red]Failed to push changes.[/bold red]")
    else:
        console.print("[yellow]Operation aborted. Changes are local only.[/yellow]")
