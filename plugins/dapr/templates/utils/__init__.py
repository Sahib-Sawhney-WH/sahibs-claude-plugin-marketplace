"""DAPR Utility Modules.

Provides common utilities for DAPR applications:
- error_handling: Retry policies, error classification, circuit breaker
"""

from .error_handling import (
    # Policies
    RetryPolicy,
    DEFAULT_RETRY_POLICY,
    AGGRESSIVE_RETRY_POLICY,
    CONSERVATIVE_RETRY_POLICY,
    NO_RETRY_POLICY,
    # Error handling
    DaprError,
    DaprErrorHandler,
    ErrorCategory,
    classify_error,
    with_dapr_retry,
    safe_dapr_call,
    # Circuit breaker
    CircuitBreaker,
    CircuitBreakerOpen,
    # FastAPI integration
    create_fastapi_exception_handlers,
)

__all__ = [
    "RetryPolicy",
    "DEFAULT_RETRY_POLICY",
    "AGGRESSIVE_RETRY_POLICY",
    "CONSERVATIVE_RETRY_POLICY",
    "NO_RETRY_POLICY",
    "DaprError",
    "DaprErrorHandler",
    "ErrorCategory",
    "classify_error",
    "with_dapr_retry",
    "safe_dapr_call",
    "CircuitBreaker",
    "CircuitBreakerOpen",
    "create_fastapi_exception_handlers",
]
