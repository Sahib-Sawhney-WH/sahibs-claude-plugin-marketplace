"""Order Service - Orchestrates order processing with DAPR Workflows."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dapr.clients import DaprClient
from dapr.ext.workflow import DaprWorkflowContext, WorkflowRuntime, workflow, activity
from opentelemetry import trace
import uuid
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="Order Service")


# =============================================================================
# Models
# =============================================================================

class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    customer_id: str
    items: list[OrderItem]
    payment_method: str


class Order(BaseModel):
    id: str
    customer_id: str
    items: list[OrderItem]
    total: float
    status: str
    payment_method: str


# =============================================================================
# Workflow Activities
# =============================================================================

@activity
async def reserve_inventory(ctx, order: dict) -> dict:
    """Reserve inventory for all order items."""
    async with DaprClient() as client:
        reservations = []
        for item in order["items"]:
            response = await client.invoke_method(
                app_id="inventory-service",
                method_name=f"inventory/{item['product_id']}/reserve",
                http_verb="POST",
                data={"quantity": item["quantity"], "order_id": order["id"]}
            )
            result = response.json()
            if not result.get("success"):
                # Rollback previous reservations
                for res in reservations:
                    await client.invoke_method(
                        app_id="inventory-service",
                        method_name=f"inventory/{res['product_id']}/release",
                        http_verb="POST",
                        data={"reservation_id": res["reservation_id"]}
                    )
                raise Exception(f"Failed to reserve inventory for {item['product_id']}")
            reservations.append({
                "product_id": item["product_id"],
                "reservation_id": result["reservation_id"]
            })
        return {"reservations": reservations}


@activity
async def process_payment(ctx, payment_data: dict) -> dict:
    """Process payment for the order."""
    async with DaprClient() as client:
        response = await client.invoke_method(
            app_id="payment-service",
            method_name="payments",
            http_verb="POST",
            data=payment_data
        )
        result = response.json()
        if not result.get("success"):
            raise Exception(f"Payment failed: {result.get('error')}")
        return {"payment_id": result["payment_id"], "transaction_id": result["transaction_id"]}


@activity
async def create_shipment(ctx, order: dict) -> dict:
    """Create shipment for the order."""
    # Simplified - would call shipping service
    return {
        "shipment_id": f"SHIP-{order['id']}",
        "tracking_number": f"TRACK-{uuid.uuid4().hex[:8].upper()}"
    }


@activity
async def send_notification(ctx, notification: dict) -> None:
    """Send notification via pub/sub."""
    async with DaprClient() as client:
        await client.publish_event(
            pubsub_name="pubsub",
            topic_name="notifications",
            data=notification
        )


@activity
async def compensate_inventory(ctx, reservations: list) -> None:
    """Release inventory reservations (compensation)."""
    async with DaprClient() as client:
        for res in reservations:
            await client.invoke_method(
                app_id="inventory-service",
                method_name=f"inventory/{res['product_id']}/release",
                http_verb="POST",
                data={"reservation_id": res["reservation_id"]}
            )


@activity
async def refund_payment(ctx, payment_id: str) -> None:
    """Refund payment (compensation)."""
    async with DaprClient() as client:
        await client.invoke_method(
            app_id="payment-service",
            method_name=f"payments/{payment_id}/refund",
            http_verb="POST"
        )


# =============================================================================
# Order Saga Workflow
# =============================================================================

@workflow
def order_saga(ctx: DaprWorkflowContext, order: dict):
    """Orchestrate order processing with saga compensation."""
    reservations = None
    payment_result = None

    try:
        # Step 1: Reserve inventory
        inventory_result = yield ctx.call_activity(reserve_inventory, input=order)
        reservations = inventory_result["reservations"]

        # Step 2: Process payment
        payment_data = {
            "order_id": order["id"],
            "amount": order["total"],
            "method": order["payment_method"],
            "customer_id": order["customer_id"]
        }
        payment_result = yield ctx.call_activity(process_payment, input=payment_data)

        # Step 3: Create shipment
        shipment = yield ctx.call_activity(create_shipment, input=order)

        # Step 4: Send success notification
        yield ctx.call_activity(send_notification, input={
            "type": "order_completed",
            "order_id": order["id"],
            "customer_id": order["customer_id"],
            "tracking_number": shipment["tracking_number"]
        })

        return {
            "status": "completed",
            "order_id": order["id"],
            "payment_id": payment_result["payment_id"],
            "shipment_id": shipment["shipment_id"],
            "tracking_number": shipment["tracking_number"]
        }

    except Exception as e:
        # Compensate: Release inventory if reserved
        if reservations:
            yield ctx.call_activity(compensate_inventory, input=reservations)

        # Compensate: Refund payment if processed
        if payment_result:
            yield ctx.call_activity(refund_payment, input=payment_result["payment_id"])

        # Send failure notification
        yield ctx.call_activity(send_notification, input={
            "type": "order_failed",
            "order_id": order["id"],
            "customer_id": order["customer_id"],
            "reason": str(e)
        })

        raise


# =============================================================================
# Workflow Runtime
# =============================================================================

workflow_runtime = WorkflowRuntime()
workflow_runtime.register_workflow(order_saga)
workflow_runtime.register_activity(reserve_inventory)
workflow_runtime.register_activity(process_payment)
workflow_runtime.register_activity(create_shipment)
workflow_runtime.register_activity(send_notification)
workflow_runtime.register_activity(compensate_inventory)
workflow_runtime.register_activity(refund_payment)


# =============================================================================
# API Endpoints
# =============================================================================

@app.on_event("startup")
async def startup():
    await workflow_runtime.start()
    logger.info("Order service started with workflow runtime")


@app.on_event("shutdown")
async def shutdown():
    await workflow_runtime.shutdown()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "order-service"}


@app.post("/orders")
async def create_order(request: CreateOrderRequest):
    """Create a new order and start the order saga."""
    with tracer.start_as_current_span("create_order") as span:
        order_id = str(uuid.uuid4())
        total = sum(item.price * item.quantity for item in request.items)

        order = Order(
            id=order_id,
            customer_id=request.customer_id,
            items=request.items,
            total=total,
            status="pending",
            payment_method=request.payment_method
        )

        span.set_attribute("order.id", order_id)
        span.set_attribute("order.total", total)

        # Save order to state store
        async with DaprClient() as client:
            await client.save_state(
                store_name="statestore",
                key=f"order-{order_id}",
                value=order.model_dump_json()
            )

            # Start the order saga workflow
            instance_id = await client.start_workflow(
                workflow_component="dapr",
                workflow_name="order_saga",
                input=order.model_dump(),
                instance_id=order_id
            )

        logger.info(f"Order {order_id} created, workflow started: {instance_id}")

        return {
            "order_id": order_id,
            "workflow_instance_id": instance_id,
            "status": "processing"
        }


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get order details."""
    async with DaprClient() as client:
        state = await client.get_state(store_name="statestore", key=f"order-{order_id}")
        if not state.data:
            raise HTTPException(status_code=404, detail="Order not found")
        return {"order": state.json()}


@app.get("/orders/{order_id}/status")
async def get_order_status(order_id: str):
    """Get order workflow status."""
    async with DaprClient() as client:
        workflow_state = await client.get_workflow(
            workflow_component="dapr",
            instance_id=order_id
        )
        return {
            "order_id": order_id,
            "workflow_status": workflow_state.runtime_status,
            "result": workflow_state.serialized_output
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8001")))
