"""
DAPR SDK Error Handling Utilities

Provides comprehensive error handling patterns for DAPR operations including:
- Retry policies with exponential backoff
- Error classification and handling
- gRPC status code parsing
- Structured error logging with trace context

Usage:
    from utils.error_handling import with_dapr_retry, DaprErrorHandler, classify_error

    @with_dapr_retry()
    async def get_state(key: str):
        async with DaprClient() as client:
            return await client.get_state(store_name="statestore", key=key)
"""

import asyncio
import functools
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

# DAPR SDK imports
try:
    from dapr.clients import DaprClient
    from dapr.clients.exceptions import DaprInternalError
    DAPR_SDK_AVAILABLE = True
except ImportError:
    DAPR_SDK_AVAILABLE = False
    DaprInternalError = Exception  # Fallback for type hints

# OpenTelemetry for trace context
try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of DAPR errors for handling decisions."""
    TRANSIENT = "transient"           # Retry is likely to succeed
    CLIENT_ERROR = "client_error"     # Bad request, don't retry
    SERVER_ERROR = "server_error"     # Server issue, may retry
    NETWORK_ERROR = "network_error"   # Network issues, retry with backoff
    TIMEOUT = "timeout"               # Timeout, retry with longer timeout
    RESOURCE_EXHAUSTED = "resource_exhausted"  # Rate limited, backoff
    NOT_FOUND = "not_found"           # Resource doesn't exist
    CONFLICT = "conflict"             # Concurrency conflict, retry
    UNKNOWN = "unknown"               # Unknown error


# gRPC status code to error category mapping
GRPC_STATUS_CATEGORIES = {
    0: None,                           # OK
    1: ErrorCategory.CLIENT_ERROR,     # CANCELLED
    2: ErrorCategory.UNKNOWN,          # UNKNOWN
    3: ErrorCategory.CLIENT_ERROR,     # INVALID_ARGUMENT
    4: ErrorCategory.TIMEOUT,          # DEADLINE_EXCEEDED
    5: ErrorCategory.NOT_FOUND,        # NOT_FOUND
    6: ErrorCategory.CONFLICT,         # ALREADY_EXISTS
    7: ErrorCategory.CLIENT_ERROR,     # PERMISSION_DENIED
    8: ErrorCategory.RESOURCE_EXHAUSTED,  # RESOURCE_EXHAUSTED
    9: ErrorCategory.CLIENT_ERROR,     # FAILED_PRECONDITION
    10: ErrorCategory.CONFLICT,        # ABORTED
    11: ErrorCategory.CLIENT_ERROR,    # OUT_OF_RANGE
    12: ErrorCategory.CLIENT_ERROR,    # UNIMPLEMENTED
    13: ErrorCategory.SERVER_ERROR,    # INTERNAL
    14: ErrorCategory.TRANSIENT,       # UNAVAILABLE
    15: ErrorCategory.SERVER_ERROR,    # DATA_LOSS
    16: ErrorCategory.CLIENT_ERROR,    # UNAUTHENTICATED
}

# HTTP status code to error category mapping
HTTP_STATUS_CATEGORIES = {
    range(400, 404): ErrorCategory.CLIENT_ERROR,
    range(404, 405): ErrorCategory.NOT_FOUND,
    range(405, 409): ErrorCategory.CLIENT_ERROR,
    range(409, 410): ErrorCategory.CONFLICT,
    range(410, 429): ErrorCategory.CLIENT_ERROR,
    range(429, 430): ErrorCategory.RESOURCE_EXHAUSTED,
    range(430, 500): ErrorCategory.CLIENT_ERROR,
    range(500, 503): ErrorCategory.SERVER_ERROR,
    range(503, 504): ErrorCategory.TRANSIENT,
    range(504, 505): ErrorCategory.TIMEOUT,
    range(505, 600): ErrorCategory.SERVER_ERROR,
}


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 5
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retryable_categories: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.TRANSIENT,
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.TIMEOUT,
        ErrorCategory.RESOURCE_EXHAUSTED,
        ErrorCategory.CONFLICT,
        ErrorCategory.SERVER_ERROR,
    ])

    def get_backoff(self, attempt: int) -> float:
        """Calculate backoff duration for given attempt number."""
        backoff = min(
            self.initial_backoff_seconds * (self.backoff_multiplier ** attempt),
            self.max_backoff_seconds
        )
        if self.jitter:
            jitter_range = backoff * self.jitter_factor
            backoff += random.uniform(-jitter_range, jitter_range)
        return max(0, backoff)


# Pre-defined retry policies for common scenarios
DEFAULT_RETRY_POLICY = RetryPolicy()

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=10,
    initial_backoff_seconds=0.5,
    max_backoff_seconds=60.0,
    backoff_multiplier=1.5,
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    initial_backoff_seconds=2.0,
    max_backoff_seconds=10.0,
    backoff_multiplier=2.0,
)

NO_RETRY_POLICY = RetryPolicy(max_attempts=1)


@dataclass
class DaprError:
    """Structured DAPR error information."""
    category: ErrorCategory
    message: str
    error_code: Optional[str] = None
    grpc_status: Optional[int] = None
    http_status: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    retry_info: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None

    def is_retryable(self, policy: RetryPolicy = DEFAULT_RETRY_POLICY) -> bool:
        """Check if error is retryable under given policy."""
        return self.category in policy.retryable_categories


def classify_error(error: Exception) -> DaprError:
    """Classify an exception into a structured DaprError."""
    category = ErrorCategory.UNKNOWN
    error_code = None
    grpc_status = None
    http_status = None
    details = {}
    retry_info = None

    # Handle DAPR SDK internal errors
    if DAPR_SDK_AVAILABLE and isinstance(error, DaprInternalError):
        error_code = getattr(error, 'error_code', None)
        message = str(error)

        # Try to extract gRPC status
        if hasattr(error, 'status_details'):
            status_details = error.status_details
            if hasattr(status_details, 'code'):
                grpc_status = status_details.code
                category = GRPC_STATUS_CATEGORIES.get(grpc_status, ErrorCategory.UNKNOWN)

            # Extract retry info if available
            if hasattr(status_details, 'retry_info'):
                retry_info = {
                    "retry_delay": getattr(status_details.retry_info, 'retry_delay', None)
                }

        # Extract raw response if available
        if hasattr(error, 'raw_response_bytes') and error.raw_response_bytes:
            details["raw_response"] = error.raw_response_bytes[:500]  # Limit size

        return DaprError(
            category=category,
            message=message,
            error_code=error_code,
            grpc_status=grpc_status,
            details=details,
            retry_info=retry_info,
            original_exception=error
        )

    # Handle standard exceptions
    error_type = type(error).__name__
    message = str(error)

    # Classify by exception type
    if isinstance(error, (ConnectionError, ConnectionRefusedError)):
        category = ErrorCategory.NETWORK_ERROR
    elif isinstance(error, TimeoutError):
        category = ErrorCategory.TIMEOUT
    elif isinstance(error, (asyncio.TimeoutError,)):
        category = ErrorCategory.TIMEOUT
    elif isinstance(error, PermissionError):
        category = ErrorCategory.CLIENT_ERROR
    elif isinstance(error, FileNotFoundError):
        category = ErrorCategory.NOT_FOUND

    # Check for HTTP status in message (common pattern)
    import re
    http_match = re.search(r'(\d{3})', message)
    if http_match:
        status = int(http_match.group(1))
        for status_range, cat in HTTP_STATUS_CATEGORIES.items():
            if status in status_range:
                http_status = status
                category = cat
                break

    return DaprError(
        category=category,
        message=message,
        http_status=http_status,
        details={"error_type": error_type},
        original_exception=error
    )


class DaprErrorHandler:
    """Centralized error handler for DAPR operations."""

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        include_trace_context: bool = True
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.include_trace_context = include_trace_context and OTEL_AVAILABLE

    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> DaprError:
        """Handle and log an error with optional context."""
        dapr_error = classify_error(error)
        context = context or {}

        # Build log message
        log_data = {
            "error_category": dapr_error.category.value,
            "error_message": dapr_error.message,
            "error_code": dapr_error.error_code,
            "grpc_status": dapr_error.grpc_status,
            "http_status": dapr_error.http_status,
            **context
        }

        # Add trace context if available
        if self.include_trace_context:
            span = trace.get_current_span()
            if span.is_recording():
                span_context = span.get_span_context()
                log_data["trace_id"] = format(span_context.trace_id, '032x')
                log_data["span_id"] = format(span_context.span_id, '016x')
                # Record error on span
                span.set_status(Status(StatusCode.ERROR, dapr_error.message))
                span.record_exception(error)

        # Log at appropriate level
        if dapr_error.category in (ErrorCategory.CLIENT_ERROR, ErrorCategory.NOT_FOUND):
            self.logger.warning("DAPR operation failed", extra=log_data)
        else:
            self.logger.error("DAPR operation error", extra=log_data, exc_info=True)

        return dapr_error

    def is_retryable(
        self,
        error: Exception,
        policy: RetryPolicy = DEFAULT_RETRY_POLICY
    ) -> bool:
        """Check if an error should be retried."""
        dapr_error = classify_error(error)
        return dapr_error.is_retryable(policy)


T = TypeVar('T')


def with_dapr_retry(
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    error_handler: Optional[DaprErrorHandler] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for DAPR operations with retry logic.

    Args:
        policy: Retry policy configuration
        error_handler: Custom error handler
        on_retry: Callback called on each retry with (error, attempt_number)

    Usage:
        @with_dapr_retry()
        async def get_state(key: str):
            async with DaprClient() as client:
                return await client.get_state("statestore", key)

        @with_dapr_retry(policy=AGGRESSIVE_RETRY_POLICY)
        def publish_event(topic: str, data: dict):
            with DaprClient() as client:
                client.publish_event("pubsub", topic, data)
    """
    handler = error_handler or DaprErrorHandler()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(policy.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    dapr_error = handler.handle(e, {"attempt": attempt + 1})

                    if not dapr_error.is_retryable(policy):
                        raise

                    if attempt < policy.max_attempts - 1:
                        # Check for retry-after hint
                        backoff = policy.get_backoff(attempt)
                        if dapr_error.retry_info and dapr_error.retry_info.get("retry_delay"):
                            backoff = max(backoff, dapr_error.retry_info["retry_delay"])

                        if on_retry:
                            on_retry(e, attempt + 1)

                        logger.info(
                            f"Retrying after {backoff:.2f}s (attempt {attempt + 1}/{policy.max_attempts})"
                        )
                        await asyncio.sleep(backoff)

            raise last_error

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None

            for attempt in range(policy.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    dapr_error = handler.handle(e, {"attempt": attempt + 1})

                    if not dapr_error.is_retryable(policy):
                        raise

                    if attempt < policy.max_attempts - 1:
                        backoff = policy.get_backoff(attempt)
                        if dapr_error.retry_info and dapr_error.retry_info.get("retry_delay"):
                            backoff = max(backoff, dapr_error.retry_info["retry_delay"])

                        if on_retry:
                            on_retry(e, attempt + 1)

                        logger.info(
                            f"Retrying after {backoff:.2f}s (attempt {attempt + 1}/{policy.max_attempts})"
                        )
                        time.sleep(backoff)

            raise last_error

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class CircuitBreaker:
    """Simple circuit breaker for DAPR operations.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Failing, all requests rejected immediately
        - HALF_OPEN: Testing if service recovered
    """

    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = self.State.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> State:
        """Get current circuit breaker state."""
        if self._state == self.State.OPEN:
            if time.time() - (self._last_failure_time or 0) > self.recovery_timeout:
                return self.State.HALF_OPEN
        return self._state

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function through circuit breaker."""
        async with self._lock:
            state = self.state

            if state == self.State.OPEN:
                raise CircuitBreakerOpen(f"Circuit breaker is open")

            if state == self.State.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpen("Circuit breaker half-open limit reached")
                self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure()
            raise

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            self._failure_count = 0
            self._half_open_calls = 0
            if self._state != self.State.CLOSED:
                logger.info("Circuit breaker closed")
            self._state = self.State.CLOSED

    async def _on_failure(self):
        """Handle failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                self._state = self.State.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self._failure_count} failures"
                )


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


# FastAPI exception handler integration
def create_fastapi_exception_handlers():
    """Create FastAPI exception handlers for DAPR errors.

    Usage:
        from fastapi import FastAPI
        from utils.error_handling import create_fastapi_exception_handlers

        app = FastAPI()
        handlers = create_fastapi_exception_handlers()
        for exc_class, handler in handlers.items():
            app.add_exception_handler(exc_class, handler)
    """
    try:
        from fastapi import Request
        from fastapi.responses import JSONResponse
    except ImportError:
        return {}

    async def dapr_error_handler(request: Request, exc: Exception) -> JSONResponse:
        dapr_error = classify_error(exc)

        status_code = 500
        if dapr_error.category == ErrorCategory.CLIENT_ERROR:
            status_code = 400
        elif dapr_error.category == ErrorCategory.NOT_FOUND:
            status_code = 404
        elif dapr_error.category == ErrorCategory.CONFLICT:
            status_code = 409
        elif dapr_error.category == ErrorCategory.RESOURCE_EXHAUSTED:
            status_code = 429
        elif dapr_error.http_status:
            status_code = dapr_error.http_status

        return JSONResponse(
            status_code=status_code,
            content={
                "error": dapr_error.category.value,
                "message": dapr_error.message,
                "code": dapr_error.error_code
            }
        )

    handlers = {Exception: dapr_error_handler}

    if DAPR_SDK_AVAILABLE:
        handlers[DaprInternalError] = dapr_error_handler

    return handlers


# Convenience function for common patterns
async def safe_dapr_call(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    **kwargs
) -> Optional[T]:
    """Execute a DAPR call with retry and return default on failure.

    Usage:
        state = await safe_dapr_call(
            client.get_state,
            "statestore", "my-key",
            default={"count": 0}
        )
    """
    try:
        wrapped = with_dapr_retry(policy=policy)(func)
        if asyncio.iscoroutinefunction(func):
            return await wrapped(*args, **kwargs)
        return wrapped(*args, **kwargs)
    except Exception as e:
        logger.warning(f"DAPR call failed, using default: {e}")
        return default
