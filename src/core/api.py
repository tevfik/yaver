"""
Yaver AI - FastAPI Service
Exposes the workflow capabilities as a REST API.
Updated to use the new AgentEngine.
"""
import os
import sys
import logging
import asyncio
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure we can import from local modules
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import AgentEngine, AgentEvent
from agents.agent_base import create_llm
from memory.manager import MemoryManager

# Initialize Logging
logger = setup_logger()

# Initialize FastAPI
app = FastAPI(
    title="Yaver AI Service",
    description="AI-Powered Development Assistant API",
    version="2.0.0",
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Data Models ---
class TaskRequest(BaseModel):
    task: Optional[str] = None
    user_request: Optional[str] = None
    workflow_id: str = "default"
    repo_path: Optional[str] = None
    repo_url: Optional[str] = None
    mode: str = "analyze"
    use_git: bool = False


class TaskResponse(BaseModel):
    status: str
    workflow_id: str
    message: str


class MemoryRequest(BaseModel):
    text: str
    metadata: Optional[Dict] = None


class MemorySearchRequest(BaseModel):
    query: str
    limit: int = 5


class AnalysisRequest(BaseModel):
    repo_path: str
    analysis_type: str = "overview"  # overview, structure, graph_index, impact
    target: Optional[str] = None


# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()

# --- Endpoints ---


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "yaver-python-v2"}


@app.post("/api/task", response_model=TaskResponse)
async def submit_task(req: TaskRequest):
    """
    Starts an agent task in the background.
    Events will be emitted via WebSocket.
    """
    logger.info(f"Received task: {req.task}")

    # Run in background (simple implementation)
    # In production, use Celery/Redis
    asyncio.create_task(run_agent_task(req))

    return TaskResponse(
        status="accepted",
        workflow_id=req.workflow_id,
        message="Task started. Connect to /ws/events to see progress.",
    )


@app.post("/api/memory")
async def add_memory(req: MemoryRequest):
    """Add item to long-term memory."""
    try:
        mem = MemoryManager()
        result = mem.add_memory(req.text, req.metadata)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/search")
async def search_memory(req: MemorySearchRequest):
    """Search long-term memory."""
    try:
        mem = MemoryManager()
        results = mem.search_memory(req.query, req.limit)
        return {"status": "success", "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory")
async def reset_memory():
    """Reset all memory."""
    try:
        mem = MemoryManager()
        mem.reset()  # Assuming reset method exists or we implement it
        return {"status": "success", "message": "Memory cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze_repo(req: AnalysisRequest):
    """Run specialized repository analysis."""
    try:
        analyzer = GitRepoAnalyzer()
        result = analyzer.analyze(req.repo_path, req.analysis_type, req.target)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def format_analysis_report(result: Dict) -> str:
    """Format the raw analysis dictionary into a Markdown report."""
    repo_info = result.get("repo_info")
    arch = result.get("architecture_analysis")
    quality = result.get("code_quality_score")

    path = getattr(repo_info, "repo_path", "Unknown")

    # Standard Header
    report = f"# Analysis Component Report\n\n"
    report += f"**Target**: `{path}`\n\n"

    # Stats Section
    report += "## 📊 Repository Statistics\n"
    if repo_info:
        report += f"- **Files Analyzed**: {repo_info.total_files}\n"
        report += f"- **Total Lines (LOC)**: {repo_info.total_lines}\n"
        if repo_info.languages:
            langs = ", ".join([f"{k} ({v})" for k, v in repo_info.languages.items()])
            report += f"- **Languages**: {langs}\n"

    report += f"- **Code Quality Score**: {quality}/100\n\n"

    # Task Summary (if any were parsed)
    if arch and arch.recommendations:
        report += f"### 🚀 Optimization Plan\n"
        report += (
            f"**System has extracted {len(arch.recommendations)} actionable tasks:**\n"
        )
        for task in arch.recommendations:
            # Format task for summary (removing brackets if needed or keeping them)
            report += f"- {task}\n"
        report += "\n"

    # Architecture Report (Directly from LLM)
    if arch and arch.documentation:
        report += "---\n\n"
        report += arch.documentation
    elif arch:
        # Fallback to old format if 'documentation' is somehow empty
        report += "## Architecture Analysis\n"
        report += f"- **Type**: {arch.architecture_type}\n"
        if arch.patterns:
            report += f"- **Patterns**: {', '.join(arch.patterns)}\n"

        if arch.diagram:
            report += "\n### Diagram\n"
            report += "```mermaid\n" + arch.diagram + "\n```\n"

    return report


@app.post("/api/task/sync")
async def submit_task_sync(req: TaskRequest):
    """
    Runs the agent task synchronously and returns the final code.
    Blocking call (timeouts controlled by client).
    """
    actual_task = req.task or req.user_request or "Perform code analysis"
    logger.info(f"Received sync task: {actual_task} with mode={req.mode}")

    # Handle 'analyze' mode specifically using GitAnalyzer
    if req.mode == "analyze":
        try:
            # Detect temporary repo path if not provided
            repo_path = req.repo_path or req.repo_url or "."

            # Construct state for GitAnalyzer
            state: YaverState = {
                "user_request": actual_task,
                "repo_path": repo_path,
                "repo_url": req.repo_url,
                "mode": "analyze",
                "log": [],
                "errors": [],
                "should_continue": True,
            }

            # Run the analyzer node
            result_state = await asyncio.to_thread(git_analyzer_node, state)

            if not result_state.get("should_continue") and result_state.get("errors"):
                raise Exception(f"Analysis failed: {result_state.get('errors')}")

            # Format the output
            report = format_analysis_report(result_state)

            # Extract actionable tasks if available
            tasks = []
            arch = result_state.get("architecture_analysis")
            if arch:
                # arch might be a Pydantic model or a dict depending on how it was returned
                if hasattr(arch, "actionable_tasks"):
                    tasks = arch.actionable_tasks
                elif isinstance(arch, dict):
                    tasks = arch.get("actionable_tasks", [])

            return {
                "status": "control",
                "workflow_id": req.workflow_id,
                "result": report,
                "actionable_tasks": tasks,
            }
        except Exception as e:
            logger.exception("Analysis task failed")
            raise HTTPException(status_code=500, detail=str(e))

    # Default to AgentEngine for coding tasks
    # Initialize Engine with specific Repo context if provided
    # Note: AgentEngine currently doesn't accept repo_path in __init__,
    # we might need to pass it differently or update AgentEngine.
    # For now assuming AgentEngine can handle generic tasks.
    engine = AgentEngine(use_sandbox=True)

    # Run synchronously (blocking)
    try:
        # We can still emit events if we want, but for now just return result
        result = await asyncio.to_thread(engine.run, actual_task, 3)
        return {"status": "completed", "workflow_id": req.workflow_id, "result": result}
    except Exception as e:
        logger.exception("Sync task failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def run_agent_task(req: TaskRequest):
    """
    Wrapper to run the synchronous AgentEngine (or GitAnalyzer) in async context
    and broadcast events.
    """
    engine = AgentEngine(use_sandbox=True)
    actual_task = req.task or req.user_request or "Perform task"

    def event_callback(event: AgentEvent):
        # Broadcast event to all connected clients
        # We need a new event loop or helper to run async broadcast from sync callback
        asyncio.run_coroutine_threadsafe(
            manager.broadcast(
                {
                    "type": "event",
                    "workflow_id": req.workflow_id,
                    "step": event.step,
                    "message": event.message,
                    "status": event.status,
                    "data": event.data,
                }
            ),
            asyncio.get_running_loop(),
        )

    try:
        result = ""

        if req.mode == "analyze":
            # Notify start
            await manager.broadcast(
                {
                    "type": "event",
                    "workflow_id": req.workflow_id,
                    "step": "Analysis",
                    "message": "Starting repository analysis...",
                    "status": "info",
                    "data": None,
                }
            )

            state: YaverState = {
                "user_request": actual_task,
                "repo_path": req.repo_path or req.repo_url or ".",
                "repo_url": req.repo_url,
                "mode": "analyze",
                "log": [],
                "errors": [],
                "should_continue": True,
            }

            result_state = await asyncio.to_thread(git_analyzer_node, state)

            if not result_state.get("should_continue") and result_state.get("errors"):
                raise Exception(f"Analysis failed: {result_state.get('errors')}")

            result = format_analysis_report(result_state)

        else:
            # Run the engine in thread pool
            result = await asyncio.to_thread(engine.run, actual_task, 3, event_callback)

        await manager.broadcast(
            {
                "type": "result",
                "workflow_id": req.workflow_id,
                "code": result,
                "status": "completed",
            }
        )

    except Exception as e:
        logger.exception("Task failed")
        await manager.broadcast(
            {
                "type": "error",
                "workflow_id": req.workflow_id,
                "message": str(e),
                "status": "failed",
            }
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
