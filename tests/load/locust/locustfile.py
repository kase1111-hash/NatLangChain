"""
NatLangChain Load Tests - Locust

Comprehensive load testing suite using Locust.

Run with:
    locust -f tests/load/locust/locustfile.py --host=http://localhost:5000

Web UI: http://localhost:8089
Headless: locust -f locustfile.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m
"""

import os
import json
import random
import time
from datetime import datetime
from locust import HttpUser, task, between, events, tag
from locust.runners import MasterRunner, WorkerRunner


# Configuration
API_KEY = os.getenv("NATLANGCHAIN_API_KEY", "test-api-key")
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}

# Test data generators
INTENTS = [
    "Record a transaction",
    "Log an agreement",
    "Document a decision",
    "Register an event",
    "Capture a statement",
]

CONTENTS = [
    "This is a test entry for load testing purposes.",
    "Recording performance metrics under stress.",
    "Validating throughput capacity of the system.",
    "Testing concurrent entry creation.",
    "Measuring latency under high load.",
]

SEARCH_QUERIES = [
    "transaction record",
    "agreement terms",
    "performance metrics",
    "system validation",
    "throughput test",
]


def generate_entry():
    """Generate a random entry for testing."""
    return {
        "content": f"{random.choice(CONTENTS)} {int(time.time() * 1000)}",
        "author": f"loadtest-user-{random.randint(1, 1000)}",
        "intent": random.choice(INTENTS),
        "metadata": {
            "test_run": os.getenv("LOCUST_TEST_RUN", "default"),
            "timestamp": datetime.utcnow().isoformat(),
        },
        "validate": False,
        "auto_mine": False,
    }


class NatLangChainUser(HttpUser):
    """
    Simulates a typical NatLangChain API user.
    Mix of read and write operations.
    """

    wait_time = between(0.1, 0.5)  # 100-500ms between requests
    weight = 10  # Default weight

    def on_start(self):
        """Verify API is accessible on user start."""
        response = self.client.get("/health")
        if response.status_code != 200:
            raise Exception(f"API not accessible: {response.status_code}")

    @task(10)
    @tag("read", "health")
    def health_check(self):
        """Basic health check - lightweight."""
        self.client.get("/health", name="/health")

    @task(5)
    @tag("read", "chain")
    def get_chain(self):
        """Get the full blockchain."""
        self.client.get("/chain", name="/chain")

    @task(3)
    @tag("read", "stats")
    def get_stats(self):
        """Get blockchain statistics."""
        self.client.get("/stats", name="/stats")

    @task(20)
    @tag("write", "entry")
    def create_entry(self):
        """Create a new entry - primary write operation."""
        entry = generate_entry()
        self.client.post(
            "/entry",
            json=entry,
            headers=HEADERS,
            name="/entry [POST]",
        )

    @task(5)
    @tag("read", "search")
    def search_entries(self):
        """Search entries by keyword."""
        query = random.choice(SEARCH_QUERIES)
        self.client.get(
            f"/entries/search?q={query}",
            name="/entries/search",
        )

    @task(2)
    @tag("read", "validate")
    def validate_chain(self):
        """Validate the blockchain."""
        self.client.get("/validate/chain", name="/validate/chain")

    @task(1)
    @tag("read", "block")
    def get_latest_block(self):
        """Get the latest block."""
        self.client.get("/block/latest", name="/block/latest")


class HighThroughputUser(HttpUser):
    """
    High-throughput user focused on write operations.
    Used for TPS benchmarking.
    """

    wait_time = between(0.01, 0.05)  # Very short wait time
    weight = 5

    @task(1)
    @tag("write", "entry", "tps")
    def rapid_entry_creation(self):
        """Rapid entry creation for TPS testing."""
        entry = generate_entry()
        self.client.post(
            "/entry",
            json=entry,
            headers=HEADERS,
            name="/entry [TPS]",
        )


class ReadHeavyUser(HttpUser):
    """
    Read-heavy user for testing read scalability.
    """

    wait_time = between(0.1, 0.3)
    weight = 3

    @task(10)
    @tag("read")
    def read_chain(self):
        """Read the chain repeatedly."""
        self.client.get("/chain", name="/chain [read-heavy]")

    @task(5)
    @tag("read")
    def read_stats(self):
        """Read stats repeatedly."""
        self.client.get("/stats", name="/stats [read-heavy]")

    @task(3)
    @tag("read")
    def read_health(self):
        """Read health repeatedly."""
        self.client.get("/health", name="/health [read-heavy]")


# Event handlers for custom reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("\n" + "=" * 60)
    print("NatLangChain Load Test Started")
    print("=" * 60)
    print(f"Target Host: {environment.host}")
    print(f"Start Time: {datetime.utcnow().isoformat()}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    stats = environment.stats

    print("\n" + "=" * 60)
    print("NatLangChain Load Test Results")
    print("=" * 60)
    print(f"Total Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Failure Rate: {(stats.total.num_failures / max(stats.total.num_requests, 1) * 100):.2f}%")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")
    print(f"Avg Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"P50 Response Time: {stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"P95 Response Time: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99 Response Time: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print("=" * 60)

    # TPS Comparison
    tps = stats.total.total_rps
    print("\nTPS COMPARISON:")
    print(f"  Achieved TPS: {tps:.2f}")
    print(f"  Target (500 TPS): {(tps / 500 * 100):.1f}% achieved")
    print(f"  Stretch (1000 TPS): {(tps / 1000 * 100):.1f}% achieved")
    print(f"  Solana (65000 TPS): {(tps / 65000 * 100):.4f}% of Solana")
    print("=" * 60 + "\n")

    # Save results to file
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "host": environment.host,
        "total_requests": stats.total.num_requests,
        "failed_requests": stats.total.num_failures,
        "failure_rate_percent": stats.total.num_failures / max(stats.total.num_requests, 1) * 100,
        "requests_per_second": stats.total.total_rps,
        "avg_response_time_ms": stats.total.avg_response_time,
        "p50_response_time_ms": stats.total.get_response_time_percentile(0.5),
        "p95_response_time_ms": stats.total.get_response_time_percentile(0.95),
        "p99_response_time_ms": stats.total.get_response_time_percentile(0.99),
        "comparison": {
            "target_500_tps_percent": tps / 500 * 100,
            "stretch_1000_tps_percent": tps / 1000 * 100,
            "solana_65000_tps_percent": tps / 65000 * 100,
        },
    }

    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, "locust-results.json")

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {results_file}")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track individual requests for detailed analysis."""
    # Could add custom metrics here
    pass
