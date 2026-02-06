#!/usr/bin/env python3
"""
Verify Step 2: Branch Switching logic.
Assumes Step 1 (Clone) is complete and repo exists at ~/.yaver/workspaces/tevfik/yaver_test
"""
import sys
import os
import logging
import git
from typing import Dict, Any

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agents.agent_task_manager import social_developer_node
from tools.forge.tool import ForgeTool

# Credentials (Yaver)
YAVER_USER = "yaver"
YAVER_TOKEN = "06c519fcd3a3428a38bf9d40c34bd8fb026304e6"
LOCAL_REPO_PATH = os.path.expanduser("~/.yaver/workspaces/tevfik/yaver_test")

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_step2")


def main():
    logger.info("🚦 Starting Step 2: Branch Switching Verification")

    if not os.path.exists(LOCAL_REPO_PATH):
        logger.error(f"❌ Repo not found at {LOCAL_REPO_PATH}. Step 1 failed?")
        sys.exit(1)

    # Check initial branch
    try:
        repo = git.Repo(LOCAL_REPO_PATH)
        logger.info(f"ℹ️  Initial branch: {repo.active_branch.name}")
    except Exception as e:
        logger.error(f"❌ Not a git repo? {e}")
        sys.exit(1)

    # Monkeypatch CredentialManager to ensure Agent sees Yaver's view
    logger.info("🔧 Patching CredentialManager...")
    from tools.forge.credential_manager import CredentialManager, ForgeHostConfig

    def mocked_load_hosts(self):
        return {
            "git.bezg.in": ForgeHostConfig(
                provider="gitea",
                token=YAVER_TOKEN,
                api_url=f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in",
                default_owner=YAVER_USER,
            )
        }

    CredentialManager._load_hosts = mocked_load_hosts

    # Also patch tools.forge.tool constants to be safe (for legacy fallback if used)
    import tools.forge.tool

    tools.forge.tool.FORGE_PROVIDER = "gitea"
    tools.forge.tool.FORGE_URL = f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in"
    tools.forge.tool.FORGE_TOKEN = YAVER_TOKEN

    # Run Agent Node
    logger.info("🤖 Running social_developer_node...")
    state = {"log": [], "errors": []}

    try:
        updated_state = social_developer_node(state)

        # Determine expected branch name (Issue #1 -> fix/issue-1)
        expected_branch = "fix/issue-1"

        # Check current branch
        current_branch = repo.active_branch.name

        if current_branch == expected_branch:
            logger.info(f"✅ SUCCESS: Repo is on branch '{current_branch}'")
        else:
            logger.error(
                f"❌ FAILURE: Repo is on branch '{current_branch}', expected '{expected_branch}'"
            )
            # Print logs to see why
            for l in updated_state.get("log", []):
                print(f"[Log] {l}")

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
