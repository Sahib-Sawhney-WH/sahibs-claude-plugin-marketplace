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


# =============================================================================
# Cross-Service Dependency Validators (New for Robustness Enhancement)
# =============================================================================

def validate_service_dependencies(
    dapr_yaml: Dict[str, Any],
    components: List[Dict[str, Any]]
) -> List[str]:
    """
    Validate cross-service dependencies between apps and components.

    Checks:
    - All component names referenced in app configs exist
    - All app IDs in component scopes exist in dapr.yaml
    - Resiliency targets reference existing components/apps
    """
    issues = []

    # Extract app IDs from dapr.yaml
    app_ids = set()
    for app in dapr_yaml.get("apps", []):
        app_id = app.get("appId")
        if app_id:
            app_ids.add(app_id)

    # Extract component names
    component_names = set()
    for comp in components:
        name = comp.get("metadata", {}).get("name")
        if name:
            component_names.add(name)

    # Check component scopes reference valid apps
    for comp in components:
        comp_name = comp.get("metadata", {}).get("name", "unknown")
        scopes = comp.get("scopes", [])

        for scope in scopes:
            if scope not in app_ids:
                issues.append(
                    f"Component '{comp_name}' references non-existent app '{scope}' in scopes"
                )

    return issues


def detect_circular_dependencies(components: List[Dict[str, Any]]) -> List[str]:
    """
    Detect circular dependencies between components.

    Builds a dependency graph from secretKeyRef and auth.secretStore references,
    then uses DFS to detect cycles.
    """
    issues = []

    # Build component name set
    component_names = {
        comp.get("metadata", {}).get("name")
        for comp in components
        if comp.get("metadata", {}).get("name")
    }

    # Build dependency graph
    graph: Dict[str, List[str]] = {}

    for comp in components:
        name = comp.get("metadata", {}).get("name")
        if not name:
            continue

        graph[name] = []

        # Check secretKeyRef dependencies
        for meta in comp.get("spec", {}).get("metadata", []):
            if "secretKeyRef" in meta:
                ref_name = meta["secretKeyRef"].get("name", "")
                # secretKeyRef.name might be "secretstore/key" format or just key name
                store_name = ref_name.split("/")[0] if "/" in ref_name else ref_name
                if store_name in component_names and store_name != name:
                    graph[name].append(store_name)

        # Check auth.secretStore dependency
        auth = comp.get("auth", {})
        secret_store = auth.get("secretStore")
        if secret_store and secret_store in component_names and secret_store != name:
            graph[name].append(secret_store)

    # DFS to detect cycles
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: str) -> Optional[List[str]]:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                result = dfs(neighbor)
                if result:
                    return result
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]

        path.pop()
        rec_stack.remove(node)
        return None

    for node in graph:
        if node not in visited:
            cycle = dfs(node)
            if cycle:
                issues.append(f"Circular dependency detected: {' -> '.join(cycle)}")

    return issues


def validate_secret_references(
    components: List[Dict[str, Any]],
    secret_stores: Optional[List[Dict[str, Any]]] = None
) -> List[str]:
    """
    Validate that secretKeyRef references point to existing secret stores.

    Args:
        components: List of all component configurations
        secret_stores: Optional list of secret store components (auto-detected if None)
    """
    issues = []

    # Auto-detect secret stores if not provided
    if secret_stores is None:
        secret_stores = [
            comp for comp in components
            if comp.get("spec", {}).get("type", "").startswith("secretstores.")
        ]

    secret_store_names = {
        s.get("metadata", {}).get("name")
        for s in secret_stores
        if s.get("metadata", {}).get("name")
    }

    for comp in components:
        comp_name = comp.get("metadata", {}).get("name", "unknown")

        for meta in comp.get("spec", {}).get("metadata", []):
            if "secretKeyRef" in meta:
                ref = meta["secretKeyRef"]
                store_name = ref.get("name", "")

                if store_name and store_name not in secret_store_names:
                    issues.append(
                        f"Component '{comp_name}' references non-existent "
                        f"secret store '{store_name}' in field '{meta.get('name')}'"
                    )

        # Also check auth.secretStore
        auth = comp.get("auth", {})
        secret_store = auth.get("secretStore")
        if secret_store and secret_store not in secret_store_names:
            issues.append(
                f"Component '{comp_name}' references non-existent "
                f"secret store '{secret_store}' in auth.secretStore"
            )

    return issues


# =============================================================================
# Resource Quota Validators
# =============================================================================

# Platform-specific resource limits
AZURE_CONTAINER_APPS_LIMITS = {
    "cpu_min": 0.25,
    "cpu_max": 4.0,
    "memory_min_gi": 0.5,
    "memory_max_gi": 8.0,
    "max_replicas": 300,
}

KUBERNETES_DEFAULT_LIMITS = {
    "cpu_max": 8.0,
    "memory_max_gi": 32.0,
    "max_replicas": 1000,
}


def parse_memory(memory_str: str) -> float:
    """Parse memory string like '1Gi', '512Mi' to GiB."""
    if not memory_str:
        return 0.0

    memory_str = memory_str.strip()
    if memory_str.endswith("Gi"):
        return float(memory_str[:-2])
    elif memory_str.endswith("Mi"):
        return float(memory_str[:-2]) / 1024
    elif memory_str.endswith("Ki"):
        return float(memory_str[:-2]) / (1024 * 1024)
    elif memory_str.endswith("G"):
        return float(memory_str[:-1])
    elif memory_str.endswith("M"):
        return float(memory_str[:-1]) / 1024
    else:
        try:
            return float(memory_str)
        except ValueError:
            return 0.0


def validate_resource_quotas(
    dapr_yaml: Dict[str, Any],
    deployment_target: str = "container-apps"
) -> List[str]:
    """
    Validate resource quotas are within platform limits.

    Args:
        dapr_yaml: The dapr.yaml configuration
        deployment_target: "container-apps" or "kubernetes"
    """
    issues = []

    limits = (
        AZURE_CONTAINER_APPS_LIMITS
        if deployment_target == "container-apps"
        else KUBERNETES_DEFAULT_LIMITS
    )

    for app in dapr_yaml.get("apps", []):
        app_id = app.get("appId", "unknown")
        resources = app.get("resources", {})

        # Check CPU
        cpu = resources.get("cpu")
        if cpu:
            try:
                cpu_val = float(cpu)
                if cpu_val > limits.get("cpu_max", float("inf")):
                    issues.append(
                        f"App '{app_id}' CPU ({cpu_val}) exceeds platform limit ({limits['cpu_max']})"
                    )
            except ValueError:
                pass

        # Check memory
        memory = resources.get("memory", "")
        if memory:
            memory_val = parse_memory(memory)
            if memory_val > limits.get("memory_max_gi", float("inf")):
                issues.append(
                    f"App '{app_id}' memory ({memory}) exceeds platform limit ({limits['memory_max_gi']}Gi)"
                )

        # Check replica count
        scale = app.get("scale", {})
        max_replicas = scale.get("maxReplicas", 10)
        if max_replicas > limits.get("max_replicas", float("inf")):
            issues.append(
                f"App '{app_id}' maxReplicas ({max_replicas}) exceeds platform limit"
            )

    return issues


# =============================================================================
# Port Conflict Validators
# =============================================================================

# Reserved ports for DAPR and common services
RESERVED_PORTS = {
    3500,   # DAPR HTTP API
    50001,  # DAPR gRPC API
    9090,   # DAPR metrics
    8080,   # Common HTTP
    8443,   # Common HTTPS
}


def validate_port_conflicts(dapr_yaml: Dict[str, Any]) -> List[str]:
    """
    Detect port conflicts between apps and DAPR sidecars.

    Checks:
    - No duplicate appPort values across apps
    - No conflict between appPort and DAPR reserved ports
    """
    issues = []

    port_usage: Dict[int, List[str]] = {}

    for app in dapr_yaml.get("apps", []):
        app_id = app.get("appId", "unknown")
        app_port = app.get("appPort")
        dapr_http_port = app.get("daprHTTPPort", 3500)
        dapr_grpc_port = app.get("daprGRPCPort", 50001)

        # Track app port usage
        if app_port:
            try:
                port = int(app_port)
                if port in port_usage:
                    port_usage[port].append(app_id)
                else:
                    port_usage[port] = [app_id]

                # Check reserved ports
                if port in RESERVED_PORTS:
                    issues.append(
                        f"App '{app_id}' uses reserved port {port}"
                    )
            except ValueError:
                pass

        # Check custom DAPR ports for conflicts
        for port, port_type in [
            (dapr_http_port, "daprHTTPPort"),
            (dapr_grpc_port, "daprGRPCPort")
        ]:
            if port != 3500 and port != 50001:  # Only check custom ports
                if port in port_usage:
                    issues.append(
                        f"App '{app_id}' {port_type} ({port}) conflicts with another app's port"
                    )

    # Check for duplicate ports
    for port, apps in port_usage.items():
        if len(apps) > 1:
            issues.append(
                f"Port {port} used by multiple apps: {', '.join(apps)}"
            )

    return issues


# =============================================================================
# Azure Managed Identity Validators
# =============================================================================

AZURE_MI_COMPONENT_TYPES = [
    "state.azure.cosmosdb",
    "state.azure.tablestorage",
    "state.azure.blobstorage",
    "pubsub.azure.servicebus.topics",
    "pubsub.azure.servicebus.queues",
    "pubsub.azure.eventhubs",
    "bindings.azure.blobstorage",
    "bindings.azure.eventgrid",
    "bindings.azure.eventhubs",
    "bindings.azure.signalr",
    "bindings.azure.queues",
    "secretstores.azure.keyvault",
]


def validate_azure_managed_identity(
    components: List[Dict[str, Any]],
    require_mi: bool = False
) -> List[str]:
    """
    Validate Azure managed identity configuration.

    Checks:
    - azureClientId is specified for Azure components using managed identity
    - No mix of managed identity and connection string auth
    - Recommends managed identity over connection strings

    Args:
        components: List of component configurations
        require_mi: If True, require managed identity for all Azure components
    """
    issues = []

    for comp in components:
        comp_type = comp.get("spec", {}).get("type", "")
        comp_name = comp.get("metadata", {}).get("name", "unknown")

        if comp_type not in AZURE_MI_COMPONENT_TYPES:
            continue

        metadata = {
            m.get("name"): m
            for m in comp.get("spec", {}).get("metadata", [])
        }

        has_client_id = "azureClientId" in metadata
        has_connection_string = "connectionString" in metadata
        has_account_key = "accountKey" in metadata or "masterKey" in metadata

        # Check for mixed auth (potential misconfiguration)
        if has_client_id and (has_connection_string or has_account_key):
            issues.append(
                f"Component '{comp_name}' has both managed identity (azureClientId) "
                f"and connection string/key. This may cause authentication ambiguity."
            )

        # Recommend managed identity over connection strings
        if (has_connection_string or has_account_key) and not has_client_id:
            if require_mi:
                issues.append(
                    f"Component '{comp_name}' ({comp_type}) requires managed identity. "
                    f"Add azureClientId and remove connection string/key."
                )
            else:
                issues.append(
                    f"Component '{comp_name}' ({comp_type}) uses connection string/key. "
                    f"Consider using managed identity (azureClientId) for enhanced security."
                )

    return issues


# =============================================================================
# mTLS Configuration Validators
# =============================================================================

def parse_duration(duration_str: str) -> int:
    """Parse duration string like '24h', '30m', '60s' to seconds."""
    if not duration_str:
        return 0

    duration_str = duration_str.strip().lower()

    if duration_str.endswith("h"):
        return int(duration_str[:-1]) * 3600
    elif duration_str.endswith("m"):
        return int(duration_str[:-1]) * 60
    elif duration_str.endswith("s"):
        return int(duration_str[:-1])
    else:
        try:
            return int(duration_str)
        except ValueError:
            return 0


def validate_mtls_configuration(
    configuration: Optional[Dict[str, Any]] = None,
    is_production: bool = True
) -> List[str]:
    """
    Validate mTLS configuration for sidecar communication.

    Args:
        configuration: DAPR Configuration resource
        is_production: Whether this is a production environment
    """
    issues = []

    if configuration is None:
        if is_production:
            issues.append(
                "No Configuration resource found. mTLS may not be enabled "
                "for sidecar communication in production."
            )
        return issues

    mtls = configuration.get("spec", {}).get("mtls", {})

    if is_production:
        # Check mTLS is enabled
        if not mtls.get("enabled", False):
            issues.append(
                "CRITICAL: mTLS is disabled. Enable mTLS for secure "
                "sidecar-to-sidecar communication in production."
            )

        # Check cert TTL (should be 24h or less)
        cert_ttl = mtls.get("workloadCertTTL", "24h")
        if parse_duration(cert_ttl) > 86400:  # 24 hours in seconds
            issues.append(
                f"workloadCertTTL ({cert_ttl}) is longer than recommended 24h. "
                f"Shorter TTL reduces exposure window if certificates are compromised."
            )

        # Check clock skew allowance (should be 15m or less)
        clock_skew = mtls.get("allowedClockSkew", "15m")
        if parse_duration(clock_skew) > 900:  # 15 minutes in seconds
            issues.append(
                f"allowedClockSkew ({clock_skew}) may be too lenient. "
                f"Consider reducing to 5-15 minutes for tighter security."
            )

    return issues


# =============================================================================
# Resiliency Policy Validators
# =============================================================================

def validate_resiliency_policy(
    policy: Dict[str, Any],
    policy_type: str
) -> List[str]:
    """
    Validate resiliency policy configuration.

    Args:
        policy: The policy configuration
        policy_type: "retry", "timeout", or "circuitBreaker"
    """
    issues = []

    if policy_type == "retry":
        max_retries = policy.get("maxRetries", 3)
        if max_retries > 20:
            issues.append(
                f"Excessive maxRetries ({max_retries}). "
                f"Consider using circuit breaker for persistent failures."
            )

        duration = policy.get("duration", "")
        if duration and parse_duration(duration) < 100:  # Less than 100ms
            issues.append(
                f"Very short retry duration ({duration}). "
                f"This may cause retry storms."
            )

    elif policy_type == "timeout":
        timeout = policy.get("responseTimeoutInSeconds", 0)
        if timeout == 0:
            issues.append("Timeout not configured. Operations may hang indefinitely.")
        elif timeout > 300:  # 5 minutes
            issues.append(
                f"Very long timeout ({timeout}s). "
                f"Consider shorter timeout with proper retry handling."
            )

    elif policy_type == "circuitBreaker":
        consecutive_errors = policy.get("consecutiveErrors", 5)
        if consecutive_errors < 2:
            issues.append(
                f"consecutiveErrors ({consecutive_errors}) is too low. "
                f"Circuit may trip on transient errors."
            )

        timeout = policy.get("timeoutInSeconds", 0)
        if timeout == 0:
            issues.append(
                "Circuit breaker timeout not set. Circuit will never reset."
            )

        # Validate trip expression if present
        trip = policy.get("trip", "")
        if trip:
            valid_patterns = [
                "consecutiveFailures",
                "responseTime",
                "errorRate"
            ]
            if not any(p in trip for p in valid_patterns):
                issues.append(
                    f"Circuit breaker trip condition '{trip}' may be invalid. "
                    f"Use consecutiveFailures, responseTime, or errorRate."
                )

    return issues
