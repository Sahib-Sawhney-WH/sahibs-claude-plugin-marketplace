"""
Example DAPR Unit Tests

Demonstrates testing patterns for DAPR building blocks.
"""
import json
import pytest
from unittest.mock import patch, AsyncMock


# =============================================================================
# State Management Tests
# =============================================================================

class TestStateManagement:
    """Tests for state management operations."""

    @pytest.mark.asyncio
    async def test_save_state(self, dapr_client_patch, assert_state_saved):
        """Test saving state to store."""
        from dapr.clients import DaprClient

        order = {"id": "order-123", "items": ["item1", "item2"], "total": 99.99}

        async with DaprClient() as client:
            await client.save_state(
                store_name="statestore",
                key="order-123",
                value=json.dumps(order)
            )

        assert_state_saved("order-123", order)

    @pytest.mark.asyncio
    async def test_get_state(self, dapr_client_patch, state_store):
        """Test retrieving state from store."""
        from dapr.clients import DaprClient

        # Pre-populate state
        order = {"id": "order-456", "status": "pending"}
        state_store.save("order-456", order)

        async with DaprClient() as client:
            state = await client.get_state(
                store_name="statestore",
                key="order-456"
            )

        result = json.loads(state.data.decode())
        assert result["id"] == "order-456"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_delete_state(self, dapr_client_patch, state_store, assert_state_saved):
        """Test deleting state from store."""
        from dapr.clients import DaprClient

        # Pre-populate state
        state_store.save("temp-key", {"data": "temporary"})

        async with DaprClient() as client:
            await client.delete_state(
                store_name="statestore",
                key="temp-key"
            )

        assert state_store.get("temp-key") is None


# =============================================================================
# Pub/Sub Tests
# =============================================================================

class TestPubSub:
    """Tests for pub/sub messaging."""

    @pytest.mark.asyncio
    async def test_publish_event(self, dapr_client_patch, assert_event_published):
        """Test publishing an event."""
        from dapr.clients import DaprClient

        event_data = {"order_id": "123", "status": "created"}

        async with DaprClient() as client:
            await client.publish_event(
                pubsub_name="pubsub",
                topic_name="orders",
                data=json.dumps(event_data)
            )

        assert_event_published("orders", expected_data=event_data)

    @pytest.mark.asyncio
    async def test_publish_multiple_events(self, dapr_client_patch, assert_event_published):
        """Test publishing multiple events."""
        from dapr.clients import DaprClient

        async with DaprClient() as client:
            for i in range(3):
                await client.publish_event(
                    pubsub_name="pubsub",
                    topic_name="batch",
                    data=json.dumps({"index": i})
                )

        assert_event_published("batch", count=3)

    def test_subscriber_handler(self, cloud_event):
        """Test event subscriber handler."""
        received_events = []

        def handle_order_event(event):
            received_events.append(event["data"])
            return {"status": "SUCCESS"}

        # Simulate CloudEvent
        event = cloud_event(
            data={"order_id": "789", "action": "process"},
            topic="orders"
        )

        result = handle_order_event(event)

        assert result["status"] == "SUCCESS"
        assert len(received_events) == 1
        assert received_events[0]["order_id"] == "789"


# =============================================================================
# Service Invocation Tests
# =============================================================================

class TestServiceInvocation:
    """Tests for service-to-service invocation."""

    @pytest.mark.asyncio
    async def test_invoke_method(self, mock_dapr_client):
        """Test invoking a method on another service."""
        async with mock_dapr_client as client:
            response = await client.invoke_method(
                app_id="inventory-service",
                method_name="products/123",
                http_verb="GET"
            )

        assert len(mock_dapr_client.invocations) == 1
        invocation = mock_dapr_client.invocations[0]
        assert invocation["app_id"] == "inventory-service"
        assert invocation["method"] == "products/123"

    @pytest.mark.asyncio
    async def test_invoke_with_data(self, mock_dapr_client):
        """Test invoking with request body."""
        async with mock_dapr_client as client:
            response = await client.invoke_method(
                app_id="payment-service",
                method_name="payments",
                http_verb="POST",
                data=json.dumps({"amount": 100})
            )

        invocation = mock_dapr_client.invocations[0]
        assert invocation["http_verb"] == "POST"


# =============================================================================
# Secrets Tests
# =============================================================================

class TestSecrets:
    """Tests for secrets management."""

    @pytest.mark.asyncio
    async def test_get_secret(self, mock_dapr_client):
        """Test retrieving a secret."""
        # Set up secret
        mock_dapr_client.set_secret("secretstore", "db-password", "super-secret-123")

        async with mock_dapr_client as client:
            secret = await client.get_secret(
                store_name="secretstore",
                key="db-password"
            )

        assert secret.secret["db-password"] == "super-secret-123"


# =============================================================================
# FastAPI Integration Tests
# =============================================================================

class TestFastAPIIntegration:
    """Tests for FastAPI endpoints with DAPR."""

    def test_health_endpoint(self, test_app):
        """Test health check endpoint."""
        from fastapi import FastAPI

        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        client = test_app(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_order_creation(self, test_app, dapr_client_patch, assert_state_saved):
        """Test order creation with state save."""
        from fastapi import FastAPI
        from pydantic import BaseModel

        app = FastAPI()

        class Order(BaseModel):
            id: str
            items: list

        @app.post("/orders")
        async def create_order(order: Order):
            from dapr.clients import DaprClient

            async with DaprClient() as client:
                await client.save_state(
                    "statestore",
                    order.id,
                    order.model_dump_json()
                )
            return {"status": "created", "id": order.id}

        client = test_app(app)
        response = client.post(
            "/orders",
            json={"id": "test-order", "items": ["item1"]}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "created"
        assert_state_saved("test-order", {"id": "test-order", "items": ["item1"]})


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Tests for configuration management."""

    def test_config_update_callback(self, config_store):
        """Test configuration update notification."""
        updates = []

        def on_update(key, value):
            updates.append((key, value))

        config_store.subscribe(on_update)
        config_store.set("feature.enabled", "true")

        assert len(updates) == 1
        assert updates[0] == ("feature.enabled", "true")


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_state_not_found(self, dapr_client_patch):
        """Test handling of missing state."""
        from dapr.clients import DaprClient

        async with DaprClient() as client:
            state = await client.get_state(
                store_name="statestore",
                key="nonexistent-key"
            )

        assert state.data == b""

    @pytest.mark.asyncio
    async def test_service_invocation_retry(self, mock_dapr_client):
        """Test retry behavior on service invocation failure."""
        call_count = 0

        async def flaky_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Service unavailable")
            return {"status": "success"}

        mock_dapr_client.invoke_method = flaky_invoke

        # With retry logic in production code
        for attempt in range(3):
            try:
                result = await mock_dapr_client.invoke_method(
                    app_id="flaky-service",
                    method_name="endpoint"
                )
                break
            except Exception:
                continue

        assert call_count == 3
