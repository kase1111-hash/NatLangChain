"""
TPS Throughput Benchmark Tests for NatLangChain.

Measures transactions per second (TPS) for various operations:
- Entry submission throughput
- Block mining throughput
- API query throughput
- End-to-end throughput with compression
- Concurrent access patterns

Usage:
    # Run all benchmarks
    pytest tests/test_throughput.py -v -s

    # Run specific benchmark
    pytest tests/test_throughput.py::TestEntryThroughput -v -s

    # Run with detailed output
    pytest tests/test_throughput.py -v -s --tb=short

Note: These are performance benchmarks, not correctness tests.
Results will vary based on hardware.
"""

import gc
import json
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

import pytest

# Add src to path
sys.path.insert(0, "src")

from blockchain import NatLangChain, NaturalLanguageEntry

# =============================================================================
# Benchmark Configuration
# =============================================================================


@dataclass
class BenchmarkConfig:
    """Configuration for throughput benchmarks."""

    # Entry submission benchmarks
    entry_batch_size: int = 100
    entry_iterations: int = 5

    # Block mining benchmarks
    mining_batch_size: int = 50
    mining_iterations: int = 3
    mining_difficulty: int = 1  # Low difficulty for speed

    # Query benchmarks
    query_iterations: int = 100
    query_chain_size: int = 20  # Blocks in chain for query tests

    # Concurrent benchmarks
    concurrent_threads: int = 4
    concurrent_entries_per_thread: int = 25

    # Warmup settings
    warmup_iterations: int = 2

    # GC settings
    disable_gc: bool = True  # Disable GC during benchmarks for consistency


# Default configuration
CONFIG = BenchmarkConfig()


# =============================================================================
# Sample Data Generators
# =============================================================================

SAMPLE_PROSE = """
This agreement, entered into on this day, establishes a binding commitment
between the undersigned parties. The terms herein shall govern all subsequent
transactions and interactions, with particular emphasis on the mutual obligations
and responsibilities that each party agrees to uphold in good faith.
"""

SAMPLE_INTENTS = [
    "Record a contractual agreement",
    "Document a property transfer",
    "Register a service commitment",
    "Log a financial transaction",
    "Archive a legal declaration",
]

SAMPLE_AUTHORS = [
    "alice@example.com",
    "bob@example.com",
    "charlie@example.com",
    "diana@example.com",
    "eve@example.com",
]


def generate_entry(index: int) -> NaturalLanguageEntry:
    """Generate a test entry with unique content."""
    return NaturalLanguageEntry(
        content=f"{SAMPLE_PROSE} Transaction reference: TXN-{index:06d}",
        author=SAMPLE_AUTHORS[index % len(SAMPLE_AUTHORS)],
        intent=SAMPLE_INTENTS[index % len(SAMPLE_INTENTS)],
        metadata={"tx_id": f"TXN-{index:06d}", "sequence": index},
    )


def create_test_chain(
    num_blocks: int = 10, entries_per_block: int = 5, difficulty: int = 1
) -> NatLangChain:
    """Create a test blockchain with specified structure."""
    chain = NatLangChain(
        require_validation=False,
        enable_deduplication=False,
        enable_rate_limiting=False,
        enable_timestamp_validation=False,
        enable_metadata_sanitization=False,
        enable_asset_tracking=False,
        enable_quality_checks=False,
    )

    entry_num = 0
    for _ in range(num_blocks):
        for _ in range(entries_per_block):
            entry = generate_entry(entry_num)
            chain.add_entry(entry)
            entry_num += 1
        chain.mine_pending_entries(difficulty=difficulty)

    return chain


# =============================================================================
# Benchmark Result Classes
# =============================================================================


@dataclass
class ThroughputResult:
    """Result of a throughput benchmark."""

    name: str
    total_operations: int
    total_time_seconds: float
    operations_per_second: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_latency_ms: float
    percentile_50_ms: float
    percentile_95_ms: float
    percentile_99_ms: float

    def __str__(self) -> str:
        return (
            f"\n{'=' * 60}\n"
            f"  {self.name}\n"
            f"{'=' * 60}\n"
            f"  Throughput:     {self.operations_per_second:,.1f} ops/sec\n"
            f"  Total Ops:      {self.total_operations:,}\n"
            f"  Total Time:     {self.total_time_seconds:.3f}s\n"
            f"  Latency (avg):  {self.avg_latency_ms:.3f}ms\n"
            f"  Latency (min):  {self.min_latency_ms:.3f}ms\n"
            f"  Latency (max):  {self.max_latency_ms:.3f}ms\n"
            f"  Latency (std):  {self.std_latency_ms:.3f}ms\n"
            f"  P50:            {self.percentile_50_ms:.3f}ms\n"
            f"  P95:            {self.percentile_95_ms:.3f}ms\n"
            f"  P99:            {self.percentile_99_ms:.3f}ms\n"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total_operations": self.total_operations,
            "total_time_seconds": self.total_time_seconds,
            "ops_per_second": self.operations_per_second,
            "latency_avg_ms": self.avg_latency_ms,
            "latency_min_ms": self.min_latency_ms,
            "latency_max_ms": self.max_latency_ms,
            "latency_std_ms": self.std_latency_ms,
            "latency_p50_ms": self.percentile_50_ms,
            "latency_p95_ms": self.percentile_95_ms,
            "latency_p99_ms": self.percentile_99_ms,
        }


def calculate_percentile(data: list[float], percentile: float) -> float:
    """Calculate percentile from sorted data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (percentile / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def compute_throughput_result(name: str, latencies: list[float]) -> ThroughputResult:
    """Compute throughput statistics from latency measurements."""
    total_ops = len(latencies)
    total_time = sum(latencies)

    if total_time == 0:
        total_time = 0.001  # Avoid division by zero

    latencies_ms = [lat * 1000 for lat in latencies]  # Convert to ms

    return ThroughputResult(
        name=name,
        total_operations=total_ops,
        total_time_seconds=total_time,
        operations_per_second=total_ops / total_time,
        avg_latency_ms=statistics.mean(latencies_ms) if latencies_ms else 0,
        min_latency_ms=min(latencies_ms) if latencies_ms else 0,
        max_latency_ms=max(latencies_ms) if latencies_ms else 0,
        std_latency_ms=statistics.stdev(latencies_ms) if len(latencies_ms) > 1 else 0,
        percentile_50_ms=calculate_percentile(latencies_ms, 50),
        percentile_95_ms=calculate_percentile(latencies_ms, 95),
        percentile_99_ms=calculate_percentile(latencies_ms, 99),
    )


# =============================================================================
# Entry Submission Throughput Tests
# =============================================================================


class TestEntryThroughput:
    """Benchmark entry submission throughput."""

    @pytest.fixture
    def chain(self):
        """Create a fresh blockchain for each test."""
        return NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False,
            enable_asset_tracking=False,
            enable_quality_checks=False,
        )

    def test_entry_submission_tps(self, chain):
        """Measure entry submission throughput (TPS)."""
        latencies = []
        entry_num = 0

        # Warmup
        for _ in range(CONFIG.warmup_iterations):
            entry = generate_entry(entry_num)
            chain.add_entry(entry)
            entry_num += 1
        chain.pending_entries.clear()

        # Disable GC for consistent timing
        if CONFIG.disable_gc:
            gc.disable()

        try:
            for _ in range(CONFIG.entry_iterations):
                for _ in range(CONFIG.entry_batch_size):
                    entry = generate_entry(entry_num)

                    start = time.perf_counter()
                    chain.add_entry(entry)
                    elapsed = time.perf_counter() - start

                    latencies.append(elapsed)
                    entry_num += 1

                # Clear pending entries between batches
                chain.pending_entries.clear()
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Entry Submission TPS", latencies)
        print(result)

        # Sanity check: should handle at least 100 entries/sec
        assert result.operations_per_second > 100, (
            f"Entry submission too slow: {result.operations_per_second:.1f} TPS"
        )

    def test_entry_with_validation_hooks(self, chain):
        """Measure entry submission with all validation hooks enabled."""
        chain_full = NatLangChain(
            require_validation=False,  # Skip LLM validation
            enable_deduplication=True,
            enable_rate_limiting=True,
            enable_timestamp_validation=True,
            enable_metadata_sanitization=True,
            enable_asset_tracking=False,
            enable_quality_checks=False,
        )

        latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for i in range(CONFIG.entry_batch_size):
                # Use unique authors to avoid rate limits
                entry = NaturalLanguageEntry(
                    content=f"{SAMPLE_PROSE} Unique ref: {i}",
                    author=f"author_{i}@example.com",
                    intent="Record transaction",
                    metadata={"seq": i},
                )

                start = time.perf_counter()
                chain_full.add_entry(entry)
                elapsed = time.perf_counter() - start

                latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Entry with Validation Hooks", latencies)
        print(result)

        # Validation hooks add overhead but should still be reasonable
        assert result.operations_per_second > 50


# =============================================================================
# Block Mining Throughput Tests
# =============================================================================


class TestMiningThroughput:
    """Benchmark block mining throughput."""

    def test_mining_tps(self):
        """Measure block mining throughput."""
        latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for iteration in range(CONFIG.mining_iterations):
                # Create fresh chain for each iteration
                chain = NatLangChain(
                    require_validation=False,
                    enable_deduplication=False,
                    enable_rate_limiting=False,
                    enable_timestamp_validation=False,
                    enable_metadata_sanitization=False,
                    enable_asset_tracking=False,
                    enable_quality_checks=False,
                )

                # Add entries to mine
                for i in range(CONFIG.mining_batch_size):
                    entry = generate_entry(iteration * CONFIG.mining_batch_size + i)
                    chain.add_entry(entry)

                # Measure mining time
                start = time.perf_counter()
                block = chain.mine_pending_entries(difficulty=CONFIG.mining_difficulty)
                elapsed = time.perf_counter() - start

                assert block is not None
                latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Block Mining TPS", latencies)
        print(result)

        # Calculate effective TPS (entries per second)
        entries_per_second = (
            CONFIG.mining_batch_size * CONFIG.mining_iterations
        ) / result.total_time_seconds
        print(f"  Effective Entry TPS: {entries_per_second:,.1f} entries/sec")
        print(f"  Entries per Block: {CONFIG.mining_batch_size}")

    def test_mining_difficulty_scaling(self):
        """Measure how mining time scales with difficulty."""
        results = []

        for difficulty in [1, 2, 3]:
            chain = NatLangChain(
                require_validation=False,
                enable_deduplication=False,
                enable_rate_limiting=False,
            )

            # Add entries
            for i in range(20):
                chain.add_entry(generate_entry(i))

            # Time mining
            start = time.perf_counter()
            chain.mine_pending_entries(difficulty=difficulty)
            elapsed = time.perf_counter() - start

            results.append((difficulty, elapsed))
            print(f"  Difficulty {difficulty}: {elapsed * 1000:.2f}ms")

        # Higher difficulty should take longer (exponential scaling)
        assert results[1][1] > results[0][1], "Difficulty 2 should take longer than 1"


# =============================================================================
# Query Throughput Tests
# =============================================================================


class TestQueryThroughput:
    """Benchmark blockchain query throughput."""

    @pytest.fixture
    def populated_chain(self):
        """Create a blockchain with test data."""
        return create_test_chain(
            num_blocks=CONFIG.query_chain_size, entries_per_block=10, difficulty=1
        )

    def test_chain_validation_tps(self, populated_chain):
        """Measure chain validation throughput."""
        latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for _ in range(CONFIG.query_iterations):
                start = time.perf_counter()
                result = populated_chain.validate_chain()
                elapsed = time.perf_counter() - start

                assert result is True
                latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Chain Validation TPS", latencies)
        print(result)
        print(f"  Chain Length: {len(populated_chain.chain)} blocks")

    def test_get_entries_by_author_tps(self, populated_chain):
        """Measure author query throughput."""
        latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for i in range(CONFIG.query_iterations):
                author = SAMPLE_AUTHORS[i % len(SAMPLE_AUTHORS)]

                start = time.perf_counter()
                entries = populated_chain.get_entries_by_author(author)
                elapsed = time.perf_counter() - start

                assert len(entries) > 0
                latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Get Entries by Author TPS", latencies)
        print(result)

    def test_to_dict_serialization_tps(self, populated_chain):
        """Measure blockchain serialization throughput."""
        latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for _ in range(CONFIG.query_iterations):
                start = time.perf_counter()
                data = populated_chain.to_dict()
                elapsed = time.perf_counter() - start

                assert "chain" in data
                latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        result = compute_throughput_result("Chain Serialization TPS", latencies)
        print(result)

        # Measure serialized size
        json_str = json.dumps(data)
        print(f"  Serialized Size: {len(json_str):,} bytes")


# =============================================================================
# Concurrent Access Tests
# =============================================================================


class TestConcurrentThroughput:
    """Benchmark concurrent access patterns."""

    def test_concurrent_entry_submission(self):
        """Measure concurrent entry submission throughput."""
        chain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False,
            enable_asset_tracking=False,
            enable_quality_checks=False,
        )

        # Thread-safe counters
        all_latencies = []
        lock = threading.Lock()

        def submit_entries(thread_id: int):
            thread_latencies = []
            base_idx = thread_id * CONFIG.concurrent_entries_per_thread

            for i in range(CONFIG.concurrent_entries_per_thread):
                entry = generate_entry(base_idx + i)

                start = time.perf_counter()
                chain.add_entry(entry)
                elapsed = time.perf_counter() - start

                thread_latencies.append(elapsed)

            with lock:
                all_latencies.extend(thread_latencies)

        # Run concurrent submissions
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=CONFIG.concurrent_threads) as executor:
            futures = [executor.submit(submit_entries, i) for i in range(CONFIG.concurrent_threads)]
            for future in as_completed(futures):
                future.result()  # Raise any exceptions

        total_time = time.perf_counter() - start_time
        total_ops = CONFIG.concurrent_threads * CONFIG.concurrent_entries_per_thread

        result = compute_throughput_result("Concurrent Entry Submission", all_latencies)
        print(result)
        print(f"  Threads: {CONFIG.concurrent_threads}")
        print(f"  Aggregate TPS: {total_ops / total_time:,.1f} ops/sec")

    def test_concurrent_read_write(self):
        """Measure mixed read/write concurrent access."""
        chain = create_test_chain(num_blocks=10, entries_per_block=5)

        read_latencies = []
        write_latencies = []
        lock = threading.Lock()

        def reader(iterations: int):
            local_latencies = []
            for i in range(iterations):
                author = SAMPLE_AUTHORS[i % len(SAMPLE_AUTHORS)]

                start = time.perf_counter()
                chain.get_entries_by_author(author)
                elapsed = time.perf_counter() - start

                local_latencies.append(elapsed)

            with lock:
                read_latencies.extend(local_latencies)

        def writer(base_idx: int, count: int):
            local_latencies = []
            for i in range(count):
                entry = generate_entry(base_idx + i)

                start = time.perf_counter()
                chain.add_entry(entry)
                elapsed = time.perf_counter() - start

                local_latencies.append(elapsed)

            with lock:
                write_latencies.extend(local_latencies)

        # Run mixed workload
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(reader, 50),
                executor.submit(reader, 50),
                executor.submit(writer, 1000, 25),
                executor.submit(writer, 2000, 25),
            ]
            for future in as_completed(futures):
                future.result()

        read_result = compute_throughput_result("Concurrent Reads", read_latencies)
        write_result = compute_throughput_result("Concurrent Writes", write_latencies)

        print(read_result)
        print(write_result)


# =============================================================================
# Compression Throughput Tests
# =============================================================================


class TestCompressionThroughput:
    """Benchmark compression impact on throughput."""

    def test_compression_overhead(self):
        """Measure compression/decompression overhead."""
        try:
            from block_compression import BlockCompressor
        except ImportError:
            pytest.skip("block_compression module not available")

        compressor = BlockCompressor(compression_level=6)
        chain = create_test_chain(num_blocks=5, entries_per_block=10)
        chain_data = chain.to_dict()
        json_bytes = json.dumps(chain_data).encode("utf-8")

        # Measure compression throughput
        compress_latencies = []
        decompress_latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            for _ in range(CONFIG.query_iterations):
                # Compression
                start = time.perf_counter()
                result = compressor.compress(json_bytes)
                elapsed = time.perf_counter() - start
                compress_latencies.append(elapsed)

                # Decompression
                start = time.perf_counter()
                decompressed, _ = compressor.decompress(result.data)
                elapsed = time.perf_counter() - start
                decompress_latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        compress_result = compute_throughput_result("Compression TPS", compress_latencies)
        decompress_result = compute_throughput_result("Decompression TPS", decompress_latencies)

        print(compress_result)
        print(decompress_result)
        print(f"  Original Size: {len(json_bytes):,} bytes")
        print(f"  Compressed Size: {result.compressed_size:,} bytes")
        print(f"  Compression Ratio: {result.compression_ratio * 100:.1f}%")

    def test_storage_with_compression(self):
        """Measure storage throughput with compression enabled."""
        try:
            from storage.json_file import JSONFileStorage
        except ImportError:
            pytest.skip("JSONFileStorage not available")

        import os
        import tempfile

        chain = create_test_chain(num_blocks=10, entries_per_block=10)
        chain_data = chain.to_dict()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test with compression
            compressed_path = os.path.join(tmpdir, "compressed.json")
            storage_compressed = JSONFileStorage(
                file_path=compressed_path, compression_enabled=True, compression_level=6
            )

            # Test without compression
            uncompressed_path = os.path.join(tmpdir, "uncompressed.json")
            storage_uncompressed = JSONFileStorage(
                file_path=uncompressed_path, compression_enabled=False
            )

            # Measure save times
            save_latencies_compressed = []
            save_latencies_uncompressed = []

            for _ in range(10):
                start = time.perf_counter()
                storage_compressed.save_chain(chain_data)
                elapsed = time.perf_counter() - start
                save_latencies_compressed.append(elapsed)

                start = time.perf_counter()
                storage_uncompressed.save_chain(chain_data)
                elapsed = time.perf_counter() - start
                save_latencies_uncompressed.append(elapsed)

            compressed_result = compute_throughput_result(
                "Save with Compression", save_latencies_compressed
            )
            uncompressed_result = compute_throughput_result(
                "Save without Compression", save_latencies_uncompressed
            )

            print(compressed_result)
            print(uncompressed_result)

            # Report file sizes
            compressed_size = os.path.getsize(compressed_path)
            uncompressed_size = os.path.getsize(uncompressed_path)

            print(f"  Compressed File: {compressed_size:,} bytes")
            print(f"  Uncompressed File: {uncompressed_size:,} bytes")
            print(f"  Space Saved: {(1 - compressed_size / uncompressed_size) * 100:.1f}%")


# =============================================================================
# Cache Throughput Tests
# =============================================================================


class TestCacheThroughput:
    """Benchmark adaptive cache throughput."""

    def test_cache_hit_vs_miss(self):
        """Measure cache hit vs miss performance."""
        try:
            from adaptive_cache import AdaptiveCache, CacheCategory
        except ImportError:
            pytest.skip("adaptive_cache module not available")

        cache = AdaptiveCache(max_entries=1000, enabled=True)

        # Populate cache
        for i in range(100):
            cache.set(CacheCategory.INTENTS, f"key_{i}", {"data": f"value_{i}"})

        hit_latencies = []
        miss_latencies = []

        if CONFIG.disable_gc:
            gc.disable()

        try:
            # Measure cache hits
            for i in range(CONFIG.query_iterations):
                key = f"key_{i % 100}"

                start = time.perf_counter()
                result = cache.get(CacheCategory.INTENTS, key)
                elapsed = time.perf_counter() - start

                assert result is not None
                hit_latencies.append(elapsed)

            # Measure cache misses
            for i in range(CONFIG.query_iterations):
                key = f"missing_key_{i}"

                start = time.perf_counter()
                result = cache.get(CacheCategory.INTENTS, key)
                elapsed = time.perf_counter() - start

                assert result is None
                miss_latencies.append(elapsed)
        finally:
            if CONFIG.disable_gc:
                gc.enable()

        hit_result = compute_throughput_result("Cache Hit TPS", hit_latencies)
        miss_result = compute_throughput_result("Cache Miss TPS", miss_latencies)

        print(hit_result)
        print(miss_result)

        # Cache hits should be very fast
        assert hit_result.avg_latency_ms < 1.0, "Cache hits should be sub-millisecond"

    def test_get_or_compute_throughput(self):
        """Measure get_or_compute pattern throughput."""
        try:
            from adaptive_cache import AdaptiveCache, CacheCategory
        except ImportError:
            pytest.skip("adaptive_cache module not available")

        cache = AdaptiveCache(max_entries=1000, enabled=True)

        # Simulated expensive computation
        def expensive_compute(key: str) -> dict:
            # Simulate 1ms of work
            time.sleep(0.001)
            return {"computed": key}

        latencies_first = []  # First call (compute)
        latencies_cached = []  # Subsequent calls (cached)

        # First calls (will compute)
        for i in range(50):
            key = f"compute_key_{i}"

            start = time.perf_counter()
            result = cache.get_or_compute(
                CacheCategory.STATS, key, lambda k=key: expensive_compute(k)
            )
            elapsed = time.perf_counter() - start

            latencies_first.append(elapsed)

        # Second calls (should be cached)
        for i in range(50):
            key = f"compute_key_{i}"

            start = time.perf_counter()
            result = cache.get_or_compute(
                CacheCategory.STATS, key, lambda k=key: expensive_compute(k)
            )
            elapsed = time.perf_counter() - start

            latencies_cached.append(elapsed)

        first_result = compute_throughput_result("get_or_compute (miss)", latencies_first)
        cached_result = compute_throughput_result("get_or_compute (hit)", latencies_cached)

        print(first_result)
        print(cached_result)

        # Cached should be much faster than computed
        assert cached_result.avg_latency_ms < first_result.avg_latency_ms / 5


# =============================================================================
# End-to-End Throughput Test
# =============================================================================


class TestEndToEndThroughput:
    """Benchmark complete transaction lifecycle."""

    def test_full_lifecycle_tps(self):
        """Measure complete entry lifecycle: submit → mine → query."""
        chain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
        )

        lifecycle_latencies = []

        for i in range(20):  # 20 complete lifecycles
            entry = generate_entry(i)

            start = time.perf_counter()

            # Submit entry
            chain.add_entry(entry)

            # Mine block
            block = chain.mine_pending_entries(difficulty=1)

            # Query to verify
            entries = chain.get_entries_by_author(entry.author)

            elapsed = time.perf_counter() - start

            assert block is not None
            assert len(entries) > 0
            lifecycle_latencies.append(elapsed)

        result = compute_throughput_result("Full Lifecycle TPS", lifecycle_latencies)
        print(result)

    def test_batch_processing_tps(self):
        """Measure batch processing throughput (multiple entries per block)."""
        batch_sizes = [10, 25, 50, 100]

        print("\n  Batch Processing Results:")
        print("  " + "-" * 50)

        for batch_size in batch_sizes:
            chain = NatLangChain(
                require_validation=False,
                enable_deduplication=False,
                enable_rate_limiting=False,
            )

            # Submit batch
            submit_start = time.perf_counter()
            for i in range(batch_size):
                chain.add_entry(generate_entry(i))
            submit_time = time.perf_counter() - submit_start

            # Mine
            mine_start = time.perf_counter()
            block = chain.mine_pending_entries(difficulty=1)
            mine_time = time.perf_counter() - mine_start

            total_time = submit_time + mine_time
            tps = batch_size / total_time

            print(
                f"  Batch {batch_size:3d}: {tps:,.1f} TPS "
                f"(submit: {submit_time * 1000:.1f}ms, mine: {mine_time * 1000:.1f}ms)"
            )


# =============================================================================
# Summary Report
# =============================================================================


class TestThroughputSummary:
    """Generate comprehensive throughput summary."""

    def test_generate_summary_report(self):
        """Generate and print a summary of all throughput metrics."""
        results = {}

        # Create test chain
        chain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
        )

        # Entry submission
        latencies = []
        for i in range(100):
            entry = generate_entry(i)
            start = time.perf_counter()
            chain.add_entry(entry)
            latencies.append(time.perf_counter() - start)
        results["entry_submission"] = compute_throughput_result("Entry Submission", latencies)
        chain.pending_entries.clear()

        # Block mining
        for i in range(50):
            chain.add_entry(generate_entry(i))
        start = time.perf_counter()
        chain.mine_pending_entries(difficulty=1)
        mine_time = time.perf_counter() - start
        results["mining_50_entries"] = {
            "time_seconds": mine_time,
            "entries": 50,
            "effective_tps": 50 / mine_time,
        }

        # Chain validation
        latencies = []
        for _ in range(50):
            start = time.perf_counter()
            chain.validate_chain()
            latencies.append(time.perf_counter() - start)
        results["chain_validation"] = compute_throughput_result("Validation", latencies)

        # Print summary
        print("\n" + "=" * 70)
        print("  NATLANGCHAIN THROUGHPUT SUMMARY")
        print("=" * 70)

        print("\n  Entry Submission:")
        print(f"    TPS: {results['entry_submission'].operations_per_second:,.1f}")
        print(f"    Avg Latency: {results['entry_submission'].avg_latency_ms:.3f}ms")

        print("\n  Block Mining (50 entries):")
        print(f"    Time: {results['mining_50_entries']['time_seconds'] * 1000:.1f}ms")
        print(f"    Effective TPS: {results['mining_50_entries']['effective_tps']:,.1f}")

        print("\n  Chain Validation:")
        print(f"    TPS: {results['chain_validation'].operations_per_second:,.1f}")
        print(f"    Avg Latency: {results['chain_validation'].avg_latency_ms:.3f}ms")

        print("\n" + "=" * 70)
