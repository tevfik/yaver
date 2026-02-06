"""
Coder Agent - Responsible for writing code based on specifications
"""
import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


from agents.agent_base import (
    create_llm,
    print_section_header,
    print_info,
    load_file,
    retrieve_relevant_context,
)
from config.config import get_config
from utils.prompts import (
    CODER_USER_TEMPLATE,
    CODER_FIX_TEMPLATE,
    CODER_SYSTEM_PROMPT,
    CODER_EDIT_TEMPLATE,
)

logger = logging.getLogger("agents")


class CoderAgent:
    """Agent responsible for writing and modifying code"""

    def __init__(self, model_type: str = "code"):
        self.llm = create_llm(model_type, temperature=0.2)
        self.logger = logger
        self.config = get_config()

    def write_code(self, task_description: str, context: Optional[str] = None) -> str:
        """
        Generates code based on the task description.
        """
        print_section_header("Coder Agent: Writing Code", "💻")
        print_info(f"Task: {task_description[:100]}...")

        # 🧠 Memory Retrieval
        memory_context = retrieve_relevant_context(task_description)
        combined_context = context or ""

        if memory_context:
            combined_context += "\n\n" + memory_context
            self.logger.info("Injected relevant code/memory into coding context")

        if not combined_context:
            combined_context = "No additional context."

        prompt = ChatPromptTemplate.from_messages(
            [("system", CODER_SYSTEM_PROMPT), ("user", CODER_USER_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()

        result = chain.invoke({"task": task_description, "context": combined_context})

        self.logger.info("Code generation complete")
        return result

    def fix_code(
        self,
        original_code: str,
        review_feedback: str,
        previous_attempts: Optional[list] = None,
    ) -> str:
        """
        Fixes code based on review feedback.
        """
        print_section_header("Coder Agent: Fixing Code", "🔧")

        system_prompt = (
            CODER_SYSTEM_PROMPT
            + "\n\nAlso, fix the provided code based on the review feedback. Return the corrected code in a markdown code block."
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", CODER_FIX_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()

        history_text = "No previous attempts."
        if previous_attempts:
            formatted_attempts = []
            for i, attempt in enumerate(previous_attempts):
                formatted_attempts.append(f"Attempt {i+1} Failed. Feedback: {attempt}")
            history_text = "\n".join(formatted_attempts)

        result = chain.invoke(
            {
                "code": original_code,
                "feedback": review_feedback,
                "history": history_text,
            }
        )

        self.logger.info("Code fix complete")
        return result

    def edit_file_content(
        self, file_content: str, instructions: str, file_path: str = ""
    ) -> str:
        """
        Edits existing file content based on instructions.
        """
        print_section_header("Coder Agent: Editing File", "📝")

        system_prompt = (
            CODER_SYSTEM_PROMPT
            + "\n\nYou are editing an existing file. Retain the style and structure. Return the FULL updated file content in a markdown code block."
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("user", CODER_EDIT_TEMPLATE)]
        )

        chain = prompt | self.llm | StrOutputParser()

        result = chain.invoke(
            {
                "file_path": file_path,
                "instructions": instructions,
                "content": file_content,
            }
        )

        self.logger.info("File edit complete")
        return result
