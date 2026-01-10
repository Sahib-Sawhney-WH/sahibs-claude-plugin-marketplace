"""
{{WORKFLOW_NAME}} - DAPR Workflow

A durable workflow template with proper error handling and compensation.
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Tuple

from dapr.ext.workflow import (
    WorkflowRuntime,
    DaprWorkflowClient,
    DaprWorkflowContext,
    WorkflowActivityContext,
    RetryPolicy
)

# =============================================================================
# Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("{{WORKFLOW_NAME}}")

# Initialize workflow runtime
wf_runtime = WorkflowRuntime()

# Default retry policy
default_retry = RetryPolicy(
    max_number_of_attempts=3,
    first_retry_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    max_retry_interval=timedelta(seconds=30)
)


# =============================================================================
# Workflow Definition
# =============================================================================

@wf_runtime.workflow(name="{{WORKFLOW_NAME}}")
def {{WORKFLOW_NAME}}_workflow(ctx: DaprWorkflowContext, input_data: Dict[str, Any]):
    """
    Main workflow orchestration.

    This workflow demonstrates a saga pattern with compensation on failure.

    Args:
        ctx: Workflow context for calling activities and managing state
        input_data: Input data for the workflow

    Returns:
        Workflow result with status and details
    """
    workflow_id = ctx.instance_id
    logger.info(f"[{workflow_id}] Starting workflow with input: {input_data}")

    # Track completed steps for compensation
    compensations: List[Tuple[str, Dict]] = []

    try:
        # =================================================================
        # Step 1: Validate Input
        # =================================================================
        validation_result = yield ctx.call_activity(
            validate_input,
            input=input_data
        )
        logger.info(f"[{workflow_id}] Step 1 complete: Validation passed")

        # =================================================================
        # Step 2: Process Data
        # =================================================================
        process_result = yield ctx.call_activity(
            process_data,
            input=validation_result
        )
        compensations.append(("rollback_process", process_result))
        logger.info(f"[{workflow_id}] Step 2 complete: Data processed")

        # =================================================================
        # Step 3: Save Results
        # =================================================================
        save_result = yield ctx.call_activity(
            save_results,
            input=process_result
        )
        compensations.append(("delete_results", save_result))
        logger.info(f"[{workflow_id}] Step 3 complete: Results saved")

        # =================================================================
        # Step 4: Notify Completion
        # =================================================================
        yield ctx.call_activity(
            send_notification,
            input={
                "type": "success",
                "workflow_id": workflow_id,
                "result": save_result
            }
        )
        logger.info(f"[{workflow_id}] Step 4 complete: Notification sent")

        return {
            "status": "completed",
            "workflow_id": workflow_id,
            "result": save_result
        }

    except Exception as e:
        logger.error(f"[{workflow_id}] Workflow failed: {e}")

        # Execute compensating transactions in reverse order
        for comp_activity, comp_data in reversed(compensations):
            try:
                logger.info(f"[{workflow_id}] Running compensation: {comp_activity}")
                yield ctx.call_activity(comp_activity, input=comp_data)
            except Exception as comp_error:
                logger.error(f"[{workflow_id}] Compensation failed: {comp_error}")

        # Notify failure
        yield ctx.call_activity(
            send_notification,
            input={
                "type": "failure",
                "workflow_id": workflow_id,
                "error": str(e)
            }
        )

        return {
            "status": "failed",
            "workflow_id": workflow_id,
            "error": str(e)
        }


# =============================================================================
# Activity Definitions
# =============================================================================

@wf_runtime.activity(name="validate_input")
def validate_input(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the input data."""
    logger.info(f"Validating input: {data}")

    # Add your validation logic here
    if not data:
        raise ValueError("Input data cannot be empty")

    return {
        "validated": True,
        "original_data": data
    }


@wf_runtime.activity(name="process_data")
def process_data(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the validated data."""
    logger.info(f"Processing data: {data}")

    # Add your processing logic here
    result = {
        "processed": True,
        "input": data,
        "output": {"transformed": True}
    }

    return result


@wf_runtime.activity(name="save_results")
def save_results(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> Dict[str, Any]:
    """Save the processed results."""
    logger.info(f"Saving results: {data}")

    # Add your save logic here (e.g., to state store, database)
    result = {
        "saved": True,
        "data": data,
        "location": "statestore/results"
    }

    return result


@wf_runtime.activity(name="send_notification")
def send_notification(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> None:
    """Send notification about workflow status."""
    logger.info(f"Sending notification: {data}")

    # Add your notification logic here (e.g., email, pub/sub event)
    pass


# =============================================================================
# Compensation Activities
# =============================================================================

@wf_runtime.activity(name="rollback_process")
def rollback_process(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> None:
    """Rollback the processing step."""
    logger.info(f"Rolling back process: {data}")
    # Add your rollback logic here


@wf_runtime.activity(name="delete_results")
def delete_results(ctx: WorkflowActivityContext, data: Dict[str, Any]) -> None:
    """Delete saved results."""
    logger.info(f"Deleting results: {data}")
    # Add your delete logic here


# =============================================================================
# Workflow Client Functions
# =============================================================================

async def start_workflow(input_data: Dict[str, Any], instance_id: str = None) -> str:
    """Start a new workflow instance."""
    async with DaprWorkflowClient() as client:
        instance_id = await client.schedule_new_workflow(
            workflow="{{WORKFLOW_NAME}}",
            input=input_data,
            instance_id=instance_id
        )
        logger.info(f"Started workflow: {instance_id}")
        return instance_id


async def get_workflow_status(instance_id: str) -> Dict[str, Any]:
    """Get the status of a workflow instance."""
    async with DaprWorkflowClient() as client:
        state = await client.get_workflow_state(instance_id)
        return {
            "instance_id": instance_id,
            "status": state.runtime_status.name,
            "created_at": str(state.created_at),
            "last_updated": str(state.last_updated_at),
            "output": state.serialized_output
        }


async def terminate_workflow(instance_id: str) -> None:
    """Terminate a running workflow."""
    async with DaprWorkflowClient() as client:
        await client.terminate_workflow(instance_id)
        logger.info(f"Terminated workflow: {instance_id}")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting workflow runtime...")
    wf_runtime.start()

    try:
        # Keep the runtime running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down workflow runtime...")
        wf_runtime.shutdown()
