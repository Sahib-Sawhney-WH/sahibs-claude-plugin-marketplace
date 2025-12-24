"""
Evaluator-Optimizer Pattern

Iterative improvement loop where one agent generates and another evaluates.
Continues until quality threshold is met or max iterations reached.

Example use cases:
- Content refinement and polishing
- Code review and improvement
- Answer verification and enhancement
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
from pydantic import BaseModel, Field
import uvicorn
import uuid
import os
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Evaluator-Optimizer Pattern")


# =============================================================================
# Generator and Evaluator Agents
# =============================================================================

generator_agent = AssistantAgent(
    name="generator",
    role="Content Generator",
    instructions="""You are a content generator.
    Create high-quality content based on the given task.
    If feedback is provided, incorporate it to improve your output.
    Be creative and thorough.""",
    model="gpt-4o",
    temperature=0.8
)

evaluator_agent = AssistantAgent(
    name="evaluator",
    role="Quality Evaluator",
    instructions="""You are a quality evaluator.
    Evaluate the given content on these criteria:
    - Accuracy: Is the information correct?
    - Completeness: Does it cover all aspects?
    - Clarity: Is it easy to understand?
    - Relevance: Does it address the task?

    Provide your response in this exact format:
    SCORE: [0.0-1.0]
    FEEDBACK: [Specific improvements needed]

    Be constructive but honest. Score 0.9+ only for excellent work.""",
    model="gpt-4o",
    temperature=0.2
)

optimizer_agent = AssistantAgent(
    name="optimizer",
    role="Content Optimizer",
    instructions="""You are a content optimizer.
    Take the original content and feedback, and produce an improved version.
    Address each point in the feedback specifically.
    Maintain the good aspects while fixing issues.""",
    model="gpt-4o",
    temperature=0.6
)


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def generate_content(ctx, task: str) -> str:
    """Generate initial content."""
    logger.info("Generating initial content...")
    return await generator_agent.run(
        f"Create content for this task:\n\n{task}"
    )


@activity
async def evaluate_content(ctx, data: dict) -> dict:
    """Evaluate content quality."""
    task = data["task"]
    content = data["content"]

    logger.info("Evaluating content...")
    evaluation = await evaluator_agent.run(
        f"""Evaluate this content for the task.

Task: {task}

Content:
{content}"""
    )

    # Parse score and feedback
    score = 0.5  # default
    feedback = evaluation

    # Try to extract score
    score_match = re.search(r'SCORE:\s*([\d.]+)', evaluation)
    if score_match:
        try:
            score = float(score_match.group(1))
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except ValueError:
            pass

    # Try to extract feedback
    feedback_match = re.search(r'FEEDBACK:\s*(.+)', evaluation, re.DOTALL)
    if feedback_match:
        feedback = feedback_match.group(1).strip()

    return {
        "score": score,
        "feedback": feedback,
        "raw_evaluation": evaluation
    }


@activity
async def optimize_content(ctx, data: dict) -> str:
    """Optimize content based on feedback."""
    content = data["content"]
    feedback = data["feedback"]

    logger.info("Optimizing content...")
    return await optimizer_agent.run(
        f"""Improve this content based on the feedback.

Original Content:
{content}

Feedback:
{feedback}

Produce an improved version that addresses all feedback points."""
    )


# =============================================================================
# Evaluator-Optimizer Workflow
# =============================================================================

@workflow
def eval_optimize_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Iterative evaluation and optimization loop.

    Args:
        data: Contains 'task', 'max_iterations', 'quality_threshold'
    """
    task = data["task"]
    max_iterations = data.get("max_iterations", 5)
    quality_threshold = data.get("quality_threshold", 0.85)

    # Generate initial content
    content = yield ctx.call_activity(generate_content, input=task)

    iterations = []
    final_score = 0.0

    for i in range(max_iterations):
        logger.info(f"Iteration {i + 1}/{max_iterations}")

        # Evaluate current content
        evaluation = yield ctx.call_activity(
            evaluate_content,
            input={"task": task, "content": content}
        )

        final_score = evaluation["score"]
        iterations.append({
            "iteration": i + 1,
            "score": final_score,
            "feedback": evaluation["feedback"]
        })

        # Check if quality threshold met
        if final_score >= quality_threshold:
            logger.info(f"Quality threshold met at iteration {i + 1}")
            break

        # Optimize if not at last iteration
        if i < max_iterations - 1:
            content = yield ctx.call_activity(
                optimize_content,
                input={
                    "content": content,
                    "feedback": evaluation["feedback"]
                }
            )

    return {
        "task": task,
        "final_content": content,
        "final_score": final_score,
        "iterations": iterations,
        "total_iterations": len(iterations),
        "threshold_met": final_score >= quality_threshold
    }


@workflow
def self_critique_workflow(ctx: DaprWorkflowContext, data: dict):
    """
    Self-critique pattern: Same agent generates and critiques.
    """
    task = data["task"]
    critique_rounds = data.get("rounds", 3)

    # Initial generation
    content = yield ctx.call_activity(generate_content, input=task)

    critique_agent = AssistantAgent(
        name="self-critic",
        role="Self-Critic",
        instructions="""Critically review your own work.
        Identify weaknesses and suggest specific improvements.
        Be harsh but constructive.""",
        model="gpt-4o"
    )

    for i in range(critique_rounds):
        # Self-critique
        critique = await critique_agent.run(
            f"Critique this content and suggest improvements:\n\n{content}"
        )

        # Self-improve
        content = await generator_agent.run(
            f"""Improve this content based on the critique.

Content:
{content}

Critique:
{critique}"""
        )

    return {
        "task": task,
        "final_content": content,
        "rounds": critique_rounds
    }


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(eval_optimize_workflow)
workflow_runtime.register_workflow(self_critique_workflow)
workflow_runtime.register_activity(generate_content)
workflow_runtime.register_activity(evaluate_content)
workflow_runtime.register_activity(optimize_content)


# =============================================================================
# API
# =============================================================================

class OptimizeRequest(BaseModel):
    task: str
    max_iterations: int = Field(default=5, ge=1, le=10)
    quality_threshold: float = Field(default=0.85, ge=0.5, le=1.0)


@app.on_event("startup")
async def startup():
    await workflow_runtime.start()


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.post("/optimize")
async def start_optimization(request: OptimizeRequest):
    instance_id = str(uuid.uuid4())

    async with DaprClient() as client:
        await client.start_workflow(
            workflow_component="dapr",
            workflow_name="eval_optimize_workflow",
            input=request.model_dump(),
            instance_id=instance_id
        )

    return {
        "instance_id": instance_id,
        "max_iterations": request.max_iterations,
        "quality_threshold": request.quality_threshold,
        "status": "started"
    }


@app.get("/optimize/{instance_id}")
async def get_optimization_status(instance_id: str):
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
