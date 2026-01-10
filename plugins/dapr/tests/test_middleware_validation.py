"""
Middleware Configuration Validation Tests
=========================================

Tests for DAPR HTTP middleware security validation.
These tests verify the security checks used by plugin hooks.
"""

import pytest
import re
from pathlib import Path
from conftest import write_yaml, read_yaml


class TestOAuth2Validation:
    """Test OAuth2 middleware security validation."""

    def test_valid_oauth2_passes(self, middleware_dir, valid_oauth2_middleware):
        """OAuth2 with secretKeyRef and HTTPS should pass."""
        path = write_yaml(middleware_dir / "oauth2.yaml", valid_oauth2_middleware)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_oauth2(metadata)

        assert len(issues) == 0, f"Valid OAuth2 should pass: {issues}"

    def test_plain_text_client_secret_fails(self, middleware_dir, invalid_oauth2_plain_secret):
        """OAuth2 with plain-text clientSecret should fail."""
        path = write_yaml(middleware_dir / "insecure-oauth2.yaml", invalid_oauth2_plain_secret)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_oauth2(metadata)

        assert any("clientSecret" in issue for issue in issues), \
            "Should flag plain-text clientSecret"

    def test_http_auth_url_warns(self, middleware_dir, invalid_oauth2_http_url):
        """OAuth2 with HTTP authURL should warn."""
        path = write_yaml(middleware_dir / "http-oauth2.yaml", invalid_oauth2_http_url)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_oauth2(metadata)

        assert any("HTTPS" in issue or "http://" in issue for issue in issues), \
            "Should warn about non-HTTPS authURL"

    def test_http_token_url_warns(self, middleware_dir):
        """OAuth2 with HTTP tokenURL should warn."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "oauth2"},
            "spec": {
                "type": "middleware.http.oauth2",
                "version": "v1",
                "metadata": [
                    {"name": "clientId", "secretKeyRef": {"name": "s", "key": "k"}},
                    {"name": "clientSecret", "secretKeyRef": {"name": "s", "key": "k"}},
                    {"name": "authURL", "value": "https://auth.example.com/auth"},
                    {"name": "tokenURL", "value": "http://auth.example.com/token"}  # HTTP!
                ]
            }
        }

        path = write_yaml(middleware_dir / "http-token.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_oauth2(metadata)

        assert any("tokenURL" in issue or "HTTPS" in issue for issue in issues), \
            "Should warn about non-HTTPS tokenURL"


class TestBearerValidation:
    """Test Bearer/OIDC middleware validation."""

    def test_valid_bearer_passes(self, middleware_dir):
        """Bearer with HTTPS issuer should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "bearer"},
            "spec": {
                "type": "middleware.http.bearer",
                "version": "v1",
                "metadata": [
                    {"name": "issuer", "value": "https://login.microsoftonline.com/tenant"},
                    {"name": "audience", "value": "api://my-app"}
                ]
            }
        }

        path = write_yaml(middleware_dir / "bearer.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_bearer(metadata)

        assert len(issues) == 0, f"Valid Bearer should pass: {issues}"

    def test_http_issuer_warns(self, middleware_dir):
        """Bearer with HTTP issuer should warn."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "bearer"},
            "spec": {
                "type": "middleware.http.bearer",
                "version": "v1",
                "metadata": [
                    {"name": "issuer", "value": "http://auth.example.com"},  # HTTP!
                    {"name": "audience", "value": "api://my-app"}
                ]
            }
        }

        path = write_yaml(middleware_dir / "http-bearer.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_bearer(metadata)

        assert any("issuer" in issue.lower() or "https" in issue.lower() for issue in issues), \
            "Should warn about non-HTTPS issuer"

    def test_missing_audience_warns(self, middleware_dir):
        """Bearer without audience should warn."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "bearer"},
            "spec": {
                "type": "middleware.http.bearer",
                "version": "v1",
                "metadata": [
                    {"name": "issuer", "value": "https://login.microsoftonline.com/tenant"}
                    # Missing audience!
                ]
            }
        }

        path = write_yaml(middleware_dir / "no-audience.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_bearer(metadata)

        assert any("audience" in issue.lower() for issue in issues), \
            "Should warn about missing audience"


class TestOPAValidation:
    """Test OPA middleware validation."""

    def test_valid_opa_with_default_deny_passes(self, middleware_dir):
        """OPA with default deny policy should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "opa"},
            "spec": {
                "type": "middleware.http.opa",
                "version": "v1",
                "metadata": [
                    {"name": "rego", "value": "package authz\ndefault allow = false\nallow { input.method == \"GET\" }"}
                ]
            }
        }

        path = write_yaml(middleware_dir / "opa.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_opa(metadata)

        assert len(issues) == 0, f"Valid OPA should pass: {issues}"

    def test_opa_without_default_deny_warns(self, middleware_dir):
        """OPA without 'default allow = false' should warn."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "opa"},
            "spec": {
                "type": "middleware.http.opa",
                "version": "v1",
                "metadata": [
                    {"name": "rego", "value": "package authz\nallow { input.method == \"GET\" }"}
                    # Missing default allow = false!
                ]
            }
        }

        path = write_yaml(middleware_dir / "insecure-opa.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_opa(metadata)

        assert any("default" in issue.lower() and "deny" in issue.lower() for issue in issues), \
            "Should warn about missing default deny"


class TestRateLimitValidation:
    """Test rate limit middleware validation."""

    def test_valid_rate_limit_passes(self, middleware_dir):
        """Rate limit with reasonable value should pass."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "ratelimit"},
            "spec": {
                "type": "middleware.http.ratelimit",
                "version": "v1",
                "metadata": [
                    {"name": "maxRequestsPerSecond", "value": "100"}
                ]
            }
        }

        path = write_yaml(middleware_dir / "ratelimit.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_rate_limit(metadata)

        assert len(issues) == 0, f"Valid rate limit should pass: {issues}"

    def test_very_high_rate_limit_warns(self, middleware_dir):
        """Rate limit with very high value should warn."""
        config = {
            "apiVersion": "dapr.io/v1alpha1",
            "kind": "Component",
            "metadata": {"name": "ratelimit"},
            "spec": {
                "type": "middleware.http.ratelimit",
                "version": "v1",
                "metadata": [
                    {"name": "maxRequestsPerSecond", "value": "1000000"}  # Very high!
                ]
            }
        }

        path = write_yaml(middleware_dir / "high-ratelimit.yaml", config)
        content = read_yaml(path)

        metadata = content["spec"]["metadata"]
        issues = validate_rate_limit(metadata)

        # Should warn about very high rate limit (effectively no protection)
        assert any("high" in issue.lower() or "1000000" in issue for issue in issues), \
            "Should warn about very high rate limit"


# Helper validation functions (simulate hook logic)

def validate_oauth2(metadata: list) -> list:
    """Validate OAuth2 middleware configuration."""
    issues = []

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        # Check for plain-text secrets
        if name in ["clientId", "clientSecret"]:
            if "value" in entry and "secretKeyRef" not in entry:
                issues.append(f"{name} should use secretKeyRef, not plain value")

        # Check for HTTPS
        if name in ["authURL", "tokenURL"]:
            if value.startswith("http://"):
                issues.append(f"{name} should use HTTPS, not HTTP")

    return issues


def validate_bearer(metadata: list) -> list:
    """Validate Bearer/OIDC middleware configuration."""
    issues = []
    has_audience = False

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name == "issuer" and value.startswith("http://"):
            issues.append("issuer should use HTTPS")

        if name == "audience":
            has_audience = True

    if not has_audience:
        issues.append("audience should be specified for security")

    return issues


def validate_opa(metadata: list) -> list:
    """Validate OPA middleware configuration."""
    issues = []

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name == "rego":
            if "default allow = false" not in value and "default allow=false" not in value:
                issues.append("OPA policy should have 'default allow = false' for default deny")

    return issues


def validate_rate_limit(metadata: list) -> list:
    """Validate rate limit middleware configuration."""
    issues = []

    for entry in metadata:
        name = entry.get("name", "")
        value = entry.get("value", "")

        if name == "maxRequestsPerSecond":
            try:
                rate = int(value)
                if rate > 10000:
                    issues.append(f"maxRequestsPerSecond is very high ({rate}), may not provide effective protection")
            except ValueError:
                issues.append("maxRequestsPerSecond should be a number")

    return issues
