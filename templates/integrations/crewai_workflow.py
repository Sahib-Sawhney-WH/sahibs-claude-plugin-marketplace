"""
CrewAI + DAPR Workflow Integration

Run CrewAI agent crews as durable DAPR workflows.
Combines CrewAI's collaborative agent patterns with DAPR's fault tolerance.

Features:
- Durable crew execution with automatic retries
- State persistence between crew tasks
- Checkpoint/resume for long-running crews
- Event-driven crew coordination
"""

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool as crewai_tool
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    workflow,
    activity,
)
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import uuid
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CrewAI DAPR Workflow")


# =============================================================================
# CrewAI Agent Definitions
# =============================================================================

# Research Agent
researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments and insights",
    backstory="""You are an expert research analyst with a passion for
    discovering new information. You have a keen eye for detail and
    can synthesize complex information into clear insights.""",
    verbose=True,
    allow_delegation=False,
    llm=os.getenv("LLM_MODEL", "gpt-4o")
)

# Writer Agent
writer = Agent(
    role="Tech Content Writer",
    goal="Create engaging and informative content",
    backstory="""You are a skilled content writer specializing in
    technical topics. You can take complex research and transform
    it into accessible, engaging content.""",
    verbose=True,
    allow_delegation=False,
    llm=os.getenv("LLM_MODEL", "gpt-4o")
)

# Editor Agent
editor = Agent(
    role="Senior Editor",
    goal="Ensure content quality and accuracy",
    backstory="""You are an experienced editor who ensures all content
    meets the highest standards of quality, accuracy, and clarity.""",
    verbose=True,
    allow_delegation=False,
    llm=os.getenv("LLM_MODEL", "gpt-4o")
)


# =============================================================================
# DAPR-Integrated Tools for CrewAI
# =============================================================================

@crewai_tool
def save_research_notes(topic: str, notes: str) -> str:
    """Save research notes to DAPR state store."""
    import asyncio

    async def _save():
        async with DaprClient() as client:
            await client.save_state(
                store_name="statestore",
                key=f"research-{topic.replace(' ', '-')}",
                value=notes
            )
        return f"Notes saved for topic: {topic}"

    return asyncio.run(_save())


@crewai_tool
def get_research_notes(topic: str) -> str:
    """Retrieve research notes from DAPR state store."""
    import asyncio

    async def _get():
        async with DaprClient() as client:
            state = await client.get_state(
                store_name="statestore",
                key=f"research-{topic.replace(' ', '-')}"
            )
            if state.data:
                return state.data.decode() if isinstance(state.data, bytes) else str(state.data)
            return f"No notes found for topic: {topic}"

    return asyncio.run(_get())


@crewai_tool
def publish_content_event(event_type: str, content: str) -> str:
    """Publish content event via DAPR pub/sub."""
    import asyncio

    async def _publish():
        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name="pubsub",
                topic_name="content-events",
                data=json.dumps({
                    "event_type": event_type,
                    "content": content[:500]  # Preview
                })
            )
        return f"Published event: {event_type}"

    return asyncio.run(_publish())


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def run_research_task(ctx, data: dict) -> dict:
    """Execute research task within CrewAI."""
    topic = data["topic"]
    context = data.get("context", "")

    logger.info(f"Running research task for: {topic}")

    # Create research task
    research_task = Task(
        description=f"""Research the following topic thoroughly:
        Topic: {topic}
        Additional Context: {context}

        Provide comprehensive findings including:
        1. Key facts and data
        2. Recent developments
        3. Expert opinions
        4. Potential implications""",
        expected_output="Detailed research report with citations",
        agent=researcher,
        tools=[save_research_notes, get_research_notes]
    )

    # Run single-agent crew
    crew = Crew(
        agents=[researcher],
        tasks=[research_task],
        verbose=True
    )

    result = crew.kickoff()

    return {
        "task": "research",
        "topic": topic,
        "output": str(result),
        "status": "completed"
    }


@activity
async def run_writing_task(ctx, data: dict) -> dict:
    """Execute writing task within CrewAI."""
    topic = data["topic"]
    research = data["research"]

    logger.info(f"Running writing task for: {topic}")

    writing_task = Task(
        description=f"""Create engaging content based on this research:
        Topic: {topic}
        Research:
        {research}

        Write a comprehensive, well-structured article that:
        1. Has a compelling introduction
        2. Presents key findings clearly
        3. Includes relevant examples
        4. Has a strong conclusion""",
        expected_output="Well-written article (800-1200 words)",
        agent=writer
    )

    crew = Crew(
        agents=[writer],
        tasks=[writing_task],
        verbose=True
    )

    result = crew.kickoff()

    return {
        "task": "writing",
        "topic": topic,
        "output": str(result),
        "status": "completed"
    }


@activity
async def run_editing_task(ctx, data: dict) -> dict:
    """Execute editing task within CrewAI."""
    content = data["content"]

    logger.info("Running editing task")

    editing_task = Task(
        description=f"""Review and edit this content:
        {content}

        Check for:
        1. Grammar and spelling
        2. Clarity and flow
        3. Factual accuracy
        4. Engagement and readability

        Provide the edited final version.""",
        expected_output="Polished, publication-ready content",
        agent=editor,
        tools=[publish_content_event]
    )

    crew = Crew(
        agents=[editor],
        tasks=[editing_task],
        verbose=True
    )

    result = crew.kickoff()

    return {
        "task": "editing",
        "output": str(result),
        "status": "completed"
    }


@activity
async def run_full_crew(ctx, data: dict) -> dict:
    """Run complete CrewAI crew with all agents."""
    topic = data["topic"]
    context = data.get("context", "")

    logger.info(f"Running full crew for: {topic}")

    # Define tasks
    research_task = Task(
        description=f"Research the topic: {topic}. Context: {context}",
        expected_output="Comprehensive research findings",
        agent=researcher,
        tools=[save_research_notes]
    )

    writing_task = Task(
        description="Write an article based on the research findings",
        expected_output="Draft article",
        agent=writer,
        context=[research_task]
    )

    editing_task = Task(
        description="Edit and polish the article",
        expected_output="Final publication-ready article",
        agent=editor,
        context=[writing_task],
        tools=[publish_content_event]
    )

    # Create and run crew
    crew = Crew(
        agents=[researcher, writer, editor],
        tasks=[research_task, writing_task, editing_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()

    return {
        "topic": topic,
        "final_output": str(result),
        "status": "completed"
    }


# =============================================================================
# DAPR Workflows
# =============================================================================

@workflow
def sequential_crew_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Run CrewAI tasks sequentially as durable workflow steps.
    Each step is checkpointed for fault tolerance.
    """
    topic = data["topic"]
    context = data.get("context", "")

    # Step 1: Research (durable)
    research_result = yield ctx.call_activity(
        run_research_task,
        input={"topic": topic, "context": context}
    )

    # Step 2: Writing (durable)
    writing_result = yield ctx.call_activity(
        run_writing_task,
        input={"topic": topic, "research": research_result["output"]}
    )

    # Step 3: Editing (durable)
    editing_result = yield ctx.call_activity(
        run_editing_task,
        input={"content": writing_result["output"]}
    )

    return {
        "topic": topic,
        "research": research_result["output"],
        "draft": writing_result["output"],
        "final": editing_result["output"],
        "status": "completed"
    }


@workflow
def full_crew_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Run complete CrewAI crew as a single durable activity.
    Simpler but less granular checkpointing.
    """
    result = yield ctx.call_activity(run_full_crew, input=data)
    return result


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(sequential_crew_workflow)
workflow_runtime.register_workflow(full_crew_workflow)
workflow_runtime.register_activity(run_research_task)
workflow_runtime.register_activity(run_writing_task)
workflow_runtime.register_activity(run_editing_task)
workflow_runtime.register_activity(run_full_crew)


# =============================================================================
# API Models
# =============================================================================

class CrewRequest(BaseModel):
    topic: str = Field(..., description="Topic to research and write about")
    context: str = Field(default="", description="Additional context")
    workflow_type: str = Field(
        default="sequential",
        description="sequential or full_crew"
    )


class CrewStatus(BaseModel):
    instance_id: str
    status: str
    result: Optional[dict] = None


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("CrewAI DAPR Workflow service started")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/crew/start", response_model=CrewStatus)
async def start_crew(request: CrewRequest):
    """Start a CrewAI workflow."""
    instance_id = str(uuid.uuid4())

    workflow_name = (
        "sequential_crew_workflow"
        if request.workflow_type == "sequential"
        else "full_crew_workflow"
    )

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name=workflow_name,
            input=request.model_dump(),
            instance_id=instance_id
        )

    return CrewStatus(
        instance_id=instance_id,
        status="started"
    )


@app.get("/crew/{instance_id}", response_model=CrewStatus)
async def get_crew_status(instance_id: str):
    """Get crew workflow status."""
    async with DaprClient() as client:
        state = await client.get_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )

        result = None
        if state.serialized_output:
            try:
                result = json.loads(state.serialized_output)
            except json.JSONDecodeError:
                result = {"output": state.serialized_output}

        return CrewStatus(
            instance_id=instance_id,
            status=state.runtime_status,
            result=result
        )


@app.post("/crew/{instance_id}/terminate")
async def terminate_crew(instance_id: str):
    """Terminate a running crew workflow."""
    async with DaprClient() as client:
        await client.terminate_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )
    return {"instance_id": instance_id, "status": "terminated"}


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
