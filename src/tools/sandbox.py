"""
Sandbox Environment
Executes generated code in a controlled subprocess environment to capture
runtime errors, stdout, and stderr.
"""
import sys
import subprocess
import tempfile
import os
import logging
from typing import Tuple, Optional

logger = logging.getLogger("agents")


class Sandbox:
    def __init__(self, timeout: int = 10, cwd: Optional[str] = None):
        self.timeout = timeout
        self.cwd = cwd

    def execute_code(self, code: str, run_args: list = None) -> Tuple[bool, str]:
        """
        Saves code to a temporary file and executes it.
        Returns: (success: bool, output: str)
        """
        run_args = run_args or []

        # Identify dependencies (simple heuristic or pre-installed)
        # In a real scenario, we would install requirements inside a docker container.

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            # Run the code
            cmd = [sys.executable, temp_file_path] + run_args
            logger.info(f"Sandbox: Executing {cmd}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.cwd,  # Run in specific directory if set
            )

            output_log = (
                "--- STDOUT ---\n"
                + result.stdout
                + "\n--- STDERR ---\n"
                + result.stderr
            )

            if result.returncode == 0:
                return True, output_log
            else:
                return (
                    False,
                    f"Execution Failed (Exit Code {result.returncode}):\n{output_log}",
                )

        except subprocess.TimeoutExpired:
            return False, f"Execution Timed Out after {self.timeout} seconds."
        except Exception as e:
            return False, f"Sandbox Error: {str(e)}"
        finally:
            # Cleanup
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
