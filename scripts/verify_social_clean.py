#!/usr/bin/env python3
"""
Verify Social Developer Flow (Clean Sandbox):
1. Sets up a clean sandbox environment.
2. Clones the test repo using 'yaver' credentials.
3. Configures ForgeTool with 'yaver' credentials.
4. Simulates an agent loop to detect and handle:
   - Assigned Issues
   - Mentions
   - PR Comments
"""

import sys
import os
import shutil
import logging
import git
from typing import Dict, Any

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from config.config import get_config
from tools.forge.tool import ForgeTool
from agents.agent_task_manager import social_developer_node, YaverState

# Credentials provided by user
YAVER_USER = "yaver"
YAVER_TOKEN = "06c519fcd3a3428a38bf9d40c34bd8fb026304e6"
REPO_URL = "https://git.bezg.in/tevfik/yaver_test.git"
REPO_AUTH_URL = f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in/tevfik/yaver_test.git"

SANDBOX_DIR = os.path.expanduser("~/.yaver/sandbox")
LOCAL_REPO_PATH = os.path.join(SANDBOX_DIR, "yaver_test")

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_social_clean")


def setup_sandbox():
    logger.info(f"🧹 Setting up sandbox at {SANDBOX_DIR}...")
    if os.path.exists(SANDBOX_DIR):
        shutil.rmtree(SANDBOX_DIR)
    os.makedirs(SANDBOX_DIR, exist_ok=True)

    logger.info(f"📥 Cloning {REPO_URL}...")
    try:
        git.Repo.clone_from(REPO_AUTH_URL, LOCAL_REPO_PATH)
        logger.info("✅ Clone successful.")
    except Exception as e:
        logger.error(f"Failed to clone: {e}")
        sys.exit(1)


def main():
    logger.info("🚦 Starting Systematic Social Developer Test")

    # 1. Setup Sandbox
    setup_sandbox()

    # 2. Configure Environment for Yaver
    # We patch os.environ so config.py picks it up if needed,
    # OR we initialize ForgeTool with explicit args if supported (currently env vars fallback)
    os.environ["FORGE_PROVIDER"] = "gitea"
    # IMPORTANT: Include credentials in URL for fallback cloning to avoid interactive prompt
    os.environ["FORGE_URL"] = f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in"
    os.environ["FORGE_TOKEN"] = YAVER_TOKEN
    os.environ["FORGE_OWNER"] = "tevfik"  # Owner of the repo we are checking
    os.environ["FORGE_REPO"] = "yaver_test"

    logger.info("🔐 Verifying credentials (and monkeypatching CredentialManager)...")

    # Monkeypatch CredentialManager to force Yaver credentials for git.bezg.in
    from tools.forge.credential_manager import CredentialManager, ForgeHostConfig

    original_load = CredentialManager._load_hosts

    def mocked_load_hosts(self):
        # Return a dict with our forced config
        return {
            "git.bezg.in": ForgeHostConfig(
                provider="gitea",
                token=YAVER_TOKEN,
                # IMPORTANT: Include basic auth in base URL so clone URLs derived from it are authenticated!
                api_url=f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in",
                default_owner=YAVER_USER,
            )
        }

    CredentialManager._load_hosts = mocked_load_hosts

    forge = ForgeTool(repo_path=LOCAL_REPO_PATH)
    try:
        user = forge.run("get_user")
        logger.info(f"✅ Authenticated as: {user.get('username') or user.get('login')}")
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        sys.exit(1)

    # 3. Check for Triggers
    logger.info("👂 Checking for notifications/assignments...")

    try:
        # Check Assigned Issues
        logger.info("Checking assigned issues...")
        assigned = forge.run("list_assigned_issues")
        if isinstance(assigned, list) and assigned:
            logger.info(f"✅ Found {len(assigned)} assigned issues:")
            for issue in assigned:
                logger.info(f"   - #{issue.get('number')}: {issue.get('title')}")
                # We could dispatch here, but let's just use social_developer_node logic
        else:
            logger.info("ℹ️  No assigned issues found.")

        # Check Mentions (Notifications)
        logger.info("Checking mentions...")
        mentions = forge.run("list_mentions")
        if isinstance(mentions, list) and mentions:
            logger.info(f"✅ Found {len(mentions)} notifications:")
            for note in mentions:
                subject = note.get("subject", {})
                logger.info(f"   - {subject.get('type')}: {subject.get('title')}")
        else:
            logger.info("ℹ️  No mentions found.")

    except Exception as e:
        logger.error(f"Error checking triggers: {e}")

    # 4. Trigger Social Developer Node
    # We need to monkeypatch/configure it to search OUR sandbox repo, not the global list

    logger.info("🤖 Running Social Developer Node (Single Iteration)...")

    # IMPORTANT: Ensure the monkeypatch applies to the checks inside social_developer_node
    # Since we patched CredentialManager class, any NEW instance usage should use it.
    # However, social_developer_node imports ForgeTool inside the function.
    # And ForgeTool imports CredentialManager inside _initialize_provider.
    # So if we patched the CLASS `tools.forge.credential_manager.CredentialManager`, it should work.

    state = {"log": [], "errors": []}

    # Patch ForgeTool inside social_developer_node is safer?
    # Or maybe cwd is issue.
    # The error "Forge provider not configured" means ForgeTool(repo_path=".") failed.
    # In sandbox, "." is not a git repo.
    # But wait, ForgeTool(repo_path=None) -> "."
    # If "." is not git repo, it falls back to Env Vars.
    # Env vars ARE set.
    # Why did Env Vars fallback fail?
    # Because FORGE_PROVIDER constant in tools.forge.tool was imported BEFORE we set env vars?
    # YES. "from config.config import FORGE_PROVIDER..." at module level.

    # FIX: We need to reload the config module or patch the tool module constants.
    import tools.forge.tool

    tools.forge.tool.FORGE_PROVIDER = "gitea"
    tools.forge.tool.FORGE_URL = os.environ["FORGE_URL"]
    tools.forge.tool.FORGE_TOKEN = os.environ["FORGE_TOKEN"]
    tools.forge.tool.FORGE_OWNER = os.environ["FORGE_OWNER"]
    tools.forge.tool.FORGE_REPO = os.environ["FORGE_REPO"]

    try:
        # Note: social_developer_node instantiates its own ForgeTool()
        # Since we set os.environ, it should pick up the correct creds?
        # BUT ForgeTool logic prefers CredentialManager if git repo is present.
        # Inside social_developer_node, it calls ForgeTool().
        # If run from CWD, it might check CWD.
        # Let's change CWD to sandbox to be safe
        os.chdir(SANDBOX_DIR)

        # We also need to make sure `list_repositories` returns the test repo.
        # If 'yaver' is a collaborator, it should show up.

        updated_state = social_developer_node(state)

        # Log results
        for entry in updated_state.get("log", []):
            print(f"[Log] {entry}")

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")


if __name__ == "__main__":
    main()
