"""
Git Analyzer Agent - Repository analysis and code quality assessment
Combines features from IntelligentAgent's git_analysis plugin
"""

import os
import subprocess
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, Counter
import re
import asyncio

import git

# lizard and radon imports removed as they are now in tools/metrics/complexity.py
from bandit.core import manager as bandit_manager
from bandit.core import config as bandit_config

# Import local Parser for AST extraction
from tools.analysis.graph import GraphIndexer
from tools.analysis.parser import CodeParser
from tools.metrics.complexity import MetricsManager

from agents.agent_base import (
    YaverState,
    RepositoryInfo,
    FileAnalysis,
    ArchitectureAnalysis,
    logger,
    print_section_header,
    print_success,
    print_error,
    print_warning,
    create_llm,
    format_log_entry,
)
from config.config import get_config
from agents.agent_graph import GraphManager
from agents.agent_memory import get_memory_manager, MemoryType
from utils.prompts import ARCHITECTURE_JSON_PROMPT, GIT_ARCHITECT_SYSTEM_PROMPT


# ============================================================================
# Constants
# ============================================================================
SUPPORTED_PARSER_EXTENSIONS = {
    ".py",
    ".c",
    ".cpp",
    ".cc",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
}


# ============================================================================
# Helper Functions
# ============================================================================
def is_text_file(file_path: Path) -> bool:
    """Check if file is a text file (not binary)"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(512)
        return True
    except (UnicodeDecodeError, PermissionError):
        return False


def get_language_from_extension(file_path: str) -> str:
    """Determine programming language from file extension"""
    extension_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".jsx": "JavaScript (React)",
        ".ts": "TypeScript",
        ".tsx": "TypeScript (React)",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".c": "C",
        ".cpp": "C++",
        ".cc": "C++",
        ".h": "C/C++ Header",
        ".hpp": "C++ Header",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".r": "R",
        ".sh": "Shell",
        ".bash": "Bash",
        ".html": "HTML",
        ".css": "CSS",
        ".scss": "SCSS",
        ".sql": "SQL",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".json": "JSON",
        ".xml": "XML",
        ".md": "Markdown",
    }
    ext = Path(file_path).suffix.lower()
    return extension_map.get(ext, "Unknown")


def should_ignore_file(file_path: Path) -> bool:
    """Check if file should be ignored in analysis"""
    ignore_patterns = [
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "build",
        "dist",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dll",
        "*.exe",
        "*.o",
        "*.a",
        ".egg-info",
        ".eggs",
        ".coverage",
        "htmlcov",
        ".DS_Store",
        "Thumbs.db",
        "*.log",
    ]
    path_str = str(file_path)
    for pattern in ignore_patterns:
        if pattern.startswith("*."):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True
    return False


def analyze_file(file_path: Path, repo_root: Path) -> Optional[FileAnalysis]:
    """Analyze a single file"""
    if should_ignore_file(file_path) or not is_text_file(file_path):
        return None

    language = get_language_from_extension(str(file_path))
    if language == "Unknown":
        return None

    # Use MetricsManager for unified analysis
    metrics_manager = MetricsManager()
    metrics = metrics_manager.get_metrics(file_path)

    lines = metrics.get("lines", {})
    code_lines = lines.get("code", 0)

    if code_lines == 0:
        return None

    analysis = FileAnalysis(
        file_path=str(file_path.relative_to(repo_root)),
        language=language,
        lines_of_code=code_lines,
        complexity=0,
        maintainability=100.0,
        code_smells=[],
        security_issues=[],
        suggestions=[],
    )

    # 1. Complexity & Security Stats
    stats = metrics.get("complexity")
    if stats:
        analysis.complexity = stats.get("avg_complexity", 0)
        # Default to 100 if None (e.g. Lizard doesn't provide it)
        analysis.maintainability = stats.get("maintainability_index") or 100.0

        complex_funcs = stats.get("complex_functions", [])
        if complex_funcs:
            # Format complex functions for suggestion
            # complex_funcs is a list of dicts now: [{'name': '...', 'complexity': 12}, ...]
            func_names = [f"{f['name']} ({f['complexity']})" for f in complex_funcs]
            analysis.suggestions.append(
                f"Refactor complex functions: {', '.join(func_names[:3])}"
            )

    # 2. Extract Structural Memory (Classes, Functions) using CodeParser
    try:
        if file_path.suffix.lower() in SUPPORTED_PARSER_EXTENSIONS:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            parser = CodeParser(language)
            structure = parser.parse(content, str(file_path))

            # Integrate with Memory Manager (Vector + Graph)
            memory_manager = get_memory_manager()
            repo_name = repo_root.name

            # Store Classes
            for cls_name in structure.get("classes", []):
                # Simple extraction of the class block is hard without exact line numbers from current parser,
                # so we store the whole file snippet or specific lines if parser supports it.
                # Assuming parser returns just names for now, we index the symbol presence.
                memory_manager.add_code_memory(
                    file_path=str(file_path.relative_to(repo_root)),
                    code_snippet=f"Class {cls_name} defined in {file_path}",  # Placeholder for full body
                    symbol_name=cls_name,
                    symbol_type="Class",
                    metadata={"repo_name": repo_name, "language": language},
                )

            # Store Functions
            for func_name in structure.get("functions", []):
                memory_manager.add_code_memory(
                    file_path=str(file_path.relative_to(repo_root)),
                    code_snippet=f"Function {func_name} defined in {file_path}",
                    symbol_name=func_name,
                    symbol_type="Function",
                    metadata={"repo_name": repo_name, "language": language},
                )

    except Exception as e:
        logger.debug(f"Failed to extract structure from {file_path}: {e}")

    return analysis


def analyze_repository_files(
    repo: git.Repo,
) -> Tuple[List[FileAnalysis], Dict[str, int]]:
    """Analyze all files in repository"""
    print_section_header("Analyzing files", "🔍")
    repo_root = Path(repo.working_dir)
    file_analyses = []
    language_stats = defaultdict(int)

    for file_path in repo_root.rglob("*"):
        if file_path.is_file():
            # Pass repo_root to calculate relative paths correctly
            analysis = analyze_file(file_path, repo_root)
            if analysis:
                file_analyses.append(analysis)
                language_stats[analysis.language] += 1

    print_success(f"{len(file_analyses)} files analyzed")
    return file_analyses, dict(language_stats)


# ... (Keeping Architecture Analysis and Git Operations similar to original if needed)
# For brevity, I am assuming the critical update was integrating CodeParser and MemoryManager into analyze_file.

# ... Redefining other required functions (clone_or_open_repository, get_repository_info, git_analyzer_node)
# to ensure the file is complete.


def clone_or_open_repository(repo_url_or_path: str) -> Optional[git.Repo]:
    """Clone remote repository or open local repository"""
    config = get_config()
    logger.info(f"Opening repo: {repo_url_or_path}")

    if os.path.exists(repo_url_or_path) and os.path.isdir(repo_url_or_path):
        try:
            # Just instantiate regardless of .git existence for analysis
            return git.Repo(repo_url_or_path)
        except git.InvalidGitRepositoryError:
            logger.warning(f"Not a git repo, treating as directory: {repo_url_or_path}")
            # Mock a repo object or return None and handle directory walk manually?
            # For now, let's just return a Mock if possible, or try to init a temp git repo?
            # Simplest: Just use git.Repo.init(repo_url_or_path) if valid dir?
            # No, do not modify user dir.
            # We will handle Non-Git dirs by ensuring the caller handles 'repo' object failure gracefully,
            # but here we return None.
            return None
        except Exception as e:
            return None

    # Clone logic...
    temp_dir = Path("./temp_repos")
    temp_dir.mkdir(exist_ok=True)
    repo_name = repo_url_or_path.split("/")[-1].replace(".git", "")
    clone_path = temp_dir / repo_name

    if clone_path.exists():
        return git.Repo(clone_path)

    try:
        return git.Repo.clone_from(repo_url_or_path, clone_path, depth=1)
    except Exception as e:
        logger.error(f"Clone failed: {e}")
        return None


def get_repository_info(repo: git.Repo) -> RepositoryInfo:
    """Extract repository information"""
    try:
        repo_path = str(Path(repo.working_dir).resolve())
        # Safe access to git properties
        try:
            repo_url = repo.remotes.origin.url
        except:
            repo_url = "local"

        try:
            branch = repo.active_branch.name
        except:
            branch = "detached"

        return RepositoryInfo(
            repo_path=repo_path,
            repo_url=repo_url,
            branch=branch,
            last_commit="unknown",
            contributors=[],
        )
    except Exception:
        return RepositoryInfo(
            repo_path=".",
            repo_url="",
            branch="unknown",
            last_commit="",
            contributors=[],
        )


import json
from langchain_core.messages import SystemMessage, HumanMessage


def analyze_architecture(
    repo_path: Path,
    file_analyses: List[FileAnalysis],
    code_structure: Optional[List[Dict]] = None,
    user_request: str = "",
    mermaid_graph: Optional[str] = None,
) -> ArchitectureAnalysis:
    """Analyze project architecture using LLM"""
    print_section_header("Analyzing architecture", "🏛️")

    # 1. Prepare Context from Analysis
    total_files = len(file_analyses)
    total_loc = sum(f.lines_of_code for f in file_analyses)
    langs = Counter(f.language for f in file_analyses)

    # Top files by complexity
    complex_files = sorted(
        file_analyses, key=lambda f: f.complexity or 0, reverse=True
    )[:10]
    complex_files_summary = "\n".join(
        [
            f"- {f.file_path} (Complexity: {f.complexity}, Lang: {f.language})"
            for f in complex_files
        ]
    )

    # NEW: Read content of top complex files for context (to prevent hallucination)
    file_contents = []
    # If user request mentions specific files, prioritize them
    target_files = []
    if user_request:
        for f in file_analyses:
            if (
                Path(f.file_path).name in user_request
                or Path(f.file_path).name.lower() in user_request.lower()
            ):
                target_files.append(f)

    # Combine targets + top complex ones (unique)
    context_candidates = (target_files + complex_files)[:5]
    seen_paths = set()
    unique_candidates = []
    for c in context_candidates:
        if c.file_path not in seen_paths:
            unique_candidates.append(c)
            seen_paths.add(c.file_path)

    for f in unique_candidates:
        try:
            full_path = repo_path / f.file_path
            if full_path.exists():
                with open(full_path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read(3000)  # Limit to 3000 chars
                    file_contents.append(
                        f"--- File: {f.file_path} ---\n{content}\n...\n"
                    )
        except Exception as e:
            logger.warning(f"Failed to read file context for {f.file_path}: {e}")
            pass

    files_context = "\n".join(file_contents)

    summary = f"""
    Project Information:
    - Total Files: {total_files}
    - Total Lines of Code: {total_loc}
    - Language Distribution: {dict(langs)}

    Top Most Complex Files:
    {complex_files_summary}

    Selected Source Code Context:
    {files_context}
    """

    # 2. Call LLM for Insights
    llm = create_llm("general")

    prompt = ARCHITECTURE_JSON_PROMPT.format(summary=summary, user_request=user_request)

    try:
        response = llm.invoke(
            [
                SystemMessage(content=GIT_ARCHITECT_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        # Parse JSON output
        content = response.content.strip()

        # Try to find JSON block with regex
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content_json = json_match.group(1)
        else:
            # Fallback: check for any code block
            code_match = re.search(r"```\s*(.*?)\s*```", content, re.DOTALL)
            if code_match:
                content_json = code_match.group(1)
            else:
                content_json = content

        try:
            data = json.loads(content_json)
        except json.JSONDecodeError:
            # Fallback for simple parsing failure - use the content as documentation
            logger.warning(f"Failed to parse LLM architecture JSON. Using raw content.")
            data = {
                "architecture_type": "Text Report",
                "issues": ["Response was not in JSON format"],
                "documentation": content,
            }

        return ArchitectureAnalysis(
            architecture_type=data.get("architecture_type", "Undetermined"),
            patterns=data.get("patterns", []),
            layers=data.get("layers", []),
            modules=data.get("modules", []),
            dependencies={},  # LLM doesn't extract this reliably without graph analysis
            issues=data.get("issues", []),
            recommendations=data.get("recommendations", []),
            actionable_tasks=data.get("actionable_tasks", []),
            diagram=mermaid_graph,
            documentation=data.get("documentation", content),
        )

    except Exception as e:
        logger.error(f"Architecture analysis failed: {e}")
        return ArchitectureAnalysis(
            architecture_type="Analysis Failed",
            issues=[f"Error during analysis: {str(e)}"],
            documentation=summary,
            diagram=mermaid_graph,
        )


def git_analyzer_node(state: YaverState) -> Dict:
    """Main Git Analyzer Agent Node"""
    repo_path = state.get("repo_path")
    if not repo_path:
        return {"errors": ["No repo path provided"]}

    repo = clone_or_open_repository(repo_path)
    if not repo:
        # Fallback for non-git dirs?
        if os.path.isdir(repo_path):

            class MockRepo:
                working_dir = repo_path

                def rglob(self, p):
                    return Path(repo_path).rglob(p)

            repo = MockRepo()
        else:
            return {"errors": [f"Failed to open repository: {repo_path}"]}

    # Analysis
    if isinstance(repo, git.Repo):
        repo_info = get_repository_info(repo)
    else:
        repo_info = RepositoryInfo(
            repo_path=str(repo_path),
            repo_url="",
            branch="",
            last_commit="",
            contributors=[],
        )

    file_analyses, language_stats = analyze_repository_files(repo)

    repo_info.total_files = len(file_analyses)
    repo_info.total_lines = sum(f.lines_of_code for f in file_analyses)
    repo_info.languages = language_stats

    # Identify key files (high complexity or central)
    key_files = sorted(file_analyses, key=lambda f: f.complexity, reverse=True)[:5]

    # --- Perform Architecture Analysis (LLM) ---
    logger.info("Starting Architecture Analysis with LLM...")
    user_request = state.get("user_request", "")

    # Try to generate Mermaid Graph via CodeParser/GraphManager if possible
    # For now, we pass None and let analyze_architecture handle it or add it later
    mermaid_graph = None

    arch_analysis = analyze_architecture(
        repo_path=Path(repo_path),
        file_analyses=file_analyses,
        user_request=user_request,
        mermaid_graph=mermaid_graph,
    )

    analysis_results = {
        "repo_info": repo_info,
        "file_analyses": file_analyses,
        "code_quality_score": round(
            sum(f.maintainability for f in file_analyses) / len(file_analyses), 2
        )
        if file_analyses
        else 0.0,
        "architecture_analysis": arch_analysis,  # Added this
        "key_files": [f.file_path for f in key_files],
    }

    return analysis_results
