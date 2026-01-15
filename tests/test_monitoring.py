"""
Tests for monitoring and metrics infrastructure.
"""

import json
import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

# Skip all tests if monitoring dependencies are not available
try:
    from monitoring.logging import (
        JSONFormatter,
        LoggingContext,
        clear_request_context,
        get_logger,
        get_request_context,
        set_request_context,
    )
    from monitoring.metrics import MetricsCollector, metrics as global_metrics

    MONITORING_AVAILABLE = True
except ImportError as e:
    MONITORING_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason=f"monitoring module not available (flask required): {e}")


class TestMetricsCollector:
    """Tests for the MetricsCollector class."""

    def test_counter_increment(self):
        """Test basic counter increments."""
        m = MetricsCollector()
        m.increment("test_counter")
        assert m.get_counter("test_counter") == 1

        m.increment("test_counter", 5)
        assert m.get_counter("test_counter") == 6

    def test_counter_with_labels(self):
        """Test counters with labels."""
        m = MetricsCollector()
        m.increment("http_requests", labels={"method": "GET"})
        m.increment("http_requests", labels={"method": "POST"})
        m.increment("http_requests", labels={"method": "GET"})

        assert m.get_counter("http_requests", labels={"method": "GET"}) == 2
        assert m.get_counter("http_requests", labels={"method": "POST"}) == 1

    def test_gauge_set(self):
        """Test gauge setting."""
        m = MetricsCollector()
        m.set_gauge("active_connections", 10)
        assert m.get_gauge("active_connections") == 10

        m.set_gauge("active_connections", 5)
        assert m.get_gauge("active_connections") == 5

    def test_gauge_increment_decrement(self):
        """Test gauge increment and decrement."""
        m = MetricsCollector()
        m.set_gauge("queue_size", 10)
        m.increment_gauge("queue_size", 3)
        assert m.get_gauge("queue_size") == 13

        m.decrement_gauge("queue_size", 5)
        assert m.get_gauge("queue_size") == 8

    def test_histogram_timing(self):
        """Test histogram timing observations."""
        m = MetricsCollector()
        m.timing("request_duration", 50)
        m.timing("request_duration", 100)
        m.timing("request_duration", 150)

        data = m.get_all()
        hist = data["histograms"]["request_duration"]["_total"]

        assert hist["count"] == 3
        assert hist["sum"] == 300
        assert hist["avg"] == 100

    def test_timer_context_manager(self):
        """Test the timer context manager."""
        m = MetricsCollector()

        with m.timer("operation_time"):
            time.sleep(0.01)  # 10ms

        data = m.get_all()
        hist = data["histograms"]["operation_time"]["_total"]
        assert hist["count"] == 1
        assert hist["sum"] >= 10  # At least 10ms

    def test_get_all(self):
        """Test getting all metrics."""
        m = MetricsCollector()
        m.increment("counter1")
        m.set_gauge("gauge1", 42)
        m.timing("timing1", 100)

        data = m.get_all()

        assert "uptime_seconds" in data
        assert data["counters"]["counter1"] == 1
        assert data["gauges"]["gauge1"] == 42
        assert "timing1" in data["histograms"]

    def test_prometheus_format(self):
        """Test Prometheus text format export."""
        m = MetricsCollector()
        m.increment("test_requests", labels={"status": "200"})
        m.set_gauge("test_gauge", 42)
        m.timing("test_latency", 100)

        output = m.to_prometheus()

        assert "natlangchain_test_requests" in output
        assert "natlangchain_test_gauge 42" in output
        assert "natlangchain_test_latency_bucket" in output
        assert "natlangchain_uptime_seconds" in output

    def test_reset(self):
        """Test resetting all metrics."""
        m = MetricsCollector()
        m.increment("counter")
        m.set_gauge("gauge", 10)

        m.reset()

        assert m.get_counter("counter") == 0
        assert m.get_gauge("gauge") == 0

    def test_thread_safety(self):
        """Test thread-safe counter increments."""
        m = MetricsCollector()
        results = []

        def increment_many():
            for _ in range(100):
                m.increment("concurrent_counter")
            results.append(True)

        threads = [threading.Thread(target=increment_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert m.get_counter("concurrent_counter") == 1000


class TestStructuredLogging:
    """Tests for structured logging functionality."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        assert logger is not None
        assert logger.name == "test_module"

    def test_request_context(self):
        """Test request context management."""
        set_request_context(request_id="abc123", user="alice")
        context = get_request_context()

        assert context["request_id"] == "abc123"
        assert context["user"] == "alice"

        clear_request_context()
        assert get_request_context() == {}

    def test_logging_context_manager(self):
        """Test the LoggingContext context manager."""
        with LoggingContext(request_id="ctx123", action="test"):
            context = get_request_context()
            assert context["request_id"] == "ctx123"
            assert context["action"] == "test"

        # Context should be cleared after exiting
        assert get_request_context() == {}

    def test_json_formatter(self):
        """Test JSON log formatting."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_json_formatter_with_context(self):
        """Test JSON formatter includes request context."""
        set_request_context(request_id="req123")

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["context"]["request_id"] == "req123"

        clear_request_context()

    def test_json_formatter_with_exception(self):
        """Test JSON formatter includes exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]


class TestMiddlewareDecorators:
    """Tests for middleware decorators."""

    def test_timed_decorator(self):
        """Test the @timed decorator works and tracks time."""
        from monitoring.middleware import timed

        # Use a unique metric name to avoid conflicts
        metric_name = f"test_function_{time.time_ns()}"

        @timed(metric_name)
        def slow_function():
            time.sleep(0.01)
            return 42

        result = slow_function()
        assert result == 42

        # Verify the metric was recorded
        data = global_metrics.get_all()
        assert metric_name in data["histograms"]
        assert data["histograms"][metric_name]["_total"]["count"] >= 1

    def test_counted_decorator(self):
        """Test the @counted decorator increments counter."""
        from monitoring.middleware import counted

        # Use a unique metric name to avoid conflicts
        metric_name = f"test_calls_{time.time_ns()}"

        @counted(metric_name)
        def test_function():
            return "hello"

        initial = global_metrics.get_counter(metric_name)

        test_function()
        test_function()
        test_function()

        assert global_metrics.get_counter(metric_name) == initial + 3


class TestGlobalMetrics:
    """Tests for global metrics instance."""

    def test_global_instance_exists(self):
        """Test that global metrics instance is available."""
        assert global_metrics is not None
        assert isinstance(global_metrics, MetricsCollector)

    def test_global_counter(self):
        """Test using global metrics counter."""
        initial = global_metrics.get_counter("test_global")
        global_metrics.increment("test_global")
        assert global_metrics.get_counter("test_global") == initial + 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
