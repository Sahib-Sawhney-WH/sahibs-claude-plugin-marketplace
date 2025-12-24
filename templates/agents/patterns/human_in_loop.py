"""
Human-in-the-Loop Pattern

Workflow that pauses for human approval or input at critical steps.
Uses Dapr Workflow external events for human interaction.

Example use cases:
- Content approval workflows
- Sensitive action confirmation
- Expert review gates
"""

from dapr_agents import AssistantAgent
from dapr.ext.workflow import (
    DaprWorkflowContext,
    WorkflowRuntime,
    workflow,
    activity,
)
from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import uuid
import os
import logging
from datetime import timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Human-in-the-Loop Pattern")


# =============================================================================
# Agents
# =============================================================================

draft_agent = AssistantAgent(
    name="drafter",
    role="Content Drafter",
    instructions="""Create professional draft content.
    Make it comprehensive but flag any areas needing human review.
    Be clear about what decisions need human input.""",
    model="gpt-4o"
)

revision_agent = AssistantAgent(
    name="reviser",
    role="Content Reviser",
    instructions="""Revise content based on human feedback.
    Incorporate all feedback points carefully.
    Maintain consistency with the original intent.""",
    model="gpt-4o"
)

finalize_agent = AssistantAgent(
    name="finalizer",
    role="Content Finalizer",
    instructions="""Finalize the approved content.
    Add any finishing touches for professional presentation.
    Ensure consistency and polish.""",
    model="gpt-4o"
)


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def create_draft(ctx, request: dict) -> dict:
    """Create initial draft."""
    task = request["task"]
    context = request.get("context", "")

    logger.info("Creating draft...")
    draft = await draft_agent.run(
        f"""Create a draft for:

Task: {task}
Context: {context}

Include:
1. Main content
2. Any areas requiring human decision
3. Alternative options if applicable"""
    )

    return {
        "draft": draft,
        "task": task,
        "status": "pending_review"
    }


@activity
async def apply_feedback(ctx, data: dict) -> dict:
    """Apply human feedback to draft."""
    draft = data["draft"]
    feedback = data["feedback"]
    action = data["action"]

    logger.info(f"Applying feedback (action: {action})...")

    if action == "approve":
        return {
            "content": draft,
            "status": "approved",
            "feedback_applied": False
        }

    elif action == "revise":
        revised = await revision_agent.run(
            f"""Revise this draft based on feedback.

Original Draft:
{draft}

Human Feedback:
{feedback}"""
        )
        return {
            "content": revised,
            "status": "revised",
            "feedback_applied": True
        }

    elif action == "reject":
        return {
            "content": None,
            "status": "rejected",
            "reason": feedback
        }

    else:
        raise ValueError(f"Unknown action: {action}")


@activity
async def finalize_content(ctx, content: str) -> str:
    """Finalize approved content."""
    logger.info("Finalizing content...")
    return await finalize_agent.run(
        f"Finalize this approved content for publication:\n\n{content}"
    )


# =============================================================================
# Human-in-the-Loop Workflow
# =============================================================================

@workflow
def human_approval_workflow(ctx: DaprWorkflowContext, request: dict):
    """
    Workflow with human approval gate.

    Flow:
    1. Create draft
    2. Wait for human review (external event)
    3. Apply feedback or approve
    4. Finalize if approved
    """
    task = request["task"]
    timeout_hours = request.get("timeout_hours", 24)

    # Step 1: Create draft
    draft_result = yield ctx.call_activity(create_draft, input=request)

    # Step 2: Wait for human review
    # This pauses the workflow until human provides input
    try:
        human_input = yield ctx.wait_for_external_event(
            "human_review",
            timeout=timedelta(hours=timeout_hours)
        )
    except TimeoutError:
        return {
            "status": "timeout",
            "message": f"No response received within {timeout_hours} hours",
            "draft": draft_result["draft"]
        }

    # Step 3: Apply feedback based on human action
    feedback_result = yield ctx.call_activity(
        apply_feedback,
        input={
            "draft": draft_result["draft"],
            "feedback": human_input.get("feedback", ""),
            "action": human_input.get("action", "approve")
        }
    )

    # If rejected, return early
    if feedback_result["status"] == "rejected":
        return {
            "status": "rejected",
            "reason": feedback_result.get("reason"),
            "original_draft": draft_result["draft"]
        }

    # If revised, might need another review round
    if feedback_result["status"] == "revised" and human_input.get("require_re_review"):
        try:
            second_review = yield ctx.wait_for_external_event(
                "human_review",
                timeout=timedelta(hours=timeout_hours)
            )

            if second_review.get("action") != "approve":
                return {
                    "status": "rejected_on_revision",
                    "content": feedback_result["content"]
                }
        except TimeoutError:
            return {
                "status": "timeout_on_revision",
                "content": feedback_result["content"]
            }

    # Step 4: Finalize
    final_content = yield ctx.call_activity(
        finalize_content,
        input=feedback_result["content"]
    )

    return {
        "status": "completed",
        "task": task,
        "final_content": final_content,
        "was_revised": feedback_result["feedback_applied"]
    }


@workflow
def multi_approval_workflow(ctx: DaprWorkflowContext, request: dict):
    """
    Workflow requiring multiple approvals.
    """
    task = request["task"]
    approvers = request.get("approvers", ["manager", "legal", "compliance"])
    timeout_hours = request.get("timeout_hours", 48)

    # Create draft
    draft_result = yield ctx.call_activity(create_draft, input=request)
    content = draft_result["draft"]

    approvals = {}

    # Get approval from each required approver
    for approver in approvers:
        try:
            approval = yield ctx.wait_for_external_event(
                f"approval_{approver}",
                timeout=timedelta(hours=timeout_hours)
            )

            approvals[approver] = {
                "approved": approval.get("approved", False),
                "comments": approval.get("comments", "")
            }

            if not approval.get("approved"):
                return {
                    "status": "rejected",
                    "rejected_by": approver,
                    "reason": approval.get("comments"),
                    "approvals_received": approvals
                }

        except TimeoutError:
            return {
                "status": "timeout",
                "waiting_on": approver,
                "approvals_received": approvals
            }

    # All approved - finalize
    final_content = yield ctx.call_activity(finalize_content, input=content)

    return {
        "status": "completed",
        "final_content": final_content,
        "approvals": approvals
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(human_approval_workflow)
workflow_runtime.register_workflow(multi_approval_workflow)
workflow_runtime.register_activity(create_draft)
workflow_runtime.register_activity(apply_feedback)
workflow_runtime.register_activity(finalize_content)


# =============================================================================
# API Models
# =============================================================================

class ApprovalRequest(BaseModel):
    task: str
    context: str = ""
    timeout_hours: int = Field(default=24, ge=1, le=168)


class HumanReview(BaseModel):
    action: str = Field(..., description="approve, revise, or reject")
    feedback: str = ""
    require_re_review: bool = False


class ApproverReview(BaseModel):
    approved: bool
    comments: str = ""


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/approval")
async def start_approval(request: ApprovalRequest):
    """Start a human approval workflow."""
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="human_approval_workflow",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {
        "instance_id": instance_id,
        "status": "pending_review",
        "message": f"Workflow started. Submit review at /approval/{instance_id}/review"
    }


@app.post("/approval/{instance_id}/review")
async def submit_review(instance_id: str, review: HumanReview):
    """Submit human review for a pending workflow."""
    async with DaprClient() as client:
        await client.raise_workflow_event(
            workflow_component="dapr",
            instance_id=instance_id,
            event_name="human_review",
            event_data=review.model_dump()
        )

    return {
        "instance_id": instance_id,
        "review_submitted": True,
        "action": review.action
    }


@app.get("/approval/{instance_id}")
async def get_approval_status(instance_id: str):
    """Get workflow status."""
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
