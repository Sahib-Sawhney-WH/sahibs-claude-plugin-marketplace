"""
Parallelization Pattern

Execute multiple agent tasks concurrently and aggregate results.
Useful for processing multiple items, getting diverse perspectives,
or speeding up independent operations.

Example use cases:
- Analyzing multiple documents simultaneously
- Getting perspectives from different expert agents
- Parallel data processing pipelines
"""

from dapr_agents import AssistantAgent
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    workflow,
    activity,
    when_all,
)
from dapr.clients import DaprClient
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import uuid
import os
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Parallelization Pattern")


# =============================================================================
# Parallel Processing Agents
# =============================================================================

# Generic processing agent
processing_agent = AssistantAgent(
    name="processor",
    role="Parallel Processor",
    instructions="""Process the given item efficiently.
    Provide a structured response with key findings.""",
    model="gpt-4o"
)

# Aggregation agent
aggregator_agent = AssistantAgent(
    name="aggregator",
    role="Result Aggregator",
    instructions="""Combine and synthesize multiple results into a coherent summary.
    Identify common themes, differences, and overall patterns.""",
    model="gpt-4o"
)


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def process_item(ctx, item: dict) -> dict:
    """Process a single item."""
    item_id = item.get("id", "unknown")
    content = item.get("content", "")

    logger.info(f"Processing item: {item_id}")

    result = await processing_agent.run(
        f"Process this item:\n\nID: {item_id}\nContent: {content}"
    )

    return {
        "item_id": item_id,
        "result": result,
        "status": "completed"
    }


@activity
async def aggregate_results(ctx, results: list) -> str:
    """Aggregate all parallel results."""
    logger.info(f"Aggregating {len(results)} results")

    results_text = "\n\n".join([
        f"Item {r['item_id']}:\n{r['result']}"
        for r in results
    ])

    return await aggregator_agent.run(
        f"Aggregate and summarize these results:\n\n{results_text}"
    )


# =============================================================================
# Parallel Workflow
# =============================================================================

@workflow
def parallel_processing_workflow(ctx: DaprWorkflowContext, items: list):
    """
    Process multiple items in parallel and aggregate results.

    Args:
        items: List of items to process, each with 'id' and 'content'
    """
    # Launch all processing tasks in parallel
    tasks = []
    for item in items:
        task = ctx.call_activity(process_item, input=item)
        tasks.append(task)

    # Wait for all tasks to complete
    results = yield when_all(tasks)

    # Aggregate results
    summary = yield ctx.call_activity(aggregate_results, input=results)

    return {
        "individual_results": results,
        "summary": summary,
        "total_processed": len(results)
    }


@workflow
def fan_out_fan_in_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Fan-out/Fan-in pattern: Split work, process in parallel, combine.

    Args:
        data: Contains 'input' to split and 'chunk_size' for splitting
    """
    input_text = data.get("input", "")
    chunk_size = data.get("chunk_size", 500)

    # Fan-out: Split input into chunks
    chunks = [
        input_text[i:i + chunk_size]
        for i in range(0, len(input_text), chunk_size)
    ]

    # Process chunks in parallel
    tasks = []
    for i, chunk in enumerate(chunks):
        task = ctx.call_activity(
            process_item,
            input={"id": f"chunk-{i}", "content": chunk}
        )
        tasks.append(task)

    # Wait for all chunks
    results = yield when_all(tasks)

    # Fan-in: Aggregate
    summary = yield ctx.call_activity(aggregate_results, input=results)

    return {
        "chunks_processed": len(chunks),
        "results": results,
        "summary": summary
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(parallel_processing_workflow)
workflow_runtime.register_workflow(fan_out_fan_in_workflow)
workflow_runtime.register_activity(process_item)
workflow_runtime.register_activity(aggregate_results)


# =============================================================================
# API
# =============================================================================

class ParallelRequest(BaseModel):
    items: List[dict]


class FanOutRequest(BaseModel):
    input: str
    chunk_size: int = 500


@app.on_event("startup")
async def startup():
    await workflow_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/parallel")
async def start_parallel(request: ParallelRequest):
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="parallel_processing_workflow",
            input=request.items,
            instance_id=instance_id
        )

    return {"instance_id": instance_id, "items_count": len(request.items)}


@app.post("/fanout")
async def start_fanout(request: FanOutRequest):
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="fan_out_fan_in_workflow",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {"instance_id": instance_id}


@app.get("/status/{instance_id}")
async def get_status(instance_id: str):
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
