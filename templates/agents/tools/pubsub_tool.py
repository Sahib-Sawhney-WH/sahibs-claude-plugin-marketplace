"""
Pub/Sub Messaging Tool

Tools for publish/subscribe messaging in DAPR Agents.
Enables event-driven agent communication and multi-agent orchestration.

Features:
- Event publishing
- Topic subscription handling
- Multi-agent event coordination
- Message routing
"""

from dapr_agents import tool, AssistantAgent
from dapr.clients import DaprClient
from dapr.ext.workflow import DaprWorkflowContext, workflow, activity
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Callable
import json
import os
import logging
import asyncio
from datetime import datetime
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_PUBSUB = "pubsub"


# =============================================================================
# Input Models
# =============================================================================

class PublishInput(BaseModel):
    """Input for publishing events."""
    topic: str = Field(..., description="Topic to publish to")
    data: Dict[str, Any] = Field(..., description="Event data")
    pubsub_name: str = Field(default=DEFAULT_PUBSUB)
    metadata: Optional[Dict[str, str]] = Field(default=None)


class EventMessage(BaseModel):
    """Standard event message format."""
    event_type: str
    source: str
    data: Dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    correlation_id: Optional[str] = None


# =============================================================================
# Publishing Tools
# =============================================================================

@tool
async def publish_event(topic: str, data: dict) -> str:
    """
    Publish an event to a topic.

    Args:
        topic: Topic name
        data: Event data as dictionary

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DEFAULT_PUBSUB,
            topic_name=topic,
            data=json.dumps(data)
        )
    return f"Event published to topic: {topic}"


@tool
async def publish_typed_event(input: PublishInput) -> str:
    """
    Publish an event with full configuration.

    Args:
        input: Event publishing configuration

    Returns:
        Confirmation with details
    """
    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=input.pubsub_name,
            topic_name=input.topic,
            data=json.dumps(input.data),
            publish_metadata=input.metadata or {}
        )
    return f"Event published to {input.pubsub_name}/{input.topic}"


@tool
async def notify_agents(event_type: str, message: str, target_agents: List[str]) -> str:
    """
    Notify multiple agents via pub/sub.

    Args:
        event_type: Type of event
        message: Notification message
        target_agents: List of agent IDs to notify

    Returns:
        Notification status
    """
    event = EventMessage(
        event_type=event_type,
        source="notifier-agent",
        data={
            "message": message,
            "target_agents": target_agents
        },
        correlation_id=str(uuid.uuid4())
    )

    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DEFAULT_PUBSUB,
            topic_name="agent-notifications",
            data=event.model_dump_json()
        )

    return f"Notification sent to {len(target_agents)} agents"


@tool
async def broadcast_message(channel: str, message: str) -> str:
    """
    Broadcast a message to all subscribers of a channel.

    Args:
        channel: Channel/topic name
        message: Message to broadcast

    Returns:
        Broadcast status
    """
    event = {
        "type": "broadcast",
        "channel": channel,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DEFAULT_PUBSUB,
            topic_name=channel,
            data=json.dumps(event)
        )

    return f"Broadcast sent to channel: {channel}"


# =============================================================================
# Agent Communication Tools
# =============================================================================

@tool
async def request_agent_action(
    target_agent: str,
    action: str,
    parameters: dict
) -> str:
    """
    Request another agent to perform an action.

    Args:
        target_agent: Agent ID to request
        action: Action to perform
        parameters: Action parameters

    Returns:
        Request ID for tracking
    """
    request_id = str(uuid.uuid4())

    event = {
        "request_id": request_id,
        "action": action,
        "parameters": parameters,
        "requester": "calling-agent",
        "timestamp": datetime.utcnow().isoformat()
    }

    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DEFAULT_PUBSUB,
            topic_name=f"agent-requests-{target_agent}",
            data=json.dumps(event)
        )

    return f"Request {request_id} sent to agent: {target_agent}"


@tool
async def report_agent_result(
    request_id: str,
    result: dict,
    status: str = "success"
) -> str:
    """
    Report the result of an agent action.

    Args:
        request_id: Original request ID
        result: Action result
        status: success, failed, or partial

    Returns:
        Confirmation
    """
    event = {
        "request_id": request_id,
        "status": status,
        "result": result,
        "completed_at": datetime.utcnow().isoformat()
    }

    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DEFAULT_PUBSUB,
            topic_name="agent-results",
            data=json.dumps(event)
        )

    return f"Result reported for request: {request_id}"


# =============================================================================
# Event Subscription Handler
# =============================================================================

class EventHandler:
    """
    Handler for pub/sub events.
    Register handlers for different event types.
    """

    def __init__(self):
        self.handlers: Dict[str, Callable] = {}

    def on(self, event_type: str):
        """Decorator to register event handlers."""
        def decorator(func):
            self.handlers[event_type] = func
            return func
        return decorator

    async def handle(self, event_type: str, data: dict):
        """Handle an incoming event."""
        if event_type in self.handlers:
            handler = self.handlers[event_type]
            if asyncio.iscoroutinefunction(handler):
                return await handler(data)
            return handler(data)
        else:
            logger.warning(f"No handler for event type: {event_type}")
            return None


# =============================================================================
# FastAPI Event Subscription Service
# =============================================================================

def create_subscription_service(
    app: FastAPI,
    pubsub_name: str = DEFAULT_PUBSUB,
    topics: List[str] = None
) -> EventHandler:
    """
    Create a FastAPI service with pub/sub subscriptions.

    Args:
        app: FastAPI application
        pubsub_name: Name of the pub/sub component
        topics: List of topics to subscribe to

    Returns:
        EventHandler for registering handlers
    """
    handler = EventHandler()
    topics = topics or ["agent-events"]

    # DAPR subscription endpoint
    @app.get("/dapr/subscribe")
    async def subscribe():
        return [
            {
                "pubsubname": pubsub_name,
                "topic": topic,
                "route": f"/events/{topic}"
            }
            for topic in topics
        ]

    # Event receiver endpoints
    for topic in topics:
        @app.post(f"/events/{topic}")
        async def receive_event(request: Request, _topic=topic):
            body = await request.json()
            event_type = body.get("type", "unknown")
            data = body.get("data", body)

            logger.info(f"Received event on {_topic}: {event_type}")

            try:
                result = await handler.handle(event_type, data)
                return {"success": True, "result": result}
            except Exception as e:
                logger.error(f"Error handling event: {e}")
                return {"success": False, "error": str(e)}

    return handler


# =============================================================================
# Multi-Agent Coordinator
# =============================================================================

class AgentCoordinator:
    """
    Coordinate multiple agents via pub/sub.
    Handles task distribution and result aggregation.
    """

    def __init__(self, coordinator_id: str):
        self.coordinator_id = coordinator_id
        self.pending_tasks: Dict[str, dict] = {}

    async def distribute_task(
        self,
        task: str,
        agents: List[str],
        wait_for_all: bool = True
    ) -> str:
        """Distribute a task to multiple agents."""
        task_id = str(uuid.uuid4())

        self.pending_tasks[task_id] = {
            "task": task,
            "agents": agents,
            "results": {},
            "wait_for_all": wait_for_all
        }

        # Publish task to each agent
        async with DaprClient() as client:
            for agent in agents:
                await client.publish_event(
                    pubsub_name=DEFAULT_PUBSUB,
                    topic_name=f"agent-tasks-{agent}",
                    data=json.dumps({
                        "task_id": task_id,
                        "task": task,
                        "coordinator": self.coordinator_id
                    })
                )

        return task_id

    async def receive_result(self, task_id: str, agent: str, result: Any):
        """Receive a result from an agent."""
        if task_id in self.pending_tasks:
            self.pending_tasks[task_id]["results"][agent] = result

            task_info = self.pending_tasks[task_id]
            expected = set(task_info["agents"])
            received = set(task_info["results"].keys())

            if expected == received:
                logger.info(f"All results received for task {task_id}")
                return True

        return False


# =============================================================================
# Example Agent with Pub/Sub Tools
# =============================================================================

def create_pubsub_agent() -> AssistantAgent:
    """Create an agent with pub/sub messaging tools."""
    return AssistantAgent(
        name="pubsub-agent",
        role="Event-Driven Agent",
        instructions="""You can publish events and communicate with other agents.
        Use publish_event for general events.
        Use notify_agents to alert specific agents.
        Use request_agent_action to delegate tasks.
        Use broadcast_message for channel-wide announcements.""",
        tools=[
            publish_event,
            publish_typed_event,
            notify_agents,
            broadcast_message,
            request_agent_action,
            report_agent_result,
        ],
        model="gpt-4o"
    )


# =============================================================================
# Example: Event-Driven Agent Service
# =============================================================================

app = FastAPI(title="Event-Driven Agent Service")

# Create event handler
event_handler = create_subscription_service(
    app,
    topics=["agent-events", "agent-tasks", "agent-notifications"]
)

# Global agent
agent: Optional[AssistantAgent] = None


@app.on_event("startup")
async def startup():
    global agent
    agent = create_pubsub_agent()
    logger.info("Event-driven agent started")


# Register event handlers
@event_handler.on("task")
async def handle_task(data: dict):
    """Handle incoming task events."""
    task = data.get("task", "")
    logger.info(f"Received task: {task}")

    if agent:
        result = await agent.run(task)
        return result
    return "Agent not initialized"


@event_handler.on("notification")
async def handle_notification(data: dict):
    """Handle notification events."""
    message = data.get("message", "")
    logger.info(f"Notification: {message}")
    return "Notification received"


# API endpoints
class PublishRequest(BaseModel):
    topic: str
    event_type: str
    data: dict


@app.post("/publish")
async def publish(request: PublishRequest):
    """Publish an event via the agent."""
    result = await publish_event(request.topic, {
        "type": request.event_type,
        "data": request.data
    })
    return {"status": "published", "result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
