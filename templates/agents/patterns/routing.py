"""
Routing Pattern

Dynamically route requests to specialized agents based on content.
Useful for multi-domain systems where different expertise is needed.

Example use cases:
- Customer support routing (technical, billing, general)
- Multi-language support
- Domain-specific processing
"""

from dapr_agents import AssistantAgent
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    workflow,
    activity,
)
from dapr.clients import DaprClient
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import uuid
import os
import logging
from typing import Dict, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Routing Pattern")


# =============================================================================
# Router Agent
# =============================================================================

router_agent = AssistantAgent(
    name="router",
    role="Request Router",
    instructions="""You are a routing agent that classifies incoming requests.

Analyze the request and respond with ONLY one of these categories:
- technical: Programming, software, systems, debugging
- billing: Payments, invoices, subscriptions, pricing
- sales: Product info, demos, purchasing
- support: General help, how-to questions
- escalate: Complex issues needing human review

Respond with just the category name, nothing else.""",
    model="gpt-4o",
    temperature=0.1
)


# =============================================================================
# Specialist Agents
# =============================================================================

technical_agent = AssistantAgent(
    name="technical",
    role="Technical Support",
    instructions="""You are a technical support specialist.
    Help with programming, software issues, and technical troubleshooting.
    Provide clear, step-by-step solutions when possible.""",
    model="gpt-4o"
)

billing_agent = AssistantAgent(
    name="billing",
    role="Billing Support",
    instructions="""You are a billing support specialist.
    Help with payment issues, invoices, subscriptions, and pricing questions.
    Be accurate with financial information.""",
    model="gpt-4o"
)

sales_agent = AssistantAgent(
    name="sales",
    role="Sales Representative",
    instructions="""You are a sales representative.
    Help with product information, demos, and purchasing decisions.
    Be helpful and informative without being pushy.""",
    model="gpt-4o"
)

support_agent = AssistantAgent(
    name="support",
    role="General Support",
    instructions="""You are a general support agent.
    Help with general questions and how-to guidance.
    Be friendly and helpful.""",
    model="gpt-4o"
)

escalation_agent = AssistantAgent(
    name="escalation",
    role="Escalation Handler",
    instructions="""You are handling an escalated issue.
    Acknowledge the complexity, gather key details, and explain next steps.
    Be empathetic and thorough.""",
    model="gpt-4o"
)

# Agent registry
AGENTS: Dict[str, AssistantAgent] = {
    "technical": technical_agent,
    "billing": billing_agent,
    "sales": sales_agent,
    "support": support_agent,
    "escalate": escalation_agent
}


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def route_request(ctx, request: str) -> dict:
    """Route the request to appropriate category."""
    logger.info(f"Routing request: {request[:50]}...")

    category = await router_agent.run(request)
    category = category.strip().lower()

    # Validate category
    if category not in AGENTS:
        logger.warning(f"Unknown category '{category}', defaulting to 'support'")
        category = "support"

    logger.info(f"Routed to: {category}")

    return {
        "category": category,
        "request": request
    }


@activity
async def handle_request(ctx, data: dict) -> dict:
    """Handle the request with the appropriate agent."""
    category = data["category"]
    request = data["request"]

    agent = AGENTS[category]
    logger.info(f"Handling with {agent.name} agent")

    response = await agent.run(request)

    return {
        "category": category,
        "agent": agent.name,
        "response": response
    }


@activity
async def post_process(ctx, result: dict) -> dict:
    """Post-process the response (logging, analytics, etc.)."""
    logger.info(f"Post-processing response from {result['agent']}")

    # Add metadata
    result["processed"] = True

    # Could add: analytics tracking, satisfaction survey, follow-up scheduling

    return result


# =============================================================================
# Routing Workflow
# =============================================================================

@workflow
def routing_workflow(ctx: DaprWorkflowContext, request: str):
    """
    Route request to appropriate specialist and handle.

    Flow: Route → Handle → Post-process
    """
    # Step 1: Route the request
    routing = yield ctx.call_activity(route_request, input=request)

    # Step 2: Handle with specialist
    result = yield ctx.call_activity(handle_request, input=routing)

    # Step 3: Post-process
    final = yield ctx.call_activity(post_process, input=result)

    return final


@workflow
def multi_route_workflow(ctx: DaprWorkflowContext, request: str):
    """
    Route to multiple specialists for comprehensive response.
    Useful when a request spans multiple domains.
    """
    # Get primary route
    routing = yield ctx.call_activity(route_request, input=request)
    primary_category = routing["category"]

    # Define related categories for comprehensive response
    related = {
        "technical": ["support"],
        "billing": ["support", "sales"],
        "sales": ["technical"],
        "support": [],
        "escalate": ["technical", "billing"]
    }

    # Collect responses from primary and related agents
    responses = []

    # Primary response
    primary = yield ctx.call_activity(
        handle_request,
        input={"category": primary_category, "request": request}
    )
    responses.append(primary)

    # Related responses
    for category in related.get(primary_category, []):
        related_response = yield ctx.call_activity(
            handle_request,
            input={"category": category, "request": request}
        )
        responses.append(related_response)

    return {
        "primary": primary,
        "all_responses": responses,
        "categories_consulted": [r["category"] for r in responses]
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(routing_workflow)
workflow_runtime.register_workflow(multi_route_workflow)
workflow_runtime.register_activity(route_request)
workflow_runtime.register_activity(handle_request)
workflow_runtime.register_activity(post_process)


# =============================================================================
# API
# =============================================================================

class RouteRequest(BaseModel):
    request: str
    multi_route: bool = False


@app.on_event("startup")
async def startup():
    await workflow_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/route")
async def start_routing(request: RouteRequest):
    instance_id = str(uuid.uuid4())
    workflow_name = "multi_route_workflow" if request.multi_route else "routing_workflow"

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name=workflow_name,
            input=request.request,
            instance_id=instance_id
        )

    return {
        "instance_id": instance_id,
        "workflow": workflow_name,
        "status": "started"
    }


@app.get("/route/{instance_id}")
async def get_routing_status(instance_id: str):
    async with DaprClient() as client:
        state = await client.get_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )
        return {
            "instance_id": instance_id,
            "status": state.runtime_status,
            "result": state.serialized_output
        }


@app.get("/agents")
async def list_agents():
    return {
        "agents": [
            {"name": agent.name, "role": agent.role}
            for agent in AGENTS.values()
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
