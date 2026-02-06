"""
Chat Agent Integration
Integrates RAG, Code Analysis, and LLM for interactive chat.
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict
import time
import json

from rich.console import Console
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from cli.ui import format_panel
from tools.code_analyzer.analyzer import CodeAnalyzer
from agents.agent_base import create_llm, retrieve_relevant_context
from tools.sandbox import Sandbox
from utils.prompts import CLI_CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Intelligent Agent for Yaver Chat.
    Combines general LLM capabilities with RAG-based code knowledge.
    """

    def __init__(self, session_id: str, repo_path: str = ".", project_id: str = None):
        self.console = Console()
        self.session_id = session_id  # Chat session ID
        self.project_id = project_id  # Project ID for filtering repos in RAG
        self.repo_path = Path(repo_path)
        self.analyzer: Optional[CodeAnalyzer] = None
        # Initialize Sandbox with the repo path as CWD to allow file system operations on the codebase
        self.sandbox = Sandbox(timeout=30, cwd=str(self.repo_path.resolve()))

        # Initialize history with System Prompt
        self.history = [SystemMessage(content=CLI_CHAT_SYSTEM_PROMPT)]

        self._llm = None

        self._initialize_resources()

    def _initialize_resources(self):
        """Initialize Analyzer and RAG service."""
        try:
            self.console.print("[dim]Initializing Code Analysis Engine...[/dim]")

            # Initialize Code Analyzer
            # Use project_id if available to access learned knowledge base (project context)
            # otherwise fallback to session_id (chat context)
            analyzer_id = self.project_id if self.project_id else self.session_id
            self.analyzer = CodeAnalyzer(analyzer_id, self.repo_path)

            # Connect to Neo4j (using default local config for now)
            try:
                self.analyzer.connect_db("bolt://localhost:7687", ("neo4j", "password"))
            except Exception as e:
                self.console.print(
                    f"[yellow]Warning: Graph database not connected (Neo4j): {e}[/yellow]"
                )

            # Initialize basic LLM for conversational parts
            self._llm = create_llm()

        except Exception as e:
            import traceback

            self.console.print(f"[red]Error initializing agent resources: {e}[/red]")
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def _load_quality_context(self) -> str:
        """Load recent code quality findings to enrich chat context"""
        if not self.project_id:
            return ""

        try:
            # Reconstruct path matching CodeQualityAgent's logic
            # Check sessions first, then projects
            project_dir = Path.home() / ".yaver" / "sessions" / self.project_id
            if not project_dir.exists():
                project_dir = Path.home() / ".yaver" / "projects" / self.project_id

            agent_dir = project_dir / "agent"
            analyses_dir = agent_dir / "analyses"
            if not analyses_dir.exists():
                return ""

            reports = sorted(list(analyses_dir.glob("*_analysis.json")))
            if not reports:
                return ""

            latest_report_file = reports[-1]
            self.console.print(
                f"[dim]Stats: Loading analysis context from {latest_report_file.name}[/dim]"
            )

            with open(latest_report_file) as f:
                report = json.load(f)

            summary = []
            health = report.get("repository_health", {})
            score = health.get("quality_score", 0)
            summary.append(f"Repository Quality Score: {score}/100")

            issues = report.get("recommendations", [])
            if issues:
                summary.append(f"Identified {len(issues)} code quality issues:")
                for issue in issues[:5]:
                    summary.append(
                        f"- [{issue.get('priority', '?')}/10] {issue.get('title', 'Unknown Issue')}"
                    )
            else:
                summary.append("No critical code quality issues detected.")

            return "\n".join(summary)
        except Exception as e:
            logger.warning(f"Failed to load quality context: {e}")
            return ""

    def chat(self, user_input: str) -> str:
        """
        Process a user message and return the response.
        Uses Hybrid RAG via MemoryQueryOrchestrator.
        """
        self.history.append(HumanMessage(content=user_input))

        response_text = ""

        try:
            # 1. Retrieve Context
            context = retrieve_relevant_context(user_input)
            quality_ctx = self._load_quality_context()

            full_context = f"{context}\n\n{quality_ctx}"

            # 2. Invoke LLM with Context
            # Construct message history with injected context
            messages_to_send = list(self.history[:-1])  # All past messages

            # Inject Context as a temporary System Message before the latest user input
            context_msg = SystemMessage(
                content=f"Context from Codebase:\n{full_context}"
            )
            messages_to_send.append(context_msg)

            # Append the latest user message
            messages_to_send.append(self.history[-1])

            # Debug: Log the message structure sizes
            # logger.debug(f"Sending {len(messages_to_send)} messages to LLM")

            resp = self._llm.invoke(messages_to_send)
            response_text = resp.content if hasattr(resp, "content") else str(resp)

            # Logic to extract code from either Tool Calls or Markdown Blocks
            code_to_run = None

            # 1. Check for structured tool calls (LangChain/Ollama parsing)
            if hasattr(resp, "tool_calls") and resp.tool_calls:
                for tool in resp.tool_calls:
                    # Match name loosely
                    if (
                        "python" in tool.get("name", "").lower()
                        and "exec" in tool.get("name", "").lower()
                    ):
                        args = tool.get("args", {})
                        code_to_run = (
                            args.get("command")
                            or args.get("code")
                            or args.get("script")
                        )
                        if code_to_run:
                            self.console.print(
                                f"[dim]Tool Call Detected: {tool['name']}[/dim]"
                            )
                            break

            # 2. Check for Markdown blocks if no tool call found
            if not code_to_run and (
                "```python:execute" in response_text
                or "```python:exec" in response_text
            ):
                import re

                code_match = re.search(
                    r"```python:(?:execute|exec)\n(.*?)```", response_text, re.DOTALL
                )
                if code_match:
                    code_to_run = code_match.group(1)

            # Execution Logic
            if code_to_run:
                self.console.print(
                    "[dim]⚡ Detected executable code block. Running in Sandbox...[/dim]"
                )
                success, output = self.sandbox.execute_code(code_to_run)

                self.console.print(
                    format_panel(output, title="Sandbox Output", border_style="yellow")
                )

                # Feed result back to LLM for final interpretation
                follow_up_messages = list(messages_to_send)
                # Ensure we have a valid previous message content
                prev_content = (
                    response_text
                    if response_text
                    else "Exec: Code generated via tool call."
                )
                follow_up_messages.append(AIMessage(content=prev_content))
                follow_up_messages.append(
                    SystemMessage(content=f"Execution Result:\n{output}")
                )
                follow_up_messages.append(
                    HumanMessage(content="Interpret this result.")
                )

                final_resp = self._llm.invoke(follow_up_messages)
                interpretation = (
                    final_resp.content
                    if hasattr(final_resp, "content")
                    else str(final_resp)
                )

                if not response_text:
                    response_text = f"I've calculated this using the following code:\n```python\n{code_to_run}\n```\n\n**Analysis:**\n{interpretation}"
                else:
                    response_text += "\n\n**Execution Result:**\n" + interpretation

            # Fallback for empty responses if NO code was executed
            elif not response_text or not response_text.strip():
                response_text = "I apologize, but I couldn't generate a response. Please try asking again or check the system logs."
                self.console.print(
                    f"[yellow]Warning: LLM returned empty response. Raw: {resp}[/yellow]"
                )

        except Exception as e:
            self.console.print(f"[yellow]Error: {e}[/yellow]")
            response_text = (
                f"I encountered an error accessing the codebase knowledge: {e}"
            )

        self.history.append(AIMessage(content=response_text))
        return response_text

    def close(self):
        if self.analyzer:
            self.analyzer.close()
