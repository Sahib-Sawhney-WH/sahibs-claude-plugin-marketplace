"""
DAPR Health Check Framework

Provides comprehensive health checks for DAPR microservices including:
- Liveness probes (/health)
- Readiness probes (/ready)
- Detailed health status (/health/detailed)
- DAPR sidecar connectivity
- Component health verification

Usage:
    from observability.health_checks import HealthCheckRegistry, setup_health_endpoints

    # Register custom health checks
    registry = HealthCheckRegistry()
    registry.register("database", check_database_connection)

    # Setup FastAPI endpoints
    setup_health_endpoints(app, registry)
"""

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import aiohttp

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthResponse:
    """Aggregated health response."""
    status: HealthStatus
    checks: List[HealthCheckResult]
    version: str = "1.0.0"
    uptime_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp.isoformat(),
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "duration_ms": c.duration_ms,
                    "details": c.details
                }
                for c in self.checks
            ]
        }


HealthCheckFn = Callable[[], Union[HealthCheckResult, bool]]
AsyncHealthCheckFn = Callable[[], "asyncio.Future[Union[HealthCheckResult, bool]]"]


class HealthCheckRegistry:
    """Registry for health checks."""

    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        self._checks: Dict[str, Union[HealthCheckFn, AsyncHealthCheckFn]] = {}
        self._readiness_checks: Dict[str, Union[HealthCheckFn, AsyncHealthCheckFn]] = {}
        self._start_time = time.time()
        self._version = os.getenv("SERVICE_VERSION", "1.0.0")

        # Register default DAPR checks
        self._register_default_checks()

    def _register_default_checks(self):
        """Register default DAPR health checks."""
        self.register("dapr_sidecar", self._check_dapr_sidecar, is_readiness=True)

    def register(
        self,
        name: str,
        check_fn: Union[HealthCheckFn, AsyncHealthCheckFn],
        is_readiness: bool = False
    ):
        """Register a health check function.

        Args:
            name: Unique name for the check
            check_fn: Function that returns HealthCheckResult or bool
            is_readiness: If True, include in readiness checks
        """
        self._checks[name] = check_fn
        if is_readiness:
            self._readiness_checks[name] = check_fn
        logger.info(f"Registered health check: {name} (readiness={is_readiness})")

    def unregister(self, name: str):
        """Remove a health check."""
        self._checks.pop(name, None)
        self._readiness_checks.pop(name, None)

    async def _check_dapr_sidecar(self) -> HealthCheckResult:
        """Check DAPR sidecar connectivity."""
        dapr_host = os.getenv("DAPR_HTTP_ENDPOINT", "http://localhost:3500")
        health_url = f"{dapr_host}/v1.0/healthz"

        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    duration = (time.time() - start) * 1000

                    if resp.status == 200:
                        return HealthCheckResult(
                            name="dapr_sidecar",
                            status=HealthStatus.HEALTHY,
                            message="DAPR sidecar is healthy",
                            duration_ms=duration,
                            details={"endpoint": dapr_host}
                        )
                    elif resp.status == 503:
                        return HealthCheckResult(
                            name="dapr_sidecar",
                            status=HealthStatus.DEGRADED,
                            message="DAPR sidecar is initializing",
                            duration_ms=duration
                        )
                    else:
                        return HealthCheckResult(
                            name="dapr_sidecar",
                            status=HealthStatus.UNHEALTHY,
                            message=f"Unexpected status: {resp.status}",
                            duration_ms=duration
                        )
        except asyncio.TimeoutError:
            return HealthCheckResult(
                name="dapr_sidecar",
                status=HealthStatus.UNHEALTHY,
                message="Timeout connecting to DAPR sidecar",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return HealthCheckResult(
                name="dapr_sidecar",
                status=HealthStatus.UNHEALTHY,
                message=f"Error: {str(e)}",
                duration_ms=(time.time() - start) * 1000
            )

    async def _run_check(
        self,
        name: str,
        check_fn: Union[HealthCheckFn, AsyncHealthCheckFn]
    ) -> HealthCheckResult:
        """Run a single health check."""
        start = time.time()
        try:
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()

            duration = (time.time() - start) * 1000

            if isinstance(result, bool):
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    duration_ms=duration
                )
            elif isinstance(result, HealthCheckResult):
                result.duration_ms = duration
                return result
            else:
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message="Invalid check result type",
                    duration_ms=duration
                )

        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    async def run_liveness_checks(self) -> HealthResponse:
        """Run basic liveness check (is the process running?)."""
        # Liveness is simple - if we can respond, we're live
        uptime = time.time() - self._start_time
        return HealthResponse(
            status=HealthStatus.HEALTHY,
            checks=[],
            version=self._version,
            uptime_seconds=uptime
        )

    async def run_readiness_checks(self) -> HealthResponse:
        """Run readiness checks (can we serve traffic?)."""
        results = await asyncio.gather(*[
            self._run_check(name, fn)
            for name, fn in self._readiness_checks.items()
        ])

        # Determine overall status
        overall = HealthStatus.HEALTHY
        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
                break
            elif result.status == HealthStatus.DEGRADED:
                overall = HealthStatus.DEGRADED

        uptime = time.time() - self._start_time
        return HealthResponse(
            status=overall,
            checks=list(results),
            version=self._version,
            uptime_seconds=uptime
        )

    async def run_all_checks(self) -> HealthResponse:
        """Run all registered health checks."""
        results = await asyncio.gather(*[
            self._run_check(name, fn)
            for name, fn in self._checks.items()
        ])

        # Determine overall status
        overall = HealthStatus.HEALTHY
        for result in results:
            if result.status == HealthStatus.UNHEALTHY:
                overall = HealthStatus.UNHEALTHY
                break
            elif result.status == HealthStatus.DEGRADED and overall == HealthStatus.HEALTHY:
                overall = HealthStatus.DEGRADED

        uptime = time.time() - self._start_time
        return HealthResponse(
            status=overall,
            checks=list(results),
            version=self._version,
            uptime_seconds=uptime
        )


# =============================================================================
# Pre-built Health Check Functions
# =============================================================================

def create_state_store_check(
    store_name: str = "statestore",
    test_key: str = "__health_check__"
) -> AsyncHealthCheckFn:
    """Create a health check for DAPR state store.

    Args:
        store_name: Name of the state store component
        test_key: Key to use for health check
    """
    async def check() -> HealthCheckResult:
        try:
            from dapr.clients import DaprClient

            async with DaprClient() as client:
                # Try to get a non-existent key (should not error)
                await client.get_state(store_name, test_key)

                return HealthCheckResult(
                    name=f"state_store:{store_name}",
                    status=HealthStatus.HEALTHY,
                    details={"store": store_name}
                )
        except Exception as e:
            return HealthCheckResult(
                name=f"state_store:{store_name}",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                details={"store": store_name}
            )

    return check


def create_pubsub_check(
    pubsub_name: str = "pubsub"
) -> AsyncHealthCheckFn:
    """Create a health check for DAPR pub/sub component."""
    async def check() -> HealthCheckResult:
        dapr_host = os.getenv("DAPR_HTTP_ENDPOINT", "http://localhost:3500")
        metadata_url = f"{dapr_host}/v1.0/metadata"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(metadata_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        components = data.get("components", [])

                        # Find pubsub component
                        for comp in components:
                            if comp.get("name") == pubsub_name:
                                return HealthCheckResult(
                                    name=f"pubsub:{pubsub_name}",
                                    status=HealthStatus.HEALTHY,
                                    details={"type": comp.get("type")}
                                )

                        return HealthCheckResult(
                            name=f"pubsub:{pubsub_name}",
                            status=HealthStatus.UNHEALTHY,
                            message=f"Component {pubsub_name} not found"
                        )
                    else:
                        return HealthCheckResult(
                            name=f"pubsub:{pubsub_name}",
                            status=HealthStatus.UNHEALTHY,
                            message=f"Metadata API returned {resp.status}"
                        )
        except Exception as e:
            return HealthCheckResult(
                name=f"pubsub:{pubsub_name}",
                status=HealthStatus.UNHEALTHY,
                message=str(e)
            )

    return check


def create_http_dependency_check(
    name: str,
    url: str,
    expected_status: int = 200,
    timeout_seconds: float = 5.0
) -> AsyncHealthCheckFn:
    """Create a health check for an HTTP dependency."""
    async def check() -> HealthCheckResult:
        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                ) as resp:
                    duration = (time.time() - start) * 1000

                    if resp.status == expected_status:
                        return HealthCheckResult(
                            name=name,
                            status=HealthStatus.HEALTHY,
                            duration_ms=duration,
                            details={"url": url, "status": resp.status}
                        )
                    else:
                        return HealthCheckResult(
                            name=name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"Unexpected status {resp.status}",
                            duration_ms=duration,
                            details={"url": url}
                        )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000,
                details={"url": url}
            )

    return check


def create_database_check(
    name: str,
    connection_string: str,
    query: str = "SELECT 1"
) -> AsyncHealthCheckFn:
    """Create a health check for a database connection.

    Note: Requires appropriate database driver (asyncpg, aiomysql, etc.)
    """
    async def check() -> HealthCheckResult:
        start = time.time()
        try:
            # Try asyncpg for PostgreSQL
            if "postgresql" in connection_string or "postgres" in connection_string:
                import asyncpg
                conn = await asyncpg.connect(connection_string, timeout=5)
                await conn.fetchval(query)
                await conn.close()
            else:
                # Fallback - just check connection string is set
                if not connection_string:
                    raise ValueError("Connection string not configured")

            return HealthCheckResult(
                name=name,
                status=HealthStatus.HEALTHY,
                duration_ms=(time.time() - start) * 1000
            )
        except ImportError:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="Database driver not installed"
            )
        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    return check


# =============================================================================
# FastAPI Integration
# =============================================================================

def setup_health_endpoints(app, registry: HealthCheckRegistry):
    """
    Set up health check endpoints on a FastAPI application.

    Endpoints:
        GET /health - Liveness probe (always returns 200 if running)
        GET /ready - Readiness probe (returns 503 if not ready)
        GET /health/detailed - Full health status with all checks

    Args:
        app: FastAPI application
        registry: HealthCheckRegistry with registered checks
    """
    try:
        from fastapi import Response
        from fastapi.responses import JSONResponse
    except ImportError:
        logger.error("FastAPI not installed - cannot setup health endpoints")
        return

    @app.get("/health", tags=["Health"])
    async def liveness():
        """Liveness probe - is the service running?"""
        response = await registry.run_liveness_checks()
        return {"status": response.status.value}

    @app.get("/ready", tags=["Health"])
    async def readiness(response: Response):
        """Readiness probe - can the service handle requests?"""
        health = await registry.run_readiness_checks()

        if health.status == HealthStatus.UNHEALTHY:
            response.status_code = 503

        return health.to_dict()

    @app.get("/health/detailed", tags=["Health"])
    async def detailed_health(response: Response):
        """Detailed health status with all registered checks."""
        health = await registry.run_all_checks()

        if health.status == HealthStatus.UNHEALTHY:
            response.status_code = 503
        elif health.status == HealthStatus.DEGRADED:
            response.status_code = 200  # Still serving but degraded

        return health.to_dict()

    logger.info("Health endpoints registered: /health, /ready, /health/detailed")


# =============================================================================
# Kubernetes Probe Configuration
# =============================================================================

def get_kubernetes_probe_config() -> Dict[str, Any]:
    """
    Get Kubernetes probe configuration for DAPR service.

    Returns YAML-compatible dict for pod spec.

    Example:
        probes = get_kubernetes_probe_config()
        # Add to your deployment YAML
    """
    return {
        "livenessProbe": {
            "httpGet": {
                "path": "/health",
                "port": 8080
            },
            "initialDelaySeconds": 10,
            "periodSeconds": 15,
            "timeoutSeconds": 5,
            "failureThreshold": 3
        },
        "readinessProbe": {
            "httpGet": {
                "path": "/ready",
                "port": 8080
            },
            "initialDelaySeconds": 5,
            "periodSeconds": 10,
            "timeoutSeconds": 5,
            "failureThreshold": 3
        },
        "startupProbe": {
            "httpGet": {
                "path": "/health",
                "port": 8080
            },
            "initialDelaySeconds": 0,
            "periodSeconds": 5,
            "timeoutSeconds": 5,
            "failureThreshold": 30  # Allow up to 150s for startup
        }
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def main():
        # Create registry
        registry = HealthCheckRegistry(service_name="test-service")

        # Register custom checks
        registry.register(
            "external_api",
            create_http_dependency_check("api", "https://httpbin.org/status/200"),
            is_readiness=True
        )

        # Run checks
        print("Running liveness check...")
        liveness = await registry.run_liveness_checks()
        print(f"Liveness: {liveness.status.value}")

        print("\nRunning readiness checks...")
        readiness = await registry.run_readiness_checks()
        print(f"Readiness: {readiness.status.value}")
        for check in readiness.checks:
            print(f"  - {check.name}: {check.status.value} ({check.duration_ms:.1f}ms)")

        print("\nRunning all checks...")
        detailed = await registry.run_all_checks()
        print(f"Overall: {detailed.status.value}")
        for check in detailed.checks:
            print(f"  - {check.name}: {check.status.value}")
            if check.message:
                print(f"    Message: {check.message}")

    asyncio.run(main())
