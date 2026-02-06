"""
Internal State Management System for Yaver

Tracks which repository is currently active, metadata about the repo,
memory configuration, and provides visibility into the system's context.
"""

import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
import hashlib

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

logger = logging.getLogger("agents.internal_state")


@dataclass
class RepositoryState:
    """Complete state of a repository in Yaver's memory"""

    repo_id: str  # Unique identifier (hash of remote URL)
    git_remote_url: str  # https://github.com/user/project
    local_path: str  # /home/user/projects/...
    git_branch: str  # main, develop, feature/x
    git_commit_hash: str  # Current HEAD
    project_type: str  # python, go, rust, nodejs, etc.
    detected_frameworks: List[str] = field(default_factory=list)  # [django, fastapi]
    last_accessed: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # Memory configuration for THIS repo
    qdrant_collection_code: str = ""  # repo_XXX_code_memory
    qdrant_collection_episodic: str = ""  # repo_XXX_episodic_memory
    neo4j_graph_name: str = ""  # project_XXX_graph

    # Statistics
    interaction_count: int = 0
    memory_size_bytes: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0

    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Auto-populate memory collection names if not set"""
        if not self.qdrant_collection_code:
            self.qdrant_collection_code = f"repo_{self.repo_id}_code_memory"
        if not self.qdrant_collection_episodic:
            self.qdrant_collection_episodic = f"repo_{self.repo_id}_episodic_memory"
        if not self.neo4j_graph_name:
            self.neo4j_graph_name = f"project_{self.repo_id}_graph"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        data = asdict(self)
        data["last_accessed"] = self.last_accessed.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepositoryState":
        """Create from dict"""
        data_copy = data.copy()
        data_copy["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        data_copy["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data_copy)


class InternalStateManager:
    """
    Manages the internal state of Yaver across multiple repositories.
    Provides visibility into which repo is active and what resources are allocated.
    """

    def __init__(self, state_file: Optional[str] = None):
        self.current_repo: Optional[RepositoryState] = None
        self.history: Dict[str, RepositoryState] = {}  # repo_id -> RepositoryState

        if not state_file:
            log_dir = Path(__file__).parent.parent / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            state_file = str(log_dir / "yaver_state.json")

        self.state_file = Path(state_file)
        self.console = Console()

        # Load existing state from disk
        self.load_state()

        logger.info(f"InternalStateManager initialized. State file: {self.state_file}")

    @staticmethod
    def _generate_repo_id(git_remote_url: str) -> str:
        """
        Generate a unique repo ID from git remote URL.
        Example: https://github.com/user/project → repo_<hash>
        """
        # Normalize URL (remove .git suffix, etc)
        normalized = git_remote_url.lower().strip()
        if normalized.endswith(".git"):
            normalized = normalized[:-4]

        # Create hash
        hash_obj = hashlib.md5(normalized.encode())
        hash_hex = hash_obj.hexdigest()[:8]

        return f"repo_{hash_hex}"

    def set_current_repo(
        self,
        repo_path: str = ".",
        git_remote_url: Optional[str] = None,
        git_branch: Optional[str] = None,
        git_commit_hash: Optional[str] = None,
        project_type: Optional[str] = None,
        frameworks: Optional[List[str]] = None,
    ) -> RepositoryState:
        """
        Set the current repository context.
        Can auto-detect from git if parameters not provided.
        """

        # Auto-detect from git if needed
        if not git_remote_url or not git_branch or not git_commit_hash:
            from agents.repo_manager import RepositoryManager

            try:
                repo_mgr = RepositoryManager(repo_path)
                git_remote_url = git_remote_url or repo_mgr.get_remote_url()
                git_branch = git_branch or repo_mgr.get_current_branch()
                git_commit_hash = git_commit_hash or repo_mgr.get_current_commit()
            except Exception as e:
                logger.warning(f"Could not auto-detect git info: {e}")

        # Generate repo ID
        repo_id = self._generate_repo_id(git_remote_url or "unknown")

        # Check if we already know this repo
        if repo_id in self.history:
            self.current_repo = self.history[repo_id]
            self.current_repo.last_accessed = datetime.now()
            logger.info(f"Switched to known repository: {repo_id}")
        else:
            # Create new repository state
            self.current_repo = RepositoryState(
                repo_id=repo_id,
                git_remote_url=git_remote_url or "unknown",
                local_path=str(Path(repo_path).resolve()),
                git_branch=git_branch or "unknown",
                git_commit_hash=git_commit_hash or "unknown",
                project_type=project_type or "unknown",
                detected_frameworks=frameworks or [],
                last_accessed=datetime.now(),
                created_at=datetime.now(),
            )
            self.history[repo_id] = self.current_repo
            logger.info(f"Created new repository state: {repo_id}")

        # Save state
        self.save_state()

        return self.current_repo

    def get_current_repo(self) -> Optional[RepositoryState]:
        """Get the current active repository state"""
        if not self.current_repo:
            self.set_current_repo()
        return self.current_repo

    def get_repo(self, repo_id: str) -> Optional[RepositoryState]:
        """Get a specific repository state by ID"""
        return self.history.get(repo_id)

    def list_repos(self) -> List[RepositoryState]:
        """List all known repositories, sorted by last access"""
        repos = list(self.history.values())
        repos.sort(key=lambda r: r.last_accessed, reverse=True)
        return repos

    def save_state(self):
        """Persist state to disk (JSON)"""
        try:
            data = {
                "current_repo_id": self.current_repo.repo_id
                if self.current_repo
                else None,
                "version": "1.0",
                "last_updated": datetime.now().isoformat(),
                "repos": {
                    repo_id: state.to_dict() for repo_id, state in self.history.items()
                },
            }

            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def load_state(self):
        """Load state from disk (JSON)"""
        if not self.state_file.exists():
            logger.debug(f"State file not found: {self.state_file}")
            return

        try:
            data = json.loads(self.state_file.read_text())

            for repo_id, repo_data in data.get("repos", {}).items():
                try:
                    state = RepositoryState.from_dict(repo_data)
                    self.history[repo_id] = state
                except Exception as e:
                    logger.warning(f"Could not load state for {repo_id}: {e}")

            # Set current repo
            current_repo_id = data.get("current_repo_id")
            if current_repo_id and current_repo_id in self.history:
                self.current_repo = self.history[current_repo_id]

            logger.info(f"Loaded state with {len(self.history)} repositories")
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def print_current_context(self, detailed: bool = False):
        """Display current repository context in human-readable format"""
        if not self.current_repo:
            self.console.print("[yellow]⚠️  No active repository context[/yellow]")
            return

        state = self.current_repo

        # Repository info table
        repo_table = Table(title="📍 Yaver Repository Context", show_header=False)
        repo_table.add_row("Repository", f"[blue]{state.git_remote_url}[/blue]")
        repo_table.add_row("Repo ID", f"[cyan]{state.repo_id}[/cyan]")
        repo_table.add_row("Local Path", f"[yellow]{state.local_path}[/yellow]")
        repo_table.add_row("Git Branch", f"[green]{state.git_branch}[/green]")
        repo_table.add_row(
            "Git Commit", f"[magenta]{state.git_commit_hash[:8]}[/magenta]"
        )
        repo_table.add_row("Project Type", f"[cyan]{state.project_type}[/cyan]")

        if state.detected_frameworks:
            repo_table.add_row("Frameworks", ", ".join(state.detected_frameworks))

        repo_table.add_row("Created", state.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        repo_table.add_row(
            "Last Accessed", state.last_accessed.strftime("%Y-%m-%d %H:%M:%S")
        )

        self.console.print(Panel(repo_table, border_style="blue"))

        # Memory configuration table
        memory_table = Table(title="🧠 Memory Configuration", show_header=False)
        memory_table.add_row(
            "Qdrant Code Collection", f"[cyan]{state.qdrant_collection_code}[/cyan]"
        )
        memory_table.add_row(
            "Qdrant Episodic Collection",
            f"[cyan]{state.qdrant_collection_episodic}[/cyan]",
        )
        memory_table.add_row("Neo4j Graph", f"[cyan]{state.neo4j_graph_name}[/cyan]")

        self.console.print(Panel(memory_table, border_style="cyan"))

        # Statistics table
        stats_table = Table(title="📊 Statistics", show_header=False)
        stats_table.add_row("Interactions", str(state.interaction_count))
        stats_table.add_row(
            "Memory Size", f"{state.memory_size_bytes / 1024 / 1024:.2f} MB"
        )
        stats_table.add_row("Graph Nodes", str(state.graph_nodes))
        stats_table.add_row("Graph Edges", str(state.graph_edges))

        self.console.print(Panel(stats_table, border_style="green"))

        if detailed:
            self._print_metadata(state.metadata)

    def _print_metadata(self, metadata: Dict[str, Any]):
        """Print custom metadata"""
        if not metadata:
            return

        meta_table = Table(title="🔧 Custom Metadata", show_header=False)
        for key, value in metadata.items():
            meta_table.add_row(key, str(value)[:100])

        self.console.print(Panel(meta_table, border_style="yellow"))

    def print_all_repositories(self):
        """Display all known repositories"""
        repos = self.list_repos()

        if not repos:
            self.console.print("[yellow]No repositories tracked yet[/yellow]")
            return

        table = Table(title="📚 Known Repositories", show_header=True)
        table.add_column("Repo ID", style="cyan")
        table.add_column("Repository", style="blue")
        table.add_column("Project Type", style="magenta")
        table.add_column("Interactions", justify="right")
        table.add_column("Last Accessed", style="green")

        for repo in repos:
            table.add_row(
                repo.repo_id,
                repo.git_remote_url.split("/")[-1],  # Just the repo name
                repo.project_type,
                str(repo.interaction_count),
                repo.last_accessed.strftime("%m-%d %H:%M"),
            )

        self.console.print(Panel(table, border_style="blue"))

    def update_stats(
        self,
        interaction_count: Optional[int] = None,
        memory_size_bytes: Optional[int] = None,
        graph_nodes: Optional[int] = None,
        graph_edges: Optional[int] = None,
    ):
        """Update statistics for current repository"""
        if not self.current_repo:
            logger.warning("No active repository to update stats")
            return

        if interaction_count is not None:
            self.current_repo.interaction_count = interaction_count
        if memory_size_bytes is not None:
            self.current_repo.memory_size_bytes = memory_size_bytes
        if graph_nodes is not None:
            self.current_repo.graph_nodes = graph_nodes
        if graph_edges is not None:
            self.current_repo.graph_edges = graph_edges

        self.current_repo.last_accessed = datetime.now()
        self.save_state()


# Global instance
_state_manager: Optional[InternalStateManager] = None


def get_state_manager() -> InternalStateManager:
    """Get or create global state manager instance"""
    global _state_manager
    if _state_manager is None:
        _state_manager = InternalStateManager()
    return _state_manager
