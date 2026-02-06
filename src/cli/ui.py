"""
Yaver CLI UI Helpers
Centralized Rich console and styling configuration.
"""

from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from typing import Optional, Any

# Custom theme for Yaver
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "title": "bold magenta",
        "subtitle": "blue",
        "dim": "dim white",
    }
)

console = Console(theme=custom_theme)


def print_success(message: str):
    """Print a success message with green checkmark."""
    console.print(f"✅ [success]{message}[/success]")


def print_error(message: str):
    """Print an error message with red cross."""
    console.print(f"❌ [error]{message}[/error]")


def print_warning(message: str):
    """Print a warning message with yellow triangle."""
    console.print(f"⚠️  [warning]{message}[/warning]")


def print_info(message: str):
    """Print an info message."""
    console.print(f"ℹ️  [info]{message}[/info]")


def print_title(title: str, subtitle: Optional[str] = None):
    """Print a styled title."""
    console.print()
    console.rule(f"[title]{title}[/title]")
    if subtitle:
        console.print(f"[subtitle]{subtitle}[/subtitle]", justify="center")
    console.print()


def format_panel(
    content: Any, title: Optional[str] = None, border_style: str = "blue"
) -> Panel:
    """Create a styled panel."""
    # Convert string content to Markdown if pertinent, but handled safely
    if isinstance(content, str):
        # Basic check to see if it looks like markdown or just text
        renderable = Markdown(content)
    else:
        renderable = content

    return Panel(
        renderable,
        title=f"[bold]{title}[/bold]" if title else None,
        border_style=border_style,
        expand=False,
    )


def create_table(columns: list[str], title: Optional[str] = None) -> Table:
    """Create a standard styled table."""
    table = Table(
        title=title,
        title_style="bold magenta",
        header_style="bold cyan",
        show_lines=True,
        box=None,
    )
    for col in columns:
        table.add_column(col)
    return table


def print_section_header(title: str, emoji: str = "🔹"):
    """Print formatted section header"""
    console.print(f"\n{emoji} [bold cyan]{title}[/bold cyan]")
    console.print("─" * 60)
