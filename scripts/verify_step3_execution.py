#!/usr/bin/env python3
"""
Verify Step 3: Task Execution logic.
Assumes Step 2 (Branch Switching) is complete.
Checks if the agent *actually* works on the assigned task and produces code.
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
logger = logging.getLogger("verify_step3")


def main():
    logger.info("🚦 Starting Step 3: Task Execution Verification")

    if not os.path.exists(LOCAL_REPO_PATH):
        logger.error(f"❌ Repo not found at {LOCAL_REPO_PATH}. Step 1 failed?")
        sys.exit(1)

    repo = git.Repo(LOCAL_REPO_PATH)
    initial_commit = repo.head.commit
    logger.info(
        f"ℹ️  Initial Commit: {initial_commit.hexsha} ({initial_commit.message.strip()})"
    )

    # Monkeypatch CredentialManager
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

    # Also patch tools.forge.tool constants
    import tools.forge.tool

    tools.forge.tool.FORGE_PROVIDER = "gitea"
    tools.forge.tool.FORGE_URL = f"https://{YAVER_USER}:{YAVER_TOKEN}@git.bezg.in"
    tools.forge.tool.FORGE_TOKEN = YAVER_TOKEN

    # Run Agent Node
    logger.info("🤖 Running social_developer_node (Task Execution)...")
    state = {"log": [], "errors": []}

    try:
        updated_state = social_developer_node(state)

        # Determine expected branch name
        expected_branch = "fix/issue-1"

        # 1. Check Branch
        if repo.active_branch.name != expected_branch:
            logger.error(
                f"❌ Branch mismatch. Expected {expected_branch}, got {repo.active_branch.name}"
            )

        # 2. Check for New Commit (Work Done)
        current_commit = repo.head.commit
        if current_commit != initial_commit:
            logger.info(f"✅ SUCCESS: New commit created: {current_commit.hexsha}")
            # Check message
            logger.info(f"   Message: {current_commit.message.strip()}")
        else:
            logger.warning(
                f"⚠️  No new commit created. Did the agent actually write code?"
            )
            # It might be in PLANNING state or failed to commit.
            # Check for dirty working directory?
            if repo.is_dirty():
                logger.info("ℹ️  Repo is dirty. Changes staged but not committed?")

            # Check logs for agent activity
            logger.info("🔍 Printing recent agent logs:")
            for l in updated_state.get("log", [])[-20:]:  # Last 20 logs
                print(f"[Log] {l}")

            logger.info(f"🔍 State Keys: {updated_state.keys()}")
            if "errors" in updated_state and updated_state["errors"]:
                logger.error(f"❌ State Errors: {updated_state['errors']}")

            # Check if tasks were created
            if "tasks" in updated_state:
                logger.info(f"ℹ️ Tasks found in state: {len(updated_state['tasks'])}")
                for t in updated_state["tasks"]:
                    logger.info(f"   - {t.get('title')} ({t.get('status')})")

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
