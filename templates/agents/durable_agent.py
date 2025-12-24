"""
DAPR Durable Agent Template

A workflow-backed agent with fault tolerance, automatic retries,
and persistent state across restarts.

Usage:
    dapr run --app-id durable-agent --app-port 8000 --resources-path ./components -- python durable_agent.py
"""

from dapr_agents import DurableAgent, tool
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    WorkflowActivityContext,
    workflow,
    activity,
)
from dapr.clients import DaprClient
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException
import uvicorn
import asyncio
import os
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Durable Agent Service")


# =============================================================================
# Tool Input Schemas
# =============================================================================

class ResearchInput(BaseModel):
    """Input for research tool."""
    topic: str = Field(..., description="Topic to research")
    depth: str = Field(default="medium", description="Research depth: shallow, medium, deep")


class AnalyzeInput(BaseModel):
    """Input for analysis tool."""
    data: str = Field(..., description="Data to analyze")
    analysis_type: str = Field(default="summary", description="Type: summary, detailed, comparison")


# =============================================================================
# Agent Tools
# =============================================================================

@tool
async def research_topic(input: ResearchInput) -> str:
    """Research a topic using available sources.

    Performs comprehensive research on the given topic.
    Depth levels affect the thoroughness of research.

    Args:
        input: Research parameters

    Returns:
        Research findings as structured text
    """
    logger.info(f"Researching: {input.topic} (depth: {input.depth})")
    # TODO: Implement actual research logic
    return f"""Research findings on '{input.topic}':

Key Points:
1. First key finding about {input.topic}
2. Second important discovery
3. Third relevant point

Sources consulted: 3
Confidence: High
"""


@tool
async def analyze_data(input: AnalyzeInput) -> str:
    """Analyze data and provide insights.

    Performs analysis on provided data based on the specified type.

    Args:
        input: Analysis parameters

    Returns:
        Analysis results and insights
    """
    logger.info(f"Analyzing data (type: {input.analysis_type})")
    return f"""Analysis Results ({input.analysis_type}):

Summary:
- Data contains relevant patterns
- Key metrics identified
- Actionable insights extracted

Recommendations:
1. Consider the main trends
2. Focus on highlighted areas
"""


# =============================================================================
# Durable Agent Definition
# =============================================================================

# Create the durable agent instance
durable_agent = DurableAgent(
    name="research-analyst",
    role="Research and Analysis Expert",
    instructions="""You are an expert research and analysis agent.

Your capabilities:
- Research topics thoroughly using the research_topic tool
- Analyze data and provide insights using the analyze_data tool

You provide well-structured, actionable insights based on your research.
Always cite your sources and explain your reasoning.
""",
    tools=[research_topic, analyze_data],
    model="gpt-4o"
)


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def research_activity(ctx: WorkflowActivityContext, topic: str) -> dict:
    """Activity that performs research using the durable agent."""
    logger.info(f"Research activity started for: {topic}")

    result = await durable_agent.run(
        f"Research the following topic thoroughly: {topic}"
    )

    return {
        "topic": topic,
        "research": result,
        "status": "completed"
    }


@activity
async def analyze_activity(ctx: WorkflowActivityContext, data: dict) -> dict:
    """Activity that analyzes research results."""
    logger.info("Analysis activity started")

    result = await durable_agent.run(
        f"Analyze the following research and provide key insights:\n{data['research']}"
    )

    return {
        "analysis": result,
        "original_topic": data["topic"],
        "status": "completed"
    }


@activity
async def generate_report_activity(ctx: WorkflowActivityContext, data: dict) -> str:
    """Activity that generates a final report."""
    logger.info("Report generation activity started")

    result = await durable_agent.run(
        f"""Generate a comprehensive report based on:

Topic: {data['original_topic']}
Research: {data.get('research', 'N/A')}
Analysis: {data['analysis']}

Format the report with sections for Executive Summary, Findings, and Recommendations.
"""
    )

    return result


# =============================================================================
# Durable Workflow
# =============================================================================

@workflow
def research_workflow(ctx: DaprWorkflowContext, input_data: dict):
    """
    Durable workflow for research and analysis.

    This workflow:
    1. Researches a topic
    2. Analyzes the research
    3. Generates a final report

    Each step is durable and will retry on failure.
    """
    topic = input_data.get("topic", "general topic")

    # Step 1: Research the topic (with retry)
    research_result = yield ctx.call_activity(
        research_activity,
        input=topic,
        retry_policy={
            "max_attempts": 3,
            "initial_interval": "5s",
            "backoff_coefficient": 2.0,
            "max_interval": "60s"
        }
    )

    # Step 2: Analyze the research
    analysis_result = yield ctx.call_activity(
        analyze_activity,
        input=research_result,
        retry_policy={
            "max_attempts": 3,
            "initial_interval": "5s"
        }
    )

    # Step 3: Generate final report
    report = yield ctx.call_activity(
        generate_report_activity,
        input=analysis_result
    )

    return {
        "topic": topic,
        "report": report,
        "status": "completed"
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(research_workflow)
workflow_runtime.register_activity(research_activity)
workflow_runtime.register_activity(analyze_activity)
workflow_runtime.register_activity(generate_report_activity)


# =============================================================================
# API Endpoints
# =============================================================================

class ResearchRequest(BaseModel):
    topic: str


@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("Durable agent workflow runtime started")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": durable_agent.name}


@app.post("/research")
async def start_research(request: ResearchRequest):
    """Start a new research workflow."""
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="research_workflow",
            input={"topic": request.topic},
            instance_id=instance_id
        )

    return {
        "instance_id": instance_id,
        "topic": request.topic,
        "status": "started"
    }


@app.get("/research/{instance_id}")
async def get_research_status(instance_id: str):
    """Get the status of a research workflow."""
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


@app.post("/chat")
async def chat(message: str):
    """Direct chat with the durable agent (non-workflow)."""
    response = await durable_agent.run(message)
    return {"response": response}


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
