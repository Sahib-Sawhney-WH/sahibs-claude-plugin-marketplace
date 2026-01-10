"""
OpenAI Agents + DAPR Integration

Integrate OpenAI Agents SDK with DAPR for session management,
state persistence, and durable execution.

Features:
- Persistent agent sessions via DAPR state
- Message history persistence
- Tool execution with DAPR services
- Multi-session management
"""

from openai import OpenAI
from openai.types.beta.threads import Run
from openai.types.beta import Thread, Assistant
from dapr.clients import DaprClient
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    workflow,
    activity,
)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import uvicorn
import uuid
import json
import logging
import os
import asyncio
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="OpenAI Agents + DAPR")


# =============================================================================
# Configuration
# =============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STATE_STORE = "statestore"
PUBSUB_NAME = "pubsub"

client = OpenAI(api_key=OPENAI_API_KEY)


# =============================================================================
# DAPR Session Manager
# =============================================================================

class DaprSessionManager:
    """
    Manage OpenAI Agent sessions with DAPR state persistence.
    """

    def __init__(self, store_name: str = STATE_STORE):
        self.store_name = store_name

    async def save_session(self, session_id: str, data: dict):
        """Save session data to DAPR state."""
        async with DaprClient() as dapr:
            await dapr.save_state(
                store_name=self.store_name,
                key=f"openai-session-{session_id}",
                value=json.dumps(data)
            )
            logger.info(f"Session saved: {session_id}")

    async def load_session(self, session_id: str) -> Optional[dict]:
        """Load session data from DAPR state."""
        async with DaprClient() as dapr:
            state = await dapr.get_state(
                store_name=self.store_name,
                key=f"openai-session-{session_id}"
            )
            if state.data:
                data = state.data.decode() if isinstance(state.data, bytes) else state.data
                return json.loads(data)
            return None

    async def delete_session(self, session_id: str):
        """Delete session from DAPR state."""
        async with DaprClient() as dapr:
            await dapr.delete_state(
                store_name=self.store_name,
                key=f"openai-session-{session_id}"
            )
            logger.info(f"Session deleted: {session_id}")

    async def list_sessions(self, user_id: str) -> List[str]:
        """List all sessions for a user."""
        async with DaprClient() as dapr:
            state = await dapr.get_state(
                store_name=self.store_name,
                key=f"user-sessions-{user_id}"
            )
            if state.data:
                data = state.data.decode() if isinstance(state.data, bytes) else state.data
                return json.loads(data)
            return []

    async def add_user_session(self, user_id: str, session_id: str):
        """Add session to user's session list."""
        sessions = await self.list_sessions(user_id)
        if session_id not in sessions:
            sessions.append(session_id)
            async with DaprClient() as dapr:
                await dapr.save_state(
                    store_name=self.store_name,
                    key=f"user-sessions-{user_id}",
                    value=json.dumps(sessions)
                )


session_manager = DaprSessionManager()


# =============================================================================
# OpenAI Agent Wrapper
# =============================================================================

class DaprAgent:
    """
    OpenAI Agent with DAPR integration.
    Handles session persistence and tool execution.
    """

    def __init__(
        self,
        assistant_id: str,
        session_id: Optional[str] = None,
        user_id: str = "default"
    ):
        self.assistant_id = assistant_id
        self.session_id = session_id or str(uuid.uuid4())
        self.user_id = user_id
        self.thread_id: Optional[str] = None
        self.run_id: Optional[str] = None

    async def initialize(self):
        """Initialize or restore session."""
        session_data = await session_manager.load_session(self.session_id)

        if session_data:
            # Restore existing session
            self.thread_id = session_data.get("thread_id")
            logger.info(f"Restored session: {self.session_id}")
        else:
            # Create new thread
            thread = client.beta.threads.create()
            self.thread_id = thread.id
            await self._save_session()
            await session_manager.add_user_session(self.user_id, self.session_id)
            logger.info(f"Created new session: {self.session_id}")

    async def _save_session(self):
        """Save current session state."""
        await session_manager.save_session(self.session_id, {
            "thread_id": self.thread_id,
            "assistant_id": self.assistant_id,
            "user_id": self.user_id,
            "last_updated": datetime.utcnow().isoformat()
        })

    async def send_message(self, content: str) -> str:
        """Send a message and get response."""
        if not self.thread_id:
            await self.initialize()

        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=content
        )

        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=self.thread_id,
            assistant_id=self.assistant_id
        )
        self.run_id = run.id

        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            await asyncio.sleep(0.5)
            run = client.beta.threads.runs.retrieve(
                thread_id=self.thread_id,
                run_id=run.id
            )

            # Handle tool calls if needed
            if run.status == "requires_action":
                await self._handle_tool_calls(run)

        if run.status == "failed":
            raise Exception(f"Run failed: {run.last_error}")

        # Get the response
        messages = client.beta.threads.messages.list(
            thread_id=self.thread_id,
            limit=1
        )

        if messages.data:
            response = messages.data[0].content[0].text.value
            await self._save_session()
            return response

        return "No response generated"

    async def _handle_tool_calls(self, run: Run):
        """Handle tool calls with DAPR services."""
        tool_outputs = []

        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            logger.info(f"Tool call: {function_name}({arguments})")

            # Execute tool via DAPR service invocation
            result = await self._execute_dapr_tool(function_name, arguments)

            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": result
            })

        # Submit tool outputs
        client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.thread_id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

    async def _execute_dapr_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool via DAPR service invocation."""
        try:
            async with DaprClient() as dapr:
                response = await dapr.invoke_method(
                    app_id="tool-service",
                    method_name=f"tools/{tool_name}",
                    data=json.dumps(arguments),
                    http_verb="POST",
                    content_type="application/json"
                )
                return str(response.data) if response.data else "Success"
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error: {str(e)}"

    async def get_history(self) -> List[dict]:
        """Get message history."""
        if not self.thread_id:
            return []

        messages = client.beta.threads.messages.list(
            thread_id=self.thread_id,
            limit=100
        )

        return [
            {
                "role": msg.role,
                "content": msg.content[0].text.value,
                "created_at": msg.created_at
            }
            for msg in reversed(messages.data)
        ]


# =============================================================================
# Assistant Creation
# =============================================================================

def create_assistant(
    name: str,
    instructions: str,
    tools: List[dict] = None
) -> Assistant:
    """Create an OpenAI Assistant with tools."""
    return client.beta.assistants.create(
        name=name,
        instructions=instructions,
        model="gpt-4o",
        tools=tools or []
    )


# Example assistant with DAPR tools
DAPR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_state",
            "description": "Save data to persistent state store",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "State key"},
                    "value": {"type": "string", "description": "Value to store"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_state",
            "description": "Retrieve data from state store",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "State key"}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "publish_event",
            "description": "Publish an event to a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic name"},
                    "data": {"type": "object", "description": "Event data"}
                },
                "required": ["topic", "data"]
            }
        }
    }
]


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def run_agent_task(ctx, data: dict) -> dict:
    """Run an agent task as a durable activity."""
    assistant_id = data["assistant_id"]
    session_id = data.get("session_id")
    message = data["message"]
    user_id = data.get("user_id", "default")

    agent = DaprAgent(
        assistant_id=assistant_id,
        session_id=session_id,
        user_id=user_id
    )
    await agent.initialize()

    response = await agent.send_message(message)

    return {
        "session_id": agent.session_id,
        "response": response,
        "status": "completed"
    }


@activity
async def batch_agent_messages(ctx, data: dict) -> dict:
    """Process multiple messages in sequence."""
    assistant_id = data["assistant_id"]
    session_id = data.get("session_id")
    messages = data["messages"]

    agent = DaprAgent(
        assistant_id=assistant_id,
        session_id=session_id
    )
    await agent.initialize()

    responses = []
    for message in messages:
        response = await agent.send_message(message)
        responses.append(response)

    return {
        "session_id": agent.session_id,
        "responses": responses,
        "status": "completed"
    }


# =============================================================================
# Durable Agent Workflow
# =============================================================================

@workflow
def durable_agent_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Run OpenAI Agent as durable workflow.
    Survives crashes and can be resumed.
    """
    result = yield ctx.call_activity(run_agent_task, input=data)
    return result


@workflow
def multi_message_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Process multiple messages with checkpointing.
    """
    assistant_id = data["assistant_id"]
    session_id = data.get("session_id", str(uuid.uuid4()))
    messages = data["messages"]

    results = []

    for i, message in enumerate(messages):
        result = yield ctx.call_activity(
            run_agent_task,
            input={
                "assistant_id": assistant_id,
                "session_id": session_id,
                "message": message
            }
        )
        results.append({
            "message_index": i,
            "response": result["response"]
        })
        session_id = result["session_id"]  # Use same session

    return {
        "session_id": session_id,
        "results": results,
        "status": "completed"
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(durable_agent_workflow)
workflow_runtime.register_workflow(multi_message_workflow)
workflow_runtime.register_activity(run_agent_task)
workflow_runtime.register_activity(batch_agent_messages)


# =============================================================================
# API Models
# =============================================================================

class ChatRequest(BaseModel):
    assistant_id: str
    message: str
    session_id: Optional[str] = None
    user_id: str = "default"
    durable: bool = Field(
        default=False,
        description="Run as durable workflow"
    )


class MultiMessageRequest(BaseModel):
    assistant_id: str
    messages: List[str]
    session_id: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: str
    thread_id: Optional[str] = None
    assistant_id: str
    last_updated: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("OpenAI Agents + DAPR service started")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with an OpenAI Agent."""
    if request.durable:
        # Run as durable workflow
        instance_id = str(uuid.uuid4())

        async with DaprClient() as dapr:
            await dapr.start_workflow(
                workflow_component="dapr",
                workflow_name="durable_agent_workflow",
                input={
                    "assistant_id": request.assistant_id,
                    "session_id": request.session_id,
                    "message": request.message,
                    "user_id": request.user_id
                },
                instance_id=instance_id
            )

        return {
            "workflow_id": instance_id,
            "status": "started",
            "message": "Use /workflow/{id} to check status"
        }

    else:
        # Direct execution
        agent = DaprAgent(
            assistant_id=request.assistant_id,
            session_id=request.session_id,
            user_id=request.user_id
        )
        await agent.initialize()

        response = await agent.send_message(request.message)

        return {
            "session_id": agent.session_id,
            "response": response
        }


@app.post("/batch")
async def batch_chat(request: MultiMessageRequest):
    """Process multiple messages as durable workflow."""
    instance_id = str(uuid.uuid4())

    async with DaprClient() as dapr:
        await dapr.start_workflow(
            workflow_component="dapr",
            workflow_name="multi_message_workflow",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {
        "workflow_id": instance_id,
        "status": "started",
        "message_count": len(request.messages)
    }


@app.get("/workflow/{instance_id}")
async def get_workflow_status(instance_id: str):
    """Get workflow status."""
    async with DaprClient() as dapr:
        state = await dapr.get_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )

        result = None
        if state.serialized_output:
            try:
                result = json.loads(state.serialized_output)
            except json.JSONDecodeError:
                result = {"output": state.serialized_output}

        return {
            "instance_id": instance_id,
            "status": state.runtime_status,
            "result": result
        }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    data = await session_manager.load_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionInfo(
        session_id=session_id,
        **data
    )


@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get session message history."""
    data = await session_manager.load_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = DaprAgent(
        assistant_id=data["assistant_id"],
        session_id=session_id
    )
    agent.thread_id = data.get("thread_id")

    history = await agent.get_history()

    return {"session_id": session_id, "messages": history}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    await session_manager.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.get("/users/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """List all sessions for a user."""
    sessions = await session_manager.list_sessions(user_id)
    return {"user_id": user_id, "sessions": sessions}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
