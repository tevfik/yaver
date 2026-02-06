import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agents.agent_chat import ChatAgent


def test_sandbox_trigger():
    print("Initializing Chat Agent...")
    try:
        # Dummy session
        agent = ChatAgent(session_id="test_sandbox")

        # Test query
        # Using a very specifically phrased question to trigger the "file system" heuristic in the prompt
        query = "How many python files are in this directory? Count them for me."
        print(f"\nUser Query: {query}")
        print("-" * 50)

        response = agent.chat(query)

        print("\nFinal Agent Response:")
        print(response)

        if "**Execution Result:**" in response:
            print("\n[SUCCESS] Sandbox was triggered and output was captured.")
        else:
            print("\n[WARNING] Sandbox might not have been triggered.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_sandbox_trigger()
