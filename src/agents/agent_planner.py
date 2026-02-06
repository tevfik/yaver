"""
Planner Agent - Responsible for architectural planning before coding
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from agents.agent_base import create_llm, load_file
from config.config import get_config
from core.tools import ToolRegistry
from utils.prompts import PLANNER_USER_TEMPLATE, PLANNER_SYSTEM_PROMPT

logger = logging.getLogger("agents")


class PlannerAgent:
    """Agent responsible for creating implementation plans"""

    def __init__(self, model_type: str = "reasoning"):
        # Uses reasoning model for better planning
        self.llm = create_llm(model_type, temperature=0.3)
        self.config = get_config()
        self.tool_registry = ToolRegistry()

    def create_plan(self, task_description: str, context: str = "") -> str:
        """
        Generates a plan for the task.
        """
        logger.info("Planner Agent: Thinking...")

        # Get available tools awareness
        tools_info = self.tool_registry.list_tools()
        tool_list_str = "\n".join(
            [f"- **{t['name']}**: {t['description']}" for t in tools_info]
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", PLANNER_SYSTEM_PROMPT), ("user", PLANNER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke(
            {
                "task_description": task_description,
                "context": context,
                "tool_list": tool_list_str,
            }
        )
