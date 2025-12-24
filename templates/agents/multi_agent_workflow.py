"""
DAPR Multi-Agent Workflow Template

A coordinated multi-agent system using DAPR Workflows for orchestration.
Demonstrates agent specialization, task routing, and collaborative processing.

Usage:
    dapr run --app-id multi-agent --app-port 8000 --resources-path ./components -- python multi_agent_workflow.py
"""

from dapr_agents import AssistantAgent, tool
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    WorkflowActivityContext,
    workflow,
    activity,
    when_all,
)
from dapr.clients import DaprClient
from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn
import asyncio
import uuid
import os
import logging
from typing import Literal
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Orchestration Service")


# =============================================================================
# Specialized Agents
# =============================================================================

# Triage Agent - Routes requests to appropriate specialists
triage_agent = AssistantAgent(
    name="triage",
    role="Request Triage Specialist",
    instructions="""You are a triage specialist that classifies incoming requests.

Your job is to analyze requests and classify them into one of these categories:
- "technical": Technical questions, coding help, system issues
- "research": Information gathering, analysis, market research
- "creative": Content creation, writing, design suggestions
- "general": Everything else

Respond with ONLY the category name, nothing else.
""",
    model="gpt-4o",
    temperature=0.1  # Low temperature for consistent classification
)

# Technical Expert Agent
technical_agent = AssistantAgent(
    name="technical-expert",
    role="Technical Expert",
    instructions="""You are a technical expert specializing in:
- Software development and coding
- System architecture and design
- Debugging and troubleshooting
- DevOps and infrastructure

Provide detailed, accurate technical responses.
Include code examples when helpful.
Explain complex concepts clearly.
""",
    model="gpt-4o"
)

# Research Agent
research_agent = AssistantAgent(
    name="research-analyst",
    role="Research Analyst",
    instructions="""You are a research analyst specializing in:
- Information gathering and synthesis
- Data analysis and interpretation
- Market research and trends
- Comparative analysis

Provide well-structured, factual responses.
Cite sources when possible.
Highlight key findings and insights.
""",
    model="gpt-4o"
)

# Creative Agent
creative_agent = AssistantAgent(
    name="creative-specialist",
    role="Creative Specialist",
    instructions="""You are a creative specialist focusing on:
- Content writing and copywriting
- Creative ideation and brainstorming
- Marketing messages and campaigns
- Storytelling and narrative design

Be creative, engaging, and original.
Offer multiple options when appropriate.
Consider the target audience.
""",
    model="gpt-4o",
    temperature=0.9  # Higher temperature for creativity
)

# General Assistant
general_agent = AssistantAgent(
    name="general-assistant",
    role="General Assistant",
    instructions="""You are a helpful general assistant.
Handle a wide variety of requests professionally.
Be clear, concise, and helpful.
""",
    model="gpt-4o"
)


# =============================================================================
# Agent Registry
# =============================================================================

AGENTS = {
    "technical": technical_agent,
    "research": research_agent,
    "creative": creative_agent,
    "general": general_agent
}


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def triage_request(ctx: WorkflowActivityContext, request: str) -> str:
    """Classify the request using the triage agent."""
    logger.info(f"Triaging request: {request[:50]}...")
    classification = await triage_agent.run(request)
    category = classification.strip().lower()

    # Validate category
    if category not in AGENTS:
        category = "general"

    logger.info(f"Request classified as: {category}")
    return category


@activity
async def process_with_agent(ctx: WorkflowActivityContext, data: dict) -> dict:
    """Process request with the appropriate specialist agent."""
    category = data["category"]
    request = data["request"]

    agent = AGENTS[category]
    logger.info(f"Processing with {agent.name}...")

    response = await agent.run(request)

    return {
        "category": category,
        "agent": agent.name,
        "response": response
    }


@activity
async def synthesize_results(ctx: WorkflowActivityContext, results: list[dict]) -> str:
    """Synthesize results from multiple agents."""
    # Use a synthesis agent for combining results
    synthesis_prompt = "Synthesize the following responses into a coherent answer:\n\n"
    for i, result in enumerate(results, 1):
        synthesis_prompt += f"Response {i} from {result['agent']}:\n{result['response']}\n\n"

    synthesizer = AssistantAgent(
        name="synthesizer",
        role="Response Synthesizer",
        instructions="Combine multiple agent responses into a single coherent answer.",
        model="gpt-4o"
    )

    return await synthesizer.run(synthesis_prompt)


# =============================================================================
# Workflows
# =============================================================================

@workflow
def single_agent_workflow(ctx: DaprWorkflowContext, request: str):
    """
    Simple workflow: Triage → Process with single agent.
    """
    # Step 1: Triage the request
    category = yield ctx.call_activity(triage_request, input=request)

    # Step 2: Process with specialist
    result = yield ctx.call_activity(
        process_with_agent,
        input={"category": category, "request": request}
    )

    return result


@workflow
def parallel_agents_workflow(ctx: DaprWorkflowContext, request: str):
    """
    Parallel workflow: Get responses from multiple agents and synthesize.
    """
    # Process with multiple agents in parallel
    tasks = []
    for category in ["technical", "research", "creative"]:
        task = ctx.call_activity(
            process_with_agent,
            input={"category": category, "request": request}
        )
        tasks.append(task)

    # Wait for all agents
    results = yield when_all(tasks)

    # Synthesize results
    final_response = yield ctx.call_activity(synthesize_results, input=results)

    return {
        "individual_responses": results,
        "synthesized_response": final_response
    }


@workflow
def iterative_refinement_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Iterative workflow: Generate → Evaluate → Refine loop.
    """
    request = data["request"]
    max_iterations = data.get("max_iterations", 3)
    quality_threshold = data.get("quality_threshold", 0.8)

    # Initial generation
    result = yield ctx.call_activity(
        process_with_agent,
        input={"category": "creative", "request": request}
    )

    current_response = result["response"]

    for iteration in range(max_iterations):
        # Evaluate the response
        evaluator = AssistantAgent(
            name="evaluator",
            role="Quality Evaluator",
            instructions="""Evaluate the response quality on a scale of 0-1.
            Consider: accuracy, completeness, clarity, and relevance.
            Respond with just a number and brief feedback.
            Format: SCORE|FEEDBACK""",
            model="gpt-4o",
            temperature=0.1
        )

        eval_result = yield ctx.call_activity(
            lambda ctx, data: evaluator.run(
                f"Evaluate this response to '{data['request']}':\n\n{data['response']}"
            ),
            input={"request": request, "response": current_response}
        )

        # Parse evaluation
        try:
            score_str, feedback = eval_result.split("|", 1)
            score = float(score_str.strip())
        except:
            score = 0.5
            feedback = "Unable to parse evaluation"

        if score >= quality_threshold:
            return {
                "response": current_response,
                "iterations": iteration + 1,
                "final_score": score
            }

        # Refine based on feedback
        refinement = yield ctx.call_activity(
            process_with_agent,
            input={
                "category": "creative",
                "request": f"Improve this response based on feedback.\n\nOriginal: {current_response}\n\nFeedback: {feedback}"
            }
        )
        current_response = refinement["response"]

    return {
        "response": current_response,
        "iterations": max_iterations,
        "note": "Reached max iterations"
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(single_agent_workflow)
workflow_runtime.register_workflow(parallel_agents_workflow)
workflow_runtime.register_workflow(iterative_refinement_workflow)
workflow_runtime.register_activity(triage_request)
workflow_runtime.register_activity(process_with_agent)
workflow_runtime.register_activity(synthesize_results)


# =============================================================================
# API Models
# =============================================================================

class WorkflowRequest(BaseModel):
    request: str
    workflow_type: Literal["single", "parallel", "iterative"] = "single"
    max_iterations: int = Field(default=3, ge=1, le=10)
    quality_threshold: float = Field(default=0.8, ge=0, le=1)


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("Multi-agent workflow runtime started")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agents": list(AGENTS.keys()),
        "workflows": ["single", "parallel", "iterative"]
    }


@app.post("/process")
async def process_request(request: WorkflowRequest):
    """Start a multi-agent workflow."""
    instance_id = str(uuid.uuid4())

    workflow_map = {
        "single": "single_agent_workflow",
        "parallel": "parallel_agents_workflow",
        "iterative": "iterative_refinement_workflow"
    }

    workflow_name = workflow_map[request.workflow_type]

    # Prepare input based on workflow type
    if request.workflow_type == "iterative":
        workflow_input = {
            "request": request.request,
            "max_iterations": request.max_iterations,
            "quality_threshold": request.quality_threshold
        }
    else:
        workflow_input = request.request

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name=workflow_name,
            input=workflow_input,
            instance_id=instance_id
        )

    return {
        "instance_id": instance_id,
        "workflow_type": request.workflow_type,
        "status": "started"
    }


@app.get("/process/{instance_id}")
async def get_status(instance_id: str):
    """Get workflow status."""
    async with DaprClient() as client:
        state = await client.get_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )

        return {
            "instance_id": instance_id,
            "status": state.runtime_status,
            "result": state.serialized_output if state.runtime_status == "COMPLETED" else None
        }


@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {
        "agents": [
            {"name": agent.name, "role": agent.role}
            for agent in AGENTS.values()
        ]
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
