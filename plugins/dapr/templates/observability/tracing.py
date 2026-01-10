"""
DAPR OpenTelemetry Tracing Configuration

Configures distributed tracing for DAPR microservices.
"""
import os
import logging
from functools import wraps
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat

# Exporters
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

logger = logging.getLogger(__name__)


def configure_tracing(
    service_name: str,
    otlp_endpoint: str = "localhost:4317",
    environment: str = "development",
    version: str = "1.0.0"
) -> trace.Tracer:
    """
    Configure OpenTelemetry tracing for DAPR service.

    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP collector endpoint
        environment: Deployment environment
        version: Service version

    Returns:
        Configured tracer

    Example:
        tracer = configure_tracing(
            service_name="order-service",
            otlp_endpoint="otel-collector:4317",
            environment="production"
        )
    """
    # Create resource with service information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: version,
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: environment,
        "dapr.app.id": service_name,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=environment != "production"
    )

    # Add span processor
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Set B3 propagation for DAPR compatibility
    set_global_textmap(B3MultiFormat())

    logger.info(f"Tracing configured for {service_name} -> {otlp_endpoint}")

    return trace.get_tracer(service_name)


def instrument_fastapi(app):
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented with OpenTelemetry")


def instrument_http_clients():
    """Instrument HTTP client libraries."""
    RequestsInstrumentor().instrument()
    AioHttpClientInstrumentor().instrument()
    logger.info("HTTP clients instrumented")


def traced(name: Optional[str] = None):
    """
    Decorator to add tracing to a function.

    Args:
        name: Span name (defaults to function name)

    Example:
        @traced("process_order")
        async def process_order(order_id: str):
            # Function body
            pass
    """
    def decorator(func):
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                # Add function arguments as span attributes
                for i, arg in enumerate(args):
                    if isinstance(arg, (str, int, float, bool)):
                        span.set_attribute(f"arg.{i}", str(arg))

                for key, value in kwargs.items():
                    if isinstance(value, (str, int, float, bool)):
                        span.set_attribute(f"kwarg.{key}", str(value))

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(span_name) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def add_span_attributes(**attributes):
    """
    Add attributes to the current span.

    Example:
        add_span_attributes(
            order_id="123",
            customer_id="456",
            total_amount=99.99
        )
    """
    span = trace.get_current_span()
    for key, value in attributes.items():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict = None):
    """
    Add an event to the current span.

    Example:
        add_span_event("order_validated", {"items_count": 5})
    """
    span = trace.get_current_span()
    span.add_event(name, attributes or {})


# =============================================================================
# FastAPI Integration Example
# =============================================================================

def setup_tracing_middleware(app, service_name: str):
    """
    Set up complete tracing for FastAPI app.

    Args:
        app: FastAPI application
        service_name: Service name for tracing

    Example:
        from fastapi import FastAPI
        app = FastAPI()
        setup_tracing_middleware(app, "order-service")
    """
    # Configure tracing
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")
    environment = os.getenv("ENVIRONMENT", "development")

    configure_tracing(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        environment=environment
    )

    # Instrument app
    instrument_fastapi(app)
    instrument_http_clients()

    # Add middleware for request context
    @app.middleware("http")
    async def add_trace_context(request, call_next):
        span = trace.get_current_span()
        if span:
            # Add request info to span
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.method", request.method)

        response = await call_next(request)

        if span:
            span.set_attribute("http.status_code", response.status_code)

        return response

    logger.info(f"Tracing middleware configured for {service_name}")
