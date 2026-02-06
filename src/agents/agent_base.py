"""
Agent Base Module - Core state and utilities for Yaver AI

Inspired by IntelligentAgent and CodingAgent architectures
"""

import os
import logging
from pathlib import Path
from typing import TypedDict, List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.logging import RichHandler

from config.config import get_config as get_yaver_config


class ConfigWrapper:
    """Convert dict config to object with attribute access"""

    def __init__(self, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict):
                    setattr(self, key, ConfigWrapper(value))
                else:
                    setattr(self, key, value)
        else:
            self.__dict__ = data.__dict__ if hasattr(data, "__dict__") else {}


def get_config():
    """Get the central Yaver configuration"""
    return get_yaver_config()


# ============================================================================
# Rich Console for beautiful output
# ============================================================================
# Disable Rich console in worker mode to prevent JSON corruption
if os.getenv("YAVER_NO_RICH"):
    CONSOLE = None
else:
    CONSOLE = Console()


# ============================================================================
# Logging Setup
# ============================================================================
# ============================================================================
# Logging Setup
# ============================================================================
import json


class JSONFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": "python_agent",
            "module": record.module,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logger(name: str = "yaver") -> logging.Logger:
    """Setup rich logger with file and console handlers"""
    config = get_config()

    logger = logging.getLogger(name)

    # Safe config access with defaults
    log_level = getattr(config, "logging", None)
    if log_level and hasattr(log_level, "log_level"):
        logger.setLevel(getattr(logging, log_level.log_level, logging.INFO))
    else:
        logger.setLevel(logging.INFO)

    # Clear existing handlers
    logger.handlers.clear()

    # Use log path from config (defaults to yaver/logs/yaver.log)
    log_file = getattr(config, "logging", None)
    if log_file and hasattr(log_file, "log_file"):
        log_path = Path(log_file.log_file).resolve()
    else:
        log_path = Path.home() / ".yaver" / "logs" / "yaver.log"

    log_path.parent.mkdir(parents=True, exist_ok=True)

    from logging.handlers import RotatingFileHandler

    # Rotate at 10MB, keep 5 backups
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # Use JSON Formatter for file
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    # Console handler (Rich) remains for human readability
    logging_config = getattr(config, "logging", None)
    enable_rich = (
        getattr(logging_config, "enable_rich_logging", True) if logging_config else True
    )

    if enable_rich and CONSOLE:
        console_handler = RichHandler(
            console=CONSOLE, rich_tracebacks=True, tracebacks_show_locals=True
        )
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

    return logger


# Global logger - lazy loaded
_logger = None


def get_logger():
    """Get global logger (lazy initialized)"""
    global _logger
    if _logger is None:
        _logger = setup_logger()
    return _logger


# Initialize logger immediately
logger = get_logger()


# ============================================================================
# Enums
# ============================================================================
class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    CONTROL = "control"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Task priority levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AnalysisType(str, Enum):
    """Types of code analysis"""

    STRUCTURE = "structure"
    QUALITY = "quality"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    DEPENDENCIES = "dependencies"


# ============================================================================
# Pydantic Models
# ============================================================================
class FileAnalysis(BaseModel):
    """Analysis result for a single file"""

    file_path: str
    language: str
    lines_of_code: int
    complexity: Optional[float] = None
    maintainability: Optional[float] = None
    security_issues: List[str] = Field(default_factory=list)
    code_smells: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class ArchitectureAnalysis(BaseModel):
    """Architecture analysis result"""

    architecture_type: str = "Unknown"
    patterns: List[str] = Field(default_factory=list)
    layers: List[str] = Field(default_factory=list)
    modules: List[str] = Field(default_factory=list)
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    actionable_tasks: List[Dict[str, str]] = Field(
        default_factory=list
    )  # Parsed tasks from suggestions
    diagram: Optional[str] = None  # Mermaid JS diagram
    documentation: Optional[str] = None  # Generated documentation summary


class Task(BaseModel):
    """Task model for iteration management"""

    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_task_id: Optional[str] = None
    subtasks: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    assigned_agent: Optional[str] = None
    iteration: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None
    repo_path: Optional[str] = None  # Repository path for this task
    branch_name: Optional[str] = None  # Git branch name
    comments: List[Dict] = Field(default_factory=list)
    originating_comment_id: Optional[
        int
    ] = None  # ID of the PR/Issue comment that triggered this task
    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )  # Flexible metadata for special tasks


class RepositoryInfo(BaseModel):
    """Git repository information"""

    repo_path: str
    repo_url: Optional[str] = None
    branch: str = "main"
    total_files: int = 0
    total_lines: int = 0
    languages: Dict[str, int] = Field(default_factory=dict)
    last_commit: Optional[str] = None
    contributors: List[str] = Field(default_factory=list)


# ============================================================================
# TypedDict for LangGraph State
# ============================================================================
class YaverState(TypedDict, total=False):
    """Main state for Yaver AI workflow"""

    # User input
    user_request: str
    mode: str  # "analyze", "architect", "task_solve", "full_assistance"

    # Repository information
    repo_path: Optional[str]
    repo_url: Optional[str]
    repo_info: Optional[RepositoryInfo]

    # Analysis results
    file_analyses: List[FileAnalysis]
    architecture_analysis: Optional[ArchitectureAnalysis]
    code_quality_score: Optional[float]

    # Task management
    tasks: List[Task]
    current_task: Optional[Task]
    completed_tasks: List[str]
    iteration_count: int

    # Generated outputs
    architecture_diagram: Optional[str]
    documentation: Optional[str]
    refactoring_plan: Optional[str]
    implementation_files: Dict[str, str]  # filename -> content

    # Workflow control
    log: List[str]
    errors: List[str]
    should_continue: bool
    final_report: Optional[str]


# Try to import SQLLoggingCallback (optional)
try:
    from tools.interaction_logger import SQLLoggingCallback

    HAS_SQL_LOGGING = True
except ImportError:
    HAS_SQL_LOGGING = False


# ============================================================================
# LLM Factory
# ============================================================================
def create_llm(model_type: str = "general", **kwargs) -> ChatOllama:
    """Create LLM instance based on type with optional authentication"""
    config = get_config()

    # Handle both flat and nested config formats
    if isinstance(config, dict):
        # Flat format (current) - try multiple key variations
        model_general = config.get(
            "OLLAMA_MODEL_GENERAL", config.get("OLLAMA_MODEL", "mistral")
        )
        model_code = config.get(
            "OLLAMA_MODEL_CODE", config.get("OLLAMA_MODEL_CODER", "mistral")
        )
        model_extraction = config.get(
            "OLLAMA_MODEL_EXTRACTION", model_code
        )  # Fallback to code model
        base_url = config.get(
            "OLLAMA_BASE_URL", config.get("OLLAMA_URL", "http://localhost:11434")
        )
        username = config.get("OLLAMA_USERNAME")
        password = config.get("OLLAMA_PASSWORD")
    else:
        # Nested format (from config.py)
        model_general = config.ollama.model_general
        model_reasoning = config.ollama.model_reasoning
        model_code = config.ollama.model_code
        model_extraction = config.ollama.model_extraction
        base_url = config.ollama.base_url
        username = config.ollama.username
        password = config.ollama.password

    model_map = {
        "general": model_general,
        "reasoning": model_reasoning,
        "code": model_code,
        "extraction": model_extraction,
    }

    model_name = model_map.get(model_type, model_general)

    # Build auth tuple if credentials provided
    if username and password:
        # LangChain Ollama might not support 'auth' directly in some versions
        # So we inject it into headers via client_kwargs for robustness
        import base64

        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()

        # Prepare headers
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Basic {b64_auth}"

        # We REMOVE headers from kwargs to avoid duplication or confusion
        # and instead pass them inside client_kwargs which ChatOllama uses for httpx.Client
        if "headers" in kwargs:
            del kwargs["headers"]

        client_kwargs = kwargs.get("client_kwargs", {})
        client_kwargs["headers"] = headers
        kwargs["client_kwargs"] = client_kwargs

        # Also clean up auth if it was passed
        if "auth" in kwargs:
            del kwargs["auth"]

        logger.info(f"🔐 Ollama authentication enabled for user: {username}")

    # Add SQL Logger Callback if available
    if HAS_SQL_LOGGING:
        callbacks = kwargs.get("callbacks", [])
        if not any(isinstance(c, SQLLoggingCallback) for c in callbacks):
            try:
                callbacks.append(SQLLoggingCallback(model_name=model_name))
                kwargs["callbacks"] = callbacks
            except Exception:
                # Ignore if SQL logging fails
                pass

    return ChatOllama(model=model_name, base_url=base_url, **kwargs)


# ============================================================================
# Utility Functions
# ============================================================================
def create_task_id() -> str:
    """Generate unique task ID"""
    return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def calculate_elapsed_time(start_time: datetime) -> str:
    """Calculate elapsed time in human-readable format"""
    elapsed = datetime.now() - start_time
    seconds = elapsed.total_seconds()

    if seconds < 60:
        return f"{seconds:.1f} saniye"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} dakika"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} saat"


def ensure_directory(path: str) -> Path:
    """Ensure directory exists and return Path object"""
    dir_path = Path(path).expanduser()
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_output_file(
    content: str, filename: str, output_dir: Optional[str] = None
) -> str:
    """Save output file and return path"""
    config = get_config()

    if output_dir is None:
        output_dir = config.project.default_output_dir

    output_path = ensure_directory(output_dir)
    file_path = output_path / filename

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"✅ File saved: {file_path}")
    return str(file_path)


def load_file(file_path: str) -> Optional[str]:
    """Load file content safely"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"❌ File read failed {file_path}: {e}")
        return None


def format_log_entry(agent_name: str, message: str) -> str:
    """Format log entry with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] [{agent_name}] {message}"


def retrieve_relevant_context(query: str, limit: int = 5) -> str:
    """
    Retrieves relevant context (code snippets, memory) for a user query.
    Uses MemoryQueryOrchestrator for Hybrid RAG (Vector + Graph).
    """
    try:
        from core.query_orchestrator import MemoryQueryOrchestrator
        from core.session_manager import get_session_manager

        # Using Orchestrator instead of raw MemoryManager
        orchestrator = MemoryQueryOrchestrator()
        result = orchestrator.execute_query(query)

        session_mgr = get_session_manager()
        active_session = session_mgr.get_active_session()

        if not result.sources and not result.fused_results:
            return ""

        context_str = f"\n\n=== 🧠 RECALLED MEMORY [Confidence: {result.overall_confidence:.2f}] ===\n"

        # 1. Add Semantic Results (Code Snippets)
        semantic_sources = [
            s for s in result.sources if s.query_type.value == "semantic"
        ]
        if semantic_sources:
            context_str += "\n--- 🔍 Related Code (Vector Search) ---\n"
            for source in semantic_sources:
                for item in source.results:
                    file_path = item.get("file", "unknown")
                    snippet = item.get("snippet", "")
                    context_str += f"- {file_path}:\n  {snippet[:300]}...\n"

        # 2. Add Structural Results (Graph)
        structural_sources = [
            s for s in result.sources if s.query_type.value == "structural"
        ]
        if structural_sources:
            context_str += "\n--- 🕸️ Structural Context (Graph) ---\n"
            for source in structural_sources:
                if not source.results:
                    continue
                data = source.results[0]
                nodes = data.get("nodes", [])
                rels = data.get("relationships", [])

                found_names = ", ".join([n.get("name", "unknown") for n in nodes])
                if found_names:
                    context_str += f"Entities: {found_names}\n"

                for rel in rels:
                    r_type = rel.get("type", "related")
                    # Try to parse our specific relationship format
                    source_id = rel.get("source", "unknown")
                    target_id = rel.get("details", {}).get("to", "unknown")
                    context_str += f"- {r_type}: {source_id} -> {target_id}\n"

        return context_str

    except Exception as e:
        logger.warning(f"Failed to retrieve context: {e}")
        return ""


def print_section_header(title: str, emoji: str = "🔹"):
    """Print formatted section header"""
    if CONSOLE:
        CONSOLE.print(f"\n{emoji} [bold cyan]{title}[/bold cyan]")
        CONSOLE.print("─" * 60)


def print_success(message: str):
    """Print success message"""
    if CONSOLE:
        CONSOLE.print(f"✅ [green]{message}[/green]")


def print_error(message: str):
    """Print error message"""
    if CONSOLE:
        CONSOLE.print(f"❌ [red]{message}[/red]")


def print_warning(message: str):
    """Print warning message"""
    if CONSOLE:
        CONSOLE.print(f"⚠️  [yellow]{message}[/yellow]")


def print_info(message: str):
    """Print info message"""
    if CONSOLE:
        CONSOLE.print(f"ℹ️  [blue]{message}[/blue]")


# ============================================================================
# Initialize module
# ============================================================================
if __name__ == "__main__":
    # Test module
    print_section_header("Yaver AI - Agent Base Module Test", "🧪")

    config = get_config()
    print_success(f"Config loaded: {config.ollama.model_general}")

    # Test LLM creation
    llm = create_llm("general")
    print_success(f"LLM created: {llm.model}")

    # Test task creation
    task = Task(
        id=create_task_id(), title="Test Task", description="This is a test task"
    )
    print_success(f"Task created: {task.id}")

    logger.info("Agent base module test completed successfully!")
