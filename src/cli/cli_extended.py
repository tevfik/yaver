
import sys
import subprocess
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from yaver_cli.agent_base import create_llm

console = Console()

def handle_explain(command_str: str):
    """
    Explains a shell command in plain English.
    """
    llm = create_llm()
    console.print(f"[bold blue]Analyzing command...[/bold blue]")
    
    prompt = f"Explain the following shell command in detail, breaking down each flag and argument:\n\n`{command_str}`"
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are a helpful UNIX/Linux shell expert. Explain commands clearly using Markdown."),
            HumanMessage(content=prompt)
        ])
        
        console.print(Panel(Markdown(response.content), title="Command Explanation", border_style="blue"))
        
    except Exception as e:
        console.print(f"[red]Error explaining command: {e}[/red]")

def handle_commit(extra_context: str = None):
    """
    Generates a commit message based on staged changes.
    """
    # 1. Check staged changes
    try:
        diff_proc = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=True)
        diff = diff_proc.stdout
        
        if not diff.strip():
            console.print("[yellow]No staged changes found. Use 'git add' first.[/yellow]")
            return
            
    except subprocess.CalledProcessError:
        console.print("[red]Not a git repository or git error.[/red]")
        return

    # 2. Generate Message
    llm = create_llm()
    console.print(f"[bold blue]Analyzing changes... (Diff size: {len(diff)} chars)[/bold blue]")
    
    prompt = f"""
    Generate a concise and descriptive git commit message for the following changes.
    Follow the Conventional Commits specification (e.g., feat:, fix:, docs:, refactor:).
    
    Format:
    <type>: <subject>
    
    <body>
    
    Diff:
    {diff[:10000]}
    """ # Truncate large diffs
    
    if extra_context:
        prompt += f"\n\nContext/Intent: {extra_context}"
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert developer. Output ONLY the commit message in the requested format."),
            HumanMessage(content=prompt)
        ])
        
        msg = response.content.strip()
        # Clean up code blocks if present
        if msg.startswith("```"):
             lines = msg.split('\n')
             msg = "\n".join([line for line in lines if not line.strip().startswith("```")]).strip()

        console.print(Panel(msg, title="Generic Commit Message", border_style="green"))
        
        # 3. Offer to commit
        from rich.prompt import Confirm
        if Confirm.ask("Use this commit message?"):
            try:
                subprocess.run(["git", "commit", "-m", msg], check=True)
                console.print("[green]Commit successful![/green]")
            except subprocess.CalledProcessError as e:
                 console.print(f"[red]Commit failed: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Error generating commit message: {e}[/red]")

def handle_fix(command: list = None):
    """
    Analyzes error logs (from pipe or command execution) and suggests fixes.
    Usage: 
      1. command 2>&1 | yaver fix
      2. yaver fix -- command arg1 arg2
    """
    error_content = ""
    command_str = ""

    # Mode 1: Wrapper Mode (yaver fix python script.py)
    if command:
        command_str = " ".join(command)
        console.print(f"[bold blue]Running command:[/bold blue] {command_str}")
        try:
            # Run user command and capture output
            result = subprocess.run(
                command_str, 
                shell=True, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                console.print(result.stdout)
                console.print("[green]Command executed successfully. No errors to fix.[/green]")
                return
            else:
                # Capture both stdout and stderr for context
                error_content = f"{result.stdout}\n{result.stderr}"
                console.print(result.stdout)
                console.print("[red]Command failed. Analyzing error...[/red]")
                
        except Exception as e:
            console.print(f"[red]Execution failed: {e}[/red]")
            return

    # Mode 2: Pipe Mode (command | yaver fix)
    elif not sys.stdin.isatty():
        # Read from pipe
        console.print("[bold blue]Reading log from stdin...[/bold blue]")
        error_content = sys.stdin.read()
        if not error_content.strip():
            console.print("[yellow]Empty input received.[/yellow]")
            return
    else:
        console.print("[yellow]Usage: \n  1. Pipe logs: `make | yaver fix`\n  2. Wrap command: `yaver fix -- python script.py`[/yellow]")
        return

    # LLM Analysis
    llm = create_llm()
    console.print(f"[bold blue]Diagnosing error... ({len(error_content)} chars)[/bold blue]")
    
    prompt = f"""
    Analyze the following command output/error log and provide a solution.
    
    Command (if known): {command_str or 'Unknown (Piped Input)'}
    
    Error Log:
    {error_content[:15000]} 
    
    Instructions:
    1. Identify the root cause of the error.
    2. Propose a specific fix (command to run, code change, or configuration).
    3. Keep explanation concise.
    """
    
    try:
        response = llm.invoke([
            SystemMessage(content="You are an expert DevOps and Software Engineer. Fix the error."),
            HumanMessage(content=prompt)
        ])
        
        console.print(Panel(Markdown(response.content), title="Auto-Diagnosis & Fix", border_style="red"))
        
    except Exception as e:
        console.print(f"[red]Diagnosis failed: {e}[/red]")
