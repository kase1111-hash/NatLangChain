"""
Flask middleware for request logging and metrics.

Provides:
- Request/response logging with timing
- Automatic metrics collection for all requests
- Request ID tracking for distributed tracing
"""

import time
import uuid
from collections.abc import Callable
from functools import wraps

from flask import Flask, Response, g, request


def setup_request_logging(app: Flask) -> None:
    """
    Set up request logging middleware for a Flask app.

    Adds:
    - Request ID generation and tracking
    - Request timing
    - Structured logging of requests/responses
    - Metrics collection

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request():
        """Run before each request."""
        # Generate request ID
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        g.start_time = time.perf_counter()

        # Set up logging context
        try:
            from monitoring.logging import set_request_context

            set_request_context(
                request_id=g.request_id,
                method=request.method,
                path=request.path,
            )
        except ImportError:
            pass

        # Track active requests
        try:
            from monitoring import metrics

            metrics.increment_gauge("http_requests_active")
        except ImportError:
            pass

    @app.after_request
    def after_request(response: Response) -> Response:
        """Run after each request (for successful responses)."""
        _record_request_metrics(response.status_code)

        # Add request ID to response headers
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id

        return response

    @app.teardown_request
    def teardown_request(exception=None):
        """Run after each request (always, even on error)."""
        # Clear logging context
        try:
            from monitoring.logging import clear_request_context

            clear_request_context()
        except ImportError:
            pass

        # Decrement active requests
        try:
            from monitoring import metrics

            metrics.decrement_gauge("http_requests_active")
        except ImportError:
            pass

        # Log errors
        if exception:
            try:
                from monitoring import get_logger

                logger = get_logger("natlangchain.request")
                logger.error(
                    "Request failed with exception",
                    exc_info=exception,
                    extra={
                        "request_id": getattr(g, "request_id", "unknown"),
                        "path": request.path,
                        "method": request.method,
                    },
                )
            except ImportError:
                pass


def _record_request_metrics(status_code: int) -> None:
    """Record metrics for a completed request."""
    try:
        from monitoring import metrics

        # Calculate duration
        duration_ms = 0
        if hasattr(g, "start_time"):
            duration_ms = (time.perf_counter() - g.start_time) * 1000

        # Determine status category
        f"{status_code // 100}xx"

        # Increment request counter
        metrics.increment(
            "http_requests_total",
            labels={
                "method": request.method,
                "path": _normalize_path(request.path),
                "status": str(status_code),
            },
        )

        # Record timing
        metrics.timing(
            "http_request_duration_ms",
            duration_ms,
            labels={
                "method": request.method,
                "path": _normalize_path(request.path),
            },
        )

        # Log the request
        try:
            from monitoring import get_logger

            logger = get_logger("natlangchain.request")

            log_level = "info"
            if status_code >= 500:
                log_level = "error"
            elif status_code >= 400:
                log_level = "warning"

            getattr(logger, log_level)(
                f"{request.method} {request.path} -> {status_code}",
                extra={
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "request_id": getattr(g, "request_id", "unknown"),
                },
            )
        except ImportError:
            pass

    except ImportError:
        pass


def _normalize_path(path: str) -> str:
    """
    Normalize path for metrics labels.

    Replaces dynamic segments with placeholders to prevent
    high cardinality in metrics.
    """
    parts = path.strip("/").split("/")
    normalized = []

    for part in parts:
        # Replace numeric IDs with placeholder
        if part.isdigit():
            normalized.append(":id")
        # Replace UUIDs with placeholder
        elif len(part) == 36 and part.count("-") == 4:
            normalized.append(":uuid")
        # Replace hashes with placeholder
        elif len(part) == 64 and all(c in "0123456789abcdef" for c in part.lower()):
            normalized.append(":hash")
        else:
            normalized.append(part)

    return "/" + "/".join(normalized) if normalized else "/"


def timed(metric_name: str | None = None):
    """
    Decorator for timing function execution.

    Args:
        metric_name: Custom metric name (defaults to function name)

    Usage:
        @timed("blockchain_mine")
        def mine_block():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = metric_name or f"function_{func.__name__}"
            try:
                from monitoring import metrics

                with metrics.timer(name):
                    return func(*args, **kwargs)
            except ImportError:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def counted(metric_name: str | None = None, labels: dict[str, str] | None = None):
    """
    Decorator for counting function calls.

    Args:
        metric_name: Custom metric name (defaults to function name)
        labels: Additional labels for the counter

    Usage:
        @counted("entries_added")
        def add_entry():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = metric_name or f"function_{func.__name__}_total"
            try:
                from monitoring import metrics

                metrics.increment(name, labels=labels)
            except ImportError:
                pass
            return func(*args, **kwargs)

        return wrapper

    return decorator
