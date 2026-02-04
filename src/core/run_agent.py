"""
Simple Agent Runner - Orchestrates Coder and Reviewer for consistent results
"""
import sys
import logging
import argparse
from typing import Dict, Any
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

import logging
from engine import AgentEngine

logger = logging.getLogger(__name__)


def print_section_header(title: str, emoji: str = ""):
    """Print section header"""
    console.print(f"\n[bold {emoji}]{emoji} {title}[/bold]")


class GitOps:
    """Placeholder for git operations"""

    pass


console = Console()
logger = setup_logger()


def run_coding_task(
    task_description: str, output_file: str = None, use_git: bool = False
):
    """
    Runs the Agent Engine and handles CLI presentation/Git ops.
    """
    git_ops = GitOps() if use_git else None

    # Callback to update the fancy CLI UI
    def cli_handler(event):
        if event.status == "success":
            style = "green"
        elif event.status == "warning":
            style = "yellow"
        elif event.status == "error":
            style = "red"
        else:
            style = "white"

        console.print(f"[{style}]➜ {event.step}: {event.message}[/{style}]")

        if event.data:
            if "plan" in event.data:
                console.print(
                    Panel(
                        Markdown(event.data["plan"]),
                        title="Architect's Plan",
                        border_style="blue",
                    )
                )
            if "code" in event.data:
                console.print(Markdown(event.data["code"]))
            if "review" in event.data:
                console.print(Markdown(event.data["review"]))
            if "output" in event.data:
                console.print(f"[dim]{str(event.data['output'])[:200]}...[/dim]")

    # Run Engine
    print_section_header("Yaver AI Engine Starting", "🚀")
    engine = AgentEngine(use_sandbox=True)
    result = engine.run(task_description, on_event=cli_handler)

    # Process Result (Handle both single string and dictionary task results)
    final_content = ""

    if isinstance(result, str):
        final_content = result
    elif isinstance(result, dict):
        console.print("\n[bold]Execution Summary:[/bold]")

        # Check if 'main' is the only key (fallback)
        if "main" in result and len(result) == 1:
            final_content = result["main"].get("code", "")
        else:
            # Concatenate results for output (or just show them)
            for task_id, task_data in result.items():
                code = task_data.get("code", "")
                status = task_data.get("status", "unknown")
                desc = task_data.get("description", "No description")

                console.print(f"- [cyan]{task_id}[/cyan]: {desc} ([{status}])")

                if code:
                    final_content += f"\n\n# --- Task: {desc} ---\n{code}"

    # Save output
    if output_file and final_content:
        try:
            # simple cleanup - try to extract code if it looks like markdown
            import re

            # If we have multiple blocks, we might want to keep the headers
            if isinstance(result, str):
                code_blocks = re.findall(
                    r"```(?:\w+)?\n(.*?)```", final_content, re.DOTALL
                )
                if code_blocks:
                    content_to_save = code_blocks[0]  # Assume one file for simple mode
                else:
                    content_to_save = final_content
            else:
                content_to_save = final_content  # Save concatenated for now

            with open(output_file, "w") as f:
                f.write(content_to_save)
            console.print(f"\n[green]✅ Output saved to {output_file}[/green]")

            # Git Integration
            if use_git and git_ops:
                print_section_header("Step 5: Git Integration", "🐙")
                branch = git_ops.create_pr_branch(task_description)
                if branch:
                    git_ops.commit_changes(
                        output_file,
                        f"feat: {task_description[:50]}...\n\nImplemented by Yaver AI Agent.",
                    )
                    console.print(
                        f"[bold green]✅ Changes committed to branch '{branch}'[/bold green]"
                    )
                    console.print("Ready for Pull Request.")

        except Exception as e:
            console.print(f"[red]❌ Failed to save file: {e}[/red]")
    elif not output_file:
        console.print("\n[dim]No output file specified, results shown in log.[/dim]")


def main():
    parser = argparse.ArgumentParser(description="Yaver Simple Runner")
    parser.add_argument("task", help="Description of the coding task")
    parser.add_argument("--output", "-o", help="File to save the output code to")
    parser.add_argument(
        "--git", action="store_true", help="Commit changes to a new git branch"
    )

    args = parser.parse_args()

    try:
        run_coding_task(args.task, args.output, args.git)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.exception("Fatal error in run_agent")


if __name__ == "__main__":
    main()
