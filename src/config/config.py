"""
Configuration Management for Yaver AI
Combines best practices from IntelligentAgent and CodingAgent projects
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseSettings):
    """Ollama LLM configuration"""

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path.home() / ".yaver" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    base_url: str = Field(
        default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL"
    )
    model_general: str = Field(
        default="llama3.2:3b-instruct-q4_K_M", validation_alias="OLLAMA_MODEL_GENERAL"
    )
    model_code: str = Field(
        default="qwen2.5-coder:7b-instruct-q4_K_M", validation_alias="OLLAMA_MODEL_CODE"
    )
    model_extraction: str = Field(
        default="qwen2.5-coder:7b-instruct-q4_K_M",
        validation_alias="OLLAMA_MODEL_EXTRACTION",
    )
    model_embedding: str = Field(
        default="nomic-embed-text:latest", validation_alias="OLLAMA_MODEL_EMBEDDING"
    )
    username: Optional[str] = Field(default=None, validation_alias="OLLAMA_USERNAME")
    password: Optional[str] = Field(default=None, validation_alias="OLLAMA_PASSWORD")


class ProjectConfig(BaseSettings):
    """Project and output configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    api_base_url: str = Field(
        default="http://localhost:8080/api/v1", validation_alias="API_BASE_URL"
    )
    default_output_dir: str = Field(
        default="./output", validation_alias="DEFAULT_OUTPUT_DIR"
    )
    enable_backup: bool = Field(default=True, validation_alias="ENABLE_BACKUP")
    backup_dir: str = Field(default="~/.yaver/backups", validation_alias="BACKUP_DIR")
    max_iterations: int = Field(default=5, validation_alias="MAX_ITERATIONS")
    max_files_per_iteration: int = Field(
        default=10, validation_alias="MAX_FILES_PER_ITERATION"
    )


class CodeAnalysisConfig(BaseSettings):
    """Code analysis thresholds"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    max_complexity_warning: int = Field(
        default=10, validation_alias="MAX_COMPLEXITY_WARNING"
    )
    max_complexity_error: int = Field(
        default=15, validation_alias="MAX_COMPLEXITY_ERROR"
    )
    min_maintainability_index: int = Field(
        default=65, validation_alias="MIN_MAINTAINABILITY_INDEX"
    )
    enable_security_scan: bool = Field(
        default=True, validation_alias="ENABLE_SECURITY_SCAN"
    )
    enable_type_checking: bool = Field(
        default=True, validation_alias="ENABLE_TYPE_CHECKING"
    )


class GitConfig(BaseSettings):
    """Git operations configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    clone_depth: int = Field(default=50, validation_alias="CLONE_DEPTH")
    max_repo_size_mb: int = Field(default=500, validation_alias="MAX_REPO_SIZE_MB")
    enable_submodules: bool = Field(default=False, validation_alias="ENABLE_SUBMODULES")
    default_branch: str = Field(default="main", validation_alias="DEFAULT_BRANCH")
    github_token: Optional[str] = Field(default=None, validation_alias="GITHUB_TOKEN")


class VectorDBConfig(BaseSettings):
    """Vector database configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    chroma_persist_dir: str = Field(
        default="~/.yaver/chroma_db", validation_alias="CHROMA_PERSIST_DIR"
    )
    embedding_batch_size: int = Field(
        default=100, validation_alias="EMBEDDING_BATCH_SIZE"
    )
    top_k_similar_files: int = Field(default=5, validation_alias="TOP_K_SIMILAR_FILES")
    provider: str = Field(default="qdrant", validation_alias="VECTOR_DB_PROVIDER")


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration"""

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path.home() / ".yaver" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    host: Optional[str] = Field(default="localhost", validation_alias="QDRANT_HOST")
    port: int = Field(default=6333, validation_alias="QDRANT_PORT")
    path: Optional[str] = Field(default=None, validation_alias="QDRANT_PATH")
    collection: str = Field(
        default="yaver_memory", validation_alias="QDRANT_COLLECTION"
    )
    use_local: bool = Field(default=False, validation_alias="QDRANT_USE_LOCAL")


class Neo4jConfig(BaseSettings):
    """Neo4j graph database configuration"""

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path.home() / ".yaver" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    password: str = Field(default="password", validation_alias="NEO4J_PASSWORD")


class GraphDBConfig(BaseSettings):
    """Graph database configuration"""

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path.home() / ".yaver" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )
    provider: str = Field(default="networkx", validation_alias="GRAPH_DB_PROVIDER")
    networkx_persist_path: str = Field(
        default="~/.yaver/graph.pkl", validation_alias="NETWORKX_PERSIST_PATH"
    )


class MemoryConfig(BaseSettings):
    """Memory management configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    enable_memory: bool = Field(default=True, validation_alias="ENABLE_MEMORY")
    memory_type: str = Field(default="qdrant", validation_alias="MEMORY_TYPE")
    short_term_limit: int = Field(
        default=50, validation_alias="SHORT_TERM_MEMORY_LIMIT"
    )
    long_term_limit: int = Field(
        default=1000, validation_alias="LONG_TERM_MEMORY_LIMIT"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: str = Field(
        default="~/.yaver/logs/yaver.log", validation_alias="LOG_FILE"
    )
    enable_rich_logging: bool = Field(
        default=True, validation_alias="ENABLE_RICH_LOGGING"
    )

class PromptsConfig(BaseSettings):
    """Configuration for Prompt files"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    coder_system_prompt_path: str = Field(
        default="~/.yaver/prompts/coder_system.md",
        validation_alias="PROMPT_CODER_SYSTEM_PATH",
    )
    reviewer_system_prompt_path: str = Field(
        default="~/.yaver/prompts/reviewer_system.md",
        validation_alias="PROMPT_REVIEWER_SYSTEM_PATH",
    )
    planner_system_prompt_path: str = Field(
        default="~/.yaver/prompts/planner_system.md",
        validation_alias="PROMPT_PLANNER_SYSTEM_PATH",
    )


class YaverConfig(BaseSettings):
    """Main configuration class"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    code_analysis: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    vector_db: VectorDBConfig = Field(default_factory=VectorDBConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    graph_db: GraphDBConfig = Field(default_factory=GraphDBConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)


# Global config instance
_config: Optional[YaverConfig] = None


def get_config() -> YaverConfig:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = YaverConfig()

        # Create necessary directories
        os.makedirs(
            Path(_config.project.default_output_dir).expanduser(), exist_ok=True
        )
        os.makedirs(Path(_config.project.backup_dir).expanduser(), exist_ok=True)
        os.makedirs(Path(_config.logging.log_file).parent.expanduser(), exist_ok=True)
        os.makedirs(
            Path(_config.vector_db.chroma_persist_dir).expanduser(), exist_ok=True
        )

    return _config


def reload_config() -> YaverConfig:
    """Reload configuration from environment"""
    global _config
    _config = None
    return get_config()


# Export flat config for easier access in tools
_c = get_config()
FORGE_PROVIDER = os.getenv("FORGE_PROVIDER", "none")
FORGE_URL = os.getenv("FORGE_URL", "")
FORGE_TOKEN = os.getenv("FORGE_TOKEN", "")
FORGE_OWNER = os.getenv("FORGE_OWNER", "")
FORGE_REPO = os.getenv("FORGE_REPO", "")


if __name__ == "__main__":
    # Test configuration loading
    config = get_config()
    print("✅ Configuration loaded successfully!")
    print(f"Ollama URL: {config.ollama.base_url}")
    print(f"General Model: {config.ollama.model_general}")
    print(f"Code Model: {config.ollama.model_code}")
    print(f"Output Directory: {config.project.default_output_dir}")
    print(f"Forge Provider: {FORGE_PROVIDER}")
