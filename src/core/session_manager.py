"""
Session Manager for Yaver CLI
Handles user sessions with tagging and context switching.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

SESSION_DIR = Path.home() / ".yaver"
SESSIONS_FILE = SESSION_DIR / "sessions.json"
ACTIVE_SESSION_FILE = SESSION_DIR / ".active_session"


class SessionManager:
    """Manage Yaver sessions with tags and metadata"""

    def __init__(self):
        """Initialize session manager"""
        SESSION_DIR.mkdir(exist_ok=True)
        self._ensure_sessions_file()

    def _ensure_sessions_file(self):
        """Create sessions file if it doesn't exist"""
        if not SESSIONS_FILE.exists():
            SESSIONS_FILE.write_text(json.dumps({"sessions": []}, indent=2))

    def _read_sessions(self) -> Dict[str, Any]:
        """Read all sessions"""
        try:
            return json.loads(SESSIONS_FILE.read_text())
        except Exception:
            return {"sessions": []}

    def _write_sessions(self, data: Dict[str, Any]):
        """Write sessions to file"""
        SESSIONS_FILE.write_text(json.dumps(data, indent=2))

    def create_session(self, name: str = None, tags: List[str] = None) -> str:
        """Create a new session with optional name and tags"""
        session_id = str(uuid.uuid4())[:8]

        session = {
            "id": session_id,
            "name": name or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "metadata": {},
        }

        data = self._read_sessions()
        data["sessions"].append(session)
        self._write_sessions(data)

        self.set_active_session(session_id)
        return session_id

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        data = self._read_sessions()
        return data.get("sessions", [])

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific session by ID"""
        data = self._read_sessions()
        for session in data.get("sessions", []):
            if session["id"] == session_id:
                return session
        return None

    def set_active_session(self, session_id: str) -> bool:
        """Set the active session"""
        if not self.get_session(session_id):
            return False

        ACTIVE_SESSION_FILE.write_text(session_id)

        # Update last_used
        data = self._read_sessions()
        for session in data.get("sessions", []):
            if session["id"] == session_id:
                session["last_used"] = datetime.now().isoformat()
        self._write_sessions(data)

        return True

    def get_active_session(self) -> Optional[str]:
        """Get the active session ID"""
        if ACTIVE_SESSION_FILE.exists():
            session_id = ACTIVE_SESSION_FILE.read_text().strip()
            if self.get_session(session_id):
                return session_id
        return None

    def add_tag(self, session_id: str, tag: str) -> bool:
        """Add a tag to a session"""
        data = self._read_sessions()
        for session in data.get("sessions", []):
            if session["id"] == session_id:
                if tag not in session["tags"]:
                    session["tags"].append(tag)
                    self._write_sessions(data)
                return True
        return False

    def remove_tag(self, session_id: str, tag: str) -> bool:
        """Remove a tag from a session"""
        data = self._read_sessions()
        for session in data.get("sessions", []):
            if session["id"] == session_id:
                if tag in session["tags"]:
                    session["tags"].remove(tag)
                    self._write_sessions(data)
                return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        data = self._read_sessions()
        data["sessions"] = [
            s for s in data.get("sessions", []) if s["id"] != session_id
        ]
        self._write_sessions(data)

        # Clear active session if it was deleted
        if self.get_active_session() == session_id:
            if data["sessions"]:
                self.set_active_session(data["sessions"][0]["id"])
            else:
                ACTIVE_SESSION_FILE.unlink(missing_ok=True)

        return True

    def search_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Search sessions by tag"""
        data = self._read_sessions()
        return [s for s in data.get("sessions", []) if tag in s.get("tags", [])]

    def update_metadata(self, session_id: str, key: str, value: Any) -> bool:
        """Update session metadata"""
        data = self._read_sessions()
        for session in data.get("sessions", []):
            if session["id"] == session_id:
                session["metadata"][key] = value
                self._write_sessions(data)
                return True
        return False


# Singleton instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
