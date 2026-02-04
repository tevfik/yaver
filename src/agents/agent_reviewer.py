"""
Reviewer Agent - Responsible for checking code quality and correctness
"""
import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field


from yaver_cli.agent_base import create_llm, print_section_header, print_info, print_warning, print_success, load_file
from yaver_cli.config import get_config
from yaver_cli.prompts import REVIEWER_USER_TEMPLATE

logger = logging.getLogger("yaver_cli")

class ReviewResult(BaseModel):
    is_valid: bool = Field(description="Whether the code is valid and safe to use")
    issues: list[str] = Field(description="List of issues found in the code")
    suggestions: list[str] = Field(description="Suggestions for improvement")
    corrected_code: Optional[str] = Field(description="Optional corrected version if trivial fixes needed")

class ReviewerAgent:
    """Agent responsible for reviewing code"""
    
    def __init__(self, model_type: str = "code"):
        # Use a slightly higher temperature for critical analysis
        self.llm = create_llm(model_type, temperature=0.1) 
        self.logger = logger
        self.config = get_config()
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load system prompt from file defined in config"""
        prompt_path = self.config.prompts.reviewer_system_prompt_path
        content = load_file(prompt_path)
        if content:
            return content
        else:
            self.logger.warning(f"Could not load prompt from {prompt_path}, using default.")
            return """You are a Senior Code Reviewer and QA Engineer.
Your task is to analyze the provided code for:
1. Correctness
2. Quality
3. Bugs
4. Security
"""

    def review_code(self, code: str, requirements: str) -> str:
        """
        Reviews the code against requirements and best practices.
        Returns a structured review or text feedback.
        """
        print_section_header("Reviewer Agent: Analyzing Code", "🧐")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", REVIEWER_USER_TEMPLATE)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        result = chain.invoke({
            "code": code,
            "requirements": requirements
        })
        
        if "APPROVED" in result:
            print_success("Code review passed!")
        else:
            print_warning("Issues found in code review.")
            
        self.logger.info("Code review complete")
        return result
