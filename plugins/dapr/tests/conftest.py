"""
DAPR Plugin Test Fixtures
========================

Pytest fixtures for testing DAPR plugin validation logic.
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def components_dir(temp_dir):
    """Create a components directory structure."""
    components = temp_dir / "components"
    components.mkdir()
    return components


@pytest.fixture
def middleware_dir(temp_dir):
    """Create a middleware directory structure."""
    middleware = temp_dir / "middleware"
    middleware.mkdir()
    return middleware


@pytest.fixture
def bindings_dir(temp_dir):
    """Create a bindings directory structure."""
    bindings = temp_dir / "bindings"
    bindings.mkdir()
    return bindings


@pytest.fixture
def valid_component():
    """Return a valid DAPR component YAML structure."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "statestore",
            "namespace": "default"
        },
        "spec": {
            "type": "state.redis",
            "version": "v1",
            "metadata": [
                {"name": "redisHost", "value": "localhost:6379"}
            ]
        }
    }


@pytest.fixture
def valid_component_with_secret():
    """Return a valid component with secretKeyRef."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "statestore",
            "namespace": "default"
        },
        "spec": {
            "type": "state.azure.cosmosdb",
            "version": "v1",
            "metadata": [
                {"name": "url", "value": "https://myaccount.documents.azure.com:443/"},
                {
                    "name": "masterKey",
                    "secretKeyRef": {
                        "name": "cosmos-secrets",
                        "key": "master-key"
                    }
                }
            ]
        }
    }


@pytest.fixture
def invalid_component_plain_secret():
    """Return a component with plain-text secret (should fail validation)."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "statestore"
        },
        "spec": {
            "type": "state.azure.cosmosdb",
            "version": "v1",
            "metadata": [
                {"name": "url", "value": "https://myaccount.documents.azure.com:443/"},
                {"name": "masterKey", "value": "supersecretkey123"}  # Plain text!
            ]
        }
    }


@pytest.fixture
def valid_oauth2_middleware():
    """Return valid OAuth2 middleware configuration."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "oauth2"
        },
        "spec": {
            "type": "middleware.http.oauth2",
            "version": "v1",
            "metadata": [
                {
                    "name": "clientId",
                    "secretKeyRef": {
                        "name": "oauth-secrets",
                        "key": "client-id"
                    }
                },
                {
                    "name": "clientSecret",
                    "secretKeyRef": {
                        "name": "oauth-secrets",
                        "key": "client-secret"
                    }
                },
                {"name": "authURL", "value": "https://auth.example.com/authorize"},
                {"name": "tokenURL", "value": "https://auth.example.com/token"}
            ]
        }
    }


@pytest.fixture
def invalid_oauth2_plain_secret():
    """Return OAuth2 middleware with plain-text clientSecret (should fail)."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "oauth2"
        },
        "spec": {
            "type": "middleware.http.oauth2",
            "version": "v1",
            "metadata": [
                {"name": "clientId", "value": "my-client-id"},
                {"name": "clientSecret", "value": "my-secret-value"},  # Plain text!
                {"name": "authURL", "value": "https://auth.example.com/authorize"},
                {"name": "tokenURL", "value": "https://auth.example.com/token"}
            ]
        }
    }


@pytest.fixture
def invalid_oauth2_http_url():
    """Return OAuth2 middleware with HTTP (non-HTTPS) URL (should warn)."""
    return {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "oauth2"
        },
        "spec": {
            "type": "middleware.http.oauth2",
            "version": "v1",
            "metadata": [
                {
                    "name": "clientId",
                    "secretKeyRef": {"name": "oauth-secrets", "key": "client-id"}
                },
                {
                    "name": "clientSecret",
                    "secretKeyRef": {"name": "oauth-secrets", "key": "client-secret"}
                },
                {"name": "authURL", "value": "http://auth.example.com/authorize"},  # HTTP!
                {"name": "tokenURL", "value": "https://auth.example.com/token"}
            ]
        }
    }


def write_yaml(path: Path, content: dict) -> Path:
    """Helper to write YAML content to a file."""
    with open(path, "w") as f:
        yaml.dump(content, f)
    return path


def read_yaml(path: Path) -> dict:
    """Helper to read YAML content from a file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)
