"""Docker services management for Yaver"""

import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional
import json
import time


class DockerManager:
    """Manage Docker services for Yaver"""

    def __init__(self):
        # Get project root (go up from src/cli to project root)
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_dir = self.project_root / "docker"
        self.compose_file = self.docker_dir / "docker-compose.yml"

    def check_docker_installed(self) -> bool:
        """Check if Docker is installed"""
        try:
            subprocess.run(
                ["docker", "--version"], capture_output=True, check=True, timeout=5
            )
            return True
        except Exception:
            return False

    def check_docker_running(self) -> bool:
        """Check if Docker daemon is running"""
        try:
            subprocess.run(["docker", "ps"], capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False

    def check_compose_installed(self) -> bool:
        """Check if Docker Compose is installed (v1 or v2)"""
        # Try docker compose v2 first (new format)
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except Exception:
            pass

        # Fallback to docker-compose v1
        try:
            subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except Exception:
            return False

    def get_compose_command(self) -> list:
        """Get the correct docker compose command (v2 or v1)"""
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return ["docker", "compose"]
        except Exception:
            return ["docker-compose"]

    def compose_exists(self) -> bool:
        """Check if docker-compose.yml exists"""
        return self.compose_file.exists()

    def get_service_status(self) -> dict:
        """Get status of all services"""
        if not self.compose_exists():
            return {"error": "docker-compose.yml not found"}

        try:
            compose_cmd = self.get_compose_command()
            result = subprocess.run(
                compose_cmd + ["-f", str(self.compose_file), "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.docker_dir),
            )

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            return {}
        except Exception as e:
            return {"error": str(e)}

    def start_services(self, verbose: bool = True) -> Tuple[bool, str]:
        """Start Docker services"""
        if not self.check_docker_installed():
            return (
                False,
                "❌ Docker is not installed. Install from: https://docs.docker.com/get-docker/",
            )

        if not self.check_docker_running():
            return (
                False,
                "❌ Docker daemon is not running. Start Docker Desktop or daemon.",
            )

        if not self.check_compose_installed():
            return (
                False,
                "❌ Docker Compose is not installed. Install from: https://docs.docker.com/compose/install/",
            )

        if not self.compose_exists():
            return False, f"❌ docker-compose.yml not found at {self.compose_file}"

        try:
            compose_cmd = self.get_compose_command()
            if verbose:
                print("\n🐳 Starting Docker services...")
                print(f"   Location: {self.docker_dir}\n")
                # Run with output
                result = subprocess.run(
                    compose_cmd + ["-f", str(self.compose_file), "up", "-d"],
                    timeout=60,
                    cwd=str(self.docker_dir),
                )
            else:
                result = subprocess.run(
                    compose_cmd + ["-f", str(self.compose_file), "up", "-d"],
                    capture_output=True,
                    timeout=60,
                    cwd=str(self.docker_dir),
                )

            if result.returncode == 0:
                time.sleep(2)  # Wait for services to stabilize
                return True, "✅ Docker services started successfully"
            else:
                return False, "❌ Failed to start Docker services"

        except subprocess.TimeoutExpired:
            return False, "❌ Docker compose timeout - taking too long"
        except Exception as e:
            return False, f"❌ Error starting services: {str(e)}"

    def stop_services(self, verbose: bool = True) -> Tuple[bool, str]:
        """Stop Docker services"""
        if not self.compose_exists():
            return False, f"❌ docker-compose.yml not found"

        try:
            compose_cmd = self.get_compose_command()
            if verbose:
                print("\n🛑 Stopping Docker services...")
                result = subprocess.run(
                    compose_cmd + ["-f", str(self.compose_file), "down"],
                    timeout=30,
                    cwd=str(self.docker_dir),
                )
            else:
                result = subprocess.run(
                    compose_cmd + ["-f", str(self.compose_file), "down"],
                    capture_output=True,
                    timeout=30,
                    cwd=str(self.docker_dir),
                )

            if result.returncode == 0:
                return True, "✅ Docker services stopped"
            else:
                return False, "❌ Failed to stop services"

        except Exception as e:
            return False, f"❌ Error stopping services: {str(e)}"

    def check_services_health(self) -> dict:
        """Check health of individual services"""
        health = {}

        services = {
            "ollama": ("http://localhost:11434", "Ollama LLM"),
            "qdrant": ("http://localhost:6333", "Qdrant Vector DB"),
            "neo4j": ("http://localhost:7687", "Neo4j Graph DB"),
        }

        # Check if ChromaDB is defined in docker-compose.yml
        chroma_enabled = False
        try:
            import yaml

            if self.compose_file.exists():
                with open(self.compose_file) as f:
                    compose_config = yaml.safe_load(f)
                    if compose_config and "services" in compose_config:
                        chroma_enabled = "chroma" in compose_config["services"]
        except Exception:
            # If YAML parsing fails, try JSON format
            try:
                import json

                with open(self.compose_file) as f:
                    compose_config = json.load(f)
                    if compose_config and "services" in compose_config:
                        chroma_enabled = "chroma" in compose_config["services"]
            except Exception:
                pass

        # Add ChromaDB only if it's defined in docker-compose.yml
        if chroma_enabled:
            services["chroma"] = ("http://localhost:8000", "ChromaDB (memory storage)")

        import requests

        for service_name, (url, description) in services.items():
            try:
                response = requests.get(url, timeout=2)
                if response.status_code < 500:
                    health[service_name] = {
                        "status": "✅ running",
                        "url": url,
                        "description": description,
                    }
                else:
                    health[service_name] = {
                        "status": "⚠️  error",
                        "url": url,
                        "description": description,
                    }
            except Exception:
                health[service_name] = {
                    "status": "❌ unreachable",
                    "url": url,
                    "description": description,
                }

        return health

    def print_status(self):
        """Print status of all services"""
        print("\n" + "=" * 60)
        print("🐳 Docker Services Status".center(60))
        print("=" * 60)

        # Check prerequisites
        print("\n📋 Docker Prerequisites:")
        print(
            f"  • Docker installed: {'✅ yes' if self.check_docker_installed() else '❌ no'}"
        )
        print(
            f"  • Docker running: {'✅ yes' if self.check_docker_running() else '❌ no'}"
        )
        print(
            f"  • Docker Compose: {'✅ yes' if self.check_compose_installed() else '❌ no'}"
        )
        print(f"  • compose.yml found: {'✅ yes' if self.compose_exists() else '❌ no'}")

        # Service status
        print("\n📊 Service Status:")
        health = self.check_services_health()
        for service, info in health.items():
            print(f"  {info['status']} {info['description']}")
            print(f"      → {info['url']}")

        print("\n" + "=" * 60 + "\n")

    def print_quick_commands(self):
        """Print quick reference commands"""
        print("\n" + "=" * 60)
        print("⚡ Quick Commands".center(60))
        print("=" * 60)
        print("\n  yaver docker start      - Start all services")
        print("  yaver docker stop       - Stop all services")
        print("  yaver docker status     - Check service status")
        print("  yaver docker logs       - View service logs")
        print("  yaver docker restart    - Restart services\n")
        print("=" * 60 + "\n")


def manage_docker_interactive():
    """Interactive Docker management"""
    manager = DockerManager()

    print("\n" + "=" * 60)
    print("🐳 Yaver Docker Manager".center(60))
    print("=" * 60 + "\n")

    # Check prerequisites
    if not manager.check_docker_installed():
        print("❌ Docker is not installed!")
        print("   Install from: https://docs.docker.com/get-docker/\n")
        return False

    if not manager.check_docker_running():
        print("❌ Docker is not running!")
        print("   Please start Docker Desktop or the Docker daemon.\n")
        return False

    if not manager.check_compose_installed():
        print("⚠️  Docker Compose is not installed!")
        print("   Install from: https://docs.docker.com/compose/install/\n")
        return False

    # Show menu
    print("What would you like to do?\n")
    print("  1. Start services")
    print("  2. Stop services")
    print("  3. Check service status")
    print("  4. View logs")
    print("  5. Restart services")
    print("  6. Exit\n")

    choice = input("Choose (1-6): ").strip()

    if choice == "1":
        success, msg = manager.start_services()
        print(f"\n{msg}\n")
        if success:
            manager.print_status()
        return success

    elif choice == "2":
        success, msg = manager.stop_services()
        print(f"\n{msg}\n")
        return success

    elif choice == "3":
        manager.print_status()
        return True

    elif choice == "4":
        print("\n📋 Docker Logs:\n")
        try:
            compose_cmd = manager.get_compose_command()
            subprocess.run(
                compose_cmd
                + ["-f", str(manager.compose_file), "logs", "-f", "--tail=50"],
                cwd=str(manager.docker_dir),
            )
        except KeyboardInterrupt:
            print("\n\nLogs stopped.\n")
        return True

    elif choice == "5":
        print("\n🔄 Restarting services...")
        manager.stop_services(verbose=False)
        time.sleep(2)
        success, msg = manager.start_services()
        print(f"\n{msg}\n")
        if success:
            manager.print_status()
        return success

    else:
        print("Exiting.\n")
        return True


if __name__ == "__main__":
    manage_docker_interactive()
