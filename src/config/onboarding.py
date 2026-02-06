"""Interactive onboarding and setup wizard for Yaver"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class YaverSetupWizard:
    """Interactive setup wizard for Yaver configuration"""

    def __init__(self):
        # Store config in user's home directory
        self.config_dir = Path.home() / ".yaver"
        self.env_file = self.config_dir / ".env"
        self.config_file = self.config_dir / "config.json"

        # Load existing config for defaults
        self.existing_config = self._load_existing_env()

        self.config_dir.mkdir(exist_ok=True)

    def _load_existing_env(self) -> Dict[str, str]:
        """Load existing environment variables from .env file"""
        config = {}
        if self.env_file.exists():
            try:
                from dotenv import dotenv_values

                config = dotenv_values(self.env_file)
            except ImportError:
                # Fallback manual parsing if dotenv not installed
                with open(self.env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            config[key] = val
        return config

    def print_header(self):
        """Print welcome header"""
        print("\n" + "=" * 60)
        print("🚀 Yaver Setup Wizard".center(60))
        print("=" * 60 + "\n")
        print("Let's configure Yaver for your first time!\n")

    def print_section(self, title: str):
        """Print section header"""
        print(f"\n📋 {title}")
        print("-" * 50)

    def input_with_default(self, prompt: str, default: Optional[str] = None) -> str:
        """
        Get user input with optional default value.
        Prioritizes existing loaded config value if a known key is passed as context,
        or simply falls back to provided default.
        """
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "

        user_input = input(display_prompt).strip()
        return user_input if user_input else (default or "")

    def input_with_config_default(
        self, config_key: str, prompt: str, fallback_default: str = ""
    ) -> str:
        """
        Helper to get input using the existing config value as the default.
        Usage: value = self.input_with_config_default("OLLAMA_BASE_URL", "Ollama URL", "http://localhost:11434")
        """
        current_val = self.existing_config.get(config_key, fallback_default)
        return self.input_with_default(prompt, current_val)

    def validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        return url.startswith("http://") or url.startswith("https://")

    def fetch_ollama_models(self, url: str, auth: tuple = None) -> list:
        """Fetch available models from Ollama server"""
        try:
            import requests

            response = requests.get(f"{url}/api/tags", timeout=3, auth=auth)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return models
        except Exception:
            pass
        return []

    def select_model_role(self, models: list, role: str, description: str) -> str:
        """Select a model for a specific role"""
        print(f"\n{description}")
        print(f"Available models for {role}:")
        for i, model in enumerate(models, 1):
            print(f"  {i}. {model}")

        while True:
            choice = self.input_with_default(f"Select model number for {role}", "1")
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    return models[idx]
                else:
                    print(f"❌ Please enter a number between 1 and {len(models)}")
            except ValueError:
                # User entered a model name directly
                return choice

    def setup_ollama(self) -> Dict:
        """Setup Ollama configuration with multiple model roles"""
        self.print_section("Ollama Configuration")
        print("Ollama is a local LLM runtime for running models locally.")
        print("Make sure Ollama is running: ollama serve\n")

        while True:
            url = self.input_with_config_default(
                "OLLAMA_BASE_URL", "Ollama server URL", "http://localhost:11434"
            )
            if self.validate_url(url):
                break
            print("❌ Please provide a valid URL (http://... or https://...)\n")

        # Ask about authentication (optional)
        print("\n🔐 Does your Ollama server require authentication?")
        has_auth_configured = bool(self.existing_config.get("OLLAMA_USERNAME"))
        default_choice = "y" if has_auth_configured else "n"

        use_auth = (
            self.input_with_default(
                "Use basic authentication? (y/n)", default_choice
            ).lower()
            == "y"
        )

        config = {"OLLAMA_BASE_URL": url}
        auth = None

        if use_auth:
            username = self.input_with_config_default(
                "OLLAMA_USERNAME", "Ollama username", ""
            )

            # Don't show password in default, just indicator
            pass_default_msg = (
                "***" if self.existing_config.get("OLLAMA_PASSWORD") else ""
            )
            display_prompt = f"Ollama password (will be saved in .env) [{'***' if pass_default_msg else ''}]: "
            password_input = input(display_prompt).strip()

            # If user pressed enter and we have existing password, keep it
            if not password_input and pass_default_msg:
                password = self.existing_config.get("OLLAMA_PASSWORD")
            else:
                password = password_input

            if username and password:
                config["OLLAMA_USERNAME"] = username
                config["OLLAMA_PASSWORD"] = password
                auth = (username, password)
                print("✅ Authentication credentials configured\n")

        # Try to fetch available models
        print("\n🔄 Fetching available models from Ollama...")
        models = self.fetch_ollama_models(url, auth)

        if models:
            print(f"\n✅ Found {len(models)} available models\n")

            # Pre-calculate defaults based on existing config
            default_roles = []
            if self.existing_config.get("OLLAMA_MODEL_GENERAL"):
                default_roles.append("1")
            if self.existing_config.get("OLLAMA_MODEL_CODE"):
                default_roles.append("2")
            if self.existing_config.get("OLLAMA_MODEL_TOOL"):
                default_roles.append("3")
            if self.existing_config.get("OLLAMA_MODEL_EMBEDDING"):
                default_roles.append("4")

            default_roles_str = ",".join(default_roles) if default_roles else "1"

            # Ask which model roles to configure
            print("📋 Model Roles Available:")
            print("  1. General Purpose (chat, reasoning, default)")
            print("  2. Code Specialist (code generation, analysis)")
            print("  3. Tool Calling (function calling, structured output)")
            print("  4. Embedding (RAG, semantic search)\n")

            roles_input = self.input_with_default(
                "Select roles to configure (comma-separated, e.g., 1,2,4)",
                default_roles_str,
            )

            role_map = {
                "1": (
                    "OLLAMA_MODEL_GENERAL",
                    "General Purpose LLM",
                    "for chat and reasoning",
                ),
                "2": (
                    "OLLAMA_MODEL_CODE",
                    "Code Specialist LLM",
                    "for code generation",
                ),
                "3": ("OLLAMA_MODEL_TOOL", "Tool Calling LLM", "for function calling"),
                "4": (
                    "OLLAMA_MODEL_EMBEDDING",
                    "Embedding Model",
                    "for RAG/semantic search",
                ),
            }

            for role_num in roles_input.split(","):
                role_num = role_num.strip()
                if role_num in role_map:
                    config_key, role_name, description = role_map[role_num]

                    # Try to find current model in the list to make it default
                    current_model = self.existing_config.get(config_key)
                    prompt_default = "1"
                    if current_model and current_model in models:
                        prompt_default = str(models.index(current_model) + 1)

                    # We pass custom logic for default selection inside the function?
                    # No, select_model_role takes a hardcoded default. Let's patch it.
                    # Or simpler: just let user re-select.

                    # Actually, let's just make select_model_role smart enough or pass the existing value
                    # Since existing signature is strictly list based, let's wrap logic here.

                    print(f"\n{description}")
                    print(f"Available models for {role_name}:")
                    for i, m in enumerate(models, 1):
                        marker = " (*)" if m == current_model else ""
                        print(f"  {i}. {m}{marker}")

                    choice = self.input_with_default(
                        f"Select model number for {role_name}", prompt_default
                    )
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(models):
                            config[config_key] = models[idx]
                        else:
                            print(
                                f"❌ Invalid selection, keeping previous: {current_model}"
                            )
                            if current_model:
                                config[config_key] = current_model
                            else:
                                config[config_key] = models[0]
                    except ValueError:
                        config[config_key] = choice  # Raw string

            # Default: if no roles selected, use first model for general purpose
            if "OLLAMA_MODEL_GENERAL" not in config:
                config["OLLAMA_MODEL_GENERAL"] = (
                    self.existing_config.get("OLLAMA_MODEL_GENERAL") or models[0]
                )
        else:
            print("\n⚠️  Could not fetch models from Ollama server.")
            print("   Make sure Ollama is running at the URL you provided.\n")
            model = self.input_with_config_default(
                "OLLAMA_MODEL_GENERAL",
                "Enter model name manually (mistral, llama2, neural-chat, etc)",
                "mistral",
            )
            config["OLLAMA_MODEL_GENERAL"] = model

        return config

    def setup_memory(self) -> Dict:
        """Setup Memory (Vector Database) configuration"""
        self.print_section("Memory Configuration (Vector Database)")
        print("Yaver uses vector database for semantic memory and RAG.")
        print("Select your Vector Backend:")
        print(
            "  1. Qdrant (Recommended): Robust enterprise vector database (Docker/Cloud)"
        )
        print("  2. ChromaDB: Standard local vector database\n")

        current_provider = self.existing_config.get("VECTOR_DB_PROVIDER", "qdrant")
        print(f"(Current: {current_provider})")

        default_choice = "2" if current_provider == "chroma" else "1"
        choice = self.input_with_default("Choice (1-2)", default_choice)
        config = {}

        if choice == "1":
            print("\n✅ Selected Qdrant")
            config["VECTOR_DB_PROVIDER"] = "qdrant"
            config["MEMORY_TYPE"] = "qdrant"

            print("\nConfiguring Qdrant...")
            print("Options:")
            print("  1. Local (default): Uses local Qdrant server in Docker")
            print("  2. Cloud: Uses Qdrant Cloud service\n")

            current_mode = self.existing_config.get("QDRANT_MODE", "local")
            mode_default = "2" if current_mode == "cloud" else "1"
            q_choice = self.input_with_default("Choice (1 or 2)", mode_default)

            if q_choice == "2":
                url = self.input_with_config_default(
                    "QDRANT_URL",
                    "Qdrant Cloud URL",
                    "https://xxx-x-y-z-xxxxx.eu-central1-0.qdb.cloud",
                )
                api_key = self.input_with_config_default(
                    "QDRANT_API_KEY", "Qdrant API Key (keep it secret!)", ""
                )
                config.update(
                    {
                        "QDRANT_URL": url,
                        "QDRANT_API_KEY": api_key,
                        "QDRANT_MODE": "cloud",
                    }
                )
            else:
                url = self.input_with_config_default(
                    "QDRANT_URL", "Qdrant local server URL", "http://localhost:6333"
                )
                config.update({"QDRANT_URL": url, "QDRANT_MODE": "local"})

        elif choice == "2":
            print("\n✅ Selected ChromaDB")
            config["VECTOR_DB_PROVIDER"] = "chroma"
            config["MEMORY_TYPE"] = "chroma"

            persist_dir = self.input_with_config_default(
                "CHROMA_PERSIST_DIR", "Persistence directory", "~/.yaver/chroma_db"
            )
            config["CHROMA_PERSIST_DIR"] = persist_dir

        return config

    def setup_neo4j(self) -> Dict:
        """Setup Graph Database configuration"""
        self.print_section("Graph Database Configuration")
        print("Graph database stores code structure and relationships for analysis.")
        print("Options:")
        print(
            "  1. NetworkX (recommended): Pure Python, zero setup, local file storage"
        )
        print("  2. Neo4j (Docker): More powerful, requires Docker container")
        print("  3. Neo4j (Remote): Connect to remote Neo4j server\n")

        current_provider = self.existing_config.get("GRAPH_DB_PROVIDER", "networkx")
        default_choice = "1"
        if current_provider == "neo4j":
            # Guess check URI to distinguish 2 vs 3
            if "localhost" in self.existing_config.get("NEO4J_URI", ""):
                default_choice = "2"
            else:
                default_choice = "3"

        choice = self.input_with_default("Choice (1, 2, or 3)", default_choice)

        if choice == "1":
            print("\n✅ Selected NetworkX (local)")
            persist_path = self.input_with_config_default(
                "NETWORKX_PERSIST_PATH", "Graph persistence path", "~/.yaver/graph.pkl"
            )
            return {
                "GRAPH_DB_PROVIDER": "networkx",
                "NETWORKX_PERSIST_PATH": persist_path,
            }
        elif choice == "2":
            print("\n✅ Selected Neo4j (Docker)")
            return {
                "GRAPH_DB_PROVIDER": "neo4j",
                "NEO4J_URI": "bolt://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "yaver123",
            }
        elif choice == "3":
            print("\n✅ Selected Neo4j (Remote)")
            url = self.input_with_config_default(
                "NEO4J_URI", "Neo4j URL", "bolt://localhost:7687"
            )
            user = self.input_with_config_default("NEO4J_USER", "Username", "neo4j")

            pass_default_msg = (
                "***" if self.existing_config.get("NEO4J_PASSWORD") else ""
            )
            display_prompt = (
                f"Password (will not display) [{'***' if pass_default_msg else ''}]: "
            )
            password_input = input(display_prompt).strip()
            if not password_input and pass_default_msg:
                password = self.existing_config.get("NEO4J_PASSWORD")
            else:
                password = password_input

            return {
                "GRAPH_DB_PROVIDER": "neo4j",
                "NEO4J_URI": url,
                "NEO4J_USER": user,
                "NEO4J_PASSWORD": password,
            }
        else:
            # Default to NetworkX
            return {
                "GRAPH_DB_PROVIDER": "networkx",
                "NETWORKX_PERSIST_PATH": "~/.yaver/graph.pkl",
            }

    def setup_chromadb(self) -> Dict:
        """Setup ChromaDB (local memory) configuration"""
        self.print_section("ChromaDB Configuration (Local Memory)")
        print("ChromaDB stores conversation history and learned patterns locally.\n")

        persist_dir = self.input_with_default(
            "Persistence directory", "~/.yaver/chroma_db"
        )

        return {"CHROMA_PERSIST_DIR": persist_dir}

    def setup_optional_services(self) -> Dict:
        """Setup optional services"""
        self.print_section("Optional Services")
        config = {}

        # API settings
        print("\nAPI Server Settings:")
        api_enable = (
            self.input_with_default("Enable FastAPI server (y/n)", "n").lower() == "y"
        )
        if api_enable:
            config["API_ENABLE"] = "true"
            config["API_HOST"] = self.input_with_default("API host", "localhost")
            config["API_PORT"] = self.input_with_default("API port", "8000")

        # Logging
        print("\nLogging:")
        log_level = self.input_with_default(
            "Log level (DEBUG/INFO/WARNING/ERROR)", "INFO"
        )
        config["LOG_LEVEL"] = log_level

        # Forge (Remote Git) Settings
        self.print_section("Forge Integration (Gitea/GitHub/GitLab)")
        print("Required for remote operations (PRs, Issues, etc.)")
        print("Yaver supports multiple hosts via ~/.yaver/hosts.json")

        if (
            self.input_with_default(
                "Configure Forge Credential Manager? (y/n)", "n"
            ).lower()
            == "y"
        ):
            try:
                from tools.forge.credential_manager import (
                    CredentialManager,
                    ForgeHostConfig,
                )

                creds = CredentialManager()

                while True:
                    print("\n--- Add New Host ---")
                    provider = self.input_with_default(
                        "Provider Type (gitea/github/none)", "gitea"
                    ).lower()
                    if provider == "none":
                        break

                    domain_or_url = self.input_with_default(
                        "Host Domain or URL (e.g. gitea.company.com)"
                    )
                    if not domain_or_url:
                        break

                    # Clean domain
                    if "://" in domain_or_url:
                        domain = domain_or_url.split("://")[1].split("/")[0]
                        api_url = domain_or_url  # User gave full URL
                    else:
                        domain = domain_or_url.split("/")[0]
                        api_url = f"https://{domain}"  # Default to https

                    if provider == "gitea":
                        token_prompt = f"Token for {domain} (Settings -> Applications -> Generate New Token)"
                    else:
                        token_prompt = f"Token for {domain} (Personal Access Token)"

                    token = self.input_with_default(token_prompt)
                    owner = self.input_with_default("Default Owner (optional)")

                    # Save
                    cfg = ForgeHostConfig(
                        provider=provider,
                        token=token,
                        api_url=api_url,
                        default_owner=owner or None,
                    )
                    creds.save_host(domain, cfg)
                    print(f"✅ Saved {domain} to hosts.json")

                    if (
                        self.input_with_default("Add another host? (y/n)", "n").lower()
                        != "y"
                    ):
                        break

            except ImportError:
                print(
                    "⚠️  Could not import CredentialManager. Skipping advanced setup."
                )

        # Also Configure Fallback Env Vars (User requested clarity here)
        print("\n--- Fallback/Single Repo Configuration ---")
        print("Useful if you want to force specific repo context via ENV variables.")

        current_provider = self.existing_config.get("FORGE_PROVIDER", "none")
        provider = self.input_with_default(
            "Fallback Provider (gitea/github/none)", current_provider
        ).lower()

        if provider in ["gitea", "github"]:
            config["FORGE_PROVIDER"] = provider

            # Token
            current_token = self.existing_config.get("FORGE_TOKEN", "")
            token_display = (
                f"{provider.title()} Token [{'***' if current_token else ''}]: "
            )
            token_input = input(token_display).strip()
            config["FORGE_TOKEN"] = token_input if token_input else current_token

            if provider == "gitea":
                config["FORGE_URL"] = self.input_with_config_default(
                    "FORGE_URL", "Gitea URL"
                )

            # Owner/Repo explanation
            print("\nℹ️  FORGE_OWNER and FORGE_REPO are optional defaults.")
            print(
                "   If set, Yaver will default to this repo when no specific repo is provided."
            )
            print(
                "   However, Yaver can still work across multiple repos if configured correctly in hosts.json"
            )

            config["FORGE_OWNER"] = self.input_with_config_default(
                "FORGE_OWNER", "Default Repo Owner"
            )
            config["FORGE_REPO"] = self.input_with_config_default(
                "FORGE_REPO", "Default Repo Name"
            )

        return config

        return config

    def save_env_file(self, config: Dict) -> bool:
        """Save configuration to .env file"""
        try:
            env_content = "# Yaver Configuration\n"
            env_content += f"# Generated by setup wizard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            env_content += "# Edit this file manually if needed\n\n"

            for key, value in config.items():
                if value:
                    # Quote values with spaces
                    if isinstance(value, str) and " " in value:
                        env_content += f'{key}="{value}"\n'
                    else:
                        env_content += f"{key}={value}\n"

            with open(self.env_file, "w") as f:
                f.write(env_content)

            # Also save as JSON for programmatic access
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2)

            print(f"\n✅ Configuration files saved:")
            print(
                f"   .env file: {self.env_file.relative_to(self.env_file.parent.parent)}"
            )
            print(
                f"   JSON file: {self.config_file.relative_to(self.config_file.parent.parent)}"
            )

            return True
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            return False

    def load_existing_config(self) -> Optional[Dict]:
        """Load existing configuration if available"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def display_summary(self, config: Dict):
        """Display configuration summary"""
        self.print_section("Configuration Summary")
        print("Here's what was configured:\n")

        categories = {
            "🔧 Ollama": ["OLLAMA_URL", "OLLAMA_MODEL"],
            "🧠 Memory": ["MEMORY_TYPE", "QDRANT_URL", "QDRANT_MODE"],
            "🔗 Forge": ["FORGE_PROVIDER", "FORGE_URL", "FORGE_OWNER"],
            "📊 Neo4j": ["NEO4J_URI", "NEO4J_USER"],
            "💾 ChromaDB": ["CHROMA_PERSIST_DIR"],
        }

        for category, keys in categories.items():
            values = {k: config.get(k) for k in keys if k in config and config.get(k)}
            if values:
                print(f"  {category}")
                for k, v in values.items():
                    if k == "NEO4J_PASSWORD":
                        display_v = "***hidden***"
                    elif isinstance(v, str) and len(v) > 45:
                        display_v = v[:42] + "..."
                    else:
                        display_v = v or "(not set)"
                    print(f"    • {k}: {display_v}")

        # Show optional
        optional_keys = [
            k for k in config.keys() if not any(k in v for v in categories.values())
        ]
        if optional_keys:
            print(f"\n  ⚙️  Optional Settings")
            for k in optional_keys:
                print(f"    • {k}: {config[k]}")

        print(f"\n✅ Setup complete! You can now use Yaver.\n")
        print("Next steps:")
        print("  1. Start services: docker-compose up -d (in docker/ directory)")
        print("  2. Run: yaver status")
        print("  3. Try: yaver chat\n")

        # Offer Docker setup
        print("Optional:")
        print("  • Start Docker: yaver docker start")
        print("  • Check status: yaver docker status\n")

    def run(self, skip_intro: bool = False) -> Dict:
        """Run the complete setup wizard"""
        if not skip_intro:
            self.print_header()

        # Check if already configured
        existing = self.load_existing_config()
        if existing and not skip_intro:
            print("📦 Configuration already exists!")
            modify = self.input_with_default("Reconfigure (y/n)", "n").lower() == "y"
            if not modify:
                return existing

        # Run setup sections
        config = {}
        config.update(self.setup_ollama())
        config.update(self.setup_memory())
        config.update(self.setup_neo4j())
        config.update(self.setup_chromadb())
        config.update(self.setup_optional_services())

        # Save
        if self.save_env_file(config):
            self.display_summary(config)
            return config
        else:
            print("\n❌ Setup failed. Please try again.\n")
            return {}


def check_and_setup_if_needed():
    """Check if Yaver is configured, if not run setup"""
    wizard = YaverSetupWizard()

    # Check if already configured
    if wizard.config_file.exists():
        try:
            with open(wizard.config_file, "r") as f:
                config = json.load(f)
                if config and len(config) > 0:
                    return config
        except Exception:
            pass

    # Need setup - but silently load if .env exists
    try:
        if wizard.env_file.exists():
            # Try loading from .env
            config = {}
            with open(wizard.env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.strip()] = value.strip().strip("\"'")
            if config:
                # Save as JSON for next time
                with open(wizard.config_file, "w") as f:
                    json.dump(config, f, indent=2)
                return config
    except Exception:
        pass

    # Need interactive setup
    print("\n" + "=" * 60)
    print("Yaver - First Time Setup Required".center(60))
    print("=" * 60)

    return wizard.run(skip_intro=True)


def get_config() -> Dict:
    """Get current configuration or run setup if needed"""
    return check_and_setup_if_needed()


if __name__ == "__main__":
    wizard = YaverSetupWizard()
    wizard.run()
