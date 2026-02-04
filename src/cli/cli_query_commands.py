"""
CLI commands for unified memory query interface.

Commands:
- yaver query "question"     → Multi-source semantic search
- yaver analyze "problem"    → Structural code analysis + recommendations
- yaver insights             → Code quality report
"""

import json
import argparse
from typing import Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

from .internal_state import get_state_manager
from .query_orchestrator import CombinedMemoryInterface, AnalyticsQueryExecutor
from .neo4j_analyzers import CodeIntelligenceProvider
from .codebase_analyzer import PythonCodeAnalyzer, create_analyzer

console = Console()


def cmd_query(args: argparse.Namespace) -> None:
    """Execute multi-source query against memory."""
    question = args.question
    
    console.print(f"\n🔍 [bold]Query:[/bold] {question}\n")

    state = get_state_manager()
    current_repo = state.get_current_repo()

    if not current_repo:
        console.print("[red]Error: No repository context. Run 'yaver status' to set context.[/red]")
        return

    # Initialize combined memory interface
    memory = CombinedMemoryInterface(current_repo.repo_id)

    # Execute query
    result = memory.query(question)

    # Display results
    console.print(f"[bold]Query Type:[/bold] {result['query_type']}")
    console.print(f"[bold]Confidence:[/bold] {result['overall_confidence']:.1%}")
    console.print(f"[bold]Sources:[/bold] {', '.join(result['sources'])}")
    console.print(f"[bold]Execution Time:[/bold] {result['execution_time_ms']:.0f}ms\n")

    # Results table
    if result["results"]:
        table = Table(title="Query Results", show_header=True, header_style="bold magenta")
        table.add_column("Source", width=12)
        table.add_column("Result", width=50)
        table.add_column("Confidence", width=12)

        for item in result["results"]:
            result_text = str(item).replace('{', '').replace('}', '')[:47]
            table.add_row(
                item.get("source", "unknown"),
                result_text,
                f"{item.get('confidence', 0):.1%}",
            )

        console.print(table)
    else:
        console.print("[yellow]No results found[/yellow]")

    # Recommendations
    if result["recommendations"]:
        console.print("\n[bold]💡 Recommendations:[/bold]")
        for rec in result["recommendations"]:
            console.print(f"  • {rec}")


def cmd_inspect(args: argparse.Namespace) -> None:
    """Analyze problem and provide solution recommendations."""
    problem = args.problem

    console.print(f"\n🔬 [bold]Inspecting:[/bold] {problem}\n")

    state = get_state_manager()
    current_repo = state.get_current_repo()

    if not current_repo:
        console.print("[red]Error: No repository context. Run 'yaver status' to set context.[/red]")
        return

    # Initialize combined memory interface
    memory = CombinedMemoryInterface(current_repo.repo_id)

    # Solve problem
    solution = memory.solve_problem(problem)

    # Display problem analysis
    console.print(Panel(solution["problem"], title="Problem", border_style="cyan"))

    # Related code
    console.print("\n[bold]📌 Related Code:[/bold]")
    if solution["related_code"]:
        for i, item in enumerate(solution["related_code"], 1):
            console.print(f"  {i}. {item}")
    else:
        console.print("  [yellow]No related code found[/yellow]")

    # Code quality context
    quality = solution["code_quality_context"]
    console.print("\n[bold]📊 Code Quality Context:[/bold]")
    
    if quality and "issues" in quality:
        console.print(f"  • Issues: {quality['issues'].get('total', 0)}")
        console.print(f"  • Critical: {quality['issues'].get('by_severity', {}).get('critical', 0)}")
        console.print(f"  • Warnings: {quality['issues'].get('by_severity', {}).get('warning', 0)}")
    else:
        console.print("  • Quality report not available")

    # Recommendations
    console.print("\n[bold]✅ Recommended Approach:[/bold]")
    for rec in solution["recommended_approach"]:
        console.print(f"  {rec}")

    # Next steps
    console.print("\n[bold]📋 Next Steps:[/bold]")
    for step in solution["next_steps"]:
        console.print(f"  {step}")


def cmd_insights(args: argparse.Namespace) -> None:
    """Display code quality insights for current repository."""
    console.print("\n📊 [bold]Code Quality Insights[/bold]\n")

    state = get_state_manager()
    current_repo = state.get_current_repo()

    if not current_repo:
        console.print("[red]Error: No repository context. Run 'yaver status' to set context.[/red]")
        return

    # Analyze codebase
    try:
        analyzer = create_analyzer(current_repo.project_type or "python", 
                                  current_repo.repo_id or "yaver",
                                  Path(current_repo.local_path))
        graph = analyzer.analyze()
        provider = CodeIntelligenceProvider(graph)

        # Get insights
        memory = CombinedMemoryInterface(current_repo.repo_id)
        insights = memory.get_insights()

        # Display statistics
        stats_table = Table(title="Codebase Statistics", show_header=True, header_style="bold green")
        stats_table.add_column("Metric", width=20)
        stats_table.add_column("Value", width=15)

        stat_items = insights["statistics"]
        stats_table.add_row("Files", str(stat_items["files"]))
        stats_table.add_row("Functions", str(stat_items["functions"]))
        stats_table.add_row("Classes", str(stat_items["classes"]))
        stats_table.add_row("Total LOC", f"{stat_items['total_loc']:,}")

        console.print(stats_table)

        # Display issues
        console.print("\n[bold]Issues Found:[/bold]")
        issues = insights["issues"]
        console.print(f"  Total: {issues['total']}")
        for issue_type, count in issues["by_type"].items():
            console.print(f"  • {issue_type}: {count}")

        # Display recommendations
        console.print("\n[bold]📋 Recommendations:[/bold]")
        for rec in insights["recommendations"]:
            console.print(f"  {rec}")

        # Display top critical functions
        console.print("\n[bold]🔥 Top Critical Functions:[/bold]")
        for func in insights["critical_functions"][:5]:
            console.print(
                f"  • {func['id']} (importance: {func['importance']:.2f}, calls: {func['call_count']})"
            )

    except Exception as e:
        console.print(f"[red]Error analyzing codebase: {e}[/red]")


def register_query_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register query/inspect/insights commands to CLI."""

    # Query command
    query_parser = subparsers.add_parser(
        "query",
        help="Search memory with multi-source query",
        description="Execute semantic search across Qdrant, Neo4j, and SQLite.",
    )
    query_parser.add_argument(
        "question",
        type=str,
        help="Question to search memory for",
    )
    query_parser.set_defaults(func=cmd_query)

    # Inspect command (renamed from analyze to avoid conflict)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Analyze problem and get recommendations",
        description="Structural analysis with code quality context.",
    )
    inspect_parser.add_argument(
        "problem",
        type=str,
        help="Problem description to analyze",
    )
    inspect_parser.set_defaults(func=cmd_inspect)

    # Insights command
    insights_parser = subparsers.add_parser(
        "insights",
        help="Display code quality insights",
        description="Generate code quality report with metrics and recommendations.",
    )
    insights_parser.set_defaults(func=cmd_insights)
