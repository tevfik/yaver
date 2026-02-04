"""
Memory Manager - Handles chat history and memory operations
Simple implementation for storing conversation history
"""

from typing import List, Dict, Optional, Any
from datetime import datetime


class MemoryManager:
    """
    Manages conversation history and memory operations.
    Simple in-memory storage for chat sessions.
    """

    def __init__(self, max_history: int = 100):
        """Initialize memory manager"""
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "created_at": datetime.now().isoformat(),
            "session_id": None,
        }

    def add(self, content: str, message_type: str = "user", **kwargs):
        """Add message to history"""
        message = {
            "timestamp": datetime.now().isoformat(),
            "type": message_type,
            "content": content,
            **kwargs,
        }
        self.history.append(message)

        # Keep history bounded
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

    def get_history(self) -> List[Dict[str, Any]]:
        """Get entire history"""
        return self.history

    def get_recent(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages"""
        return self.history[-count:]

    def clear(self):
        """Clear all history"""
        self.history = []

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search history for messages containing query"""
        return [
            msg
            for msg in self.history
            if query.lower() in msg.get("content", "").lower()
        ]
