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
import re
import sys
import threading
from datetime import UTC, datetime
from typing import Any

# ============================================================
# Sensitive Data Redaction
# ============================================================

# Patterns for sensitive data that should be redacted in logs
SENSITIVE_PATTERNS = [
    # API keys and tokens
    (re.compile(r"(api[_-]?key|apikey|token|secret|password|passwd|pwd)([\"']?\s*[:=]\s*[\"']?)([^\s\"',}{]+)", re.IGNORECASE), r"\1\2[REDACTED]"),
    # Bearer tokens
    (re.compile(r"(Bearer\s+)([^\s]+)", re.IGNORECASE), r"\1[REDACTED]"),
    # Private keys (PEM format)
    (re.compile(r"-----BEGIN[^-]+PRIVATE KEY-----.*?-----END[^-]+PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    # Email addresses (partial redaction)
    (re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"), r"\1[...]@\2"),
    # Credit card numbers (basic pattern)
    (re.compile(r"\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b"), r"\1-****-****-\4"),
    # Wallet addresses (show first/last 4 chars)
    (re.compile(r"\b(0x)([a-fA-F0-9]{4})([a-fA-F0-9]{32})([a-fA-F0-9]{4})\b"), r"\1\2...\4"),
    # DID identifiers (show method, redact specific id)
    (re.compile(r"(did:[a-z]+:)([a-zA-Z0-9]{8})([a-zA-Z0-9]+)"), r"\1\2..."),
]

# Fields that should be completely redacted
REDACTED_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "api-key",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
    "private_keys",
    "secret_key",
    "auth",
    "authorization",
    "credential",
    "credentials",
}


def redact_sensitive_data(data: Any, depth: int = 0, max_depth: int = 10) -> Any:
    """
    Recursively redact sensitive data from logs.

    Args:
        data: The data to redact (can be dict, list, string, or other)
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Data with sensitive information redacted
    """
    if depth > max_depth:
        return "[MAX_DEPTH_EXCEEDED]"

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_")
            if key_lower in REDACTED_FIELDS:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive_data(value, depth + 1, max_depth)
        return result

    elif isinstance(data, list):
        return [redact_sensitive_data(item, depth + 1, max_depth) for item in data]

    elif isinstance(data, str):
        result = data
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    else:
        return data


def redact_string(text: str) -> str:
    """
    Redact sensitive patterns from a string.

    Args:
        text: The string to redact

    Returns:
        String with sensitive patterns redacted
    """
    if not isinstance(text, str):
        return text

    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result

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

    Automatically redacts sensitive data from log entries.
    """

    def __init__(self, include_stack_info: bool = True, redact_sensitive: bool = True):
        super().__init__()
        self.include_stack_info = include_stack_info
        self.redact_sensitive = redact_sensitive

    def format(self, record: logging.LogRecord) -> str:
        # Base log entry with redacted message
        message = record.getMessage()
        if self.redact_sensitive:
            message = redact_string(message)

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
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

        # Add request context (redacted)
        context = get_request_context()
        if context:
            if self.redact_sensitive:
                context = redact_sensitive_data(context)
            log_entry["context"] = context

        # Add any extra fields from the log call (redacted)
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
                    if self.redact_sensitive:
                        value = redact_sensitive_data(value)
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

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        clear_request_context()
        if self.previous_context:
            set_request_context(**self.previous_context)
        return False


# Initialize default logging on import
if not logging.getLogger().handlers:
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
    )
