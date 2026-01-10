"""
DAPR Jobs Client Template
Building Block: Jobs (Scheduler)

Features:
- Schedule one-time jobs
- Schedule recurring jobs (cron, intervals)
- Get/delete scheduled jobs
- Handle job callbacks
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from dapr.clients import DaprClient
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Client for DAPR Jobs building block.

    Schedule and manage jobs for future execution.
    """

    def __init__(self, app_id: Optional[str] = None):
        """
        Initialize job scheduler.

        Args:
            app_id: Application ID (used for job callbacks)
        """
        self.app_id = app_id

    async def schedule_once(
        self,
        name: str,
        data: Any,
        due_time: str,
        ttl: Optional[str] = None
    ) -> bool:
        """
        Schedule a one-time job.

        Args:
            name: Job name (unique identifier)
            data: Job payload (will be passed to callback)
            due_time: When to execute (ISO 8601 or duration like "5m", "1h")
            ttl: Job expiry time (e.g., "24h")

        Returns:
            True if scheduled successfully

        Example:
            await scheduler.schedule_once(
                name="send-email-123",
                data={"to": "user@example.com", "subject": "Hello"},
                due_time="2024-12-25T09:00:00Z"
            )
        """
        async with DaprClient() as client:
            # Serialize data to JSON
            payload = json.dumps(data).encode("utf-8") if data else None

            await client.start_job(
                job_name=name,
                data=payload,
                due_time=due_time,
                ttl=ttl
            )

            logger.info(f"Scheduled one-time job: {name} at {due_time}")
            return True

    async def schedule_recurring(
        self,
        name: str,
        data: Any,
        schedule: str,
        due_time: Optional[str] = None,
        repeats: Optional[int] = None,
        ttl: Optional[str] = None
    ) -> bool:
        """
        Schedule a recurring job.

        Args:
            name: Job name (unique identifier)
            data: Job payload
            schedule: Cron expression or interval (@every 5m, @hourly, @daily)
            due_time: When to start (optional, defaults to now)
            repeats: Number of times to repeat (optional, None = infinite)
            ttl: Job expiry time

        Returns:
            True if scheduled successfully

        Schedule formats:
            - "@every 15m" - Every 15 minutes
            - "@every 1h" - Every hour
            - "@hourly" - Once an hour
            - "@daily" - Once a day at midnight
            - "@weekly" - Once a week
            - "0 30 * * * *" - Cron: At minute 30 of every hour
            - "0 0 9 * * MON-FRI" - Cron: 9 AM on weekdays

        Example:
            await scheduler.schedule_recurring(
                name="cleanup-job",
                data={"action": "cleanup_temp_files"},
                schedule="@daily",
                repeats=30  # Run for 30 days
            )
        """
        async with DaprClient() as client:
            payload = json.dumps(data).encode("utf-8") if data else None

            await client.start_job(
                job_name=name,
                data=payload,
                schedule=schedule,
                due_time=due_time,
                repeats=repeats,
                ttl=ttl
            )

            logger.info(f"Scheduled recurring job: {name} ({schedule})")
            return True

    async def get(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get job details.

        Args:
            name: Job name

        Returns:
            Job details or None if not found
        """
        async with DaprClient() as client:
            job = await client.get_job(job_name=name)

            if job:
                return {
                    "name": job.job_name,
                    "schedule": job.schedule,
                    "due_time": job.due_time,
                    "repeats": job.repeats,
                    "ttl": job.ttl,
                    "data": json.loads(job.data.decode()) if job.data else None
                }
            return None

    async def delete(self, name: str) -> bool:
        """
        Delete a scheduled job.

        Args:
            name: Job name

        Returns:
            True if deleted successfully
        """
        async with DaprClient() as client:
            await client.delete_job(job_name=name)
            logger.info(f"Deleted job: {name}")
            return True

    async def schedule_delayed(
        self,
        name: str,
        data: Any,
        delay: timedelta
    ) -> bool:
        """
        Schedule a job to run after a delay.

        Args:
            name: Job name
            data: Job payload
            delay: Time to wait before execution

        Example:
            await scheduler.schedule_delayed(
                name="retry-payment",
                data={"order_id": "123"},
                delay=timedelta(minutes=5)
            )
        """
        # Convert timedelta to duration string
        total_seconds = int(delay.total_seconds())
        if total_seconds >= 3600:
            due_time = f"{total_seconds // 3600}h{(total_seconds % 3600) // 60}m"
        elif total_seconds >= 60:
            due_time = f"{total_seconds // 60}m"
        else:
            due_time = f"{total_seconds}s"

        return await self.schedule_once(name, data, due_time)


# =============================================================================
# FastAPI Integration with Job Handler
# =============================================================================

app = FastAPI(title="Job Scheduler Service")
scheduler = JobScheduler()

# Job handlers registry
_job_handlers: Dict[str, Callable] = {}


def job_handler(job_type: str):
    """Decorator to register a job handler."""
    def decorator(func: Callable):
        _job_handlers[job_type] = func
        return func
    return decorator


@app.post("/job/{job_name}")
async def handle_job_callback(job_name: str, request: Request):
    """
    DAPR job callback endpoint.

    When a scheduled job triggers, DAPR calls this endpoint.
    """
    try:
        body = await request.body()
        data = json.loads(body) if body else {}

        logger.info(f"Job triggered: {job_name}")
        logger.debug(f"Job data: {data}")

        # Route to appropriate handler based on job type
        job_type = data.get("type", "default")
        handler = _job_handlers.get(job_type)

        if handler:
            result = await handler(job_name, data)
            return {"status": "success", "result": result}
        else:
            logger.warning(f"No handler for job type: {job_type}")
            return {"status": "no_handler", "job_type": job_type}

    except Exception as e:
        logger.error(f"Job execution failed: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# Example Job Handlers
# =============================================================================

@job_handler("send_email")
async def handle_send_email(job_name: str, data: dict):
    """Handle email sending job."""
    to = data.get("to")
    subject = data.get("subject")
    logger.info(f"Sending email to {to}: {subject}")
    # Implement actual email sending here
    return {"sent": True}


@job_handler("cleanup")
async def handle_cleanup(job_name: str, data: dict):
    """Handle cleanup job."""
    target = data.get("target", "temp_files")
    logger.info(f"Running cleanup: {target}")
    # Implement cleanup logic here
    return {"cleaned": True}


@job_handler("process_batch")
async def handle_batch_processing(job_name: str, data: dict):
    """Handle batch processing job."""
    batch_id = data.get("batch_id")
    logger.info(f"Processing batch: {batch_id}")
    # Implement batch processing here
    return {"processed": True, "batch_id": batch_id}


# =============================================================================
# API Endpoints for Scheduling
# =============================================================================

from pydantic import BaseModel
from typing import Optional


class ScheduleJobRequest(BaseModel):
    name: str
    data: dict
    schedule: Optional[str] = None
    due_time: Optional[str] = None
    repeats: Optional[int] = None


@app.post("/schedule")
async def schedule_job(request: ScheduleJobRequest):
    """Schedule a new job."""
    if request.schedule:
        await scheduler.schedule_recurring(
            name=request.name,
            data=request.data,
            schedule=request.schedule,
            due_time=request.due_time,
            repeats=request.repeats
        )
    elif request.due_time:
        await scheduler.schedule_once(
            name=request.name,
            data=request.data,
            due_time=request.due_time
        )
    else:
        return {"error": "Either schedule or due_time required"}

    return {"status": "scheduled", "job_name": request.name}


@app.get("/jobs/{job_name}")
async def get_job(job_name: str):
    """Get job details."""
    job = await scheduler.get(job_name)
    if job:
        return job
    return {"error": "Job not found"}


@app.delete("/jobs/{job_name}")
async def delete_job(job_name: str):
    """Delete a scheduled job."""
    await scheduler.delete(job_name)
    return {"status": "deleted", "job_name": job_name}


# =============================================================================
# CLI Usage Example
# =============================================================================

if __name__ == "__main__":
    async def main():
        sched = JobScheduler()

        # Schedule a one-time job
        await sched.schedule_once(
            name="welcome-email-123",
            data={"type": "send_email", "to": "user@example.com", "subject": "Welcome!"},
            due_time="5m"  # 5 minutes from now
        )

        # Schedule a recurring job
        await sched.schedule_recurring(
            name="daily-cleanup",
            data={"type": "cleanup", "target": "temp_files"},
            schedule="@daily",
            repeats=30  # Run for 30 days
        )

        # Schedule with cron expression
        await sched.schedule_recurring(
            name="weekday-report",
            data={"type": "process_batch", "batch_id": "reports"},
            schedule="0 0 9 * * MON-FRI"  # 9 AM on weekdays
        )

        # Get job details
        job = await sched.get("daily-cleanup")
        print(f"Job details: {job}")

        print("Jobs scheduled successfully!")

    asyncio.run(main())
