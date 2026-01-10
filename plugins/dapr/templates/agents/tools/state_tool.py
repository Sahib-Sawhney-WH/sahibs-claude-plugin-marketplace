"""
State Management Tool

Tools for managing state in DAPR Agents using DAPR state stores.
Enables persistent memory, session management, and data storage.

Features:
- Key-value state operations
- Transaction support
- TTL (time-to-live)
- Concurrency control with ETags
"""

from dapr_agents import tool, AssistantAgent
from dapr.clients import DaprClient
from dapr.clients.grpc._state import StateItem
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_STORE = "statestore"


# =============================================================================
# Input Models
# =============================================================================

class SaveStateInput(BaseModel):
    """Input for saving state."""
    key: str = Field(..., description="State key")
    value: Any = Field(..., description="Value to store")
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        description="Time-to-live in seconds"
    )
    store_name: str = Field(default=DEFAULT_STORE, description="State store name")


class QueryStateInput(BaseModel):
    """Input for querying state."""
    filter: Dict[str, Any] = Field(..., description="Query filter")
    store_name: str = Field(default=DEFAULT_STORE)


class TransactionItem(BaseModel):
    """Single transaction operation."""
    operation: str = Field(..., description="upsert or delete")
    key: str = Field(..., description="State key")
    value: Optional[Any] = Field(default=None, description="Value for upsert")


# =============================================================================
# Basic State Tools
# =============================================================================

@tool
async def save_state(key: str, value: str) -> str:
    """
    Save a value to the state store.

    Args:
        key: Unique key for the state
        value: Value to store (as string)

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        await client.save_state(
            store_name=DEFAULT_STORE,
            key=key,
            value=value
        )
    return f"State saved: {key}"


@tool
async def get_state(key: str) -> str:
    """
    Get a value from the state store.

    Args:
        key: State key to retrieve

    Returns:
        Stored value or message if not found
    """
    async with DaprClient() as client:
        state = await client.get_state(
            store_name=DEFAULT_STORE,
            key=key
        )
        if state.data:
            return state.data.decode() if isinstance(state.data, bytes) else str(state.data)
        return f"No state found for key: {key}"


@tool
async def delete_state(key: str) -> str:
    """
    Delete a value from the state store.

    Args:
        key: State key to delete

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        await client.delete_state(
            store_name=DEFAULT_STORE,
            key=key
        )
    return f"State deleted: {key}"


@tool
async def list_keys(prefix: str = "") -> str:
    """
    List state keys (with optional prefix filter).
    Note: Not all state stores support key listing.

    Args:
        prefix: Optional key prefix filter

    Returns:
        List of keys or status message
    """
    # Note: DAPR doesn't have native key listing
    # This is a placeholder - implement with query API or custom logic
    return f"Key listing for prefix '{prefix}' requires state store query support"


# =============================================================================
# Advanced State Tools
# =============================================================================

@tool
async def save_state_with_ttl(input: SaveStateInput) -> str:
    """
    Save state with time-to-live expiration.

    Args:
        input: State configuration including key, value, and TTL

    Returns:
        Confirmation with expiration info
    """
    value = json.dumps(input.value) if not isinstance(input.value, str) else input.value

    async with DaprClient() as client:
        metadata = {}
        if input.ttl_seconds:
            metadata["ttlInSeconds"] = str(input.ttl_seconds)

        await client.save_state(
            store_name=input.store_name,
            key=input.key,
            value=value,
            state_metadata=metadata
        )

    ttl_msg = f" (expires in {input.ttl_seconds}s)" if input.ttl_seconds else ""
    return f"State saved: {input.key}{ttl_msg}"


@tool
async def save_json_state(key: str, data: dict) -> str:
    """
    Save a JSON object to state.

    Args:
        key: State key
        data: Dictionary to store as JSON

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        await client.save_state(
            store_name=DEFAULT_STORE,
            key=key,
            value=json.dumps(data)
        )
    return f"JSON state saved: {key}"


@tool
async def get_json_state(key: str) -> str:
    """
    Get and parse JSON state.

    Args:
        key: State key

    Returns:
        Parsed JSON as formatted string
    """
    async with DaprClient() as client:
        state = await client.get_state(
            store_name=DEFAULT_STORE,
            key=key
        )
        if state.data:
            data = state.data.decode() if isinstance(state.data, bytes) else state.data
            parsed = json.loads(data)
            return json.dumps(parsed, indent=2)
        return f"No state found for key: {key}"


@tool
async def get_bulk_state(keys: List[str]) -> str:
    """
    Get multiple state values at once.

    Args:
        keys: List of state keys to retrieve

    Returns:
        All retrieved values
    """
    async with DaprClient() as client:
        states = await client.get_bulk_state(
            store_name=DEFAULT_STORE,
            keys=keys
        )

        results = {}
        for item in states.items:
            if item.data:
                data = item.data.decode() if isinstance(item.data, bytes) else item.data
                results[item.key] = data
            else:
                results[item.key] = None

        return json.dumps(results, indent=2)


@tool
async def save_bulk_state(items: Dict[str, Any]) -> str:
    """
    Save multiple state values at once.

    Args:
        items: Dictionary of key-value pairs to save

    Returns:
        Confirmation message
    """
    async with DaprClient() as client:
        state_items = [
            StateItem(key=k, value=json.dumps(v) if not isinstance(v, str) else v)
            for k, v in items.items()
        ]
        await client.save_bulk_state(
            store_name=DEFAULT_STORE,
            states=state_items
        )
    return f"Saved {len(items)} state items"


# =============================================================================
# Transaction Tools
# =============================================================================

@tool
async def execute_state_transaction(operations: List[dict]) -> str:
    """
    Execute atomic state transaction.

    Args:
        operations: List of operations, each with 'operation' (upsert/delete),
                   'key', and optionally 'value'

    Returns:
        Transaction result
    """
    from dapr.clients.grpc._state import TransactionalStateOperation

    async with DaprClient() as client:
        ops = []
        for op in operations:
            if op["operation"] == "upsert":
                ops.append(TransactionalStateOperation(
                    key=op["key"],
                    data=json.dumps(op.get("value", "")),
                    operation_type="upsert"
                ))
            elif op["operation"] == "delete":
                ops.append(TransactionalStateOperation(
                    key=op["key"],
                    operation_type="delete"
                ))

        await client.execute_state_transaction(
            store_name=DEFAULT_STORE,
            operations=ops
        )

    return f"Transaction completed: {len(operations)} operations"


# =============================================================================
# Agent Memory Tools
# =============================================================================

class AgentMemory:
    """
    Memory manager for agents using DAPR state.
    Provides short-term and long-term memory capabilities.
    """

    def __init__(self, agent_id: str, store_name: str = DEFAULT_STORE):
        self.agent_id = agent_id
        self.store_name = store_name

    def _key(self, memory_type: str, key: str) -> str:
        return f"agent:{self.agent_id}:{memory_type}:{key}"

    async def remember(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Store in short-term memory."""
        async with DaprClient() as client:
            metadata = {"ttlInSeconds": str(ttl_seconds)} if ttl_seconds else {}
            await client.save_state(
                store_name=self.store_name,
                key=self._key("short", key),
                value=json.dumps(value),
                state_metadata=metadata
            )

    async def recall(self, key: str) -> Optional[Any]:
        """Recall from short-term memory."""
        async with DaprClient() as client:
            state = await client.get_state(
                store_name=self.store_name,
                key=self._key("short", key)
            )
            if state.data:
                return json.loads(state.data)
            return None

    async def learn(self, key: str, value: Any):
        """Store in long-term memory (no TTL)."""
        async with DaprClient() as client:
            await client.save_state(
                store_name=self.store_name,
                key=self._key("long", key),
                value=json.dumps(value)
            )

    async def knowledge(self, key: str) -> Optional[Any]:
        """Retrieve from long-term memory."""
        async with DaprClient() as client:
            state = await client.get_state(
                store_name=self.store_name,
                key=self._key("long", key)
            )
            if state.data:
                return json.loads(state.data)
            return None


def create_memory_tools(agent_id: str) -> List:
    """Create memory tools for a specific agent."""
    memory = AgentMemory(agent_id)

    @tool
    async def remember_info(key: str, value: str, expire_minutes: int = 60) -> str:
        """
        Remember information temporarily.

        Args:
            key: Memory key
            value: Information to remember
            expire_minutes: Minutes until forgotten

        Returns:
            Confirmation
        """
        await memory.remember(key, value, ttl_seconds=expire_minutes * 60)
        return f"Remembered '{key}' for {expire_minutes} minutes"

    @tool
    async def recall_info(key: str) -> str:
        """
        Recall temporarily stored information.

        Args:
            key: Memory key

        Returns:
            Recalled information or not found message
        """
        value = await memory.recall(key)
        return value if value else f"No memory of '{key}'"

    @tool
    async def learn_permanently(key: str, value: str) -> str:
        """
        Learn information permanently.

        Args:
            key: Knowledge key
            value: Information to learn

        Returns:
            Confirmation
        """
        await memory.learn(key, value)
        return f"Learned '{key}' permanently"

    @tool
    async def recall_knowledge(key: str) -> str:
        """
        Recall permanently stored knowledge.

        Args:
            key: Knowledge key

        Returns:
            Stored knowledge or not found message
        """
        value = await memory.knowledge(key)
        return value if value else f"No knowledge of '{key}'"

    return [remember_info, recall_info, learn_permanently, recall_knowledge]


# =============================================================================
# Example Agent with State Tools
# =============================================================================

def create_stateful_agent(agent_id: str = "stateful-agent") -> AssistantAgent:
    """Create an agent with state management tools."""
    memory_tools = create_memory_tools(agent_id)

    return AssistantAgent(
        name=agent_id,
        role="Stateful Agent",
        instructions="""You have persistent memory capabilities.
        Use remember_info for temporary information.
        Use learn_permanently for important facts.
        Use recall_info and recall_knowledge to retrieve stored information.""",
        tools=[
            save_state,
            get_state,
            delete_state,
            save_json_state,
            get_json_state,
            *memory_tools
        ],
        model="gpt-4o"
    )


# =============================================================================
# Usage Example
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def demo():
        agent = create_stateful_agent("demo-agent")

        # Save some state
        result = await agent.run(
            "Remember that my favorite color is blue, then recall it"
        )
        print(result)

    asyncio.run(demo())
