"""
Analysis Session Manager (Manus Pattern)
Manages the state of deep analysis tasks using file-based persistence:
- task_plan.md: Strategy and goals
- findings.md: Knowledge and insights
- progress.md: Execution log
"""
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class AnalysisSession:
    """
    Manages the 3-file state pattern for deep analysis tasks.
    Treats the filesystem as persistent memory.
    """
    
    def __init__(self, session_id: str, base_dir: Optional[Path] = None):
        """
        Initialize analysis session files for a given session ID.
        
        Args:
            session_id: The unique session identifier
            base_dir: Optional override for storage directory (default: ~/.devmind/sessions)
        """
        self.session_id = session_id
        if base_dir:
            self.state_dir = base_dir / session_id
        else:
            self.state_dir = Path.home() / ".devmind" / "sessions" / session_id
            
        self.plan_file = self.state_dir / "task_plan.md"
        self.findings_file = self.state_dir / "findings.md"
        self.progress_file = self.state_dir / "progress.md"
        
        self._ensure_files()

    def _ensure_files(self):
        """Ensure the session directory and state files exist"""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.plan_file.exists():
            self._write_file(self.plan_file, "# Task Plan\n\n- [ ] Initialize Analysis\n")
            
        if not self.findings_file.exists():
            self._write_file(self.findings_file, "# Findings & Insights\n\n_Analysis started_\n")
            
        if not self.progress_file.exists():
            self._write_file(self.progress_file, f"# Progress Log\n\nSession started: {datetime.now()}\n")

    def _write_file(self, file_path: Path, content: str):
        """Write content to file (overwriting)"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write to {file_path}: {e}")

    def _append_file(self, file_path: Path, content: str):
        """Append content to file"""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")
        except Exception as e:
            logger.error(f"Failed to append to {file_path}: {e}")

    # --- Plan Management (task_plan.md) ---

    def update_plan(self, content: str):
        """Overwrite the task plan with new content"""
        self._write_file(self.plan_file, content)

    def read_plan(self) -> str:
        """Read current plan"""
        if self.plan_file.exists():
            return self.plan_file.read_text(encoding="utf-8")
        return ""

    # --- Knowledge Management (findings.md) ---

    def log_finding(self, title: str, description: str, severity: str = "INFO"):
        """
        Log a finding or insight.
        
        Args:
            title: Short title of the finding
            description: Detailed description
            severity: INFO, WARNING, ERROR, or RISK
        """
        entry = f"\n## [{severity}] {title}\n_{datetime.now().strftime('%H:%M:%S')}_\n\n{description}\n"
        self._append_file(self.findings_file, entry)

    # --- Progress Tracking (progress.md) ---

    def log_progress(self, message: str, step_type: str = "EXEC"):
        """
        Log an execution step or status update.
        
        Args:
            message: What happened
            step_type: EXEC, PLAN, THINK, or ERROR
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = f"- **{timestamp}** [`{step_type}`] {message}"
        self._append_file(self.progress_file, entry)
        
    def log_error(self, error: str):
        """Log an error specifically"""
        self.log_progress(f"ERROR: {error}", step_type="ERROR")

    def finalize_report(self, stats: Dict):
        """
        Write a final summary report to the progress file.
        
        Args:
            stats: Dictionary containing analysis statistics
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""
## 🏁 Session Summary
**Completed at:** {timestamp}

| Metric | Value |
|--------|-------|
| Files Analyzed | {stats.get('files_processed', 0)} |
| Total Files | {stats.get('total_files', 0)} |
| Duration | {stats.get('duration_seconds', 0):.2f}s |
| Nodes Created | {stats.get('nodes_created', 'N/A')} |
| Relationships | {stats.get('relationships_created', 'N/A')} |
| Errors | {stats.get('error_count', 0)} |

### Status: {'✅ Success' if stats.get('error_count', 0) == 0 else '⚠️ Completed with errors'}
"""
        self._append_file(self.progress_file, report)

