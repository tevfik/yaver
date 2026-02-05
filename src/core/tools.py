"""
Tool Registry
Manages available tools for the Autonomous Worker.
"""

from typing import Dict, List, Type, Any
from tools.base import Tool
from tools.filesystem.rw import FileReadTool, FileWriteTool, FileEditTool
from tools.system.shell import ShellTool
from tools.git.client import GitClient
from tools.analysis.engine import AnalysisEngine


class ToolRegistry:
    """
    Registry for all available tools.
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register standard set of tools."""
        self.register(FileReadTool())
        self.register(FileWriteTool())
        self.register(FileEditTool())
        self.register(ShellTool())
        self.register(GitClient())
        self.register(GitClient())
        self.register(AnalysisEngine())
        try:
            from tools.forge.tool import ForgeTool

            self.register(ForgeTool())
        except ImportError:
            pass  # Config might not be ready

    def register(self, tool: Tool):
        """Register a helper."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """List available tools and descriptions."""
        return [
            {"name": t.name, "description": t.description} for t in self.tools.values()
        ]

    def get_langchain_tools(self) -> List[Any]:
        """Get tools as LangChain objects."""
        return [t.to_langchain_tool() for t in self.tools.values()]
