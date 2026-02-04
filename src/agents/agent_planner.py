"""
Planner Agent - Responsible for architectural planning before coding
"""
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from yaver_cli.agent_base import create_llm, load_file
from yaver_cli.config import get_config
from utils.prompts import PLANNER_USER_TEMPLATE, PLANNER_SYSTEM_PROMPT

logger = logging.getLogger("yaver_cli")


class PlannerAgent:
    """Agent responsible for creating implementation plans"""

    def __init__(self, model_type: str = "general"):
        # Uses a slightly smarter/general model for top-level planning
        self.llm = create_llm(model_type, temperature=0.3)
        self.config = get_config()

    def create_plan(self, task_description: str, context: str = "") -> str:
        """
        Generates a plan for the task.
        """
        logger.info("Planner Agent: Thinking...")

        prompt = ChatPromptTemplate.from_messages(
            [("system", PLANNER_SYSTEM_PROMPT), ("user", PLANNER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"task_description": task_description, "context": context})
