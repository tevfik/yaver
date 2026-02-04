"""
Reviewer Agent - Responsible for checking code quality and correctness
"""
import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field


from yaver_cli.agent_base import (
    create_llm,
    print_section_header,
    print_info,
    print_warning,
    print_success,
    load_file,
)
from yaver_cli.config import get_config
from utils.prompts import REVIEWER_USER_TEMPLATE, REVIEWER_SYSTEM_PROMPT

logger = logging.getLogger("yaver_cli")


class ReviewResult(BaseModel):
    is_valid: bool = Field(description="Whether the code is valid and safe to use")
    issues: list[str] = Field(description="List of issues found in the code")
    suggestions: list[str] = Field(description="Suggestions for improvement")
    corrected_code: Optional[str] = Field(
        description="Optional corrected version if trivial fixes needed"
    )


class ReviewerAgent:
    """Agent responsible for reviewing code"""

    def __init__(self, model_type: str = "code"):
        # Use a slightly higher temperature for critical analysis
        self.llm = create_llm(model_type, temperature=0.1)
        self.logger = logger
        self.config = get_config()

    def review_code(self, code: str, requirements: str) -> str:
        """
        Reviews the code against requirements and best practices.
        Returns a structured review or text feedback.
        """
        print_section_header("Reviewer Agent: Analyzing Code", "🧐")

        prompt = ChatPromptTemplate.from_messages(
            [("system", REVIEWER_SYSTEM_PROMPT), ("user", REVIEWER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()

        result = chain.invoke({"code": code, "requirements": requirements})

        if "APPROVED" in result:
            print_success("Code review passed!")
        else:
            print_warning("Issues found in code review.")

        self.logger.info("Code review complete")
        return result
