import os
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate

PROMPTS_DIR = Path(__file__).parent


def load_prompt_template(filename: str) -> ChatPromptTemplate:
    """Load a prompt template from a markdown file in the prompts directory."""
    try:
        path = PROMPTS_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return ChatPromptTemplate.from_template(content)
    except Exception as e:
        print(f"Error loading prompt {filename}: {e}")
        # Return a fallback simple template to avoid crashing
        return ChatPromptTemplate.from_template(
            "Error loading prompt. Context: {context}"
        )


def load_raw_prompt(filename: str) -> str:
    """Load raw prompt string."""
    try:
        path = PROMPTS_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error loading prompt {filename}: {e}")
        return ""


# Expose Prompts
ARCHITECTURE_PROMPT = load_prompt_template(
    "git_analyzer_report.md"
)  # Mapped to new file
DECOMPOSITION_PROMPT = load_prompt_template("task_manager_decomposition.md")

# New prompts for CLI commands
PROJECT_SCAFFOLDER_PROMPT = load_prompt_template("project_scaffolder.md")
COMMIT_MESSAGE_PROMPT = load_prompt_template("commit_message.md")
SHELL_EXPLAINER_PROMPT = load_prompt_template("shell_explainer.md")
SHELL_SUGGESTER_PROMPT = load_prompt_template("shell_suggester.md")
ERROR_FIXER_PROMPT = load_prompt_template("error_fixer.md")
FILE_ANALYZER_PROMPT = load_prompt_template("file_analyzer.md")

# Raw templates for mixing with system prompts
PLANNER_SYSTEM_PROMPT = load_raw_prompt("planner_system.md")
CODER_SYSTEM_PROMPT = load_raw_prompt("coder_system.md")
REVIEWER_SYSTEM_PROMPT = load_raw_prompt("reviewer_system.md")
GIT_ARCHITECT_SYSTEM_PROMPT = load_raw_prompt("git_architect_system.md")
CLI_CHAT_SYSTEM_PROMPT = load_raw_prompt("cli_chat_system.md")

PLANNER_USER_TEMPLATE = load_raw_prompt("planner_user.md")
CODER_USER_TEMPLATE = load_raw_prompt("coder_user.md")
CODER_FIX_TEMPLATE = load_raw_prompt("coder_fix.md")
REVIEWER_USER_TEMPLATE = load_raw_prompt("reviewer_user.md")
ARCHITECTURE_JSON_PROMPT = load_raw_prompt("architecture_analysis_json.md")

# Deep Analysis System Prompts
CALL_GRAPH_ANALYZER_PROMPT = load_raw_prompt("call_graph_analyzer.md")
IMPACT_ANALYZER_PROMPT = load_raw_prompt("impact_analyzer.md")
ARCHITECTURE_QUESTIONER_PROMPT = load_raw_prompt("architecture_questioner.md")

# RAG Service Prompts
RAG_INTENT_CLASSIFIER_PROMPT = load_raw_prompt("rag_intent_classifier.md")
RAG_QA_ARCHITECT_PROMPT = load_raw_prompt("rag_qa_architect.md")
CONCEPT_EXPLAINER_PROMPT = load_raw_prompt("concept_explainer.md")
SIMILAR_CODE_FINDER_PROMPT = load_raw_prompt("similar_code_finder.md")
