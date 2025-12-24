"""
Prompt Chaining Pattern

Sequential LLM calls where each step builds on the previous output.
Useful for complex tasks that need to be broken down into stages.

Example use cases:
- Document analysis → summarization → action items
- Research → synthesis → report generation
- Input validation → processing → formatting
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Prompt Chaining Pattern")


# =============================================================================
# Specialized Agents for Each Stage
# =============================================================================

# Stage 1: Extract key information
extractor_agent = AssistantAgent(
    name="extractor",
    role="Information Extractor",
    instructions="""Extract the key points, facts, and important information from the input.
    Be thorough but concise. Format as a bullet list.""",
    model="gpt-4o",
    temperature=0.3
)

# Stage 2: Analyze and synthesize
analyzer_agent = AssistantAgent(
    name="analyzer",
    role="Analysis Specialist",
    instructions="""Analyze the extracted information and identify:
    - Main themes and patterns
    - Key insights
    - Potential issues or concerns
    - Opportunities or recommendations""",
    model="gpt-4o",
    temperature=0.5
)

# Stage 3: Generate final output
generator_agent = AssistantAgent(
    name="generator",
    role="Content Generator",
    instructions="""Generate a polished, professional output based on the analysis.
    Structure the content clearly with sections.
    Make it actionable and easy to understand.""",
    model="gpt-4o",
    temperature=0.7
)


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def extract_stage(ctx, input_text: str) -> str:
    """Stage 1: Extract key information."""
    logger.info("Stage 1: Extracting information...")
    return await extractor_agent.run(
        f"Extract key information from the following:\n\n{input_text}"
    )


@activity
async def analyze_stage(ctx, extracted: str) -> str:
    """Stage 2: Analyze extracted information."""
    logger.info("Stage 2: Analyzing...")
    return await analyzer_agent.run(
        f"Analyze the following extracted information:\n\n{extracted}"
    )


@activity
async def generate_stage(ctx, analysis: str) -> str:
    """Stage 3: Generate final output."""
    logger.info("Stage 3: Generating output...")
    return await generator_agent.run(
        f"Generate a comprehensive report based on this analysis:\n\n{analysis}"
    )


# =============================================================================
# Prompt Chaining Workflow
# =============================================================================

@workflow
def prompt_chain_workflow(ctx: DaprWorkflowContext, input_text: str):
    """
    Execute a chain of prompts, each building on the previous.

    Flow: Extract → Analyze → Generate
    """
    # Stage 1: Extract
    extracted = yield ctx.call_activity(extract_stage, input=input_text)

    # Stage 2: Analyze (depends on Stage 1)
    analysis = yield ctx.call_activity(analyze_stage, input=extracted)

    # Stage 3: Generate (depends on Stage 2)
    final_output = yield ctx.call_activity(generate_stage, input=analysis)

    return {
        "stages": {
            "extraction": extracted,
            "analysis": analysis,
            "final": final_output
        },
        "output": final_output
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(prompt_chain_workflow)
workflow_runtime.register_activity(extract_stage)
workflow_runtime.register_activity(analyze_stage)
workflow_runtime.register_activity(generate_stage)


# =============================================================================
# API
# =============================================================================

class ChainRequest(BaseModel):
    text: str


@app.on_event("startup")
async def startup():
    await workflow_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/chain")
async def start_chain(request: ChainRequest):
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="prompt_chain_workflow",
            input=request.text,
            instance_id=instance_id
        )

    return {"instance_id": instance_id, "status": "started"}


@app.get("/chain/{instance_id}")
async def get_chain_status(instance_id: str):
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


if __name__ == "__main__":
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
