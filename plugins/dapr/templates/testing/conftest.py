"""
DAPR Test Fixtures for Pytest

Provides mock DAPR clients and test utilities for unit and integration testing.
"""
import json
import pytest
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# =============================================================================
# Mock State Store
# =============================================================================

class MockStateStore:
    """In-memory state store for testing."""

    def __init__(self):
        self._store: Dict[str, str] = {}

    def save(self, key: str, value: Any) -> None:
        self._store[key] = json.dumps(value) if not isinstance(value, str) else value

    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    def keys(self) -> List[str]:
        return list(self._store.keys())


@pytest.fixture
def state_store():
    """Fixture providing an in-memory state store."""
    store = MockStateStore()
    yield store
    store.clear()


# =============================================================================
# Mock Pub/Sub
# =============================================================================

class MockPubSub:
    """In-memory pub/sub for testing."""

    def __init__(self):
        self._messages: Dict[str, List[Dict]] = {}
        self._subscribers: Dict[str, List[callable]] = {}

    def publish(self, topic: str, data: Any) -> None:
        if topic not in self._messages:
            self._messages[topic] = []
        self._messages[topic].append(data)

        # Notify subscribers
        for callback in self._subscribers.get(topic, []):
            callback(data)

    def subscribe(self, topic: str, callback: callable) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def get_messages(self, topic: str) -> List[Dict]:
        return self._messages.get(topic, [])

    def clear(self) -> None:
        self._messages.clear()
        self._subscribers.clear()


@pytest.fixture
def pubsub():
    """Fixture providing an in-memory pub/sub."""
    ps = MockPubSub()
    yield ps
    ps.clear()


# =============================================================================
# Mock DAPR Client
# =============================================================================

@dataclass
class MockStateResponse:
    data: bytes
    etag: str = ""


@dataclass
class MockSecretResponse:
    secret: Dict[str, str]


class MockDaprClient:
    """Mock DAPR client for unit testing."""

    def __init__(self, state_store: MockStateStore = None, pubsub: MockPubSub = None):
        self.state_store = state_store or MockStateStore()
        self.pubsub = pubsub or MockPubSub()
        self.invocations: List[Dict] = []
        self.secrets: Dict[str, Dict[str, str]] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    # State Management
    async def save_state(self, store_name: str, key: str, value: str, **kwargs):
        self.state_store.save(key, value)

    async def get_state(self, store_name: str, key: str, **kwargs) -> MockStateResponse:
        value = self.state_store.get(key)
        return MockStateResponse(data=value.encode() if value else b"")

    async def delete_state(self, store_name: str, key: str, **kwargs):
        self.state_store.delete(key)

    # Pub/Sub
    async def publish_event(self, pubsub_name: str, topic_name: str, data: str, **kwargs):
        parsed = json.loads(data) if isinstance(data, str) else data
        self.pubsub.publish(topic_name, parsed)

    # Service Invocation
    async def invoke_method(self, app_id: str, method_name: str, **kwargs):
        invocation = {"app_id": app_id, "method": method_name, **kwargs}
        self.invocations.append(invocation)
        return MagicMock(json=lambda: {"status": "mocked"})

    # Secrets
    async def get_secret(self, store_name: str, key: str, **kwargs) -> MockSecretResponse:
        store = self.secrets.get(store_name, {})
        return MockSecretResponse(secret={key: store.get(key, "mock-secret")})

    def set_secret(self, store_name: str, key: str, value: str):
        """Helper to set secrets for testing."""
        if store_name not in self.secrets:
            self.secrets[store_name] = {}
        self.secrets[store_name][key] = value

    # Bindings
    async def invoke_binding(self, binding_name: str, operation: str, data: str, **kwargs):
        return MagicMock()


@pytest.fixture
def mock_dapr_client(state_store, pubsub):
    """Fixture providing a mock DAPR client."""
    return MockDaprClient(state_store=state_store, pubsub=pubsub)


@pytest.fixture
def dapr_client_patch(mock_dapr_client):
    """Fixture that patches DaprClient globally."""
    with patch("dapr.clients.DaprClient") as mock:
        mock.return_value.__aenter__ = AsyncMock(return_value=mock_dapr_client)
        mock.return_value.__aexit__ = AsyncMock()
        yield mock_dapr_client


# =============================================================================
# Mock Configuration Store
# =============================================================================

class MockConfigStore:
    """Mock configuration store for testing."""

    def __init__(self):
        self._config: Dict[str, str] = {}
        self._callbacks: List[callable] = []

    def set(self, key: str, value: str) -> None:
        self._config[key] = value
        for callback in self._callbacks:
            callback(key, value)

    def get(self, key: str) -> Optional[str]:
        return self._config.get(key)

    def subscribe(self, callback: callable) -> None:
        self._callbacks.append(callback)


@pytest.fixture
def config_store():
    """Fixture providing mock configuration store."""
    return MockConfigStore()


# =============================================================================
# Test Utilities
# =============================================================================

@pytest.fixture
def cloud_event():
    """Factory fixture for creating CloudEvents."""
    def _create_event(data: Dict, topic: str = "test-topic"):
        return {
            "specversion": "1.0",
            "type": "com.dapr.event",
            "source": "test",
            "id": "test-id",
            "datacontenttype": "application/json",
            "topic": topic,
            "data": data
        }
    return _create_event


@pytest.fixture
def assert_state_saved(state_store):
    """Assertion helper for state operations."""
    def _assert(key: str, expected_value: Any):
        stored = state_store.get(key)
        assert stored is not None, f"State key '{key}' not found"
        actual = json.loads(stored)
        assert actual == expected_value, f"Expected {expected_value}, got {actual}"
    return _assert


@pytest.fixture
def assert_event_published(pubsub):
    """Assertion helper for pub/sub operations."""
    def _assert(topic: str, expected_data: Any = None, count: int = None):
        messages = pubsub.get_messages(topic)
        if count is not None:
            assert len(messages) == count, f"Expected {count} messages, got {len(messages)}"
        if expected_data is not None:
            assert expected_data in messages, f"Expected message not found in {messages}"
    return _assert


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest.fixture
def test_app():
    """Fixture for FastAPI test client setup."""
    from fastapi.testclient import TestClient

    def _create_client(app):
        return TestClient(app)

    return _create_client


# =============================================================================
# Integration Test Fixtures (Testcontainers)
# =============================================================================

@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for integration tests."""
    try:
        from testcontainers.redis import RedisContainer

        with RedisContainer() as redis:
            yield redis.get_connection_url()
    except ImportError:
        pytest.skip("testcontainers not installed")


@pytest.fixture(scope="session")
def dapr_sidecar():
    """Start DAPR sidecar for e2e tests."""
    import subprocess
    import time

    # Start DAPR sidecar
    process = subprocess.Popen([
        "dapr", "run",
        "--app-id", "test-app",
        "--app-port", "8000",
        "--dapr-http-port", "3500",
        "--components-path", "./components"
    ])

    # Wait for sidecar to be ready
    time.sleep(5)

    yield "http://localhost:3500"

    # Cleanup
    process.terminate()
    process.wait()
