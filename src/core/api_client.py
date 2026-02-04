"""
API Client for interacting with Yaver Backend
"""
import requests
import logging
from typing import Dict, Any, Optional
from .config import get_config

logger = logging.getLogger("yaver_cli")


class YaverClient:
    def __init__(self):
        self.config = get_config()
        self.base_url = "http://localhost:8080/api"  # Default

    def add_comment(self, task_id: str, content: str, author: str = "Yaver Agent"):
        """Add a comment to a task"""
        # For now, just log it if backend is not reachable or just mock it
        logger.info(f"[API] Adding comment to {task_id}: {content[:50]}...")
        # try:
        #     requests.post(...)
        # except:
        #     pass

    def update_task_status(self, task_id: str, status: str):
        logger.info(f"[API] Updating task {task_id} status to {status}")
