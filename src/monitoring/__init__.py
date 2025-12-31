"""
Monitoring and metrics infrastructure for NatLangChain.

This package provides:
- Application metrics collection (counters, gauges, histograms)
- Structured logging with JSON output
- Request timing middleware
- Health and readiness endpoints

Usage:
    from monitoring import metrics, get_logger

    # Record a metric
    metrics.increment("entries_added")
    metrics.timing("request_duration_ms", 42.5)

    # Get a logger
    logger = get_logger("my_module")
    logger.info("Something happened", extra={"user_id": "123"})
"""

from monitoring.metrics import MetricsCollector, metrics
from monitoring.logging import get_logger, configure_logging
from monitoring.middleware import setup_request_logging, timed, counted

__all__ = [
    "MetricsCollector",
    "metrics",
    "get_logger",
    "configure_logging",
    "setup_request_logging",
    "timed",
    "counted",
]
