"""
{{SERVICE_NAME}} - DAPR-enabled FastAPI Microservice

A production-ready microservice template with DAPR integration.
"""
import json
import os
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dapr.clients import DaprClient
from dapr.ext.fastapi import DaprApp

# =============================================================================
# Configuration
# =============================================================================

SERVICE_NAME = "{{SERVICE_NAME}}"
DAPR_STORE_NAME = "statestore"
DAPR_PUBSUB_NAME = "pubsub"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


# =============================================================================
# Application Lifecycle
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown handlers."""
    logger.info(f"Starting {SERVICE_NAME}")
    # Startup logic here (e.g., initialize connections)
    yield
    # Shutdown logic here (e.g., close connections)
    logger.info(f"Shutting down {SERVICE_NAME}")


app = FastAPI(
    title=SERVICE_NAME,
    description="DAPR-enabled microservice",
    version="1.0.0",
    lifespan=lifespan
)
dapr_app = DaprApp(app)


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint for liveness probes."""
    return {"status": "healthy", "service": SERVICE_NAME}


@app.get("/ready", tags=["Health"])
async def ready():
    """Readiness check endpoint for readiness probes."""
    # Add checks for dependencies (database, external services, etc.)
    return {"status": "ready", "service": SERVICE_NAME}


# =============================================================================
# DAPR Helper Functions
# =============================================================================

async def save_state(key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
    """Save state to DAPR state store."""
    async with DaprClient() as client:
        metadata = {}
        if ttl_seconds:
            metadata["ttlInSeconds"] = str(ttl_seconds)

        await client.save_state(
            store_name=DAPR_STORE_NAME,
            key=key,
            value=json.dumps(value),
            state_metadata=metadata
        )
        logger.debug(f"State saved: {key}")


async def get_state(key: str) -> Optional[Any]:
    """Get state from DAPR state store."""
    async with DaprClient() as client:
        state = await client.get_state(
            store_name=DAPR_STORE_NAME,
            key=key
        )
        if state.data:
            return json.loads(state.data)
        return None


async def delete_state(key: str) -> None:
    """Delete state from DAPR state store."""
    async with DaprClient() as client:
        await client.delete_state(
            store_name=DAPR_STORE_NAME,
            key=key
        )
        logger.debug(f"State deleted: {key}")


async def publish_event(topic: str, data: Any, metadata: Optional[dict] = None) -> None:
    """Publish event to DAPR pub/sub."""
    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name=DAPR_PUBSUB_NAME,
            topic_name=topic,
            data=json.dumps(data),
            data_content_type="application/json",
            publish_metadata=metadata or {}
        )
        logger.info(f"Event published to {topic}")


async def invoke_service(
    app_id: str,
    method: str,
    data: Optional[Any] = None,
    http_verb: str = "POST"
) -> Optional[Any]:
    """Invoke another DAPR service."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id=app_id,
            method_name=method,
            data=json.dumps(data) if data else None,
            content_type="application/json",
            http_verb=http_verb
        )
        if response.data:
            return response.json()
        return None


async def get_secret(secret_name: str, store_name: str = "secretstore") -> Optional[str]:
    """Get secret from DAPR secret store."""
    async with DaprClient() as client:
        secret = await client.get_secret(
            store_name=store_name,
            key=secret_name
        )
        return secret.secret.get(secret_name)


# =============================================================================
# Models
# =============================================================================

class ItemCreate(BaseModel):
    """Model for creating a new item."""
    name: str
    description: Optional[str] = None
    data: dict = {}


class Item(ItemCreate):
    """Model for an item with ID."""
    id: str


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/items", response_model=Item, tags=["Items"])
async def create_item(item: ItemCreate):
    """Create a new item."""
    import uuid
    item_id = str(uuid.uuid4())

    item_data = Item(id=item_id, **item.model_dump())

    # Save to state store
    await save_state(f"item-{item_id}", item_data.model_dump())

    # Publish event
    await publish_event("items", {
        "action": "created",
        "item": item_data.model_dump()
    })

    logger.info(f"Created item: {item_id}")
    return item_data


@app.get("/items/{item_id}", response_model=Item, tags=["Items"])
async def get_item(item_id: str):
    """Get an item by ID."""
    item = await get_state(f"item-{item_id}")
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(**item)


@app.put("/items/{item_id}", response_model=Item, tags=["Items"])
async def update_item(item_id: str, item: ItemCreate):
    """Update an existing item."""
    existing = await get_state(f"item-{item_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")

    item_data = Item(id=item_id, **item.model_dump())
    await save_state(f"item-{item_id}", item_data.model_dump())

    await publish_event("items", {
        "action": "updated",
        "item": item_data.model_dump()
    })

    logger.info(f"Updated item: {item_id}")
    return item_data


@app.delete("/items/{item_id}", tags=["Items"])
async def delete_item(item_id: str):
    """Delete an item."""
    existing = await get_state(f"item-{item_id}")
    if not existing:
        raise HTTPException(status_code=404, detail="Item not found")

    await delete_state(f"item-{item_id}")

    await publish_event("items", {
        "action": "deleted",
        "item_id": item_id
    })

    logger.info(f"Deleted item: {item_id}")
    return {"status": "deleted", "id": item_id}


# =============================================================================
# Pub/Sub Subscriptions
# =============================================================================

@dapr_app.subscribe(pubsub=DAPR_PUBSUB_NAME, topic="items")
async def handle_item_event(event: dict):
    """Handle item events from pub/sub."""
    logger.info(f"Received item event: {event.get('action', 'unknown')}")

    # Process the event
    # Add your business logic here

    return {"status": "SUCCESS"}


# =============================================================================
# Input Bindings
# =============================================================================

@app.post("/bindings/scheduled-job")
async def handle_scheduled_job(request: Request):
    """Handle scheduled job trigger from cron binding."""
    body = await request.json()
    logger.info(f"Scheduled job triggered: {body}")

    # Add your scheduled job logic here

    return {"status": "processed"}


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
