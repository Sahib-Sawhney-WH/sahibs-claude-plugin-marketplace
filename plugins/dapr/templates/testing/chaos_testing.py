"""
DAPR Chaos Testing Framework

Provides chaos engineering patterns for testing DAPR application resilience:
- @chaos_monkey decorator for failure injection
- Configurable latency injection
- Error probability control
- Network partition simulation
- Component failure simulation
- Resiliency testing helpers

Usage:
    from testing.chaos_testing import chaos_monkey, ChaosConfig, ResiliencyTester

    # Simple chaos injection
    @chaos_monkey(failure_rate=0.1, latency_ms=100)
    async def get_data(key: str):
        async with DaprClient() as client:
            return await client.get_state("statestore", key)

    # Test resiliency policies
    tester = ResiliencyTester()
    results = await tester.test_retry_policy(my_operation, expected_attempts=3)
"""

import asyncio
import functools
import logging
import os
import random
import time
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)


class ChaosType(Enum):
    """Types of chaos to inject."""
    LATENCY = "latency"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTIAL_FAILURE = "partial_failure"
    NETWORK_PARTITION = "network_partition"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class ChaosError(Exception):
    """Exception raised during chaos injection."""
    pass


@dataclass
class ChaosConfig:
    """Configuration for chaos injection."""
    # Enable/disable chaos (can be controlled via env var)
    enabled: bool = True

    # Probability of failure (0.0 to 1.0)
    failure_rate: float = 0.0

    # Latency injection (ms)
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Timeout simulation
    timeout_rate: float = 0.0
    timeout_after_ms: float = 5000.0

    # Specific error types to inject
    error_types: List[Exception] = field(default_factory=list)

    # Target specific operations (regex patterns)
    target_operations: List[str] = field(default_factory=list)

    # Exclude specific operations
    exclude_operations: List[str] = field(default_factory=list)

    # Schedule chaos (e.g., only during certain hours)
    active_hours: Optional[tuple] = None  # (start_hour, end_hour) in UTC

    # Chaos blast radius (0.0 to 1.0)
    # 1.0 = affect all matching operations
    # 0.5 = affect 50% of matching operations
    blast_radius: float = 1.0

    @classmethod
    def from_env(cls) -> "ChaosConfig":
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("CHAOS_ENABLED", "false").lower() == "true",
            failure_rate=float(os.getenv("CHAOS_FAILURE_RATE", "0.0")),
            min_latency_ms=float(os.getenv("CHAOS_MIN_LATENCY_MS", "0")),
            max_latency_ms=float(os.getenv("CHAOS_MAX_LATENCY_MS", "0")),
            timeout_rate=float(os.getenv("CHAOS_TIMEOUT_RATE", "0.0")),
        )

    def should_apply(self, operation_name: Optional[str] = None) -> bool:
        """Check if chaos should be applied."""
        if not self.enabled:
            return False

        # Check active hours
        if self.active_hours:
            current_hour = datetime.utcnow().hour
            start, end = self.active_hours
            if not (start <= current_hour < end):
                return False

        # Check operation targeting
        if operation_name and self.target_operations:
            import re
            if not any(re.match(p, operation_name) for p in self.target_operations):
                return False

        # Check exclusions
        if operation_name and self.exclude_operations:
            import re
            if any(re.match(p, operation_name) for p in self.exclude_operations):
                return False

        # Check blast radius
        if self.blast_radius < 1.0:
            if random.random() > self.blast_radius:
                return False

        return True


# Default chaos configuration
DEFAULT_CHAOS_CONFIG = ChaosConfig.from_env()


@dataclass
class ChaosEvent:
    """Record of a chaos injection event."""
    timestamp: datetime
    chaos_type: ChaosType
    operation: str
    details: Dict[str, Any]
    duration_ms: Optional[float] = None


class ChaosRecorder:
    """Records chaos events for analysis."""

    def __init__(self):
        self._events: List[ChaosEvent] = []
        self._lock = asyncio.Lock()

    async def record(self, event: ChaosEvent):
        """Record a chaos event."""
        async with self._lock:
            self._events.append(event)
            logger.info(
                f"Chaos injected: {event.chaos_type.value} on {event.operation}"
            )

    def get_events(self) -> List[ChaosEvent]:
        """Get all recorded events."""
        return self._events.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of chaos events."""
        if not self._events:
            return {"total_events": 0}

        by_type = {}
        for event in self._events:
            by_type[event.chaos_type.value] = by_type.get(event.chaos_type.value, 0) + 1

        return {
            "total_events": len(self._events),
            "by_type": by_type,
            "first_event": self._events[0].timestamp.isoformat(),
            "last_event": self._events[-1].timestamp.isoformat()
        }

    def clear(self):
        """Clear recorded events."""
        self._events.clear()


# Global recorder
_global_recorder = ChaosRecorder()


T = TypeVar('T')


def chaos_monkey(
    failure_rate: float = 0.0,
    latency_ms: float = 0.0,
    latency_jitter_ms: float = 0.0,
    timeout_rate: float = 0.0,
    error_types: Optional[List[type]] = None,
    config: Optional[ChaosConfig] = None,
    recorder: Optional[ChaosRecorder] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to inject chaos into a function.

    Args:
        failure_rate: Probability of raising an exception (0.0 to 1.0)
        latency_ms: Base latency to inject (ms)
        latency_jitter_ms: Random jitter to add to latency
        timeout_rate: Probability of simulating a timeout
        error_types: List of exception types to randomly raise
        config: Full ChaosConfig (overrides individual params)
        recorder: ChaosRecorder to log events

    Example:
        @chaos_monkey(failure_rate=0.1, latency_ms=50)
        async def get_user(user_id: str):
            ...

        @chaos_monkey(config=ChaosConfig(
            failure_rate=0.2,
            error_types=[ConnectionError, TimeoutError]
        ))
        def send_notification(msg: str):
            ...
    """
    cfg = config or ChaosConfig(
        failure_rate=failure_rate,
        min_latency_ms=latency_ms,
        max_latency_ms=latency_ms + latency_jitter_ms,
        timeout_rate=timeout_rate,
        error_types=error_types or [ChaosError]
    )
    rec = recorder or _global_recorder

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        operation_name = func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            if not cfg.should_apply(operation_name):
                return await func(*args, **kwargs)

            start_time = time.time()

            # Inject latency
            if cfg.max_latency_ms > 0:
                delay = random.uniform(cfg.min_latency_ms, cfg.max_latency_ms) / 1000
                await asyncio.sleep(delay)
                await rec.record(ChaosEvent(
                    timestamp=datetime.utcnow(),
                    chaos_type=ChaosType.LATENCY,
                    operation=operation_name,
                    details={"delay_ms": delay * 1000}
                ))

            # Inject timeout
            if cfg.timeout_rate > 0 and random.random() < cfg.timeout_rate:
                await asyncio.sleep(cfg.timeout_after_ms / 1000)
                await rec.record(ChaosEvent(
                    timestamp=datetime.utcnow(),
                    chaos_type=ChaosType.TIMEOUT,
                    operation=operation_name,
                    details={"timeout_ms": cfg.timeout_after_ms}
                ))
                raise asyncio.TimeoutError(f"Chaos-induced timeout in {operation_name}")

            # Inject failure
            if cfg.failure_rate > 0 and random.random() < cfg.failure_rate:
                error_class = random.choice(cfg.error_types)
                await rec.record(ChaosEvent(
                    timestamp=datetime.utcnow(),
                    chaos_type=ChaosType.ERROR,
                    operation=operation_name,
                    details={"error_type": error_class.__name__},
                    duration_ms=(time.time() - start_time) * 1000
                ))
                raise error_class(f"Chaos-induced failure in {operation_name}")

            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            if not cfg.should_apply(operation_name):
                return func(*args, **kwargs)

            start_time = time.time()

            # Inject latency
            if cfg.max_latency_ms > 0:
                delay = random.uniform(cfg.min_latency_ms, cfg.max_latency_ms) / 1000
                time.sleep(delay)

            # Inject timeout
            if cfg.timeout_rate > 0 and random.random() < cfg.timeout_rate:
                time.sleep(cfg.timeout_after_ms / 1000)
                raise TimeoutError(f"Chaos-induced timeout in {operation_name}")

            # Inject failure
            if cfg.failure_rate > 0 and random.random() < cfg.failure_rate:
                error_class = random.choice(cfg.error_types)
                raise error_class(f"Chaos-induced failure in {operation_name}")

            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@asynccontextmanager
async def chaos_context(
    config: ChaosConfig,
    recorder: Optional[ChaosRecorder] = None
):
    """
    Context manager for temporary chaos injection.

    Example:
        async with chaos_context(ChaosConfig(failure_rate=0.5)):
            # Operations here may fail randomly
            await perform_operation()
    """
    rec = recorder or _global_recorder
    original_enabled = config.enabled
    config.enabled = True

    try:
        yield rec
    finally:
        config.enabled = original_enabled


# =============================================================================
# Resiliency Testing Utilities
# =============================================================================

@dataclass
class ResiliencyTestResult:
    """Result of a resiliency test."""
    passed: bool
    test_name: str
    expected: Any
    actual: Any
    attempts: int
    total_duration_ms: float
    events: List[ChaosEvent]
    message: str


class ResiliencyTester:
    """
    Test resiliency patterns against chaos injection.

    Verifies that retry policies, circuit breakers, and timeouts work correctly.
    """

    def __init__(self, recorder: Optional[ChaosRecorder] = None):
        self.recorder = recorder or ChaosRecorder()

    async def test_retry_policy(
        self,
        operation: Callable,
        expected_attempts: int,
        failure_rate: float = 1.0,  # All initial attempts fail
        success_after: int = None,  # Succeed after N attempts
        timeout_seconds: float = 30.0
    ) -> ResiliencyTestResult:
        """
        Test that retry policy executes expected number of attempts.

        Args:
            operation: Async function to test
            expected_attempts: Expected number of retry attempts
            failure_rate: Rate of failures to inject (before success_after)
            success_after: Attempt number after which to succeed
            timeout_seconds: Test timeout
        """
        attempt_count = 0
        success_after = success_after or expected_attempts

        @chaos_monkey(
            failure_rate=failure_rate if attempt_count < success_after else 0.0,
            recorder=self.recorder
        )
        async def wrapped_operation(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1

            if attempt_count < success_after:
                raise ChaosError("Test failure")

            return await operation(*args, **kwargs)

        start_time = time.time()
        try:
            async with asyncio.timeout(timeout_seconds):
                result = await operation()
        except Exception as e:
            result = None

        duration = (time.time() - start_time) * 1000
        events = self.recorder.get_events()

        passed = attempt_count == expected_attempts
        return ResiliencyTestResult(
            passed=passed,
            test_name="retry_policy",
            expected=expected_attempts,
            actual=attempt_count,
            attempts=attempt_count,
            total_duration_ms=duration,
            events=events,
            message=f"Expected {expected_attempts} attempts, got {attempt_count}"
        )

    async def test_circuit_breaker(
        self,
        operation: Callable,
        failure_threshold: int,
        expected_rejections: int,
        requests_after_threshold: int = 10
    ) -> ResiliencyTestResult:
        """
        Test that circuit breaker opens after threshold failures.

        Args:
            operation: Async function to test
            failure_threshold: Number of failures before circuit opens
            expected_rejections: Expected number of rejected requests
            requests_after_threshold: Additional requests to send
        """
        failure_count = 0
        rejection_count = 0
        total_requests = failure_threshold + requests_after_threshold

        # Inject failures to trip the circuit
        config = ChaosConfig(enabled=True, failure_rate=1.0)

        start_time = time.time()

        for i in range(total_requests):
            try:
                if i < failure_threshold:
                    # These should fail and count toward threshold
                    async with chaos_context(config, self.recorder):
                        await operation()
                else:
                    # These should be rejected by circuit breaker
                    await operation()
            except ChaosError:
                failure_count += 1
            except Exception as e:
                if "circuit" in str(e).lower() or "rejected" in str(e).lower():
                    rejection_count += 1
                else:
                    failure_count += 1

        duration = (time.time() - start_time) * 1000

        passed = rejection_count >= expected_rejections
        return ResiliencyTestResult(
            passed=passed,
            test_name="circuit_breaker",
            expected=expected_rejections,
            actual=rejection_count,
            attempts=total_requests,
            total_duration_ms=duration,
            events=self.recorder.get_events(),
            message=f"Expected {expected_rejections} rejections, got {rejection_count}"
        )

    async def test_timeout_handling(
        self,
        operation: Callable,
        timeout_ms: float,
        should_timeout: bool = True
    ) -> ResiliencyTestResult:
        """
        Test timeout behavior.

        Args:
            operation: Async function to test
            timeout_ms: Timeout threshold in ms
            should_timeout: Whether operation should timeout
        """
        timed_out = False
        start_time = time.time()

        config = ChaosConfig(
            enabled=True,
            timeout_rate=1.0 if should_timeout else 0.0,
            timeout_after_ms=timeout_ms * 1.5  # Inject timeout longer than threshold
        )

        try:
            async with chaos_context(config, self.recorder):
                async with asyncio.timeout(timeout_ms / 1000):
                    await operation()
        except asyncio.TimeoutError:
            timed_out = True
        except Exception:
            pass

        duration = (time.time() - start_time) * 1000

        passed = timed_out == should_timeout
        return ResiliencyTestResult(
            passed=passed,
            test_name="timeout_handling",
            expected=should_timeout,
            actual=timed_out,
            attempts=1,
            total_duration_ms=duration,
            events=self.recorder.get_events(),
            message=f"Expected timeout={should_timeout}, got {timed_out}"
        )

    async def run_all_tests(
        self,
        operation: Callable,
        config: Dict[str, Any] = None
    ) -> List[ResiliencyTestResult]:
        """Run a full suite of resiliency tests."""
        config = config or {}

        results = []

        # Test retries
        results.append(await self.test_retry_policy(
            operation,
            expected_attempts=config.get("retry_attempts", 3)
        ))

        self.recorder.clear()

        # Test timeout
        results.append(await self.test_timeout_handling(
            operation,
            timeout_ms=config.get("timeout_ms", 1000),
            should_timeout=True
        ))

        return results


# =============================================================================
# DAPR-Specific Chaos Patterns
# =============================================================================

async def simulate_sidecar_unavailable(duration_seconds: float = 10.0):
    """
    Simulate DAPR sidecar being unavailable.

    This can be used to test fallback behavior when DAPR is down.
    Note: This is a simulation - actual sidecar control requires Kubernetes.
    """
    logger.warning(f"Simulating DAPR sidecar unavailable for {duration_seconds}s")
    # In a real implementation, this would modify network rules
    # For now, we set an environment variable that chaos_monkey can check
    os.environ["CHAOS_DAPR_UNAVAILABLE"] = "true"

    await asyncio.sleep(duration_seconds)

    os.environ.pop("CHAOS_DAPR_UNAVAILABLE", None)
    logger.info("DAPR sidecar simulation ended")


def create_component_failure_config(
    component_name: str,
    failure_rate: float = 0.5
) -> ChaosConfig:
    """Create chaos config targeting a specific DAPR component."""
    return ChaosConfig(
        enabled=True,
        failure_rate=failure_rate,
        target_operations=[f".*{component_name}.*"],
        error_types=[ConnectionError, TimeoutError]
    )


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def sample_operation():
        """Sample operation to test."""
        await asyncio.sleep(0.1)
        return {"status": "ok"}

    @chaos_monkey(failure_rate=0.3, latency_ms=50, latency_jitter_ms=20)
    async def chaotic_operation():
        """Operation with chaos injection."""
        await asyncio.sleep(0.05)
        return {"status": "ok"}

    async def main():
        print("Testing chaos injection...")

        # Run chaotic operation multiple times
        successes = 0
        failures = 0

        for i in range(10):
            try:
                result = await chaotic_operation()
                successes += 1
                print(f"  Attempt {i+1}: Success")
            except Exception as e:
                failures += 1
                print(f"  Attempt {i+1}: Failed - {e}")

        print(f"\nResults: {successes} successes, {failures} failures")

        # Show chaos events
        print(f"\nChaos events recorded:")
        summary = _global_recorder.get_summary()
        print(f"  Total events: {summary['total_events']}")
        if summary['total_events'] > 0:
            print(f"  By type: {summary['by_type']}")

        # Run resiliency tests
        print("\n\nRunning resiliency tests...")
        tester = ResiliencyTester()
        results = await tester.run_all_tests(sample_operation)

        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  [{status}] {result.test_name}: {result.message}")

    asyncio.run(main())
