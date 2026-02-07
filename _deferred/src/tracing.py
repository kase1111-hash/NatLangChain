"""
NatLangChain - Distributed Tracing with OpenTelemetry

Production-ready distributed tracing for observability across services.

Features:
- OpenTelemetry integration
- Automatic Flask instrumentation
- Request correlation with trace IDs
- Custom span creation for operations
- Export to Jaeger, Zipkin, OTLP, or console
- Baggage propagation for context

Usage:
    from tracing import init_tracing, trace_operation, get_tracer

    # Initialize at app startup
    init_tracing(service_name="natlangchain-api")

    # Decorator for tracing functions
    @trace_operation("process_entry")
    def process_entry(entry_id):
        ...

    # Manual span creation
    with get_tracer().start_as_current_span("custom_operation") as span:
        span.set_attribute("entry.id", entry_id)
        ...

Environment Variables:
    NATLANGCHAIN_TRACING_ENABLED=true
    NATLANGCHAIN_TRACING_EXPORTER=otlp  # otlp, jaeger, zipkin, console
    NATLANGCHAIN_TRACING_ENDPOINT=http://localhost:4317
    NATLANGCHAIN_TRACING_SERVICE_NAME=natlangchain-api
    NATLANGCHAIN_TRACING_SAMPLE_RATE=1.0
"""

import functools
import logging
import os
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# OpenTelemetry Imports (with graceful fallback)
# =============================================================================

try:
    from opentelemetry import trace
    from opentelemetry.context import Context
    from opentelemetry.propagate import extract, inject
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.sampling import (
        ParentBasedTraceIdRatio,
    )
    from opentelemetry.semconv.resource import ResourceAttributes
    from opentelemetry.trace import SpanKind, Status, StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    TracerProvider = None

# Optional exporters
try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    OTLP_AVAILABLE = True
except ImportError:
    OTLP_AVAILABLE = False
    OTLPSpanExporter = None

try:
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter

    JAEGER_AVAILABLE = True
except ImportError:
    JAEGER_AVAILABLE = False
    JaegerExporter = None

try:
    from opentelemetry.exporter.zipkin.json import ZipkinExporter

    ZIPKIN_AVAILABLE = True
except ImportError:
    ZIPKIN_AVAILABLE = False
    ZipkinExporter = None

# Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    FLASK_INSTRUMENTATION_AVAILABLE = True
except ImportError:
    FLASK_INSTRUMENTATION_AVAILABLE = False
    FlaskInstrumentor = None


# =============================================================================
# Configuration
# =============================================================================


class TracingConfig:
    """Configuration for distributed tracing."""

    def __init__(
        self,
        enabled: bool = True,
        service_name: str = "natlangchain-api",
        service_version: str = "1.0.0",
        environment: str = "production",
        exporter: str = "console",
        endpoint: str | None = None,
        sample_rate: float = 1.0,
        batch_export: bool = True,
    ):
        self.enabled = enabled
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.exporter = exporter
        self.endpoint = endpoint
        self.sample_rate = sample_rate
        self.batch_export = batch_export

    @classmethod
    def from_env(cls) -> "TracingConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("NATLANGCHAIN_TRACING_ENABLED", "false").lower() == "true",
            service_name=os.getenv("NATLANGCHAIN_TRACING_SERVICE_NAME", "natlangchain-api"),
            service_version=os.getenv("NATLANGCHAIN_TRACING_SERVICE_VERSION", "1.0.0"),
            environment=os.getenv("NATLANGCHAIN_ENVIRONMENT", "production"),
            exporter=os.getenv("NATLANGCHAIN_TRACING_EXPORTER", "console"),
            endpoint=os.getenv("NATLANGCHAIN_TRACING_ENDPOINT"),
            sample_rate=float(os.getenv("NATLANGCHAIN_TRACING_SAMPLE_RATE", "1.0")),
            batch_export=os.getenv("NATLANGCHAIN_TRACING_BATCH", "true").lower() == "true",
        )


# =============================================================================
# Tracer Management
# =============================================================================

_tracer_provider: TracerProvider | None = None
_tracer = None
_config: TracingConfig | None = None
_lock = threading.Lock()
_initialized = False


def init_tracing(
    config: TracingConfig | None = None,
    flask_app=None,
) -> bool:
    """
    Initialize distributed tracing.

    Args:
        config: Tracing configuration (uses env vars if None)
        flask_app: Optional Flask app for automatic instrumentation

    Returns:
        True if tracing was initialized successfully
    """
    global _tracer_provider, _tracer, _config, _initialized

    with _lock:
        if _initialized:
            return True

        _config = config or TracingConfig.from_env()

        if not _config.enabled:
            logger.info("Distributed tracing is disabled")
            _initialized = True
            return True

        if not OTEL_AVAILABLE:
            logger.warning(
                "OpenTelemetry not available. Install with: "
                "pip install opentelemetry-api opentelemetry-sdk"
            )
            _initialized = True
            return False

        try:
            # Create resource
            resource = Resource.create(
                {
                    ResourceAttributes.SERVICE_NAME: _config.service_name,
                    ResourceAttributes.SERVICE_VERSION: _config.service_version,
                    ResourceAttributes.DEPLOYMENT_ENVIRONMENT: _config.environment,
                }
            )

            # Create sampler
            sampler = ParentBasedTraceIdRatio(_config.sample_rate)

            # Create tracer provider
            _tracer_provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )

            # Create exporter
            exporter = _create_exporter(_config)
            if exporter:
                if _config.batch_export:
                    processor = BatchSpanProcessor(exporter)
                else:
                    processor = SimpleSpanProcessor(exporter)
                _tracer_provider.add_span_processor(processor)

            # Set as global tracer provider
            trace.set_tracer_provider(_tracer_provider)

            # Get tracer
            _tracer = trace.get_tracer(
                _config.service_name,
                _config.service_version,
            )

            # Instrument Flask if provided
            if flask_app and FLASK_INSTRUMENTATION_AVAILABLE:
                FlaskInstrumentor().instrument_app(flask_app)
                RequestsInstrumentor().instrument()
                logger.info("Flask instrumentation enabled")

            logger.info(
                f"Distributed tracing initialized: "
                f"service={_config.service_name}, "
                f"exporter={_config.exporter}, "
                f"sample_rate={_config.sample_rate}"
            )

            _initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}")
            _initialized = True
            return False


def _create_exporter(config: TracingConfig):
    """Create the appropriate span exporter."""
    exporter_type = config.exporter.lower()

    if exporter_type == "console":
        return ConsoleSpanExporter()

    elif exporter_type == "otlp":
        if not OTLP_AVAILABLE:
            logger.warning("OTLP exporter not available, falling back to console")
            return ConsoleSpanExporter()
        endpoint = config.endpoint or "http://localhost:4317"
        return OTLPSpanExporter(endpoint=endpoint, insecure=True)

    elif exporter_type == "jaeger":
        if not JAEGER_AVAILABLE:
            logger.warning("Jaeger exporter not available, falling back to console")
            return ConsoleSpanExporter()
        # Parse endpoint for Jaeger
        endpoint = config.endpoint or "localhost:6831"
        if ":" in endpoint:
            host, port = endpoint.rsplit(":", 1)
            port = int(port)
        else:
            host, port = endpoint, 6831
        return JaegerExporter(agent_host_name=host, agent_port=port)

    elif exporter_type == "zipkin":
        if not ZIPKIN_AVAILABLE:
            logger.warning("Zipkin exporter not available, falling back to console")
            return ConsoleSpanExporter()
        endpoint = config.endpoint or "http://localhost:9411/api/v2/spans"
        return ZipkinExporter(endpoint=endpoint)

    elif exporter_type == "none":
        return None

    else:
        logger.warning(f"Unknown exporter type: {exporter_type}, using console")
        return ConsoleSpanExporter()


def get_tracer():
    """Get the global tracer instance."""
    global _tracer

    if _tracer is None:
        init_tracing()

        # If still None (tracing disabled or failed), return noop tracer
        if _tracer is None and OTEL_AVAILABLE:
            _tracer = trace.get_tracer("natlangchain")

    return _tracer


def shutdown_tracing():
    """Shutdown the tracer provider and flush spans."""
    global _tracer_provider

    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        logger.info("Tracing shutdown complete")


# =============================================================================
# Tracing Decorators
# =============================================================================


def trace_operation(
    name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL if OTEL_AVAILABLE else None,
    attributes: dict[str, Any] | None = None,
):
    """
    Decorator to trace a function as a span.

    Args:
        name: Span name (defaults to function name)
        kind: Span kind (INTERNAL, SERVER, CLIENT, etc.)
        attributes: Static attributes to add to span

    Example:
        @trace_operation("process_entry")
        def process_entry(entry_id):
            ...

        @trace_operation(attributes={"component": "validator"})
        def validate_entry(entry):
            ...
    """

    def decorator(func: Callable) -> Callable:
        if not OTEL_AVAILABLE or not (_config and _config.enabled):
            return func

        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer is None:
                return func(*args, **kwargs)

            with tracer.start_as_current_span(
                span_name,
                kind=kind,
            ) as span:
                # Add static attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function info
                span.set_attribute("code.function", func.__name__)
                if func.__module__:
                    span.set_attribute("code.namespace", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


def trace_async_operation(
    name: str | None = None,
    kind: SpanKind = SpanKind.INTERNAL if OTEL_AVAILABLE else None,
    attributes: dict[str, Any] | None = None,
):
    """Decorator to trace an async function as a span."""

    def decorator(func: Callable) -> Callable:
        if not OTEL_AVAILABLE or not (_config and _config.enabled):
            return func

        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer is None:
                return await func(*args, **kwargs)

            with tracer.start_as_current_span(
                span_name,
                kind=kind,
            ) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                span.set_attribute("code.function", func.__name__)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


# =============================================================================
# Context Helpers
# =============================================================================


@contextmanager
def span_context(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: SpanKind = SpanKind.INTERNAL if OTEL_AVAILABLE else None,
) -> Generator:
    """
    Context manager for creating a span.

    Example:
        with span_context("process_block", {"block.index": 42}) as span:
            # do work
            span.add_event("checkpoint_reached")
    """
    if not OTEL_AVAILABLE or not (_config and _config.enabled):
        yield None
        return

    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def get_current_span():
    """Get the current active span."""
    if not OTEL_AVAILABLE:
        return None
    return trace.get_current_span()


def get_trace_id() -> str | None:
    """Get the current trace ID as a hex string."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span is None:
        return None

    ctx = span.get_span_context()
    if ctx is None or not ctx.is_valid:
        return None

    return format(ctx.trace_id, "032x")


def get_span_id() -> str | None:
    """Get the current span ID as a hex string."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span is None:
        return None

    ctx = span.get_span_context()
    if ctx is None or not ctx.is_valid:
        return None

    return format(ctx.span_id, "016x")


def add_span_attribute(key: str, value: Any):
    """Add an attribute to the current span."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict[str, Any] | None = None):
    """Add an event to the current span."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes=attributes)


def set_span_error(error: Exception):
    """Mark the current span as errored."""
    if not OTEL_AVAILABLE:
        return

    span = trace.get_current_span()
    if span:
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)


# =============================================================================
# Context Propagation
# =============================================================================


def extract_context(headers: dict[str, str]) -> Context | None:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: HTTP headers dict

    Returns:
        OpenTelemetry Context or None
    """
    if not OTEL_AVAILABLE:
        return None

    return extract(headers)


def inject_context(headers: dict[str, str]) -> dict[str, str]:
    """
    Inject trace context into HTTP headers.

    Args:
        headers: HTTP headers dict to modify

    Returns:
        Modified headers with trace context
    """
    if not OTEL_AVAILABLE:
        return headers

    inject(headers)
    return headers


# =============================================================================
# Flask Integration
# =============================================================================


def trace_request():
    """
    Get trace information for the current Flask request.

    Returns:
        Dict with trace_id, span_id if available
    """
    return {
        "trace_id": get_trace_id(),
        "span_id": get_span_id(),
    }


def add_trace_to_response(response):
    """
    Add trace headers to a Flask response.

    This enables distributed tracing across service boundaries.
    """
    trace_id = get_trace_id()
    span_id = get_span_id()

    if trace_id:
        response.headers["X-Trace-ID"] = trace_id
    if span_id:
        response.headers["X-Span-ID"] = span_id

    return response


# =============================================================================
# Specialized Tracers
# =============================================================================


@trace_operation("blockchain.add_entry", attributes={"component": "blockchain"})
def trace_add_entry(entry_content: str, agent_id: str):
    """Trace an entry addition operation."""
    span = get_current_span()
    if span:
        span.set_attribute("entry.agent_id", agent_id)
        span.set_attribute("entry.content_length", len(entry_content))


@trace_operation("blockchain.mine_block", attributes={"component": "blockchain"})
def trace_mine_block(block_index: int, entry_count: int):
    """Trace a block mining operation."""
    span = get_current_span()
    if span:
        span.set_attribute("block.index", block_index)
        span.set_attribute("block.entry_count", entry_count)


@trace_operation("llm.request", kind=SpanKind.CLIENT if OTEL_AVAILABLE else None)
def trace_llm_request(provider: str, model: str, prompt_tokens: int = 0):
    """Trace an LLM API request."""
    span = get_current_span()
    if span:
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.model", model)
        if prompt_tokens:
            span.set_attribute("llm.prompt_tokens", prompt_tokens)


@trace_operation("p2p.broadcast", attributes={"component": "p2p"})
def trace_p2p_broadcast(message_type: str, peer_count: int):
    """Trace a P2P broadcast operation."""
    span = get_current_span()
    if span:
        span.set_attribute("p2p.message_type", message_type)
        span.set_attribute("p2p.peer_count", peer_count)
