"""
Coder Agent - Responsible for writing code based on specifications
"""
import logging
from typing import Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


from yaver_cli.agent_base import create_llm, print_section_header, print_info, load_file, retrieve_relevant_context
from yaver_cli.config import get_config
from yaver_cli.prompts import CODER_USER_TEMPLATE, CODER_FIX_TEMPLATE

logger = logging.getLogger("yaver_cli")

class CoderAgent:
    """Agent responsible for writing and modifying code"""
    
    def __init__(self, model_type: str = "code"):
        self.llm = create_llm(model_type, temperature=0.2)
        self.logger = logger
        self.config = get_config()
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load system prompt from file defined in config"""
        prompt_path = self.config.prompts.coder_system_prompt_path
        content = load_file(prompt_path)
        if content:
            return content
        else:
            self.logger.warning(f"Could not load prompt from {prompt_path}, using default.")
            return """You are an expert software developer.
Your task is to write clean, efficient, and well-documented code based on the user's request.
Follow these rules strictly:
1. Return ONLY the code, wrapped in markdown code blocks (e.g., ```python ... ```).
2. Include comments explaining complex logic.
3. Follow standard best practices for the language.
"""

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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", CODER_USER_TEMPLATE)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        result = chain.invoke({
            "task": task_description,
            "context": combined_context
        })
        
        self.logger.info("Code generation complete")
        return result

    def fix_code(self, original_code: str, review_feedback: str, previous_attempts: Optional[list] = None) -> str:
        """
        Fixes code based on review feedback.
        """
        print_section_header("Coder Agent: Fixing Code", "🔧")
        
        system_prompt = self.system_prompt + "\n\nAlso, fix the provided code based on the review feedback. Return the corrected code in a markdown code block."
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", CODER_FIX_TEMPLATE)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        history_text = "No previous attempts."
        if previous_attempts:
            formatted_attempts = []
            for i, attempt in enumerate(previous_attempts):
                formatted_attempts.append(f"Attempt {i+1} Failed. Feedback: {attempt}")
            history_text = "\n".join(formatted_attempts)
        
        result = chain.invoke({
            "code": original_code,
            "feedback": review_feedback,
            "history": history_text
        })
        
        self.logger.info("Code fix complete")
        return result

    def edit_file_content(self, file_content: str, instructions: str, file_path: str = "") -> str:
        """
        Edits existing file content based on instructions.
        """
        print_section_header("Coder Agent: Editing File", "📝")
        
        system_prompt = self.system_prompt + "\n\nYou are editing an existing file. Retain the style and structure. Return the FULL updated file content in a markdown code block."
        
        edit_template = """
You are tasked with editing the following file: `{file_path}`

INSTRUCTIONS:
{instructions}

CURRENT CONTENT:
```
{content}
```

Return the complete, updated file content. Wrap it in a markdown code block.
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", edit_template)
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        result = chain.invoke({
            "file_path": file_path,
            "instructions": instructions,
            "content": file_content
        })
        
        self.logger.info("File edit complete")
        return result
