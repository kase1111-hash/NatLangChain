"""
Metrics collection for NatLangChain.

Provides a simple, thread-safe metrics collection system that tracks:
- Counters: Monotonically increasing values (requests, errors, etc.)
- Gauges: Point-in-time values (queue size, active connections)
- Histograms: Distribution of values (request latency)

Metrics are exposed in a format compatible with Prometheus scraping.
"""

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HistogramBucket:
    """A histogram bucket for tracking value distributions."""

    le: float  # Less than or equal to
    count: int = 0


@dataclass
class Histogram:
    """
    A histogram for tracking distributions of values.

    Uses configurable buckets for latency tracking.
    """

    name: str
    buckets: list[HistogramBucket] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0

    def __post_init__(self):
        if not self.buckets:
            # Default latency buckets in milliseconds
            default_bounds = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
            self.buckets = [HistogramBucket(le=b) for b in default_bounds]
            self.buckets.append(HistogramBucket(le=float("inf")))

    def observe(self, value: float) -> None:
        """Record an observation."""
        self.sum += value
        self.count += 1
        for bucket in self.buckets:
            if value <= bucket.le:
                bucket.count += 1


class MetricsCollector:
    """
    Thread-safe metrics collector.

    Collects counters, gauges, and histograms with optional labels.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._gauges: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._histograms: dict[str, dict[str, Histogram]] = defaultdict(dict)
        self._start_time = time.time()

        # Built-in metrics
        self.increment("app_start_total")

    def _labels_key(self, labels: dict[str, str] | None) -> str:
        """Convert labels dict to a hashable key."""
        if not labels:
            return ""
        return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))

    # Counter operations

    def increment(self, name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        with self._lock:
            key = self._labels_key(labels)
            self._counters[name][key] += value

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Get current counter value."""
        with self._lock:
            key = self._labels_key(labels)
            return self._counters[name].get(key, 0)

    # Gauge operations

    def set_gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        with self._lock:
            key = self._labels_key(labels)
            self._gauges[name][key] = value

    def increment_gauge(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Increment a gauge value."""
        with self._lock:
            key = self._labels_key(labels)
            self._gauges[name][key] += value

    def decrement_gauge(
        self, name: str, value: float = 1.0, labels: dict[str, str] | None = None
    ) -> None:
        """Decrement a gauge value."""
        with self._lock:
            key = self._labels_key(labels)
            self._gauges[name][key] -= value

    def get_gauge(self, name: str, labels: dict[str, str] | None = None) -> float:
        """Get current gauge value."""
        with self._lock:
            key = self._labels_key(labels)
            return self._gauges[name].get(key, 0.0)

    # Histogram operations

    def timing(self, name: str, value_ms: float, labels: dict[str, str] | None = None) -> None:
        """Record a timing observation in milliseconds."""
        with self._lock:
            key = self._labels_key(labels)
            if key not in self._histograms[name]:
                self._histograms[name][key] = Histogram(name=name)
            self._histograms[name][key].observe(value_ms)

    @contextmanager
    def timer(self, name: str, labels: dict[str, str] | None = None):
        """Context manager for timing code blocks."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.timing(name, elapsed_ms, labels)

    # Export methods

    def get_all(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        with self._lock:
            result = {
                "uptime_seconds": time.time() - self._start_time,
                "counters": {},
                "gauges": {},
                "histograms": {},
            }

            # Export counters
            for name, values in self._counters.items():
                if len(values) == 1 and "" in values:
                    result["counters"][name] = values[""]
                else:
                    result["counters"][name] = dict(values)

            # Export gauges
            for name, values in self._gauges.items():
                if len(values) == 1 and "" in values:
                    result["gauges"][name] = values[""]
                else:
                    result["gauges"][name] = dict(values)

            # Export histograms
            for name, histograms in self._histograms.items():
                result["histograms"][name] = {}
                for key, hist in histograms.items():
                    label_key = key if key else "_total"
                    result["histograms"][name][label_key] = {
                        "count": hist.count,
                        "sum": hist.sum,
                        "avg": hist.sum / hist.count if hist.count > 0 else 0,
                        "buckets": {str(b.le): b.count for b in hist.buckets},
                    }

            return result

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        with self._lock:
            # Uptime
            uptime = time.time() - self._start_time
            lines.append("# HELP natlangchain_uptime_seconds Time since application start")
            lines.append("# TYPE natlangchain_uptime_seconds gauge")
            lines.append(f"natlangchain_uptime_seconds {uptime:.2f}")
            lines.append("")

            # Counters
            for name, values in self._counters.items():
                metric_name = f"natlangchain_{name}"
                lines.append(f"# TYPE {metric_name} counter")
                for key, value in values.items():
                    if key:
                        lines.append(f"{metric_name}{{{key}}} {value}")
                    else:
                        lines.append(f"{metric_name} {value}")
                lines.append("")

            # Gauges
            for name, values in self._gauges.items():
                metric_name = f"natlangchain_{name}"
                lines.append(f"# TYPE {metric_name} gauge")
                for key, value in values.items():
                    if key:
                        lines.append(f"{metric_name}{{{key}}} {value}")
                    else:
                        lines.append(f"{metric_name} {value}")
                lines.append("")

            # Histograms
            for name, histograms in self._histograms.items():
                metric_name = f"natlangchain_{name}"
                lines.append(f"# TYPE {metric_name} histogram")
                for key, hist in histograms.items():
                    label_prefix = f"{{{key}," if key else "{"
                    label_suffix = "}" if key else ""

                    for bucket in hist.buckets:
                        le_val = "+Inf" if bucket.le == float("inf") else bucket.le
                        if key:
                            lines.append(
                                f'{metric_name}_bucket{{{key},le="{le_val}"}} {bucket.count}'
                            )
                        else:
                            lines.append(f'{metric_name}_bucket{{le="{le_val}"}} {bucket.count}')

                    if key:
                        lines.append(f"{metric_name}_sum{{{key}}} {hist.sum:.2f}")
                        lines.append(f"{metric_name}_count{{{key}}} {hist.count}")
                    else:
                        lines.append(f"{metric_name}_sum {hist.sum:.2f}")
                        lines.append(f"{metric_name}_count {hist.count}")
                lines.append("")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._start_time = time.time()


# Global metrics instance
metrics = MetricsCollector()


# Convenience functions
def increment(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None:
    """Increment a counter."""
    metrics.increment(name, value, labels)


def set_gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None:
    """Set a gauge value."""
    metrics.set_gauge(name, value, labels)


def timing(name: str, value_ms: float, labels: dict[str, str] | None = None) -> None:
    """Record a timing observation."""
    metrics.timing(name, value_ms, labels)


def timer(name: str, labels: dict[str, str] | None = None):
    """Context manager for timing code blocks."""
    return metrics.timer(name, labels)
