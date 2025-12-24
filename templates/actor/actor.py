"""
{{ACTOR_NAME}} - DAPR Virtual Actor

A virtual actor template with state management, timers, and reminders.
"""
import os
import logging
from abc import abstractmethod
from typing import Any, Dict, Optional
from datetime import timedelta

from dapr.actor import Actor, ActorInterface, Remindable, actormethod
from dapr.actor.runtime.config import ActorRuntimeConfig, ActorTypeConfig
from fastapi import FastAPI
from dapr.ext.fastapi import DaprActor

# =============================================================================
# Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("{{ACTOR_NAME}}")


# =============================================================================
# Actor Interface
# =============================================================================

class {{ACTOR_NAME}}Interface(ActorInterface):
    """Interface defining the actor's public methods."""

    @abstractmethod
    async def get_state(self) -> Dict[str, Any]:
        """Get the current state of the actor."""
        ...

    @abstractmethod
    async def set_state(self, data: Dict[str, Any]) -> None:
        """Set the state of the actor."""
        ...

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return result."""
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset the actor state."""
        ...

    @abstractmethod
    async def schedule_reminder(
        self,
        reminder_name: str,
        due_time: timedelta,
        period: Optional[timedelta] = None,
        data: Optional[bytes] = None
    ) -> None:
        """Schedule a reminder for the actor."""
        ...

    @abstractmethod
    async def start_timer(
        self,
        timer_name: str,
        callback_name: str,
        due_time: timedelta,
        period: timedelta,
        data: Optional[bytes] = None
    ) -> None:
        """Start a timer for the actor."""
        ...


# =============================================================================
# Actor Implementation
# =============================================================================

class {{ACTOR_NAME}}(Actor, {{ACTOR_NAME}}Interface, Remindable):
    """
    {{ACTOR_NAME}} virtual actor implementation.

    This actor maintains state, handles timers and reminders,
    and processes requests with automatic concurrency control.
    """

    STATE_KEY = "actor_state"

    def __init__(self, ctx, actor_id):
        """Initialize the actor."""
        super().__init__(ctx, actor_id)
        self._state: Dict[str, Any] = {}

    async def _on_activate(self) -> None:
        """Called when actor is activated (first call or after idle)."""
        logger.info(f"Actor {self.id} activating...")

        # Load persisted state if exists
        has_state, state = await self._state_manager.try_get_state(self.STATE_KEY)
        if has_state:
            self._state = state
            logger.info(f"Actor {self.id} loaded state: {state}")
        else:
            self._state = {"created": True, "data": {}}
            logger.info(f"Actor {self.id} initialized with empty state")

    async def _on_deactivate(self) -> None:
        """Called when actor is deactivated (idle timeout)."""
        logger.info(f"Actor {self.id} deactivating...")
        # State is automatically persisted, but you can do cleanup here

    # =========================================================================
    # State Management
    # =========================================================================

    @actormethod(name="GetState")
    async def get_state(self) -> Dict[str, Any]:
        """Get the current state of the actor."""
        return self._state

    @actormethod(name="SetState")
    async def set_state(self, data: Dict[str, Any]) -> None:
        """Set the state of the actor and persist it."""
        self._state = data
        await self._state_manager.set_state(self.STATE_KEY, self._state)
        await self._state_manager.save_state()
        logger.info(f"Actor {self.id} state updated")

    @actormethod(name="Reset")
    async def reset(self) -> None:
        """Reset the actor state to initial values."""
        self._state = {"created": True, "data": {}, "reset_count": self._state.get("reset_count", 0) + 1}
        await self._state_manager.set_state(self.STATE_KEY, self._state)
        await self._state_manager.save_state()
        logger.info(f"Actor {self.id} state reset")

    # =========================================================================
    # Business Logic
    # =========================================================================

    @actormethod(name="Process")
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input data and update state.

        This is where you implement your actor's main business logic.
        All calls to this method are serialized per actor instance.
        """
        logger.info(f"Actor {self.id} processing: {input_data}")

        # Update state with processed data
        self._state["last_processed"] = input_data
        self._state["process_count"] = self._state.get("process_count", 0) + 1

        # Persist state
        await self._state_manager.set_state(self.STATE_KEY, self._state)
        await self._state_manager.save_state()

        # Return result
        result = {
            "success": True,
            "actor_id": str(self.id),
            "processed": input_data,
            "total_processed": self._state["process_count"]
        }

        logger.info(f"Actor {self.id} processed successfully")
        return result

    # =========================================================================
    # Timers and Reminders
    # =========================================================================

    @actormethod(name="ScheduleReminder")
    async def schedule_reminder(
        self,
        reminder_name: str,
        due_time: timedelta,
        period: Optional[timedelta] = None,
        data: Optional[bytes] = None
    ) -> None:
        """
        Schedule a reminder that persists across actor deactivations.

        Reminders are durable - they survive actor deactivation and node failures.
        """
        await self.register_reminder(
            reminder_name=reminder_name,
            due_time=due_time,
            period=period or timedelta(seconds=0),
            state=data or b""
        )
        logger.info(f"Actor {self.id} scheduled reminder: {reminder_name}")

    async def receive_reminder(
        self,
        name: str,
        state: bytes,
        due_time: timedelta,
        period: timedelta
    ) -> None:
        """
        Handle reminder callbacks.

        This is called when a reminder fires. Implement your reminder logic here.
        """
        logger.info(f"Actor {self.id} received reminder: {name}")

        # Update state to track reminder execution
        self._state["last_reminder"] = name
        self._state["reminder_count"] = self._state.get("reminder_count", 0) + 1

        await self._state_manager.set_state(self.STATE_KEY, self._state)
        await self._state_manager.save_state()

        # Add your reminder handling logic here

    @actormethod(name="StartTimer")
    async def start_timer(
        self,
        timer_name: str,
        callback_name: str,
        due_time: timedelta,
        period: timedelta,
        data: Optional[bytes] = None
    ) -> None:
        """
        Start a timer for periodic execution.

        Timers are NOT durable - they are lost when actor deactivates.
        Use reminders for durable scheduled operations.
        """
        await self.register_timer(
            timer_name=timer_name,
            callback=callback_name,
            due_time=due_time,
            period=period,
            state=data or b""
        )
        logger.info(f"Actor {self.id} started timer: {timer_name}")

    async def timer_callback(self, state: bytes) -> None:
        """Handle timer callbacks. Override for custom timer behavior."""
        logger.info(f"Actor {self.id} timer fired")
        # Add your timer handling logic here


# =============================================================================
# Actor Runtime Configuration
# =============================================================================

# Configure actor runtime
actor_config = ActorRuntimeConfig()
actor_config.update_actor_type_configs([
    ActorTypeConfig(
        actor_type="{{ACTOR_NAME}}",
        actor_idle_timeout=timedelta(hours=1),
        actor_scan_interval=timedelta(seconds=30),
        drain_ongoing_call_timeout=timedelta(minutes=1),
        drain_rebalanced_actors=True,
        reentrancy_config=None  # Set to enable reentrancy if needed
    )
])


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="{{ACTOR_NAME}} Service")
dapr_actor = DaprActor(app)


@app.on_event("startup")
async def startup():
    """Register actors on startup."""
    await dapr_actor.register_actor({{ACTOR_NAME}})
    logger.info("Actor registered: {{ACTOR_NAME}}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "actor": "{{ACTOR_NAME}}"}


@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    return {"status": "ready", "actor": "{{ACTOR_NAME}}"}


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
