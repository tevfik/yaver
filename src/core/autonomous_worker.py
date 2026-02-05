"""
Autonomous Worker Module
Executes high-level tasks by reasoning, planning, and using tools.
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

try:
    from langchain.agents import create_tool_calling_agent, AgentExecutor
except ImportError:
    try:
        from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
    except ImportError:
        # If both fail, we might be on a very new version or very old one.
        # Check if we can find them in langgraph or elsewhere (future proofing)
        import logging

        logging.getLogger(__name__).warning(
            "Could not import standard agents, trying legacy/classic paths."
        )
        raise

from langchain_core.messages import SystemMessage

from config.config import get_config
from tools.rag.rag_service import RAGService
from memory.manager import MemoryManager
from core.tools import ToolRegistry
from utils.prompts import AUTONOMOUS_WORKER_PROMPT

logger = logging.getLogger(__name__)


class AutonomousWorker:
    """
    Autonomous Agent that can execute tasks using ReAct pattern.
    """

    def __init__(self, rag_service: RAGService, memory_manager: MemoryManager):
        self.rag = rag_service
        self.memory = memory_manager
        self.config = get_config()
        self.tool_registry = ToolRegistry()

        # Initialize LLM
        # Use a model capable of tool calling if possible, or general model with ReAct
        self.llm = ChatOllama(
            base_url=self.config.ollama.base_url,
            model=self.config.ollama.model_code or self.config.ollama.model_general,
            temperature=0.1,
            format="json",  # Force JSON for robust parsing if using custom loop, but LangChain handles it
        )

        # Tools
        self.tools = self.tool_registry.get_langchain_tools()

        # Prompt
        # Prompt
        # We use the centralized prompt template
        self.prompt = AUTONOMOUS_WORKER_PROMPT

        try:
            # Try to create an agent.
            # Note: proper tool calling with Ollama depends on the model version.
            # If this fails, we might need a simpler ReAct chain.
            self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
            self.executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
            )
            self.mode = "agent"
        except Exception as e:
            logger.warning(
                f"Failed to create Tool Calling Agent: {e}. Falling back to Planner."
            )
            self.mode = "planner"

    def run(self, task: str) -> str:
        """
        Execute the task.
        """
        logger.info(f"Worker received task: {task}")

        # 1. Retrieve Context
        logger.info("Retrieving context...")
        context = self.rag.retrieve_context(task, strategy="HYBRID")

        if self.mode == "agent":
            logger.info("Starting Agent Execution Loop...")
            try:
                result = self.executor.invoke(
                    {
                        "input": task,
                        "context": context,
                        "tool_names": [t.name for t in self.tools],
                        "chat_history": [],
                    }
                )
                output = result.get("output", "Task completed.")
            except Exception as e:
                output = f"Agent failed: {e}"
        else:
            # Fallback for models without tool calling support
            output = f"I am in Planner mode (Tool Calling unavailable).\nContext found: {len(context)} chars.\n\nPlan:\nTODO"

        # Save to Memory
        self.memory.add(
            f"Task: {task}\nResult: {output}", metadata={"type": "task_execution"}
        )

        return output
