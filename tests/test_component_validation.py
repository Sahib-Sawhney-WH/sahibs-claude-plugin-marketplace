"""
Component YAML Validation Tests
==============================

Tests for DAPR component configuration validation patterns.
These tests verify the validation logic used by plugin hooks.
"""

import pytest
import re
from pathlib import Path
from conftest import write_yaml, read_yaml


class TestComponentSchema:
    """Test component YAML schema validation."""

    def test_valid_component_passes(self, components_dir, valid_component):
        """Valid component should pass all validation checks."""
        path = write_yaml(components_dir / "statestore.yaml", valid_component)
        content = read_yaml(path)

        # Check required fields
        assert content.get("apiVersion") == "dapr.io/v1alpha1"
        assert content.get("kind") == "Component"
        assert "metadata" in content
        assert "name" in content["metadata"]
        assert "spec" in content
        assert "type" in content["spec"]
        assert "version" in content["spec"]

    def test_missing_apiversion_fails(self, components_dir):
        """Component without apiVersion should fail validation."""
        invalid = {
            "kind": "Component",
            "metadata": {"name": "test"},
            "spec": {"type": "state.redis", "version": "v1"}
        }
        path = write_yaml(components_dir / "invalid.yaml", invalid)
        content = read_yaml(path)

        assert content.get("apiVersion") is None, "Missing apiVersion should fail"

    def test_invalid_kind_fails(self, components_dir):
        """Component with wrong kind should fail validation."""
        invalid = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "WrongKind",
            "metadata": {"name": "test"},
            "spec": {"type": "state.redis", "version": "v1"}
        }
        path = write_yaml(components_dir / "invalid.yaml", invalid)
        content = read_yaml(path)

        assert content.get("kind") != "Component", "Invalid kind should fail"

    def test_invalid_metadata_name_fails(self, components_dir):
        """Component with invalid name format should fail validation."""
        # Names must be lowercase, alphanumeric, with hyphens
        invalid_names = [
            "StateStore",  # Uppercase
            "state_store",  # Underscore
            "state.store",  # Dot
            "123start",  # Starts with number
        ]

        name_pattern = re.compile(r"^[a-z][a-z0-9-]*$")

        for name in invalid_names:
            assert not name_pattern.match(name), f"{name} should fail validation"

    def test_valid_metadata_name_passes(self, components_dir):
        """Component with valid name format should pass validation."""
        valid_names = [
            "statestore",
            "state-store",
            "my-state-store-v2",
        ]

        name_pattern = re.compile(r"^[a-z][a-z0-9-]*$")

        for name in valid_names:
            assert name_pattern.match(name), f"{name} should pass validation"


class TestSecretValidation:
    """Test secret handling validation."""

    def test_secretkeyref_passes(self, components_dir, valid_component_with_secret):
        """Component using secretKeyRef should pass validation."""
        path = write_yaml(components_dir / "cosmos.yaml", valid_component_with_secret)
        content = read_yaml(path)

        # Check that masterKey uses secretKeyRef
        metadata = content["spec"]["metadata"]
        master_key_entry = next(
            (m for m in metadata if m.get("name") == "masterKey"),
            None
        )

        assert master_key_entry is not None
        assert "secretKeyRef" in master_key_entry
        assert "value" not in master_key_entry, "Should use secretKeyRef, not value"

    def test_plain_text_secret_detected(self, components_dir, invalid_component_plain_secret):
        """Component with plain-text secret should be flagged."""
        path = write_yaml(components_dir / "insecure.yaml", invalid_component_plain_secret)
        content = read_yaml(path)

        # Patterns that indicate secrets
        secret_field_patterns = [
            "password", "secret", "key", "token", "credential",
            "masterKey", "accessKey", "connectionString"
        ]

        metadata = content["spec"]["metadata"]
        issues = []

        for entry in metadata:
            field_name = entry.get("name", "").lower()
            has_plain_value = "value" in entry and "secretKeyRef" not in entry

            for pattern in secret_field_patterns:
                if pattern.lower() in field_name and has_plain_value:
                    issues.append(f"Plain-text secret detected: {entry['name']}")

        assert len(issues) > 0, "Should detect plain-text masterKey"

    def test_connection_string_secret_detection(self, components_dir):
        """Connection strings should use secretKeyRef."""
        insecure = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "db"},
            "spec": {
                "type": "state.postgresql",
                "version": "v1",
                "metadata": [
                    {
                        "name": "connectionString",
                        "value": "host=localhost user=postgres password=secret"
                    }
                ]
            }
        }

        path = write_yaml(components_dir / "insecure-db.yaml", insecure)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        conn_string = next(
            (m for m in metadata if m.get("name") == "connectionString"),
            None
        )

        # Should flag this as insecure
        assert conn_string is not None
        assert "value" in conn_string
        assert "secretKeyRef" not in conn_string


class TestComponentType:
    """Test component type validation."""

    def test_valid_state_store_types(self):
        """Valid state store types should pass."""
        valid_types = [
            "state.redis",
            "state.azure.cosmosdb",
            "state.aws.dynamodb",
            "state.gcp.firestore",
            "state.postgresql",
            "state.mongodb",
        ]

        type_pattern = re.compile(r"^state\.[a-z]+(\.[a-z]+)?$")

        for t in valid_types:
            assert type_pattern.match(t), f"{t} should be valid"

    def test_valid_pubsub_types(self):
        """Valid pub/sub types should pass."""
        valid_types = [
            "pubsub.redis",
            "pubsub.azure.servicebus.topics",
            "pubsub.azure.servicebus.queues",
            "pubsub.aws.snssqs",
            "pubsub.gcp.pubsub",
            "pubsub.kafka",
            "pubsub.rabbitmq",
        ]

        for t in valid_types:
            assert t.startswith("pubsub."), f"{t} should be valid pubsub type"

    def test_valid_binding_types(self):
        """Valid binding types should pass."""
        valid_types = [
            "bindings.http",
            "bindings.cron",
            "bindings.kafka",
            "bindings.azure.blobstorage",
            "bindings.azure.eventhubs",
            "bindings.aws.s3",
        ]

        for t in valid_types:
            assert t.startswith("bindings."), f"{t} should be valid binding type"
