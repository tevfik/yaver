"""
Task Manager Agent - Task decomposition and iterative problem solving
Jules-like iterative development with task tracking
"""

import json
import re
import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

import git
from tools.forge.tool import ForgeTool

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
from config.config import get_config
from tools.analysis.syntax import SyntaxChecker
from agents.agent_coder import CoderAgent


# Mock Client for CLI mode since api_client module is missing
class YaverClient:
    def add_comment(self, task_id, content, author="Yaver Worker"):
        logger.info(f"[{author}] Comment on {task_id}: {content}")

    def update_task_status(self, task_id, status):
        logger.info(f"Task {task_id} status updated to: {status}")


# ============================================================================
# Task Models
# ============================================================================
class TaskDecomposition(BaseModel):
    """Task decomposition result"""

    main_task: str = Field(description="Main task description")
    subtasks: List[str] = Field(description="List of subtasks")
    priorities: Dict[str, Any] = Field(
        default_factory=dict, description="Priority for each subtask"
    )
    dependencies: Dict[str, Any] = Field(
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
            # Support both object and dict
            total_files = (
                getattr(repo_info, "total_files", 0)
                if not isinstance(repo_info, dict)
                else repo_info.get("total_files", 0)
            )
            total_lines = (
                getattr(repo_info, "total_lines", 0)
                if not isinstance(repo_info, dict)
                else repo_info.get("total_lines", 0)
            )
            languages = (
                getattr(repo_info, "languages", [])
                if not isinstance(repo_info, dict)
                else repo_info.get("languages", [])
            )

            context_str += f"\n\nProject Info:\n- File count: {total_files}\n- Total lines: {total_lines}\n- Languages: {languages}"

        if context.get("architecture_analysis"):
            arch = context["architecture_analysis"]
            arch_type = (
                getattr(arch, "architecture_type", "unknown")
                if not isinstance(arch, dict)
                else arch.get("architecture_type", "unknown")
            )
            context_str += f"\n- Architecture: {arch_type}"

    from utils.prompts import DECOMPOSITION_PROMPT

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

        if not isinstance(result, dict):
            logger.error(f"Invalid decomposition result format (not a dict): {result}")
            # If it's a list, maybe it's the subtasks directly
            if isinstance(result, list):
                result = {"subtasks": [str(s) for s in result]}
            else:
                raise KeyError("subtasks")

        # Map 'tasks' to 'subtasks' if LLM hallucinated the key name
        if "tasks" in result and "subtasks" not in result:
            result["subtasks"] = [
                t["title"] if isinstance(t, dict) and "title" in t else str(t)
                for t in result["tasks"]
            ]

        # Handle case where it returned a single task object as the whole response
        if "title" in result and "subtasks" not in result:
            result["subtasks"] = [result["title"]]
            if "description" in result and "main_task" not in result:
                result["main_task"] = result["description"]

        if "main_task" not in result:
            result["main_task"] = user_request

        if "subtasks" not in result or not isinstance(result["subtasks"], list):
            result["subtasks"] = [result.get("main_task") or user_request]

        if "priorities" not in result or not isinstance(result["priorities"], dict):
            result["priorities"] = {s: "medium" for s in result["subtasks"]}

        if "dependencies" not in result or not isinstance(result["dependencies"], dict):
            result["dependencies"] = {}

        if "estimated_complexity" not in result:
            result["estimated_complexity"] = "medium"

        print_success(f"{len(result['subtasks'])} subtasks created")
        return TaskDecomposition(**result)

    except Exception as e:
        logger.error(f"Task decomposition failed: {e}")
        return TaskDecomposition(
            main_task=user_request,
            subtasks=[user_request],
            priorities={user_request: "high"},
            estimated_complexity="unknown",
            dependencies={},
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


from tools.analysis.build_analyzer import BuildAnalyzer


def execute_task_with_llm(task: Task, context: Dict) -> Dict[str, Any]:
    """Execute a single task using LLM"""
    print_section_header(f"Executing task: {task.title}", "⚙️")

    llm = create_llm("code")

    # Prepare context string
    context_str = ""
    repo_path = "."

    if context.get("repo_info"):
        repo_info = context["repo_info"]
        if isinstance(repo_info, dict):
            repo_path = repo_info.get("repo_path", ".")
        else:
            repo_path = getattr(repo_info, "repo_path", ".")

        total_files = (
            getattr(repo_info, "total_files", 0)
            if not isinstance(repo_info, dict)
            else repo_info.get("total_files", 0)
        )
        languages = (
            getattr(repo_info, "languages", [])
            if not isinstance(repo_info, dict)
            else repo_info.get("languages", [])
        )
        context_str += f"\nProject Context:\n- Total files: {total_files}\n- Languages: {languages}"

    # --- BUILD CONTEXT INJECTION ---
    try:
        build_analyzer = BuildAnalyzer(repo_path)
        # Extract potential filenames from task description/title
        # Simple heuristic: look for words with extensions
        import re

        files_mentioned = re.findall(
            r"\b[\w-]+\.\w+\b", task.title + " " + task.description
        )

        if files_mentioned:
            build_contexts = []
            for fname in files_mentioned:
                # We need full path logic ideally, but let's try to find it
                # If we can't resolve, we skip
                # BuildAnalyzer expects absolute path or relative to root
                if os.path.exists(os.path.join(repo_path, fname)):
                    b_ctx = build_analyzer.get_build_context_for_file(
                        os.path.join(repo_path, fname)
                    )
                    if b_ctx["build_type"] != "unknown":
                        build_contexts.append(f"{fname} -> {b_ctx['commands']}")

            if build_contexts:
                context_str += (
                    "\n\nBuild Context (How to compile/test tasks):\n"
                    + "\n".join(build_contexts)
                )
    except Exception as e:
        logger.warning(f"Failed to inject build context: {e}")

    if context.get("file_analyses"):
        analyses = context["file_analyses"]
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

    from utils.prompts import TASK_SOLVER_PROMPT

    prompt = TASK_SOLVER_PROMPT

    print_info(f"Sending request to LLM (Model: {llm.model})...")

    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "task_title": task.title,
                "task_description": task.description,
                "repo_context": context_str,
                "context": "Follow the plan and implement changes.",
            }
        )

        return {"success": True, "output": response.content}

    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        return {"success": False, "error": str(e), "task_id": task.id}


def apply_execution_side_effects(task, result, state=None):
    """
    Apply file changes and git operations from LLM execution result.
    Handles both dict and object (ConfigWrapper) state.
    """
    if not result or not result.get("success"):
        return

    output = result.get("output", "")
    client = YaverClient()

    # Determine repo path
    repo_path = None
    if hasattr(task, "repo_path") and task.repo_path:
        repo_path = task.repo_path
    elif state and state.get("repo_path"):
        repo_path = state.get("repo_path")
    elif state and state.get("repo_info"):
        repo_info = state.get("repo_info")
        if hasattr(repo_info, "repo_path"):
            repo_path = getattr(repo_info, "repo_path")
        elif isinstance(repo_info, dict) and "repo_path" in repo_info:
            repo_path = repo_info["repo_path"]

    if not repo_path:
        repo_path = "."
        logger.warning(f"No repo_path found, using current directory: {repo_path}")
    else:
        logger.info(f"Using repo_path: {repo_path}")

    repo = None
    is_pr_requested = False

    # 1. Detect Intent and Manage Branches (PRE-EMPTIVE)
    try:
        repo = git.Repo(repo_path)

        # Detect PR Intent (check task and original request)
        main_request = state.get("user_request", "").lower() if state else ""
        task_title_low = task.title.lower()
        task_desc_low = task.description.lower()

        # Check if this is a PR feedback task that should NOT create a new branch
        task_metadata = getattr(task, "metadata", {}) or {}
        should_skip_branch = task_metadata.get("skip_branch_creation", False)
        pr_branch = task_metadata.get("pr_branch")

        if should_skip_branch:
            logger.info(
                f"Skipping branch creation for PR feedback task. Staying on current branch."
            )
            if pr_branch:
                try:
                    current = repo.active_branch.name
                    if current != pr_branch:
                        logger.info(
                            f"Ensuring we're on PR branch: {pr_branch} (current: {current})"
                        )
                        repo.git.checkout(pr_branch)
                    else:
                        logger.info(f"Already on PR branch: {pr_branch}")
                except Exception as e:
                    logger.warning(f"Failed to checkout PR branch {pr_branch}: {e}")
        else:
            # Original PR intent detection logic
            is_pr_requested = (
                "pull request" in task_title_low
                or "pull request" in task_desc_low
                or "pull request" in main_request
                or "pr" in task_title_low.split()
                or "pr" in main_request.split()
            )
            logger.info(
                f"PR Intent Detected: {is_pr_requested} (Title: '{task.title}', Main: '{main_request[:50]}...')"
            )

            if is_pr_requested:
                new_branch_name = f"yaver-task-{task.id[:8]}"
                if new_branch_name in repo.heads:
                    logger.info(
                        f"Feature branch {new_branch_name} already exists. Switching to it."
                    )
                    try:
                        repo.git.checkout(new_branch_name)
                        # Try to merge main in case it's behind
                        try:
                            logger.info("Merging latest 'main' into feature branch...")
                            repo.git.pull("origin", "main", "--no-edit")
                        except Exception as merge_err:
                            logger.warning(f"Failed to auto-merge main: {merge_err}")
                    except Exception as checkout_err:
                        logger.warning(
                            f"Regular checkout failed, trying forced checkout: {checkout_err}"
                        )
                        repo.git.checkout("-f", new_branch_name)
                else:
                    logger.info(f"Creating feature branch: {new_branch_name}")
                    new_branch = repo.create_head(new_branch_name)
                    new_branch.checkout()
    except Exception as git_pre_err:
        logger.warning(f"Git pre-emptive branching failed: {git_pre_err}")

    # 2. File extraction and writing
    # Regex to match ```language:filepath or ```filepath
    pattern = r"```(?:\w+)?(?::([^\n]+))?\n(.*?)```"
    matches = re.finditer(pattern, output, re.DOTALL)

    changes_applied = False
    applied_files = []

    for match in matches:
        file_path_raw = match.group(1)
        code = match.group(2)

        if not file_path_raw:
            continue

        file_path = file_path_raw.strip()
        if " " in file_path or "(" in file_path or "=" in file_path:
            continue

        # Safety check: avoid writing to root or directories as files
        if file_path in [".", "./", ""] or file_path.endswith("/"):
            logger.warning(f"Skipping invalid file path from LLM: '{file_path}'")
            continue

        full_path = os.path.join(repo_path, file_path)

        # Safety check: Is it an existing directory?
        if os.path.isdir(full_path):
            logger.warning(f"Skipping write to existing directory: '{file_path}'")
            continue

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code)

            # --- SYNTAX & AUTO-FIX LOOP ---
            try:
                checker = SyntaxChecker()
                syntax_result = checker.check(full_path)

                if not syntax_result.valid:
                    error_msg = syntax_result.error_message
                    tool_used = syntax_result.tool_used
                    logger.warning(
                        f"⚠️ Syntax Error in {file_path} (via {tool_used}): {error_msg}"
                    )

                    client.add_comment(
                        task.id,
                        f"⚠️ Syntax Error detected ({tool_used}). Attempting auto-fix...\nError: {error_msg}",
                        author="SyntaxGuard",
                    )

                    # Attempt Fix (One-shot)
                    coder = CoderAgent()
                    fixed_response = coder.fix_code(
                        code, f"Compiler/Linter Error ({tool_used}): {error_msg}"
                    )

                    # Extract code from response
                    fix_match = re.search(
                        r"```(?:\w+)?\n(.*?)```", fixed_response, re.DOTALL
                    )
                    if fix_match:
                        new_code = fix_match.group(1)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(new_code)

                        # Re-verify
                        recheck = checker.check(full_path)
                        if recheck.valid:
                            logger.info(f"✅ Auto-fix successful for {file_path}")
                            client.add_comment(
                                task.id,
                                f"✅ Auto-fix successful for {file_path}.",
                                author="SyntaxGuard",
                            )
                            # Update 'code' variable in case we use it later
                            code = new_code
                        else:
                            logger.warning(f"❌ Auto-fix failed for {file_path}")
                            client.add_comment(
                                task.id,
                                f"❌ Auto-fix failed. Remaining error: {recheck.error_message}",
                                author="SyntaxGuard",
                            )
                    else:
                        logger.warning(
                            "Could not extract fixed code from agent response."
                        )

            except Exception as syntax_err:
                logger.error(f"Syntax/Auto-fix logic failed: {syntax_err}")
                # Don't stop the whole process, just log

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
        client.add_comment(
            task.id,
            f"📝 Modified files:\n- " + "\n- ".join(applied_files),
            author="Yaver Worker",
        )

    # 3. Git Add (Staging)
    try:
        if repo and repo.is_dirty(untracked_files=True) and changes_applied:
            repo.git.add(A=True)
            logger.info("Changes staged for commit.")
            client.add_comment(
                task.id,
                f"📝 Changes staged:\n- " + "\n- ".join(applied_files),
                author="Yaver Worker",
            )

            # Track staged changes in state if available
            if state is not None:
                current_staged = state.get("staged_files", [])
                state["staged_files"] = list(set(current_staged + applied_files))

    except Exception as e:
        logger.warning(f"Git staging failed: {e}")
        client.add_comment(
            task.id, f"⚠️ Git staging failed: {e}", author="Yaver Worker"
        )


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


def commit_and_push_bundle(state: Dict[str, Any], repo_path: str):
    """
    Commits staged changes, pushes to remote, handles PRs, and reacts to comments.
    Executes only once per session/task bundle.
    """
    from tools.forge.tool import ForgeTool
    from tools.git.ops import GitOps
    import git

    logger.info("Executing final commit bundle...")
    tasks = state.get("tasks", [])
    if not tasks:
        return

    # Use the first task (Main Task) for the commit message usually
    # Or find the reactive task (originating_comment_id)
    main_task = tasks[0]
    reactive_task = next(
        (t for t in tasks if getattr(t, "originating_comment_id", None)), main_task
    )

    repo = git.Repo(repo_path)
    commit_msg = f"fix: {reactive_task.title} (Task {reactive_task.id[:8]})"

    # 1. Commit
    if repo.is_dirty() or len(repo.index.diff("HEAD")) > 0:
        try:
            # Use git binary directly to handle merge states (MERGE_HEAD) correctly
            repo.git.commit("-m", commit_msg)
            logger.info(f"Committed bundle: {commit_msg}")
        except Exception:
            # Fallback to GitPython index commit if binary fails or for empty commits
            # Note: This might lose merge parents if in merge state
            repo.index.commit(commit_msg)
            logger.info(f"Committed bundle (fallback): {commit_msg}")
    else:
        logger.info("No changes to commit.")
        return

    # 2. Push & Handle Branches
    current_branch = repo.active_branch.name

    try:
        # Check if we need to push (default yes for social developer)
        logger.info(f"Pushing {current_branch} to remote...")
        repo.git.push("-u", "origin", current_branch)
    except Exception as push_err:
        logger.warning(f"Push failed: {push_err}")
        # Handle non-fast-forward (diverged branch)
        if "non-fast-forward" in str(push_err) or "rejected" in str(push_err):
            try:
                logger.info("Attempting rebase to resolve divergence...")
                repo.git.pull("--rebase", "origin", current_branch)
                repo.git.push("-u", "origin", current_branch)
                logger.info("✅ Rebase and push successful.")
            except Exception as rebase_err:
                logger.error(f"Rebase failed: {rebase_err}")
                # Safe fallback: Only force push if it is a 'fix/' branch managed by us
                if current_branch.startswith("fix/"):
                    logger.warning("⚠️ Force pushing to owned fix branch...")
                    repo.git.push("-u", "origin", current_branch, force=True)
                else:
                    logger.error("Cannot push changes.")

        # 3. Create/Update PR Logic
        active_pr = state.get("active_pr")
        forge = ForgeTool(repo_path=repo_path)

        if not active_pr:
            try:
                # Check if PR exists first (maybe created externally or just missed)
                # Gitea/Github usually returns existing if we try to create, but let's be safe
                # We don't have a direct "find_pr_by_branch" exposed in ForgeTool convenient wrapper yet,
                # but create_pr usually fails if exists or returns it.
                # Let's try to create.
                pr_title = f"{main_task.title}"
                pr_body = f"Autogenerated by Yaver Agent.\n\nTask: {main_task.title}\nID: {main_task.id}"

                logger.info(f"Creating PR for {current_branch}...")
                active_pr = forge.run(
                    "create_pr",
                    title=pr_title,
                    body=pr_body,
                    head=current_branch,
                    base="main",
                )

                if active_pr:
                    logger.info(f"✅ Created PR #{active_pr.get('number')}")
                    state["active_pr"] = active_pr
            except Exception as pr_err:
                logger.warning(f"Failed to create PR (might already exist): {pr_err}")
                # Try to fetch it? for now just ignore.

        # 4. Aesthetic Reaction (Eyes -> Thumbs Up)
        originating_comment_id = getattr(reactive_task, "originating_comment_id", None)
        if originating_comment_id:
            try:
                forge = ForgeTool(repo_path=repo_path)
                forge.run(
                    "add_reaction", issue_id=originating_comment_id, reaction="+1"
                )
                logger.info(
                    f"Added success reaction (+1) to comment {originating_comment_id}"
                )

                # Also reply with a summary comment
                staged_files = state.get("staged_files", [])
                summary_body = f"🚀 **Fix Deployed**\n\nI have addressed the feedback with the following changes:\n"
                for f in staged_files:
                    summary_body += f"- `{f}`\n"
                summary_body += f"\nCommit: `{commit_msg}`"

                if active_pr:
                    pr_id = active_pr.get("number") or active_pr.get("id")
                    forge.run("comment_issue", issue_id=pr_id, body=summary_body)

            except Exception as e:
                logger.warning(f"Failed to post aesthetic reaction/comment: {e}")

    except Exception as push_err:
        logger.error(f"Push failed: {push_err}")


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

    # --- Reactive PR Monitoring ---
    active_pr = state.get("active_pr")
    repo_path = state.get("repo_path")

    # Proactive PR Detection: If missing from state, try to find it for the current branch
    if not active_pr and repo_path:
        try:
            from tools.git.ops import GitOps

            git_tool = GitOps(repo_path)
            if git_tool.repo:
                current_branch = git_tool.repo.active_branch.name
                if current_branch and current_branch != "main":
                    logger.info(
                        f"Proactively searching for PR for branch '{current_branch}'..."
                    )
                    forge = ForgeTool(repo_path=repo_path)
                    pr_info = forge.run(
                        "find_pr_by_branch", head=current_branch, base="main"
                    )
                    if isinstance(pr_info, dict) and "id" in pr_info:
                        active_pr = pr_info
                        state["active_pr"] = pr_info
                        logger.info(
                            f"Auto-detected active PR #{active_pr.get('number') or active_pr.get('id')} for monitoring."
                        )
        except Exception as detect_err:
            logger.warning(f"PR auto-detection failed: {detect_err}")

    if active_pr and isinstance(active_pr, dict):
        try:
            forge = ForgeTool(repo_path=repo_path)
            pr_id = active_pr.get("number") or active_pr.get("id")

            logger.info(f"Monitoring PR #{pr_id} for new feedback...")

            # 0. Get Agent Username
            agent_username = "yaver"
            try:
                user_info = forge.run("get_user")
                if isinstance(user_info, dict):
                    agent_username = (
                        user_info.get("login") or user_info.get("username") or "yaver"
                    )
                logger.debug(f"Agent identified as: {agent_username}")
            except Exception as login_err:
                logger.warning(f"Failed to identify agent user: {login_err}")

            # 1. Check PR status before processing
            pr_data = forge.run("get_pr", issue_id=pr_id)
            if isinstance(pr_data, dict) and pr_data.get("state") != "open":
                logger.info(
                    f"PR #{pr_id} is {pr_data.get('state')}. Skipping reactive loop."
                )
                return state

            # 2. Fetch comments
            comments = forge.run("list_comments", issue_id=pr_id)
            if isinstance(comments, list):
                if "processed_comment_ids" not in active_pr:
                    active_pr["processed_comment_ids"] = []

                logger.debug(f"Found {len(comments)} comments on PR #{pr_id}")

                # 3. Process NEW comments (excluding own)
                for comment in comments:
                    comment_id = comment.get("id")
                    comment_body = comment.get("body", "").strip()
                    user_info = comment.get("user", {})
                    username = user_info.get("login") or user_info.get("username")

                    # Ignore own comments and already processed ones
                    is_own_comment = username == agent_username
                    if os.environ.get("YAVER_SIMULATE_REVIEWER") == "1":
                        is_own_comment = False
                        logger.debug(
                            f"Simulating reviewer: Not ignoring comment from {username}"
                        )

                    if comment_id in active_pr["processed_comment_ids"]:
                        logger.debug(f"Skipping already processed comment {comment_id}")
                        continue

                    if is_own_comment:
                        logger.debug(
                            f"Skipping self-authored comment {comment_id} from {username}"
                        )
                        continue

                    logger.info(f"New PR feedback from {username}: {comment_body}")

                    # A. REACT (eyes emoji)
                    try:
                        forge.run("add_reaction", issue_id=comment_id, reaction="eyes")
                    except Exception as e:
                        logger.debug(f"Failed to add reaction: {e}")

                    # B. ACKNOWLEDGE
                    ack_msg = f"👀 I've seen your feedback: '{comment_body}'\n\nI'm starting to work on this now. I'll push the fixes shortly."
                    ack_comment = forge.run(
                        "comment_issue", issue_id=pr_id, body=ack_msg
                    )

                    if isinstance(ack_comment, dict) and "id" in ack_comment:
                        active_pr["processed_comment_ids"].append(ack_comment["id"])

                    # C. CREATE TASK
                    # IMPORTANT: This task should work on the SAME branch as the PR
                    # We mark it with metadata to prevent creating a new branch
                    new_task_id = create_task_id()
                    # Check for conflict resolution request
                    is_conflict = any(
                        k in comment_body.lower()
                        for k in ["conflict", "merge", "çakışma", "kavga", "resolve"]
                    )

                    reactive_task = Task(
                        id=new_task_id,
                        title=f"{'Resolve Conflict' if is_conflict else 'Fix PR Feedback'}: {comment_body[:50]}...",
                        description=f"{'Resolve merge conflicts and ' if is_conflict else ''}Address reviewer feedback on PR #{pr_id}: {comment_body}",
                        priority=TaskPriority.HIGH,
                        status=TaskStatus.PENDING,
                        iteration=0,
                        originating_comment_id=comment_id,
                        metadata={
                            "is_pr_feedback": True,
                            "is_conflict_resolution": is_conflict,
                            "pr_id": pr_id,
                            "pr_branch": active_pr.get("head", {}).get("ref")
                            if isinstance(active_pr.get("head"), dict)
                            else None,
                            "skip_branch_creation": True,
                        },
                    )

                    tasks.append(reactive_task)
                    active_pr["processed_comment_ids"].append(comment_id)
                    logger.info(
                        f"Created reactive task {new_task_id} for comment {comment_id}"
                    )
            else:
                logger.warning(f"Failed to fetch comments for PR #{pr_id}: {comments}")

        except Exception as e:
            logger.warning(f"PR monitoring failed: {e}")
            import traceback

            logger.debug(traceback.format_exc())

    # Get next task
    next_task = get_next_task(tasks)

    if not next_task:
        print_info("All tasks completed or blocked")

        # Ensure we commit any pending bundles if we are finishing up
        if state.get("staged_files"):
            try:
                repo_path = state.get("repo_path")
                commit_and_push_bundle(state, repo_path)
            except Exception as e:
                logger.error(f"Final commit bundle failed: {e}")

                logger.error(f"Final commit bundle failed: {e}")

        state["should_continue"] = False
        state["log"] = state.get("log", []) + [
            format_log_entry("TaskManager", "No more tasks to execute")
        ]

        # Check for PR Conflict
        if state.get("active_pr"):
            active_pr = state["active_pr"]
            # Check if mergeable info is available and False
            if active_pr.get("mergeable") is False:
                conflict_msg = f"⚠️ PR #{active_pr.get('number')} has merge conflicts that need manual resolution."
                logger.warning(conflict_msg)
                state["log"].append(format_log_entry("TaskManager", conflict_msg))

            # Also helpful for Gitea which might use a different field or need explicit check
            # But 'mergeable' is standard GitHub/Gitea API field usually populated on detail view.

        return state

    # Update task status to in-progress
    next_task.status = TaskStatus.IN_PROGRESS
    next_task.iteration = iteration_count + 1

    # Execute task
    context = {
        "repo_info": state.get("repo_info"),
        "architecture_analysis": state.get("architecture_analysis"),
        "refactoring_plan": state.get("refactoring_plan"),
    }

    # Pre-Execution Setup for Conflict Resolution
    task_metadata = getattr(next_task, "metadata", {}) or {}
    if task_metadata and task_metadata.get("is_conflict_resolution"):
        logger.info(
            f"🔧 Preparing environment for conflict resolution task {next_task.id}..."
        )
        try:
            import git

            repo_path = state.get("repo_path") or "."
            repo = git.Repo(repo_path)

            # Ensure we are on the PR branch
            pr_branch = task_metadata.get("pr_branch")
            if pr_branch:
                if repo.active_branch.name != pr_branch:
                    logger.info(
                        f"Switching to PR branch {pr_branch} for conflict resolution..."
                    )
                    repo.git.checkout(pr_branch)

            # Attemp merge to reproduce conflict markers
            try:
                # Determine target branch from PR state or default to origin/main
                target_branch = "origin/main"
                active_pr = state.get("active_pr")
                if active_pr:
                    base_info = active_pr.get("base", {})
                    # Handle different API shapes (dict vs obj vs string)
                    if isinstance(base_info, dict) and base_info.get("ref"):
                        target_branch = f"origin/{base_info['ref']}"
                    elif hasattr(base_info, "ref"):
                        target_branch = f"origin/{base_info.ref}"

                logger.info(
                    f"Attempting merge with {target_branch} to reproduce conflicts..."
                )
                repo.git.fetch("origin")  # Ensure we have latestRefs
                repo.git.merge(target_branch)
            except git.GitCommandError as e:
                if "conflict" in str(e).lower():
                    logger.info(
                        "✅ Conflict markers reproduced successfully. LLM will see them."
                    )
                else:
                    logger.warning(f"Merge failed with unexpected error: {e}")

        except Exception as e:
            logger.error(f"Failed to prepare conflict environment: {e}")

    execution_result = execute_task_with_llm(next_task, context)

    # Side Effects: Apply changes and Git Commit/Push
    apply_execution_side_effects(next_task, execution_result, state)

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

    # Update state
    state["tasks"] = tasks
    state["current_task"] = next_task
    state["iteration_count"] = iteration_count + 1
    state["completed_tasks"] = state.get("completed_tasks", []) + (
        [next_task.id] if execution_result["success"] else []
    )
    state["should_continue"] = should_continue
    state["active_pr"] = active_pr  # Persist PR state

    new_log = [
        format_log_entry(
            "TaskManager",
            f"Iteration {iteration_count + 1}: Executed task {next_task.id}",
        ),
        format_log_entry(
            "TaskManager",
            f"Status: {'✅ Success' if execution_result['success'] else '❌ Failed'}",
        ),
    ]
    state["log"] = state.get("log", []) + new_log

    # Run final commit bundle if all tasks are completed
    if not should_continue and state.get("staged_files"):
        try:
            repo_path = state.get("repo_path")
            commit_and_push_bundle(state, repo_path)
        except Exception as e:
            logger.error(f"Final commit bundle failed: {e}")
            state["log"] = state.get("log", []) + [
                format_log_entry("TaskManager", f"❌ Bundle commit failed: {e}")
            ]

    return state


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

        state.update(
            {
                "tasks": tasks,
                "iteration_count": 0,
                "completed_tasks": [],
                "log": state.get("log", [])
                + [
                    format_log_entry("TaskManager", f"Created {len(tasks)} tasks"),
                    format_log_entry(
                        "TaskManager",
                        f"Complexity: {decomposition.estimated_complexity}",
                    ),
                ],
            }
        )
        return state
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
    apply_execution_side_effects(task, result, state)

    # Update status to CONTROL explicitly via client to ensure sync
    final_status = "control" if result["success"] else "failed"
    client.update_task_status(task.id, final_status)

    return {
        "task": task,
        "output": result.get("output", ""),
        "status": final_status,
        "result": result.get("output", ""),
    }


def social_developer_node(state: YaverState) -> dict:
    """
    Social Developer Agent Node.
    Monitors multiple repositories for activity and dispatches tasks.
    """
    from tools.forge.tool import ForgeTool
    from tools.git.client import GitClient
    import shutil

    logger.info("👀 Social Developer Agent monitoring...")

    forge = ForgeTool()  # Uses global config to authenticate
    repos = forge.run("list_repositories")

    if not isinstance(repos, list):
        logger.warning(f"Failed to list repositories: {repos}")
        return state

    processed_any = False

    # 1. Global Context First (Mentions) - Usually provider independent or global
    mentions = forge.run("list_mentions")
    all_items = []

    if isinstance(mentions, list):
        all_items.extend([{"type": "mention", "data": m} for m in mentions])

    # 2. Iterate Repos for Context-Specific Items (Assignments, Review Requests)
    for repo in repos:
        repo_name = repo.get("name")
        repo_full_name = repo.get("full_name") or repo.get("name")
        owner_data = repo.get("owner", {})
        owner_login = owner_data.get("login") or owner_data.get("username")

        # Skip if necessary (e.g. forks, archived)
        if repo.get("archived"):
            continue

        logger.info(f"Checking {repo_full_name} for tasks...")

        # Switch Context
        try:
            forge.run("set_repo", owner=owner_login, repo=repo_name)
        except Exception as e:
            logger.warning(f"Failed to switch context to {repo_full_name}: {e}")
            continue

        # Check for Assignments & Reviews in THIS repo
        assigned = forge.run("list_assigned_issues")
        if isinstance(assigned, list):
            # Enrich data with repo context if missing
            for a in assigned:
                if "repository" not in a:
                    a["repository"] = repo
                all_items.append({"type": "assignment", "data": a})

        review_requests = forge.run("list_review_requests")
        if isinstance(review_requests, list):
            for r in review_requests:
                # Ensure we have repo context
                if "repository" not in r:
                    r["repository"] = repo
                # Also ensure basic PR fields
                if "base" not in r:  # Some list views might be summary only
                    # If we need details, we might fetch get_pr later
                    pass
                all_items.append({"type": "review_request", "data": r})

    if not all_items:
        logger.info("No active social tasks found.")
        return state

    # Deduplicate items by ID/Global ID to avoid processing same thing twice if API overlaps
    # (Not implemented yet, assuming APIs are distinct enough or we handle idempotency later)

    for item in all_items:
        item_type = item["type"]
        data = item["data"]

        # Determine Context
        repository = data.get("repository")

        # If review request, 'repository' might be missing in search results sometimes, check 'url'
        if not repository and "repository_url" in data:
            # We can parse text? Or just assume we are in current repo for MVP
            # For now, let's assume we operate on the current folder's repo if context matches
            pass

        # MVP: Only process logic if we are "in" that repo or can switch to it.
        # But for 'social agent', we typically want to switch context.
        # Here we will just log and attempt local Review if it matches current dir

        issue_number = data.get("number")
        title = data.get("title")

        if item_type == "review_request":
            # Extract Repo Info from Item Data if available
            # In update above, we attached 'repository' object to data
            repo_info = data.get("repository", {})
            repo_full_name = repo_info.get("full_name") or repo_info.get("name")
            repo_ssh_url = repo_info.get("ssh_url") or repo_info.get("clone_url")

            logger.info(
                f"🔍 Found PR Review Request: #{issue_number} - {title} in {repo_full_name}"
            )

            # 1. Initialize Reviewer
            from agents.agent_reviewer import ReviewerAgent

            # We need to ensure we are in the correct directory for this repo
            # Determine local path
            workspace_dir = os.path.expanduser("~/.yaver/workspaces")
            local_repo_path = os.path.join(workspace_dir, repo_full_name)

            # Switch Forge Context to this repo for commenting
            owner = repo_info.get("owner", {}).get("login") or repo_info.get(
                "owner", {}
            ).get("username")
            name = repo_info.get("name")
            if owner and name:
                forge.run("set_repo", owner=owner, repo=name)

            # Clone if missing
            if not os.path.exists(local_repo_path):
                logger.info(f"Cloning {repo_full_name} to {local_repo_path}...")
                GitClient.clone(repo_ssh_url, local_repo_path)

            reviewer = ReviewerAgent(repo_path=local_repo_path)

            # 2. Checkout & Diff
            git = GitClient(local_repo_path)
            # Ensure we fetch the PR
            # checkout_pr handles fetching refs/pull/ID/head
            if git.checkout_pr(issue_number):
                # Diff from base (usually integration target like main/develop)
                base_branch = "main"
                if "base" in data:
                    base_ref = data["base"].get("ref")
                    if base_ref:
                        base_branch = base_ref

                # We need to make sure we have the base branch locally to diff against
                # Or use origin/base_branch
                try:
                    git.repo.remotes.origin.fetch()
                except:
                    pass

                # Diff against the base branch (remote)
                # If we use just "main", it might be local main which is old.
                # Safer to use origin/main if available
                target_base = f"origin/{base_branch}"

                diff_content = git.get_diff(target_base)

                if not diff_content:
                    # Fallback to local branch if origin ref missing
                    diff_content = git.get_diff(base_branch)

                if not diff_content:
                    logger.warning("Empty diff, skipping review.")
                    continue

                # 3. Analyze
                logger.info(f"Running automated review on PR #{issue_number}...")
                review_report = reviewer.review_code(
                    code=diff_content[:20000],  # Token limit safeguard
                    requirements="Review this Pull Request diff for security, bugs, and DORA metrics risks. Focus on the changes.",
                    file_path=f"PR #{issue_number}",
                )

                # 4. Post Feedback
                forge.run(
                    "comment_issue",
                    issue_id=issue_number,
                    body=f"## 🤖 Yaver Auto-Review\n\n{review_report}",
                )
                logger.info(f"Posted review to PR #{issue_number}")
                processed_any = True

            else:
                logger.error(f"Failed to checkout PR #{issue_number}")

        elif item_type == "mention":
            # Mentions (Notifications) have different structure
            subject = data.get("subject", {})
            title = subject.get("title")
            url = subject.get("url", "")
            try:
                issue_number = int(url.split("/")[-1])
            except (ValueError, IndexError):
                issue_number = None

            subject_type = subject.get("type")  # PullRequest or Issue

            repo_info = data.get("repository", {})
            repo_full_name = repo_info.get("full_name") or repo_info.get("name")
            repo_ssh_url = repo_info.get("ssh_url") or repo_info.get("clone_url")

            logger.info(f"🔔 Mentioned in {repo_full_name} #{issue_number}: {title}")

            if subject_type == "PullRequest" and issue_number:
                logger.info(
                    f"Mention is on a PR. Triggering auto-review for PR #{issue_number}..."
                )

                # 1. Initialize Reviewer Logic (Duplicated for robustness/independence)
                from agents.agent_reviewer import ReviewerAgent

                workspace_dir = os.path.expanduser("~/.yaver/workspaces")
                local_repo_path = os.path.join(workspace_dir, repo_full_name)

                # Switch Forge Context
                owner = repo_info.get("owner", {}).get("login") or repo_info.get(
                    "owner", {}
                ).get("username")
                name = repo_info.get("name")
                if owner and name:
                    forge.run("set_repo", owner=owner, repo=name)

                # Clone if missing
                if not os.path.exists(local_repo_path):
                    logger.info(f"Cloning {repo_full_name} to {local_repo_path}...")
                    GitClient.clone(repo_ssh_url, local_repo_path)

                reviewer = ReviewerAgent(repo_path=local_repo_path)

                # 2. Checkout & Diff
                git = GitClient(local_repo_path)
                if git.checkout_pr(issue_number):
                    base_branch = "main"
                    # Notifications don't give base branch info easily without fetching PR details
                    # We can try to fetch PR details
                    try:
                        pr_details = forge.run("get_pr", issue_id=issue_number)
                        if isinstance(pr_details, dict) and "base" in pr_details:
                            base_branch = pr_details["base"].get("ref", "main")
                    except Exception:
                        pass

                    try:
                        git.repo.remotes.origin.fetch()
                    except:
                        pass

                    target_base = f"origin/{base_branch}"
                    diff_content = git.get_diff(target_base)

                    if not diff_content:
                        diff_content = git.get_diff(base_branch)

                    if diff_content:
                        # 3. Analyze
                        logger.info(
                            f"Running automated review on PR #{issue_number} (Mention Trigger)..."
                        )
                        review_report = reviewer.review_code(
                            code=diff_content[:20000],
                            requirements="You were summoned via mention. Review this Pull Request diff for security, bugs, DORA metrics, and logical checks.",
                            file_path=f"PR #{issue_number}",
                        )

                        # 4. Post Feedback
                        forge.run(
                            "comment_issue",
                            issue_id=issue_number,
                            body=f"## 🤖 Yaver Auto-Review (Mentioned)\n\n{review_report}",
                        )
                        logger.info(
                            f"Posted mention-response review to PR #{issue_number}"
                        )
                        processed_any = True
                    else:
                        logger.warning("Empty diff, skipping review.")
                else:
                    logger.error(f"Failed to checkout PR #{issue_number}")
            else:
                logger.info(
                    "Mention is not on a PR (or ID missing). Skipping auto-review."
                )

    if not processed_any:
        logger.info("No new actionable items found.")

    return state


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
