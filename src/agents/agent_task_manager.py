"""
Task Manager Agent - Task decomposition and iterative problem solving
Jules-like iterative development with task tracking
"""

import json
from typing import List, Dict, Optional
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from .agent_base import (
    YaverState,
    Task,
    TaskStatus,
    TaskPriority,
    logger,
    print_section_header,
    print_success,
    print_warning,
    print_info,
    create_llm,
    create_task_id,
    format_log_entry,
    retrieve_relevant_context,
)
from .config import get_config
from .api_client import YaverClient


# ============================================================================
# Task Models
# ============================================================================
class TaskDecomposition(BaseModel):
    """Task decomposition result"""

    main_task: str = Field(description="Main task description")
    subtasks: List[str] = Field(description="List of subtasks")
    priorities: Dict[str, str] = Field(description="Priority for each subtask")
    dependencies: Dict[str, List[str]] = Field(
        default_factory=dict, description="Dependencies between tasks"
    )
    estimated_complexity: str = Field(description="Overall complexity: low/medium/high")


# ============================================================================
# Task Decomposition
# ============================================================================
def decompose_task_with_llm(
    user_request: str, context: Optional[Dict] = None
) -> TaskDecomposition:
    """Decompose user request into manageable subtasks using LLM"""
    print_section_header("Decomposing task", "📋")

    llm = create_llm("general", format="json")
    parser = JsonOutputParser(pydantic_object=TaskDecomposition)

    # 🧠 Memory Upgrade: Retrieve context from Qdrant/Neo4j
    memory_context = retrieve_relevant_context(user_request)

    context_str = ""
    if memory_context:
        context_str += memory_context
        print_info("Injected relevant memory context into planning")

    if context:
        if context.get("repo_info"):
            repo_info = context["repo_info"]
            context_str += f"\n\nProject Info:\n- File count: {repo_info.total_files}\n- Total lines: {repo_info.total_lines}\n- Languages: {repo_info.languages}"

        if context.get("architecture_analysis"):
            arch = context["architecture_analysis"]
            context_str += f"\n- Architecture: {arch.architecture_type}"

    from prompts import DECOMPOSITION_PROMPT

    # Note: DECOMPOSITION_PROMPT expects {context} and {user_request}
    # It returns JSON, so we still need the parser

    prompt = DECOMPOSITION_PROMPT

    config = get_config()

    chain = prompt | llm | parser

    try:
        result = chain.invoke(
            {
                "user_request": user_request,
                "context": context_str,
                "format_instructions": parser.get_format_instructions(),
                "max_tasks": config.task.max_task_depth * 3,
            }
        )

        print_success(f"{len(result['subtasks'])} subtasks created")
        return TaskDecomposition(**result)

    except Exception as e:
        logger.error(f"Task decomposition failed: {e}")
        # Fallback to simple decomposition
        return TaskDecomposition(
            main_task=user_request,
            subtasks=[user_request],
            priorities={user_request: "high"},
            estimated_complexity="unknown",
        )


def create_tasks_from_decomposition(decomposition: TaskDecomposition) -> List[Task]:
    """Create Task objects from decomposition result"""
    tasks = []

    # Create main task
    main_task_id = create_task_id()
    main_task = Task(
        id=main_task_id,
        title=decomposition.main_task[:100],
        description=decomposition.main_task,
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
    )
    tasks.append(main_task)

    # Create subtasks
    subtask_ids = {}
    for i, subtask_desc in enumerate(decomposition.subtasks):
        task_id = create_task_id()

        # Determine priority
        priority_str = decomposition.priorities.get(subtask_desc, "medium")
        priority = (
            TaskPriority(priority_str)
            if priority_str in ["critical", "high", "medium", "low"]
            else TaskPriority.MEDIUM
        )

        task = Task(
            id=task_id,
            title=f"Subtask {i+1}: {subtask_desc[:80]}",
            description=subtask_desc,
            priority=priority,
            parent_task_id=main_task_id,
            status=TaskStatus.PENDING,
        )

        tasks.append(task)
        subtask_ids[subtask_desc] = task_id

    # Set dependencies
    for subtask_desc, deps in decomposition.dependencies.items():
        if subtask_desc in subtask_ids:
            task_id = subtask_ids[subtask_desc]
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                task.dependencies = [
                    subtask_ids.get(dep, "") for dep in deps if dep in subtask_ids
                ]

    # Update main task subtasks
    main_task.subtasks = [t.id for t in tasks if t.parent_task_id == main_task_id]

    return tasks


# ============================================================================
# Task Execution
# ============================================================================
def get_next_task(tasks: List[Task]) -> Optional[Task]:
    """Get next task to execute based on priorities and dependencies"""
    config = get_config()

    # Filter executable tasks (pending, no blocking dependencies)
    executable_tasks = []

    for task in tasks:
        if task.status != TaskStatus.PENDING:
            continue

        # Check if all dependencies are completed
        if task.dependencies:
            deps_completed = all(
                any(t.id == dep_id and t.status == TaskStatus.COMPLETED for t in tasks)
                for dep_id in task.dependencies
            )
            if not deps_completed:
                continue

        executable_tasks.append(task)

    if not executable_tasks:
        return None

    # Sort by priority
    priority_order = {
        TaskPriority.CRITICAL: 0,
        TaskPriority.HIGH: 1,
        TaskPriority.MEDIUM: 2,
        TaskPriority.LOW: 3,
    }

    executable_tasks.sort(key=lambda t: priority_order.get(t.priority, 99))

    return executable_tasks[0]


def execute_task_with_llm(task: Task, context: Dict) -> Dict[str, any]:
    """Execute a single task using LLM"""
    print_section_header(f"Executing task: {task.title}", "⚙️")

    llm = create_llm("code")

    # Prepare context string
    context_str = ""
    if context.get("repo_info"):
        repo_info = context["repo_info"]
        context_str += f"\nProject Context:\n- Total files: {repo_info.total_files}\n- Languages: {repo_info.languages}"

    if context.get("file_analyses"):
        analyses = context["file_analyses"]
        # Include relevant file analyses
        relevant_analyses = [
            a
            for a in analyses
            if any(
                f in task.title or f in task.description
                for f in [a.file_path, a.file_path.split("/")[-1]]
            )
        ]
        if relevant_analyses:
            context_str += "\n\nRelevant Files Analysis:\n" + "\n".join(
                [f"- {a.file_path}: {a.suggestions}" for a in relevant_analyses]
            )

    # Include User Comments
    if hasattr(task, "comments") and task.comments:
        context_str += "\n\nUser Comments & Feedback:\n"
        for comment in task.comments:
            author = comment.get("author", "User")
            content = comment.get("content", "")
            if author != "Yaver Worker":  # Skip own auto-generated comments
                context_str += f"- [{author}]: {content}\n"

    from prompts import TASK_SOLVER_PROMPT

    # Format the prompt manually since we need to inject conditional content
    # Or better, update TASK_SOLVER_PROMPT to accept these vars

    prompt = TASK_SOLVER_PROMPT

    # We need to map variables correctly
    # existing keys: task_title, task_description, context
    # prompt keys: task_title, task_description, repo_context, context

    # Let's adjust how we invoke it below instead of changing prompt here
    pass

    print_info(f"Sending request to LLM (Model: {llm.model})...")

    chain = prompt | llm

    # We need to provide repo_context (files analysis) and context (user instructions/comments)
    # context_str current contains both. Let's rely on context_str being passed as 'repo_context'
    # and maybe empty 'context' or split if possible.
    # Looking at how context_str is built above (lines 190+), it has Repo Structure & Files Analysis.
    # So we should pass context_str as repo_context.

    try:
        response = chain.invoke(
            {
                "task_title": task.title,
                "task_description": task.description,
                "repo_context": context_str,
                "context": "Follow the plan and implement changes.",  # Additional user instruction placeholder
            }
        )

        return {"success": True, "output": response.content}

        print_success(f"Task completed: {task.title}")

        return {"success": True, "output": output, "task_id": task.id}

    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        return {"success": False, "error": str(e), "task_id": task.id}


def update_task_status(
    tasks: List[Task],
    task_id: str,
    status: TaskStatus,
    result: Optional[str] = None,
    error: Optional[str] = None,
) -> List[Task]:
    """Update task status"""
    for task in tasks:
        if task.id == task_id:
            task.status = status
            if result:
                task.result = result
            if error:
                task.error = error
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
            break

    return tasks


# ============================================================================
# Iteration Engine
# ============================================================================
def run_iteration_cycle(state: YaverState) -> dict:
    """Run one iteration of task execution"""
    config = get_config()

    iteration_count = state.get("iteration_count", 0)
    tasks = state.get("tasks", [])

    if iteration_count >= config.task.max_iterations:
        print_warning(f"Max iterations reached: {config.task.max_iterations}")
        return {
            "should_continue": False,
            "log": state.get("log", [])
            + [format_log_entry("TaskManager", "Max iterations reached")],
        }

    # Get next task
    next_task = get_next_task(tasks)

    if not next_task:
        print_info("All tasks completed or blocked")
        return {
            "should_continue": False,
            "log": state.get("log", [])
            + [format_log_entry("TaskManager", "No more tasks to execute")],
        }

    # Update task status to in-progress
    next_task.status = TaskStatus.IN_PROGRESS
    next_task.iteration = iteration_count + 1

    # Execute task
    context = {
        "repo_info": state.get("repo_info"),
        "architecture_analysis": state.get("architecture_analysis"),
        "refactoring_plan": state.get("refactoring_plan"),
    }

    execution_result = execute_task_with_llm(next_task, context)

    # Update task based on result
    if execution_result["success"]:
        tasks = update_task_status(
            tasks, next_task.id, TaskStatus.COMPLETED, result=execution_result["output"]
        )
    else:
        tasks = update_task_status(
            tasks, next_task.id, TaskStatus.FAILED, error=execution_result.get("error")
        )

    # Check if we should continue
    pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
    in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

    should_continue = len(pending_tasks) > 0 or len(in_progress_tasks) > 0

    return {
        "tasks": tasks,
        "current_task": next_task,
        "iteration_count": iteration_count + 1,
        "completed_tasks": state.get("completed_tasks", [])
        + ([next_task.id] if execution_result["success"] else []),
        "should_continue": should_continue,
        "log": state.get("log", [])
        + [
            format_log_entry(
                "TaskManager",
                f"Iteration {iteration_count + 1}: Executed task {next_task.id}",
            ),
            format_log_entry(
                "TaskManager",
                f"Status: {'✅ Success' if execution_result['success'] else '❌ Failed'}",
            ),
        ],
    }


# ============================================================================
# Main Agent Node
# ============================================================================
def task_manager_node(state: YaverState) -> dict:
    """Main task manager agent node"""
    logger.info("📋 Task Manager Agent started")

    user_request = state.get("user_request", "")

    if not user_request:
        error_msg = "User request not specified"
        return {
            "log": state.get("log", []) + [format_log_entry("TaskManager", error_msg)],
            "errors": state.get("errors", []) + [error_msg],
        }

    # Check if tasks already exist
    existing_tasks = state.get("tasks", [])

    if not existing_tasks:
        # Decompose task
        context = {
            "repo_info": state.get("repo_info"),
            "architecture_analysis": state.get("architecture_analysis"),
        }

        decomposition = decompose_task_with_llm(user_request, context)
        tasks = create_tasks_from_decomposition(decomposition)

        print_success(f"✅ {len(tasks)} tasks created")

        return {
            "tasks": tasks,
            "iteration_count": 0,
            "completed_tasks": [],
            "log": state.get("log", [])
            + [
                format_log_entry("TaskManager", f"Created {len(tasks)} tasks"),
                format_log_entry(
                    "TaskManager", f"Complexity: {decomposition.estimated_complexity}"
                ),
            ],
        }
    else:
        # Run iteration
        return run_iteration_cycle(state)


def execute_specific_task(state: YaverState, task_data: dict) -> dict:
    """Execute a specific provided task"""
    # Convert dict to Task object if needed
    try:
        task = Task(**task_data) if isinstance(task_data, dict) else task_data
    except Exception as e:
        logger.error(f"Failed to parse task data: {e}")
        # dummy task wrapper
        task = Task(
            id=task_data.get("id", "unknown"),
            title=task_data.get("title", "Unknown Task"),
            description=task_data.get("description", ""),
            priority=TaskPriority.MEDIUM,
        )

    print_section_header(f"Executing Single Task: {task.title}", "🚀")

    context = {
        "repo_info": state.get("repo_info"),
        "architecture_analysis": state.get("architecture_analysis"),
        "file_analyses": state.get("file_analyses", []),
    }

    # Init API Client
    client = YaverClient()

    # Notify start
    client.add_comment(
        task.id,
        f"🚀 Task execution started via Python Worker\nPriority: {task.priority.value}",
        author="Yaver Worker",
    )

    # Execute task with LLM
    result = execute_task_with_llm(task, context)

    # Side Effects: Apply changes and Git Commit
    if result["success"]:
        output = result["output"]

        # CRITICAL FIX: Use task.repo_path if available (from manual task or analysis)
        # instead of always using state (which may be wrong or missing)
        repo_path = None
        if hasattr(task, "repo_path") and task.repo_path:
            repo_path = task.repo_path
            logger.info(f"Using repo_path from task: {repo_path}")
        elif state.get("repo_info") and state.get("repo_info").get("repo_path"):
            repo_path = state.get("repo_info").get("repo_path")
            logger.info(f"Using repo_path from state: {repo_path}")
        else:
            repo_path = "."
            logger.warning(
                f"No repo_path found in task or state, using current directory: {repo_path}"
            )

        # We need to import helper functions.
        # Since they are not here, we implement simplified versions or move them.
        # For robustness, let's implement the logic here directly using the same logic as kanban_worker.

        # 1. Apply Changes
        import re
        import os

        pattern1 = r"```(?:\w+):([^\n]+)\n(.*?)```"
        matches1 = re.finditer(pattern1, output, re.DOTALL)

        changes_applied = False
        applied_files = []

        for match in matches1:
            file_path = match.group(1).strip()
            code = match.group(2)
            full_path = os.path.join(repo_path, file_path)

            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)
                logger.info(f"Applied changes to {file_path}")
                changes_applied = True
                applied_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to write file {file_path}: {e}")
                client.add_comment(
                    task.id,
                    f"❌ Failed to write file {file_path}: {e}",
                    author="Yaver Worker",
                )

        if applied_files:
            file_list = ", ".join(applied_files)
            client.add_comment(
                task.id,
                f"📝 Modified files:\n- " + "\n- ".join(applied_files),
                author="Yaver Worker",
            )

        # 2. Git Commit
        # We assume gitpython is available as it is a dependency
        try:
            import git

            try:
                repo = git.Repo(repo_path)

                # Create branch if we have task info
                branch_name = f"task/{task.id[:8]}"

                # Check if current branch is different, switch if needed?
                # For now in API mode, we might want to stay on current or force branch.
                # Let's simple check if dirty and commit to current branch for now,
                # strictly following "execute task" instruction.

                if repo.is_dirty(untracked_files=True) and changes_applied:
                    repo.git.add(A=True)
                    commit_msg = f"feat: {task.title} (Task {task.id[:8]})"
                    repo.index.commit(commit_msg)
                    logger.info("Changes committed to git.")
                    client.add_comment(
                        task.id,
                        f"💾 Changes committed to git.\nMessage: `{commit_msg}`",
                        author="Yaver Worker",
                    )
            except (git.InvalidGitRepositoryError, Exception) as e:
                logger.warning(f"Git operation failed: {e}")
                client.add_comment(
                    task.id, f"⚠️ Git operation failed: {e}", author="Yaver Worker"
                )
        except ImportError:
            pass

    # Update status to CONTROL explicitly via client to ensure sync
    final_status = "control" if result["success"] else "failed"
    client.update_task_status(task.id, final_status)

    return {
        "task": task,
        "output": result.get("output", ""),
        "status": final_status,
        "result": result.get("output", ""),
    }


if __name__ == "__main__":
    print_section_header("Task Manager Test", "🧪")

    # Test task decomposition
    test_request = (
        "Analyze the codebase and create a refactoring plan for high-complexity files"
    )
    decomposition = decompose_task_with_llm(test_request)

    print_info(f"Main task: {decomposition.main_task}")
    print_info(f"Subtasks: {len(decomposition.subtasks)}")
    for i, subtask in enumerate(decomposition.subtasks, 1):
        print(f"  {i}. {subtask}")

    print_success("✅ Task manager module loaded successfully")
