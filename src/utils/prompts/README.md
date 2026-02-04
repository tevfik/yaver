# Prompts Directory

This directory contains the System and User prompts for the Yaver AI agents.
The prompts are stored as external Markdown files to allow for easier editing and versioning (Prompt Engineering) without modifying the Python code.

## File Naming Convention

- `[agent_name]_system.md`: The System Prompt (Persona, Constraints, Goals).
- `[agent_name]_user.md`: The User Prompt Template (Task specifics, Context placeholders).
- `[agent_name]_[action].md`: Specific action templates (e.g., `coder_fix.md`, `task_manager_decomposition.md`).

## Special Prompts

These prompts do NOT follow the standard System Prompt structure. They are lightweight, task-specific templates used by RAG services or specialized tools.

### Git Analyzer Report (`git_analyzer_report.md`)
Unlike standard agent prompts, this prompt is used for the **Analysis Mode** report generation.
- **Agent**: GitAnalyzer
- **Purpose**: Generates a high-level architectural overview and Mermaid diagrams.
- **Custom Input**: Accepts a `{user_request}` variable, which comes from the "Analysis Customization" textbox in the UI. This allows users to focus the analysis (e.g., "Check for security flaws", "Focus on database layer").
- **Variables**:
  - `{context}`: Aggregated stats, file lists, and code structure summaries.
  - `{user_request}`: User's specific instructions for the report.

### RAG Service Prompts
These are minimal, focused prompts for the Retrieval-Augmented Generation service:

- **`rag_intent_classifier.md`**: Classifies user questions as STRUCTURE/SEMANTIC/HYBRID to route queries to Neo4j or Qdrant.
- **`rag_qa_architect.md`**: Answers architecture questions using combined graph + vector context.
- **`concept_explainer.md`**: Explains programming concepts found in the codebase with pedagogical clarity.
- **`similar_code_finder.md`**: Identifies code clones and recommends refactoring.

### Deep Analysis Prompts
Specialized prompts for the Deep Code Analysis system (Neo4j + Qdrant):

- **`call_graph_analyzer.md`**: Traces function calls, identifies callers/callees, detects circular dependencies.
- **`impact_analyzer.md`**: Predicts breaking changes when code is modified, assesses risk levels.
- **`architecture_questioner.md`**: Evaluates architecture, detects patterns/anti-patterns, recommends improvements.

## Standard System Prompt Structure (Template)

All **System Prompts** must follow this standard structure to maintain consistent agent behavior (MBTI personas, rigid constraints).

```markdown
# Role: [Role Name]

## Profile
- **Author**: Yaver AI
- **Version**: [x.x]
- **Language**: English
- **Description**: [Brief description]
- **MBTI Profile**: **[TYPE]**
  - **[Function]**: [Explanation]
  - *Thought Process*: "[Internal monologue example]"

## Goals
1.  [Goal 1]
2.  [Goal 2]

## Constraints
- [Constraint 1]
- [Constraint 2]

## Skills
- [Skill 1]
- [Skill 2]

## Workflow
1.  [Step 1]
2.  [Step 2]

## System Instruction
[Final specific instructions, "You are...", Output Format protocols]
```

## How to use in Python

Prompts are loaded via `yaver.prompts` module.

```python
from yaver.prompts import load_prompt_template, load_raw_prompt

# 1. Loading a System Prompt (usually raw string for SystemMessage)
system_prompt_str = load_raw_prompt("coder_system.md")

# 2. Loading a ChatTemplate (User prompt with vars)
user_template = load_prompt_template("coder_user.md")

# Usage in LangChain
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt_str),
    ("user", user_template) # or use raw string and let LangChain handle it
])
```

## Maintenance

- Edit `.md` files to change agent behavior.
- Ensure new agents define their `_system.md` file here.
- Add the loader shortcut in `__init__.py`.
