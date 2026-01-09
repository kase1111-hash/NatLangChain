"""
Structured logging for NatLangChain.

Provides JSON-formatted logging suitable for log aggregation systems
like ELK stack, Datadog, or CloudWatch.

Features:
- JSON output format for easy parsing
- Request context (request_id, user, etc.)
- Automatic timestamp and level formatting
- Configurable log levels per module
"""

import json
import logging
import os
import sys
import threading
from datetime import UTC, datetime
from typing import Any

# Thread-local storage for request context
_request_context = threading.local()


def set_request_context(**kwargs) -> None:
    """Set context values for the current request."""
    if not hasattr(_request_context, "data"):
        _request_context.data = {}
    _request_context.data.update(kwargs)


def clear_request_context() -> None:
    """Clear request context after request completes."""
    _request_context.data = {}


def get_request_context() -> dict[str, Any]:
    """Get current request context."""
    return getattr(_request_context, "data", {})


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Output format:
    {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "level": "INFO",
        "logger": "api.core",
        "message": "Request processed",
        "request_id": "abc123",
        "duration_ms": 42,
        ...
    }
    """

    def __init__(self, include_stack_info: bool = True):
        super().__init__()
        self.include_stack_info = include_stack_info

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add location info for errors
        if record.levelno >= logging.WARNING:
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add exception info if present
        if record.exc_info and self.include_stack_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add request context
        context = get_request_context()
        if context:
            log_entry["context"] = context

        # Add any extra fields from the log call
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in (
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "stack_info",
                    "exc_info",
                    "exc_text",
                    "thread",
                    "threadName",
                    "message",
                    "taskName",
                ):
                    log_entry[key] = value

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Human-readable console formatter with colors.

    For development use - shows colored, readable output.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        level = record.levelname[0]

        # Build the message
        msg = f"{color}{timestamp} {level} [{record.name}]{reset} {record.getMessage()}"

        # Add context if present
        context = get_request_context()
        if context:
            ctx_str = " ".join(f"{k}={v}" for k, v in context.items())
            msg += f" {color}({ctx_str}){reset}"

        # Add extra fields
        extras = []
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            ):
                extras.append(f"{key}={value}")

        if extras:
            msg += f" [{', '.join(extras)}]"

        # Add exception info
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return msg


def configure_logging(
    level: str = "INFO",
    json_output: bool | None = None,
    log_file: str | None = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Use JSON format (auto-detected if None based on environment)
        log_file: Optional file path for log output
    """
    # Auto-detect JSON mode based on environment
    if json_output is None:
        # Use JSON in production, console format in development
        json_output = os.getenv("LOG_FORMAT", "").lower() == "json"

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Choose formatter
    if json_output:
        formatter = JSONFormatter()
    else:
        formatter = ConsoleFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


class LoggingContext:
    """
    Context manager for adding temporary context to logs.

    Usage:
        with LoggingContext(request_id="abc123", user="alice"):
            logger.info("Processing request")
    """

    def __init__(self, **kwargs):
        self.context = kwargs
        self.previous_context = {}

    def __enter__(self):
        self.previous_context = get_request_context().copy()
        set_request_context(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        clear_request_context()
        if self.previous_context:
            set_request_context(**self.previous_context)
        return False


# Initialize default logging on import
if not logging.getLogger().handlers:
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
    )
