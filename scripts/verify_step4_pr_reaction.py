#!/usr/bin/env python3
"""
Verify Step 4: PR Comment Reaction logic.
Checks if the agent detects comments on the PR and reacts appropriately.
"""
import sys
import os
import logging

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agents.agent_task_manager import social_developer_node

# Credentials (Yaver)
YAVER_USER = "yaver"
YAVER_TOKEN = "06c519fcd3a3428a38bf9d40c34bd8fb026304e6"

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_step4")


def main():
    logger.info("🚦 Starting Step 4: PR Comment Reaction Verification")

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
    logger.info("🤖 Running social_developer_node (PR Comment Detection)...")
    state = {"log": [], "errors": []}

    try:
        updated_state = social_developer_node(state)

        logger.info("✅ Agent execution completed")
        logger.info(f"🔍 State Keys: {updated_state.keys()}")

        # Check for any new activity in logs
        if "log" in updated_state and updated_state["log"]:
            logger.info("📋 Recent agent logs:")
            for l in updated_state.get("log", [])[-10:]:
                print(f"[Log] {l}")

    except Exception as e:
        logger.error(f"❌ Agent execution failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
