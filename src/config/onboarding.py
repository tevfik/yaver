"""Interactive onboarding and setup wizard for DevMind"""

import os
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class DevMindSetupWizard:
    """Interactive setup wizard for DevMind configuration"""

    def __init__(self):
        # Store config in user's home directory
        self.config_dir = Path.home() / ".devmind"
        self.env_file = self.config_dir / ".env"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)

    def print_header(self):
        """Print welcome header"""
        print("\n" + "=" * 60)
        print("🚀 DevMind Setup Wizard".center(60))
        print("=" * 60 + "\n")
        print("Let's configure DevMind for your first time!\n")

    def print_section(self, title: str):
        """Print section header"""
        print(f"\n📋 {title}")
        print("-" * 50)

    def input_with_default(self, prompt: str, default: Optional[str] = None) -> str:
        """Get user input with optional default value"""
        if default:
            display_prompt = f"{prompt} [{default}]: "
        else:
            display_prompt = f"{prompt}: "

        user_input = input(display_prompt).strip()
        return user_input if user_input else (default or "")

    def validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        return url.startswith("http://") or url.startswith("https://")

    def fetch_ollama_models(self, url: str) -> list:
        """Fetch available models from Ollama server"""
        try:
            import requests
            response = requests.get(f"{url}/api/tags", timeout=3)
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
            url = self.input_with_default(
                "Ollama server URL", "http://localhost:11434"
            )
            if self.validate_url(url):
                break
            print("❌ Please provide a valid URL (http://... or https://...)\n")

        # Ask about authentication (optional)
        print("\n🔐 Does your Ollama server require authentication?")
        use_auth = self.input_with_default("Use basic authentication? (y/n)", "n").lower() == "y"
        
        config = {"OLLAMA_URL": url}
        
        if use_auth:
            username = self.input_with_default("Ollama username", "")
            password = self.input_with_default("Ollama password (will be saved in .env)", "")
            if username and password:
                config["OLLAMA_USERNAME"] = username
                config["OLLAMA_PASSWORD"] = password
                print("✅ Authentication credentials configured\n")

        # Try to fetch available models
        print("\n🔄 Fetching available models from Ollama...")
        models = self.fetch_ollama_models(url)

        if models:
            print(f"\n✅ Found {len(models)} available models\n")
            
            # Ask which model roles to configure
            print("📋 Model Roles Available:")
            print("  1. General Purpose (chat, reasoning, default)")
            print("  2. Code Specialist (code generation, analysis)")
            print("  3. Tool Calling (function calling, structured output)")
            print("  4. Embedding (RAG, semantic search)\n")
            
            roles_input = self.input_with_default(
                "Select roles to configure (comma-separated, e.g., 1,2,4)", "1"
            )
            
            role_map = {
                "1": ("OLLAMA_MODEL", "General Purpose LLM", "for chat and reasoning"),
                "2": ("OLLAMA_MODEL_CODER", "Code Specialist LLM", "for code generation"),
                "3": ("OLLAMA_MODEL_TOOL", "Tool Calling LLM", "for function calling"),
                "4": ("OLLAMA_MODEL_EMBED", "Embedding Model", "for RAG/semantic search"),
            }
            
            for role_num in roles_input.split(","):
                role_num = role_num.strip()
                if role_num in role_map:
                    config_key, role_name, description = role_map[role_num]
                    model = self.select_model_role(models, role_name, description)
                    config[config_key] = model
            
            # Default: if no roles selected, use first model for general purpose
            if "OLLAMA_MODEL" not in config:
                config["OLLAMA_MODEL"] = models[0]
        else:
            print("\n⚠️  Could not fetch models from Ollama server.")
            print("   Make sure Ollama is running at the URL you provided.\n")
            model = self.input_with_default(
                "Enter model name manually (mistral, llama2, neural-chat, etc)", "mistral"
            )
            config["OLLAMA_MODEL"] = model

        return config

    def setup_qdrant(self) -> Dict:
        """Setup Qdrant (vector database) configuration"""
        self.print_section("Qdrant Configuration (Vector Database)")
        print("Qdrant stores vector embeddings for semantic search.")
        print("Options:")
        print("  1. Local (default): Uses local Qdrant server in Docker")
        print("  2. Cloud: Uses Qdrant Cloud service\n")

        choice = self.input_with_default("Choice (1 or 2)", "1")

        if choice == "2":
            url = self.input_with_default(
                "Qdrant Cloud URL",
                "https://xxx-x-y-z-xxxxx.eu-central1-0.qdb.cloud",
            )
            api_key = self.input_with_default("Qdrant API Key (keep it secret!)")
            return {
                "QDRANT_URL": url,
                "QDRANT_API_KEY": api_key,
                "QDRANT_MODE": "cloud",
            }
        else:
            url = self.input_with_default("Qdrant local server URL", "http://localhost:6333")
            return {"QDRANT_URL": url, "QDRANT_MODE": "local"}

    def setup_neo4j(self) -> Dict:
        """Setup Neo4j (graph database) configuration"""
        self.print_section("Neo4j Configuration (Graph Database)")
        print("Neo4j stores code structure and relationships for analysis.")
        print("Options:")
        print("  1. Docker (default): Neo4j running in Docker container")
        print("  2. Remote: Connect to remote Neo4j server\n")

        choice = self.input_with_default("Choice (1 or 2)", "1")

        if choice == "2":
            url = self.input_with_default("Neo4j URL", "neo4j://localhost:7687")
            user = self.input_with_default("Username", "neo4j")
            password = self.input_with_default("Password (will not display)")
            return {
                "NEO4J_URI": url,
                "NEO4J_USER": user,
                "NEO4J_PASSWORD": password,
            }
        else:
            return {
                "NEO4J_URI": "neo4j://localhost:7687",
                "NEO4J_USER": "neo4j",
                "NEO4J_PASSWORD": "devmind123",
            }

    def setup_chromadb(self) -> Dict:
        """Setup ChromaDB (local memory) configuration"""
        self.print_section("ChromaDB Configuration (Local Memory)")
        print("ChromaDB stores conversation history and learned patterns locally.\n")

        persist_dir = self.input_with_default(
            "Persistence directory", ".devmind/chroma_db"
        )

        return {"CHROMA_PERSIST_DIR": persist_dir}

    def setup_optional_services(self) -> Dict:
        """Setup optional services"""
        self.print_section("Optional Services")
        config = {}

        # Git settings
        print("GitHub Integration (optional - for analyzing repositories):")
        use_github = (
            self.input_with_default("Enable GitHub (y/n)", "n").lower() == "y"
        )
        if use_github:
            gh_token = self.input_with_default("GitHub Personal Access Token (optional)")
            if gh_token:
                config["GITHUB_TOKEN"] = gh_token

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

        return config

    def save_env_file(self, config: Dict) -> bool:
        """Save configuration to .env file"""
        try:
            env_content = "# DevMind Configuration\n"
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
            print(f"   .env file: {self.env_file.relative_to(self.env_file.parent.parent)}")
            print(f"   JSON file: {self.config_file.relative_to(self.config_file.parent.parent)}")

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
            "📦 Qdrant": ["QDRANT_URL", "QDRANT_MODE", "QDRANT_API_KEY"],
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
        optional_keys = [k for k in config.keys() 
                        if not any(k in v for v in categories.values())]
        if optional_keys:
            print(f"\n  ⚙️  Optional Settings")
            for k in optional_keys:
                print(f"    • {k}: {config[k]}")

        print(f"\n✅ Setup complete! You can now use DevMind.\n")
        print("Next steps:")
        print("  1. Start services: docker-compose up -d (in docker/ directory)")
        print("  2. Run: devmind status")
        print("  3. Try: devmind chat\n")
        
        # Offer Docker setup
        print("Optional:")
        print("  • Start Docker: devmind docker start")
        print("  • Check status: devmind docker status\n")

    def run(self, skip_intro: bool = False) -> Dict:
        """Run the complete setup wizard"""
        if not skip_intro:
            self.print_header()

        # Check if already configured
        existing = self.load_existing_config()
        if existing and not skip_intro:
            print("📦 Configuration already exists!")
            modify = (
                self.input_with_default("Reconfigure (y/n)", "n").lower() == "y"
            )
            if not modify:
                return existing

        # Run setup sections
        config = {}
        config.update(self.setup_ollama())
        config.update(self.setup_qdrant())
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
    """Check if DevMind is configured, if not run setup"""
    wizard = DevMindSetupWizard()

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
                        config[key.strip()] = value.strip().strip('"\'')
            if config:
                # Save as JSON for next time
                with open(wizard.config_file, "w") as f:
                    json.dump(config, f, indent=2)
                return config
    except Exception:
        pass

    # Need interactive setup
    print("\n" + "=" * 60)
    print("DevMind - First Time Setup Required".center(60))
    print("=" * 60)

    return wizard.run(skip_intro=True)


def get_config() -> Dict:
    """Get current configuration or run setup if needed"""
    return check_and_setup_if_needed()


if __name__ == "__main__":
    wizard = DevMindSetupWizard()
    wizard.run()
