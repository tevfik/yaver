import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agents.agent_planner import PlannerAgent

logging.basicConfig(level=logging.INFO)


def verify_planner():
    print("Initializing Planner Agent...")
    try:
        planner = PlannerAgent()
    except Exception as e:
        print(f"Failed to initialize PlannerAgent: {e}")
        return

    task = "Create a new CLI command `yaver verify-network` that checks internet connectivity to google.com."
    context = "The project attempts to use python's `subprocess` or `socket` library. Existing CLI commands are in `src/cli/commands/`."

    print(f"\nTask: {task}")
    print("-" * 50)

    try:
        plan = planner.create_plan(task, context)
        print("\nGenerated Plan:")
        print(plan)

        # Simple string checks to verify prompt effectiveness
        if "subprocess" in plan or "socket" in plan:
            print("\n[SUCCESS] Plan references context keywords.")
        else:
            print("\n[WARNING] Plan might be ignoring context.")

        if "Step" in plan:
            print("[SUCCESS] Plan structure looks correct.")

    except Exception as e:
        print(f"Error generating plan: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    verify_planner()
