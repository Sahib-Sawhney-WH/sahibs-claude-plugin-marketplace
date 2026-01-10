"""Inventory Service - Actor-based stock management with DAPR."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dapr.clients import DaprClient
from dapr.actor import Actor, ActorInterface, ActorProxy, actormethod
from dapr.actor.runtime.config import ActorRuntimeConfig
from dapr.actor.runtime.runtime import ActorRuntime
from dapr.ext.fastapi import DaprActor
from opentelemetry import trace
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="Inventory Service")
actor_runtime = DaprActor(app)


# =============================================================================
# Models
# =============================================================================

class ReserveRequest(BaseModel):
    quantity: int
    order_id: str


class ReleaseRequest(BaseModel):
    reservation_id: str


class ProductStock(BaseModel):
    product_id: str
    available: int
    reserved: int
    reservations: dict[str, dict]  # reservation_id -> {order_id, quantity}


# =============================================================================
# Inventory Actor Interface
# =============================================================================

class InventoryActorInterface(ActorInterface):
    @actormethod(name="GetStock")
    async def get_stock(self) -> dict: ...

    @actormethod(name="Reserve")
    async def reserve(self, quantity: int, order_id: str) -> dict: ...

    @actormethod(name="Release")
    async def release(self, reservation_id: str) -> dict: ...

    @actormethod(name="Commit")
    async def commit(self, reservation_id: str) -> dict: ...


# =============================================================================
# Inventory Actor Implementation
# =============================================================================

class InventoryActor(Actor, InventoryActorInterface):
    """Actor managing stock for a single product."""

    def __init__(self, ctx, actor_id):
        super().__init__(ctx, actor_id)
        self._stock: ProductStock | None = None

    async def _on_activate(self) -> None:
        """Load stock state when actor activates."""
        logger.info(f"Activating inventory actor for product {self.id.id}")
        state = await self._state_manager.try_get_state("stock")
        if state:
            self._stock = ProductStock(**state)
        else:
            # Initialize new product with default stock
            self._stock = ProductStock(
                product_id=self.id.id,
                available=100,  # Default initial stock
                reserved=0,
                reservations={}
            )
            await self._save_state()

    async def _on_deactivate(self) -> None:
        """Save state when actor deactivates."""
        await self._save_state()

    async def _save_state(self) -> None:
        """Persist stock state."""
        await self._state_manager.set_state("stock", self._stock.model_dump())
        await self._state_manager.save_state()

    async def get_stock(self) -> dict:
        """Get current stock levels."""
        return {
            "product_id": self._stock.product_id,
            "available": self._stock.available,
            "reserved": self._stock.reserved,
            "total": self._stock.available + self._stock.reserved
        }

    async def reserve(self, quantity: int, order_id: str) -> dict:
        """Reserve stock for an order."""
        if quantity > self._stock.available:
            return {
                "success": False,
                "error": f"Insufficient stock. Available: {self._stock.available}, Requested: {quantity}"
            }

        reservation_id = str(uuid.uuid4())
        self._stock.available -= quantity
        self._stock.reserved += quantity
        self._stock.reservations[reservation_id] = {
            "order_id": order_id,
            "quantity": quantity
        }

        await self._save_state()
        logger.info(f"Reserved {quantity} units for order {order_id}, reservation {reservation_id}")

        return {
            "success": True,
            "reservation_id": reservation_id,
            "reserved_quantity": quantity
        }

    async def release(self, reservation_id: str) -> dict:
        """Release a reservation (compensation)."""
        if reservation_id not in self._stock.reservations:
            return {"success": False, "error": "Reservation not found"}

        reservation = self._stock.reservations.pop(reservation_id)
        quantity = reservation["quantity"]
        self._stock.reserved -= quantity
        self._stock.available += quantity

        await self._save_state()
        logger.info(f"Released reservation {reservation_id}, returned {quantity} units")

        return {"success": True, "released_quantity": quantity}

    async def commit(self, reservation_id: str) -> dict:
        """Commit a reservation (remove from reserved without returning to available)."""
        if reservation_id not in self._stock.reservations:
            return {"success": False, "error": "Reservation not found"}

        reservation = self._stock.reservations.pop(reservation_id)
        quantity = reservation["quantity"]
        self._stock.reserved -= quantity

        await self._save_state()
        logger.info(f"Committed reservation {reservation_id}, {quantity} units shipped")

        return {"success": True, "committed_quantity": quantity}


# =============================================================================
# Register Actor
# =============================================================================

@app.on_event("startup")
async def startup():
    await actor_runtime.register_actor(InventoryActor)
    logger.info("Inventory service started with actor runtime")


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "inventory-service"}


@app.get("/dapr/config")
async def dapr_config():
    """DAPR actor configuration endpoint."""
    return {
        "entities": ["InventoryActor"],
        "actorIdleTimeout": "1h",
        "actorScanInterval": "30s",
        "drainOngoingCallTimeout": "60s",
        "drainRebalancedActors": True
    }


@app.get("/inventory/{product_id}")
async def get_stock(product_id: str):
    """Get stock levels for a product."""
    with tracer.start_as_current_span("get_stock") as span:
        span.set_attribute("product.id", product_id)

        proxy = ActorProxy.create(
            actor_type="InventoryActor",
            actor_id=product_id,
            actor_interface=InventoryActorInterface
        )
        stock = await proxy.GetStock()
        return stock


@app.post("/inventory/{product_id}/reserve")
async def reserve_stock(product_id: str, request: ReserveRequest):
    """Reserve stock for an order."""
    with tracer.start_as_current_span("reserve_stock") as span:
        span.set_attribute("product.id", product_id)
        span.set_attribute("order.id", request.order_id)
        span.set_attribute("quantity", request.quantity)

        proxy = ActorProxy.create(
            actor_type="InventoryActor",
            actor_id=product_id,
            actor_interface=InventoryActorInterface
        )
        result = await proxy.Reserve(request.quantity, request.order_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result


@app.post("/inventory/{product_id}/release")
async def release_stock(product_id: str, request: ReleaseRequest):
    """Release a stock reservation."""
    with tracer.start_as_current_span("release_stock") as span:
        span.set_attribute("product.id", product_id)
        span.set_attribute("reservation.id", request.reservation_id)

        proxy = ActorProxy.create(
            actor_type="InventoryActor",
            actor_id=product_id,
            actor_interface=InventoryActorInterface
        )
        result = await proxy.Release(request.reservation_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result


@app.post("/inventory/{product_id}/commit")
async def commit_reservation(product_id: str, request: ReleaseRequest):
    """Commit a reservation (stock shipped)."""
    with tracer.start_as_current_span("commit_stock") as span:
        span.set_attribute("product.id", product_id)
        span.set_attribute("reservation.id", request.reservation_id)

        proxy = ActorProxy.create(
            actor_type="InventoryActor",
            actor_id=product_id,
            actor_interface=InventoryActorInterface
        )
        result = await proxy.Commit(request.reservation_id)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))

        return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8002")))
