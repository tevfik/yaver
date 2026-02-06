import os
import sys
import difflib
import re
from rich.console import Console
from rich.syntax import Syntax
from rich.prompt import Confirm
from rich.panel import Panel
from pathlib import Path

from agents.agent_coder import CoderAgent
from agents.agent_base import setup_logger

console = Console()


def extract_code_block(text: str) -> str:
    """Extracts code from markdown code blocks"""
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def handle_edit(args):
    """
    Handles the interactive 'edit' command.
    """
    file_path = args.file
    instructions = args.request

    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' does not exist.")
        return

    with console.status(f"[bold green]Reading {file_path}..."):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
        except Exception as e:
            console.print(f"[bold red]Error reading file:[/bold red] {e}")
            return

    console.print(
        Panel(
            f"[bold blue]File:[/bold blue] {file_path}\n[bold blue]Request:[/bold blue] {instructions}",
            title="Yaver Edit",
        )
    )

    with console.status("[bold yellow]AI is working on your changes..."):
        coder_agent = CoderAgent()
        result = coder_agent.edit_file_content(
            original_content, instructions, file_path
        )
        new_content = extract_code_block(result)

    # Calculate diff
    diff = difflib.unified_diff(
        original_content.splitlines(),
        new_content.splitlines(),
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    diff_text = "\n".join(diff)

    if not diff_text:
        console.print("[bold yellow]No changes were made by the AI.[/bold yellow]")
        return

    console.print("\n[bold]Proposed Changes:[/bold]")
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)

    if Confirm.ask("\n[bold green]Do you want to apply these changes?[/bold green]"):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            console.print(
                f"[bold green]✔ Successfully updated {file_path}[/bold green]"
            )
        except Exception as e:
            console.print(f"[bold red]Error writing file:[/bold red] {e}")
    else:
        console.print("[bold red]✖ Changes discarded.[/bold red]")
