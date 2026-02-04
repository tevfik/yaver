"""
Yaver Agent Engine - Orchestration engine for task execution
Core workflow engine that coordinates agents and components.
Simplified version for current CLI usage.
"""
import logging
from typing import Callable, Optional, Dict, Any, List
from dataclasses import dataclass

from agents.agent_base import create_llm

logger = logging.getLogger("yaver.engine")

@dataclass
class AgentEvent:
    step: str
    message: str
    status: str = "info"  # info, success, warning, error
    data: Optional[Dict[str, Any]] = None


class Engine:
    """
    Main Yaver orchestration engine
    Simplified implementation for CLI task execution
    """
    
    def __init__(self, model_type: str = "general"):
        """Initialize engine"""
        self.llm = create_llm(model_type)
        self.task_history: List[Dict[str, Any]] = []
        self.config = {}
    
    def execute_task(self, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Execute a task"""
        try:
            prompt = task
            if context:
                prompt = f"{context}\n\nTask: {task}"
            
            result = self.llm.invoke(prompt)
            
            task_record = {
                "task": task,
                "status": "success",
                "result": str(result)
            }
            self.task_history.append(task_record)
            
            return {
                "status": "success",
                "output": result,
                "task": task
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "task": task
            }
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get task execution history"""
        return self.task_history
    
    def clear_history(self):
        """Clear task history"""
        self.task_history = []


# Legacy AgentEngine class for backward compatibility
class AgentEngine:
    """
    Legacy agent engine - placeholder for backward compatibility
    Use Engine class instead for new code
    """
    
    def __init__(self, use_sandbox: bool = True):
        """Initialize legacy agent engine"""
        self.engine = Engine()
        self.task_history = []
        logger.warning("AgentEngine is deprecated, use Engine instead")
    
    def execute_single_task(self, task_description: str, context: str = "", 
                           max_retries: int = 3, on_event: Optional[Callable] = None) -> str:
        """
        Execute task using new Engine
        """
        result = self.engine.execute_task(task_description, context)
        
        if on_event:
            on_event(AgentEvent("Task", result.get("output", ""), 
                              "success" if result["status"] == "success" else "error"))
        
        return str(result.get("output", ""))
    
    def execute_task_decomposition(self, full_task: str, context: str = "", 
                                  max_retries: int = 3, on_event: Optional[Callable] = None) -> str:
        """Decompose and execute complex task"""
        return self.execute_single_task(full_task, context, max_retries, on_event)
    
    def run(self, task: str, max_retries: int = 3, on_event: Optional[Callable] = None) -> Dict[str, Any]:
        """Legacy run method for backward compatibility"""
        result = self.execute_task_decomposition(task, "", max_retries, on_event)
        return {"status": "completed", "output": result}

