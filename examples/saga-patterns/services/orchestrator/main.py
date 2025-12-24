"""Saga Orchestrator - Demonstrates sequential and parallel saga patterns with DAPR Workflows."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dapr.clients import DaprClient
from dapr.ext.workflow import DaprWorkflowContext, WorkflowRuntime, workflow, activity, when_all
from datetime import timedelta
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Saga Orchestrator")


# =============================================================================
# Models
# =============================================================================

class SequentialSagaRequest(BaseModel):
    order_id: str
    amount: float


class ParallelSagaRequest(BaseModel):
    batch_id: str
    items: list[str]


# =============================================================================
# Activities (Saga Steps)
# =============================================================================

@activity
async def validate_order(ctx, data: dict) -> dict:
    """Step 1: Validate order data."""
    logger.info(f"Validating order: {data['order_id']}")
    # Simulate validation
    if data.get("amount", 0) <= 0:
        raise Exception("Invalid order amount")
    return {"validated": True, "order_id": data["order_id"]}


@activity
async def reserve_funds(ctx, data: dict) -> dict:
    """Step 2: Reserve funds (call payment service)."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-a",
            method_name="reserve",
            http_verb="POST",
            data={"order_id": data["order_id"], "amount": data["amount"]}
        )
        result = response.json()
        if not result.get("success"):
            raise Exception(f"Fund reservation failed: {result.get('error')}")
        return {"reservation_id": result["reservation_id"], "amount": data["amount"]}


@activity
async def allocate_inventory(ctx, data: dict) -> dict:
    """Step 3: Allocate inventory (call inventory service)."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-b",
            method_name="allocate",
            http_verb="POST",
            data={"order_id": data["order_id"]}
        )
        result = response.json()
        if not result.get("success"):
            raise Exception(f"Inventory allocation failed: {result.get('error')}")
        return {"allocation_id": result["allocation_id"]}


@activity
async def create_shipment(ctx, data: dict) -> dict:
    """Step 4: Create shipment (call shipping service)."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-c",
            method_name="ship",
            http_verb="POST",
            data={"order_id": data["order_id"], "allocation_id": data["allocation_id"]}
        )
        return response.json()


# Compensation activities
@activity
async def release_funds(ctx, reservation_id: str) -> None:
    """Compensate: Release reserved funds."""
    logger.info(f"Compensating: Releasing funds {reservation_id}")
    async with DaprClient() as client:
        await client.invoke_method(
            app_id="service-a",
            method_name=f"release/{reservation_id}",
            http_verb="POST"
        )


@activity
async def release_inventory(ctx, allocation_id: str) -> None:
    """Compensate: Release allocated inventory."""
    logger.info(f"Compensating: Releasing inventory {allocation_id}")
    async with DaprClient() as client:
        await client.invoke_method(
            app_id="service-b",
            method_name=f"release/{allocation_id}",
            http_verb="POST"
        )


# Parallel saga activities
@activity
async def process_item_a(ctx, item: str) -> dict:
    """Process item in parallel branch A."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-a",
            method_name=f"process/{item}",
            http_verb="POST"
        )
        return {"item": item, "service": "A", "result": response.json()}


@activity
async def process_item_b(ctx, item: str) -> dict:
    """Process item in parallel branch B."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-b",
            method_name=f"process/{item}",
            http_verb="POST"
        )
        return {"item": item, "service": "B", "result": response.json()}


@activity
async def process_item_c(ctx, item: str) -> dict:
    """Process item in parallel branch C."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="service-c",
            method_name=f"process/{item}",
            http_verb="POST"
        )
        return {"item": item, "service": "C", "result": response.json()}


# =============================================================================
# Workflows (Saga Patterns)
# =============================================================================

@workflow
def sequential_saga(ctx: DaprWorkflowContext, data: dict):
    """
    Sequential Saga Pattern:
    Execute steps in order, compensate in reverse on failure.
    """
    reservation = None
    allocation = None

    try:
        # Step 1: Validate (no compensation needed)
        yield ctx.call_activity(validate_order, input=data)

        # Step 2: Reserve funds
        reservation = yield ctx.call_activity(reserve_funds, input=data)

        # Step 3: Allocate inventory
        allocation = yield ctx.call_activity(
            allocate_inventory,
            input={"order_id": data["order_id"]}
        )

        # Step 4: Create shipment
        shipment = yield ctx.call_activity(
            create_shipment,
            input={"order_id": data["order_id"], "allocation_id": allocation["allocation_id"]}
        )

        return {
            "status": "completed",
            "order_id": data["order_id"],
            "reservation": reservation,
            "allocation": allocation,
            "shipment": shipment
        }

    except Exception as e:
        # Compensate in reverse order
        logger.error(f"Saga failed: {e}. Starting compensation...")

        if allocation:
            yield ctx.call_activity(release_inventory, input=allocation["allocation_id"])

        if reservation:
            yield ctx.call_activity(release_funds, input=reservation["reservation_id"])

        return {
            "status": "compensated",
            "order_id": data["order_id"],
            "error": str(e)
        }


@workflow
def parallel_saga(ctx: DaprWorkflowContext, data: dict):
    """
    Parallel Saga Pattern:
    Execute independent steps in parallel, merge results.
    """
    items = data.get("items", [])

    # Start parallel processing for each item
    tasks = []
    for item in items:
        # Each item is processed by all three services in parallel
        task_a = ctx.call_activity(process_item_a, input=item)
        task_b = ctx.call_activity(process_item_b, input=item)
        task_c = ctx.call_activity(process_item_c, input=item)
        tasks.extend([task_a, task_b, task_c])

    # Wait for all parallel tasks to complete
    results = yield when_all(tasks)

    return {
        "status": "completed",
        "batch_id": data["batch_id"],
        "results": results
    }


@workflow
def saga_with_timeout(ctx: DaprWorkflowContext, data: dict):
    """
    Saga with timeout handling:
    Demonstrates deadline management for long-running sagas.
    """
    # Set saga deadline
    deadline = ctx.current_utc_datetime + timedelta(minutes=30)

    try:
        # Step with explicit timeout
        result = yield ctx.call_activity(
            validate_order,
            input=data,
            retry_policy={
                "max_number_of_attempts": 3,
                "first_retry_interval": timedelta(seconds=1),
                "backoff_coefficient": 2.0,
                "max_retry_interval": timedelta(seconds=30)
            }
        )

        # Check if deadline exceeded
        if ctx.current_utc_datetime > deadline:
            raise TimeoutError("Saga deadline exceeded")

        return {"status": "completed", "result": result}

    except TimeoutError:
        return {"status": "timed_out", "order_id": data["order_id"]}


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(sequential_saga)
workflow_runtime.register_workflow(parallel_saga)
workflow_runtime.register_workflow(saga_with_timeout)
workflow_runtime.register_activity(validate_order)
workflow_runtime.register_activity(reserve_funds)
workflow_runtime.register_activity(allocate_inventory)
workflow_runtime.register_activity(create_shipment)
workflow_runtime.register_activity(release_funds)
workflow_runtime.register_activity(release_inventory)
workflow_runtime.register_activity(process_item_a)
workflow_runtime.register_activity(process_item_b)
workflow_runtime.register_activity(process_item_c)


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("Saga orchestrator started with workflow runtime")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "saga-orchestrator"}


@app.post("/saga/sequential")
async def start_sequential_saga(request: SequentialSagaRequest):
    """Start a sequential saga."""
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="sequential_saga",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {"instance_id": instance_id, "saga_type": "sequential"}


@app.post("/saga/parallel")
async def start_parallel_saga(request: ParallelSagaRequest):
    """Start a parallel saga."""
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="parallel_saga",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {"instance_id": instance_id, "saga_type": "parallel"}


@app.get("/saga/{instance_id}/status")
async def get_saga_status(instance_id: str):
    """Get saga workflow status."""
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


@app.post("/saga/{instance_id}/terminate")
async def terminate_saga(instance_id: str):
    """Terminate a running saga."""
    async with DaprClient() as client:
        await client.terminate_workflow(
            workflow_component="dapr",
            instance_id=instance_id
        )
    return {"instance_id": instance_id, "status": "terminated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
