"""
TPS Benchmark - Locust

Focused test for measuring maximum TPS (Transactions Per Second).

Run with:
    locust -f tests/load/locust/tps_benchmark.py --host=http://localhost:5000 --headless \
           -u 200 -r 50 -t 5m --csv=results/tps

This test:
1. Uses minimal wait times for maximum throughput
2. Focuses only on entry creation (the "transaction")
3. Skips validation to measure raw throughput
4. Reports detailed TPS metrics
"""

import json
import os
import random
import time
from datetime import datetime

from locust import HttpUser, LoadTestShape, constant_throughput, events, task
from locust.runners import MasterRunner

API_KEY = os.getenv("NATLANGCHAIN_API_KEY", "test-api-key")
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
}


def generate_minimal_entry():
    """Generate minimal entry for maximum throughput."""
    return {
        "content": f"TPS test entry {time.time_ns()}",
        "author": f"tps-{random.randint(1, 100)}",
        "intent": "benchmark",
        "validate": False,
        "auto_mine": False,
    }


class TPSUser(HttpUser):
    """
    User focused on maximum TPS.
    Uses constant throughput to achieve target TPS.
    """

    # Target: each user makes 10 requests per second
    wait_time = constant_throughput(10)

    @task
    def create_entry(self):
        """Create entry as fast as possible."""
        entry = generate_minimal_entry()
        with self.client.post(
            "/entry",
            json=entry,
            headers=HEADERS,
            name="TPS Entry",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 201):
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


class SteppedLoadShape(LoadTestShape):
    """
    Custom load shape for finding maximum sustainable TPS.

    Steps through increasing user counts, measuring TPS at each level.
    """

    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 5},  # 1 min @ 10 users
        {"duration": 120, "users": 25, "spawn_rate": 5},  # 2 min @ 25 users
        {"duration": 180, "users": 50, "spawn_rate": 10},  # 3 min @ 50 users
        {"duration": 240, "users": 100, "spawn_rate": 20},  # 4 min @ 100 users
        {"duration": 300, "users": 150, "spawn_rate": 25},  # 5 min @ 150 users
        {"duration": 360, "users": 200, "spawn_rate": 25},  # 6 min @ 200 users
        {"duration": 420, "users": 100, "spawn_rate": 25},  # 7 min @ 100 users (cooldown)
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])

        return None  # Stop the test


# Metrics tracking
tps_samples = []
start_time = None


@events.init.add_listener
def on_init(environment, **kwargs):
    """Initialize tracking."""
    global start_time, tps_samples
    start_time = time.time()
    tps_samples = []


@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    start_time=None,
    **kwargs,
):
    """Track each request for TPS calculation."""
    if name == "TPS Entry":
        tps_samples.append(
            {
                "timestamp": time.time(),
                "response_time": response_time,
                "success": exception is None,
            }
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Calculate and report TPS metrics."""
    stats = environment.stats.total

    print("\n" + "=" * 70)
    print("TPS BENCHMARK RESULTS")
    print("=" * 70)

    # Calculate TPS from samples
    if tps_samples:
        duration = tps_samples[-1]["timestamp"] - tps_samples[0]["timestamp"]
        successful = sum(1 for s in tps_samples if s["success"])
        actual_tps = successful / duration if duration > 0 else 0

        print("\nTHROUGHPUT:")
        print(f"  Total Transactions: {len(tps_samples)}")
        print(f"  Successful Transactions: {successful}")
        print(f"  Duration: {duration:.2f} seconds")
        print(f"  Actual TPS: {actual_tps:.2f}")
        print(f"  Reported RPS: {stats.total_rps:.2f}")

        # Time-window analysis
        print("\nTIME-WINDOW ANALYSIS:")
        window_size = 10  # seconds
        windows = {}
        for sample in tps_samples:
            window = int((sample["timestamp"] - tps_samples[0]["timestamp"]) / window_size)
            if window not in windows:
                windows[window] = {"total": 0, "success": 0}
            windows[window]["total"] += 1
            if sample["success"]:
                windows[window]["success"] += 1

        max_tps = 0
        for window, data in sorted(windows.items()):
            window_tps = data["success"] / window_size
            max_tps = max(max_tps, window_tps)
            print(
                f"  Window {window * window_size}-{(window + 1) * window_size}s: {window_tps:.2f} TPS"
            )

        print(f"\n  Peak TPS (10s window): {max_tps:.2f}")

    print("\nLATENCY:")
    print(f"  Average: {stats.avg_response_time:.2f}ms")
    print(f"  P50: {stats.get_response_time_percentile(0.5):.2f}ms")
    print(f"  P95: {stats.get_response_time_percentile(0.95):.2f}ms")
    print(f"  P99: {stats.get_response_time_percentile(0.99):.2f}ms")

    print("\nRELIABILITY:")
    print(f"  Success Rate: {(1 - stats.fail_ratio) * 100:.2f}%")
    print(f"  Failed Requests: {stats.num_failures}")

    print("\nCOMPARISON:")
    tps = stats.total_rps
    print(f"  vs Target (500 TPS): {(tps / 500 * 100):.1f}%")
    print(f"  vs Stretch (1000 TPS): {(tps / 1000 * 100):.1f}%")
    print(f"  vs Solana (65000 TPS): {(tps / 65000 * 100):.4f}%")

    print("=" * 70 + "\n")

    # Save detailed results
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "test": "tps-benchmark",
        "transactions": {
            "total": len(tps_samples) if tps_samples else stats.num_requests,
            "successful": sum(1 for s in tps_samples if s["success"])
            if tps_samples
            else stats.num_requests - stats.num_failures,
            "failed": stats.num_failures,
        },
        "throughput": {
            "actual_tps": actual_tps if tps_samples else stats.total_rps,
            "reported_rps": stats.total_rps,
            "peak_tps": max_tps if tps_samples else stats.total_rps,
        },
        "latency": {
            "avg_ms": stats.avg_response_time,
            "p50_ms": stats.get_response_time_percentile(0.5),
            "p95_ms": stats.get_response_time_percentile(0.95),
            "p99_ms": stats.get_response_time_percentile(0.99),
        },
        "comparison": {
            "target_500_tps": {"achieved": tps >= 500, "percent": tps / 500 * 100},
            "stretch_1000_tps": {"achieved": tps >= 1000, "percent": tps / 1000 * 100},
            "solana_65000_tps": {"percent": tps / 65000 * 100},
        },
    }

    results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(results_dir, exist_ok=True)

    with open(os.path.join(results_dir, "tps-benchmark-locust.json"), "w") as f:
        json.dump(results, f, indent=2)
