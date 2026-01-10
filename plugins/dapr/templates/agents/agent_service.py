"""
DAPR Agent Service Template

A headless agent exposed via REST API for integration with other services.
Supports long-running tasks, webhooks, and async processing.

Usage:
    dapr run --app-id agent-service --app-port 8000 --resources-path ./components -- python agent_service.py
"""

from dapr_agents import AssistantAgent, AgentService, tool
from dapr_agents.memory import VectorMemory, ConversationMemory
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn
import asyncio
import uuid
import os
import logging
from typing import Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DAPR Agent Service",
    description="Headless AI agent with REST API",
    version="1.0.0"
)


# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[dict] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    session_id: str
    tokens_used: Optional[int] = None
    processing_time_ms: int


class TaskRequest(BaseModel):
    """Long-running task request."""
    task_description: str
    callback_url: Optional[str] = None
    priority: str = Field(default="normal", description="Task priority: low, normal, high")


class TaskStatus(BaseModel):
    """Task status response."""
    task_id: str
    status: str  # pending, running, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# =============================================================================
# Agent Tools
# =============================================================================

@tool
async def save_note(content: str, tags: list[str] = None) -> str:
    """Save a note to the agent's memory.

    Use this tool to remember important information for later.

    Args:
        content: The note content to save
        tags: Optional tags for categorization

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        note_id = str(uuid.uuid4())[:8]
        await client.save_state(
            store_name="statestore",
            key=f"note-{note_id}",
            value={
                "content": content,
                "tags": tags or [],
                "created_at": datetime.now().isoformat()
            }
        )
    return f"Note saved with ID: {note_id}"


@tool
async def search_notes(query: str) -> str:
    """Search through saved notes.

    Use this to find previously saved information.

    Args:
        query: Search query

    Returns:
        Matching notes
    """
    # TODO: Implement actual search with vector similarity
    return f"Found notes matching '{query}': [Note 1, Note 2]"


@tool
async def send_notification(channel: str, message: str) -> str:
    """Send a notification via pub/sub.

    Use this to notify external systems.

    Args:
        channel: Notification channel (email, slack, webhook)
        message: Notification message

    Returns:
        Confirmation
    """
    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name="pubsub",
            topic_name=f"notifications-{channel}",
            data={"message": message, "timestamp": datetime.now().isoformat()}
        )
    return f"Notification sent to {channel}"


# =============================================================================
# Agent Configuration
# =============================================================================

# Create the agent with vector memory for RAG capabilities
agent = AssistantAgent(
    name="service-agent",
    role="API Service Agent",
    instructions="""You are an AI agent exposed as a REST API service.

Your capabilities:
- Save and search notes using memory tools
- Send notifications to external systems
- Process complex requests asynchronously

Guidelines:
- Be concise in responses (API consumers expect efficient responses)
- Use structured outputs when appropriate
- Leverage tools for persistent operations
""",
    tools=[save_note, search_notes, send_notification],
    model="gpt-4o"
)

# Session storage for conversation continuity
sessions: dict[str, ConversationMemory] = {}

# Task storage for async processing
tasks: dict[str, TaskStatus] = {}


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent": agent.name,
        "active_sessions": len(sessions),
        "pending_tasks": sum(1 for t in tasks.values() if t.status == "pending")
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat endpoint."""
    start_time = datetime.now()

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in sessions:
        sessions[session_id] = ConversationMemory(max_messages=50)

    # Set agent memory to session
    agent.memory = sessions[session_id]

    # Add context if provided
    message = request.message
    if request.context:
        message = f"Context: {request.context}\n\nUser: {request.message}"

    # Run agent
    response = await agent.run(message)

    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

    return ChatResponse(
        response=response,
        session_id=session_id,
        processing_time_ms=processing_time
    )


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted", "session_id": session_id}
    raise HTTPException(status_code=404, detail="Session not found")


@app.post("/tasks", response_model=TaskStatus)
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Create a long-running task (async processing)."""
    task_id = str(uuid.uuid4())

    task_status = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.now().isoformat()
    )
    tasks[task_id] = task_status

    # Process in background
    background_tasks.add_task(
        process_task,
        task_id,
        request.task_description,
        request.callback_url
    )

    return task_status


async def process_task(task_id: str, description: str, callback_url: Optional[str]):
    """Background task processor."""
    tasks[task_id].status = "running"
    logger.info(f"Processing task {task_id}: {description}")

    try:
        # Run the agent for the task
        result = await agent.run(
            f"Complete the following task:\n{description}\n\nProvide a detailed response."
        )

        tasks[task_id].status = "completed"
        tasks[task_id].result = result
        tasks[task_id].completed_at = datetime.now().isoformat()

        # Send callback if provided
        if callback_url:
            async with DaprClient() as client:
                await client.invoke_binding(
                    binding_name="http-callback",
                    operation="post",
                    data={"task_id": task_id, "result": result}
                )

        logger.info(f"Task {task_id} completed")

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        tasks[task_id].status = "failed"
        tasks[task_id].error = str(e)
        tasks[task_id].completed_at = datetime.now().isoformat()


@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    """Get task status."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    """List all tasks, optionally filtered by status."""
    result = list(tasks.values())
    if status:
        result = [t for t in result if t.status == status]
    return {"tasks": result, "total": len(result)}


# =============================================================================
# Webhook Endpoints (for Dapr bindings/subscriptions)
# =============================================================================

@app.post("/webhooks/process")
async def webhook_process(event: dict):
    """Process incoming webhook events."""
    logger.info(f"Received webhook: {event}")

    # Process the event with the agent
    response = await agent.run(
        f"Process this incoming event and determine appropriate actions:\n{event}"
    )

    return {"processed": True, "agent_response": response}


@app.post("/dapr/subscribe")
async def subscribe():
    """Dapr subscription configuration."""
    return [
        {
            "pubsubname": "pubsub",
            "topic": "agent-tasks",
            "route": "/webhooks/process"
        }
    ]


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
