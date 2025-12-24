"""
Binding Configuration Validation Tests
======================================

Tests for DAPR binding security and configuration validation.
"""

import pytest
import re
from pathlib import Path
from conftest import write_yaml, read_yaml


class TestDatabaseBindingValidation:
    """Test database binding security validation."""

    def test_postgresql_with_secretkeyref_passes(self, bindings_dir):
        """PostgreSQL binding with secretKeyRef should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "postgres-db"},
            "spec": {
                "type": "bindings.postgresql",
                "version": "v1",
                "metadata": [
                    {
                        "name": "connectionString",
                        "secretKeyRef": {
                            "name": "postgres-secrets",
                            "key": "connection-string"
                        }
                    }
                ]
            }
        }

        path = write_yaml(bindings_dir / "postgres.yaml", config)
        content = read_yaml(path)

        issues = validate_database_binding(content)
        assert len(issues) == 0, f"Valid PostgreSQL should pass: {issues}"

    def test_postgresql_with_plain_connection_string_fails(self, bindings_dir):
        """PostgreSQL with plain connection string should fail."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "postgres-db"},
            "spec": {
                "type": "bindings.postgresql",
                "version": "v1",
                "metadata": [
                    {
                        "name": "connectionString",
                        "value": "host=localhost user=postgres password=secret dbname=mydb"
                    }
                ]
            }
        }

        path = write_yaml(bindings_dir / "insecure-postgres.yaml", config)
        content = read_yaml(path)

        issues = validate_database_binding(content)
        assert any("connectionString" in issue or "secret" in issue.lower() for issue in issues), \
            "Should flag plain-text connection string"

    def test_mysql_with_plain_url_fails(self, bindings_dir):
        """MySQL with plain URL containing password should fail."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "mysql-db"},
            "spec": {
                "type": "bindings.mysql",
                "version": "v1",
                "metadata": [
                    {
                        "name": "url",
                        "value": "user:password@tcp(localhost:3306)/mydb"
                    }
                ]
            }
        }

        path = write_yaml(bindings_dir / "insecure-mysql.yaml", config)
        content = read_yaml(path)

        issues = validate_database_binding(content)
        assert len(issues) > 0, "Should flag plain-text database URL with password"


class TestSMTPBindingValidation:
    """Test SMTP binding security validation."""

    def test_smtp_with_secretkeyref_passes(self, bindings_dir):
        """SMTP binding with secretKeyRef credentials should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "smtp-email"},
            "spec": {
                "type": "bindings.smtp",
                "version": "v1",
                "metadata": [
                    {"name": "host", "value": "smtp.example.com"},
                    {"name": "port", "value": "587"},
                    {
                        "name": "user",
                        "secretKeyRef": {"name": "smtp-secrets", "key": "username"}
                    },
                    {
                        "name": "password",
                        "secretKeyRef": {"name": "smtp-secrets", "key": "password"}
                    }
                ]
            }
        }

        path = write_yaml(bindings_dir / "smtp.yaml", config)
        content = read_yaml(path)

        issues = validate_smtp_binding(content)
        assert len(issues) == 0, f"Valid SMTP should pass: {issues}"

    def test_smtp_with_plain_password_fails(self, bindings_dir):
        """SMTP with plain-text password should fail."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "smtp-email"},
            "spec": {
                "type": "bindings.smtp",
                "version": "v1",
                "metadata": [
                    {"name": "host", "value": "smtp.example.com"},
                    {"name": "port", "value": "587"},
                    {"name": "user", "value": "myuser"},
                    {"name": "password", "value": "mypassword123"}  # Plain text!
                ]
            }
        }

        path = write_yaml(bindings_dir / "insecure-smtp.yaml", config)
        content = read_yaml(path)

        issues = validate_smtp_binding(content)
        assert any("password" in issue.lower() for issue in issues), \
            "Should flag plain-text SMTP password"


class TestKafkaBindingValidation:
    """Test Kafka binding security validation."""

    def test_kafka_with_auth_passes(self, bindings_dir):
        """Kafka with authentication configured should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "kafka-binding"},
            "spec": {
                "type": "bindings.kafka",
                "version": "v1",
                "metadata": [
                    {"name": "brokers", "value": "kafka:9092"},
                    {"name": "topics", "value": "my-topic"},
                    {"name": "authType", "value": "password"},
                    {
                        "name": "saslUsername",
                        "secretKeyRef": {"name": "kafka-secrets", "key": "username"}
                    },
                    {
                        "name": "saslPassword",
                        "secretKeyRef": {"name": "kafka-secrets", "key": "password"}
                    }
                ]
            }
        }

        path = write_yaml(bindings_dir / "kafka.yaml", config)
        content = read_yaml(path)

        issues = validate_kafka_binding(content)
        assert len(issues) == 0, f"Valid Kafka should pass: {issues}"

    def test_kafka_without_auth_warns(self, bindings_dir):
        """Kafka without authentication should warn for production."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "kafka-binding"},
            "spec": {
                "type": "bindings.kafka",
                "version": "v1",
                "metadata": [
                    {"name": "brokers", "value": "kafka:9092"},
                    {"name": "topics", "value": "my-topic"},
                    {"name": "authType", "value": "none"}  # No auth!
                ]
            }
        }

        path = write_yaml(bindings_dir / "insecure-kafka.yaml", config)
        content = read_yaml(path)

        issues = validate_kafka_binding(content)
        assert any("auth" in issue.lower() for issue in issues), \
            "Should warn about Kafka without authentication"


class TestHTTPBindingValidation:
    """Test HTTP binding security validation."""

    def test_http_with_https_passes(self, bindings_dir):
        """HTTP binding with HTTPS URL should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "http-api"},
            "spec": {
                "type": "bindings.http",
                "version": "v1",
                "metadata": [
                    {"name": "url", "value": "https://api.example.com/webhook"}
                ]
            }
        }

        path = write_yaml(bindings_dir / "http.yaml", config)
        content = read_yaml(path)

        issues = validate_http_binding(content)
        # HTTPS is fine for production
        https_issues = [i for i in issues if "HTTPS" in i]
        assert len(https_issues) == 0, "HTTPS URL should not warn"

    def test_http_with_http_url_warns_production(self, bindings_dir):
        """HTTP binding with HTTP URL should warn for production."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "http-api"},
            "spec": {
                "type": "bindings.http",
                "version": "v1",
                "metadata": [
                    {"name": "url", "value": "http://api.example.com/webhook"}  # HTTP!
                ]
            }
        }

        path = write_yaml(bindings_dir / "http-insecure.yaml", config)
        content = read_yaml(path)

        issues = validate_http_binding(content, is_production=True)
        assert any("http" in issue.lower() or "https" in issue.lower() for issue in issues), \
            "Should warn about HTTP URL in production"


# Helper validation functions

def validate_database_binding(content: dict) -> list:
    """Validate database binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])

    sensitive_fields = ["connectionString", "url", "password", "masterKey"]

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name in sensitive_fields:
            if "value" in entry and "secretKeyRef" not in entry:
                # Check if value contains password patterns
                if any(pattern in value.lower() for pattern in ["password=", "password:", ":password@"]):
                    issues.append(f"{name} contains credentials and should use secretKeyRef")
                elif name in ["connectionString", "password", "masterKey"]:
                    issues.append(f"{name} should use secretKeyRef for security")

    return issues


def validate_smtp_binding(content: dict) -> list:
    """Validate SMTP binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])

    for entry in metadata:
        name = entry.get("name", "")

        if name == "password":
            if "value" in entry and "secretKeyRef" not in entry:
                issues.append("SMTP password should use secretKeyRef")

    return issues


def validate_kafka_binding(content: dict) -> list:
    """Validate Kafka binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])

    auth_type = None
    has_sasl_password = False

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name == "authType":
            auth_type = value

        if name == "saslPassword":
            has_sasl_password = True
            if "value" in entry and "secretKeyRef" not in entry:
                issues.append("saslPassword should use secretKeyRef")

    if auth_type == "none":
        issues.append("Kafka authType is 'none' - configure authentication for production")

    return issues


def validate_http_binding(content: dict, is_production: bool = False) -> list:
    """Validate HTTP binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name == "url" and value.startswith("http://"):
            if is_production:
                issues.append("HTTP URL should use HTTPS in production")
            # For local development, HTTP is acceptable

    return issues
