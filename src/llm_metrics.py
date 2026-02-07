"""
LLM usage metrics for cost benchmarking.

Tracks:
- Number of LLM API calls per component
- Token usage (input/output) per call
- Latency per call
- Estimated cost per call (based on Anthropic Claude pricing)

Usage:
    from llm_metrics import llm_metrics

    # Record a call
    llm_metrics.record_call(
        component="validator",
        input_tokens=150,
        output_tokens=200,
        latency_ms=1200,
    )

    # Get summary
    summary = llm_metrics.get_summary()
"""

import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Anthropic Claude Sonnet pricing (per million tokens, as of 2026)
# Update these if pricing changes
COST_PER_M_INPUT_TOKENS = 3.00
COST_PER_M_OUTPUT_TOKENS = 15.00


@dataclass
class CallRecord:
    """A single LLM API call record."""

    component: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    timestamp: float


@dataclass
class ComponentMetrics:
    """Aggregated metrics for one component."""

    call_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0


class LLMMetrics:
    """Thread-safe LLM usage metrics tracker."""

    def __init__(self):
        self._lock = threading.Lock()
        self._calls: list[CallRecord] = []
        self._by_component: dict[str, ComponentMetrics] = {}

    def record_call(
        self,
        component: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
    ):
        """Record an LLM API call."""
        record = CallRecord(
            component=component,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            timestamp=time.time(),
        )

        with self._lock:
            self._calls.append(record)

            if component not in self._by_component:
                self._by_component[component] = ComponentMetrics()

            m = self._by_component[component]
            m.call_count += 1
            m.total_input_tokens += input_tokens
            m.total_output_tokens += output_tokens
            m.total_latency_ms += latency_ms
            m.min_latency_ms = min(m.min_latency_ms, latency_ms)
            m.max_latency_ms = max(m.max_latency_ms, latency_ms)

        logger.debug(
            "LLM call: component=%s input_tokens=%d output_tokens=%d latency_ms=%.0f",
            component,
            input_tokens,
            output_tokens,
            latency_ms,
        )

    def get_summary(self) -> dict:
        """Get a summary of all LLM metrics."""
        with self._lock:
            total_calls = len(self._calls)
            total_input = sum(c.input_tokens for c in self._calls)
            total_output = sum(c.output_tokens for c in self._calls)
            total_latency = sum(c.latency_ms for c in self._calls)

            cost_input = (total_input / 1_000_000) * COST_PER_M_INPUT_TOKENS
            cost_output = (total_output / 1_000_000) * COST_PER_M_OUTPUT_TOKENS
            total_cost = cost_input + cost_output

            components = {}
            for name, m in self._by_component.items():
                comp_cost_in = (m.total_input_tokens / 1_000_000) * COST_PER_M_INPUT_TOKENS
                comp_cost_out = (m.total_output_tokens / 1_000_000) * COST_PER_M_OUTPUT_TOKENS
                avg_latency = m.total_latency_ms / m.call_count if m.call_count else 0

                components[name] = {
                    "calls": m.call_count,
                    "input_tokens": m.total_input_tokens,
                    "output_tokens": m.total_output_tokens,
                    "avg_latency_ms": round(avg_latency, 1),
                    "min_latency_ms": round(m.min_latency_ms, 1) if m.min_latency_ms != float("inf") else 0,
                    "max_latency_ms": round(m.max_latency_ms, 1),
                    "estimated_cost_usd": round(comp_cost_in + comp_cost_out, 6),
                }

            return {
                "total_calls": total_calls,
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_latency_ms": round(total_latency, 1),
                "estimated_total_cost_usd": round(total_cost, 6),
                "cost_per_call_usd": round(total_cost / total_calls, 6) if total_calls else 0,
                "components": components,
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._calls.clear()
            self._by_component.clear()


# Singleton instance
llm_metrics = LLMMetrics()
