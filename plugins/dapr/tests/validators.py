"""
Shared Validation Functions for DAPR Plugin Tests

This module contains validation functions that are used across test files
and can also be imported by hooks for consistent validation logic.
"""

import re
from typing import List, Dict, Any, Optional


# =============================================================================
# Constants
# =============================================================================

# Unified list of field names that should use secretKeyRef
SECRET_FIELD_PATTERNS = [
    "password",
    "secret",
    "key",
    "token",
    "credential",
    "masterKey",
    "accessKey",
    "connectionString",
    "apiKey",
    "clientId",
    "clientSecret",
]

# Valid component name pattern
COMPONENT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


# =============================================================================
# Middleware Validators
# =============================================================================

def validate_oauth2(metadata: List[Dict[str, Any]]) -> List[str]:
    """Validate OAuth2 middleware configuration."""
    issues = []
    metadata_dict = {m.get("name"): m for m in metadata}

    for url_field in ["authorizationURL", "tokenURL"]:
        if url_field in metadata_dict:
            value = metadata_dict[url_field].get("value", "")
            if value and value.startswith("http://"):
                issues.append(f"{url_field} should use HTTPS, not HTTP")

    for secret_field in ["clientId", "clientSecret"]:
        if secret_field in metadata_dict:
            entry = metadata_dict[secret_field]
            if "value" in entry and "secretKeyRef" not in entry:
                issues.append(f"{secret_field} should use secretKeyRef, not plain value")

    return issues


def validate_bearer(metadata: List[Dict[str, Any]]) -> List[str]:
    """Validate Bearer token middleware configuration."""
    issues = []
    metadata_dict = {m.get("name"): m for m in metadata}

    if "issuerURL" in metadata_dict:
        value = metadata_dict["issuerURL"].get("value", "")
        if value and value.startswith("http://"):
            issues.append("issuerURL should use HTTPS, not HTTP")

    if "signingKey" in metadata_dict:
        entry = metadata_dict["signingKey"]
        if "value" in entry and "secretKeyRef" not in entry:
            issues.append("signingKey should use secretKeyRef, not plain value")

    return issues


def validate_opa(metadata: List[Dict[str, Any]]) -> List[str]:
    """Validate OPA middleware configuration."""
    issues = []
    metadata_dict = {m.get("name"): m for m in metadata}

    if "opaURL" in metadata_dict:
        value = metadata_dict["opaURL"].get("value", "")
        if value and value.startswith("http://"):
            issues.append("opaURL should use HTTPS in production")

    return issues


def validate_rate_limit(metadata: List[Dict[str, Any]]) -> List[str]:
    """Validate rate limiting middleware configuration."""
    issues = []
    metadata_dict = {m.get("name"): m for m in metadata}

    if "maxRequestsPerSecond" in metadata_dict:
        try:
            value = int(metadata_dict["maxRequestsPerSecond"].get("value", 0))
            if value <= 0:
                issues.append("maxRequestsPerSecond must be positive")
        except (ValueError, TypeError):
            issues.append("maxRequestsPerSecond must be a valid integer")

    return issues


# =============================================================================
# Binding Validators
# =============================================================================

def validate_database_binding(content: Dict[str, Any]) -> List[str]:
    """Validate database binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])
    metadata_dict = {m.get("name"): m for m in metadata}

    secret_fields = ["connectionString", "url", "password", "masterKey"]
    for field in secret_fields:
        if field in metadata_dict:
            entry = metadata_dict[field]
            if "value" in entry and "secretKeyRef" not in entry:
                value = entry.get("value", "")
                if value and not value.startswith("$") and not value.startswith("{{"):
                    issues.append(f"{field} should use secretKeyRef, not plain value")

    return issues


def validate_smtp_binding(content: Dict[str, Any]) -> List[str]:
    """Validate SMTP binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])
    metadata_dict = {m.get("name"): m for m in metadata}

    if "password" in metadata_dict:
        entry = metadata_dict["password"]
        if "value" in entry and "secretKeyRef" not in entry:
            issues.append("SMTP password should use secretKeyRef")

    return issues


def validate_kafka_binding(content: Dict[str, Any]) -> List[str]:
    """Validate Kafka binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])
    metadata_dict = {m.get("name"): m for m in metadata}

    for field in ["saslUsername", "saslPassword"]:
        if field in metadata_dict:
            entry = metadata_dict[field]
            if "value" in entry and "secretKeyRef" not in entry:
                issues.append(f"Kafka {field} should use secretKeyRef")

    return issues


def validate_http_binding(content: Dict[str, Any], is_production: bool = False) -> List[str]:
    """Validate HTTP binding configuration."""
    issues = []
    metadata = content.get("spec", {}).get("metadata", [])
    metadata_dict = {m.get("name"): m for m in metadata}

    if "url" in metadata_dict:
        value = metadata_dict["url"].get("value", "")
        if is_production and value and value.startswith("http://"):
            issues.append("HTTP binding URL should use HTTPS in production")

    if "authToken" in metadata_dict:
        entry = metadata_dict["authToken"]
        if "value" in entry and "secretKeyRef" not in entry:
            issues.append("HTTP authToken should use secretKeyRef")

    return issues


# =============================================================================
# Agent Validators
# =============================================================================

def validate_tool_file(content: str) -> List[str]:
    """Validate agent tool file for best practices."""
    issues = []

    if "@tool" not in content:
        issues.append("Tool file should contain @tool decorated functions")

    return issues


def validate_agent_file(content: str) -> List[str]:
    """Validate agent configuration file for best practices."""
    issues = []

    if "Agent(" not in content and "AssistantAgent(" not in content:
        issues.append("File should contain an Agent or AssistantAgent definition")

    if "instructions=" not in content:
        issues.append("Agent should have instructions defined")

    return issues


def validate_async_patterns(content: str) -> List[str]:
    """Validate async patterns in agent code."""
    issues = []

    if "async def" in content:
        if "await" not in content:
            issues.append("Async functions should use await for async operations")

    return issues


def validate_pydantic_usage(content: str) -> List[str]:
    """Validate Pydantic model usage in agent tools."""
    issues = []

    if "BaseModel" in content and "from pydantic" not in content:
        issues.append("Pydantic BaseModel used but pydantic not imported")

    return issues


# =============================================================================
# Component Validators
# =============================================================================

def validate_component_name(name: str) -> List[str]:
    """Validate DAPR component name."""
    issues = []

    if not name:
        issues.append("Component name is required")
    elif not COMPONENT_NAME_PATTERN.match(name):
        issues.append("Component name must be lowercase alphanumeric with hyphens")

    return issues


def validate_secret_handling(metadata: List[Dict[str, Any]]) -> List[str]:
    """Validate that secrets are handled securely."""
    issues = []

    for entry in metadata:
        name = entry.get("name", "").lower()
        has_value = "value" in entry
        has_secret_ref = "secretKeyRef" in entry

        is_secret_field = any(pattern in name for pattern in SECRET_FIELD_PATTERNS)

        if is_secret_field and has_value and not has_secret_ref:
            value = entry.get("value", "")
            if value and not value.startswith("$") and not value.startswith("{{"):
                issues.append(f"Field '{entry.get('name')}' appears to be a secret - use secretKeyRef")

    return issues
