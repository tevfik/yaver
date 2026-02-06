"""
Interactive capabilities for Yaver CLI
Handles chat loops, command suggestions, and smart context parsing.
"""
import os
import re
import subprocess
import glob
from typing import List, Tuple
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.syntax import Syntax

from agents.agent_base import create_llm, print_section_header
from config.config import get_config
from utils.prompts import CLI_CHAT_SYSTEM_PROMPT

console = Console()


def resolve_smart_context(user_input: str) -> Tuple[str, str]:
    """
    Parses user input for @filename references.
    Returns: (cleaned_input, context_string)
    """
    context_parts = []

    # Regex to find @filepath
    # We look for words starting with @
    matches = re.finditer(r"@([\w\.\-/]+)", user_input)

    files_found = []

    for match in matches:
        file_ref = match.group(1)
        # Try to resolve file
        path = Path(file_ref)

        # If absolute path
        if path.is_absolute():
            candidates = [path]
        else:
            # Relative to cwd
            candidates = [Path.cwd() / path]
            # Or try recursive glob if simple name
            if not str(path).startswith((".", "/")):
                # naive glob for convenience if not found immediately
                if not candidates[0].exists():
                    pass  # Could add glob logic here if needed, keeping simple for now

        target_file = None
        if candidates[0].exists() and candidates[0].is_file():
            target_file = candidates[0]

        if target_file:
            try:
                content = target_file.read_text(encoding="utf-8", errors="replace")
                # Add to context
                context_parts.append(
                    f"\n--- File: {file_ref} ---\n{content}\n--- End of {file_ref} ---\n"
                )
                files_found.append(file_ref)
            except Exception as e:
                console.print(
                    f"[yellow]Could not read reference @{file_ref}: {e}[/yellow]"
                )
        else:
            console.print(f"[yellow]File reference not found: @{file_ref}[/yellow]")

    # We generally leave the @file in the text so the LLM knows what was referenced,
    # but we simply append the content to the context block.

    combined_context = "\n".join(context_parts)
    return user_input, combined_context


def handle_suggest(prompt_text: str):
    """
    Generates a shell command based on the prompt, offers to execute it.
    """
    llm = create_llm()

    system_prompt = """You are a command-line expert.
    User will ask for a shell command.
    Output ONLY the shell command within a code block, or just the command.
    No valid explanation unless requested.
    Target OS: Linux/Unix.
    """

    console.print(f"[bold blue]Thinking...[/bold blue]")

    try:
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=prompt_text)]
        )

        content = response.content.strip()

        # Extract Code
        cmd = content
        if "```" in content:
            lines = content.split("\n")
            code_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    code_lines.append(line)
            if code_lines:
                cmd = "\n".join(code_lines).strip()

        # UI
        console.print(
            Panel(Syntax(cmd, "bash"), title="Suggested Command", border_style="green")
        )

        # Copilot-style interaction
        if Confirm.ask("Execute this command?"):
            console.print(f"[dim]Running: {cmd}[/dim]")
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                console.print(
                    f"[red]Command failed with exit code {e.returncode}[/red]"
                )
        else:
            console.print("[yellow]Skipped.[/yellow]")

    except Exception as e:
        console.print(f"[red]Error generating suggestion: {e}[/red]")


def handle_chat_mode():
    """
    Starts an interactive REPL chat session with context awareness.
    """
    print_section_header("Yaver AI Chat", "💬")
    console.print(
        "[dim]Type 'exit' or 'quit' to leave. Use @filename to include context.[/dim]\n"
    )

    llm = create_llm()
    history = [SystemMessage(content=CLI_CHAT_SYSTEM_PROMPT)]

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]Yaver>[/bold cyan]")
            if user_input.strip().lower() in ["exit", "quit"]:
                break

            if not user_input.strip():
                continue

            # Smart Context
            cleaned_input, file_context = resolve_smart_context(user_input)

            # Construct message with context if present
            full_prompt = cleaned_input
            if file_context:
                full_prompt += f"\n\n[System Context Injection]:\n{file_context}"
                console.print(
                    f"[dim green]Included {file_context.count('--- File:')} files in context.[/dim green]"
                )

            # Add to history
            history.append(HumanMessage(content=full_prompt))

            # Stream response
            console.print()  # Newline
            response_text = ""

            with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
                response = llm.invoke(history)
                response_text = response.content

            console.print(Markdown(response_text))

            # Add response to history
            history.append(AIMessage(content=response_text))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
