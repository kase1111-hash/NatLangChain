"""
Tests for adaptive query cache module.

Tests congestion detection, cache TTL adaptation, and
integration with the API layer.
"""

import os
import sys
import threading
import time

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from adaptive_cache import (
    AdaptiveCache,
    CacheCategory,
    CacheConfig,
    CacheEntry,
    CongestionDetector,
    CongestionLevel,
    CongestionState,
    create_cache_from_env,
    get_adaptive_cache,
    make_cache_key,
    reset_adaptive_cache,
    CONGESTION_THRESHOLD_LOW,
    CONGESTION_THRESHOLD_HIGH,
    BASE_TTL_INTENTS,
    MAX_TTL_INTENTS,
)


# =============================================================================
# CongestionDetector Tests
# =============================================================================

class TestCongestionDetector:
    """Tests for CongestionDetector class."""

    def test_initialization(self):
        """Test default initialization."""
        detector = CongestionDetector()
        assert detector.threshold_low == CONGESTION_THRESHOLD_LOW
        assert detector.threshold_high == CONGESTION_THRESHOLD_HIGH

    def test_light_load(self):
        """Test congestion detection with light load."""
        detector = CongestionDetector()
        state = detector.update(pending_count=10)

        assert state.level == CongestionLevel.LIGHT
        assert state.factor < 0.25

    def test_moderate_load(self):
        """Test congestion detection with moderate load."""
        detector = CongestionDetector(
            threshold_low=50,
            threshold_medium=100,
            threshold_high=200
        )
        state = detector.update(pending_count=120)

        assert state.level == CongestionLevel.MODERATE
        assert 0.5 <= state.factor < 0.75

    def test_heavy_load(self):
        """Test congestion detection with heavy load."""
        detector = CongestionDetector(
            threshold_low=50,
            threshold_medium=100,
            threshold_high=200
        )
        state = detector.update(pending_count=250)

        assert state.level == CongestionLevel.HEAVY
        assert state.factor >= 0.75

    def test_critical_load(self):
        """Test congestion detection with critical load."""
        detector = CongestionDetector(
            threshold_low=50,
            threshold_medium=100,
            threshold_high=200
        )
        state = detector.update(pending_count=500)

        assert state.level == CongestionLevel.CRITICAL
        assert state.factor == 1.0

    def test_pending_callback(self):
        """Test pending count callback."""
        detector = CongestionDetector()

        pending_count = [100]  # Use list to allow modification in closure
        detector.set_pending_count_callback(lambda: pending_count[0])

        state = detector.update()
        assert state.pending_count == 100

        pending_count[0] = 300
        state = detector.update()
        assert state.pending_count == 300

    def test_request_rate_tracking(self):
        """Test request rate tracking."""
        detector = CongestionDetector()

        # Record some requests
        for _ in range(10):
            detector.record_request()

        state = detector.update(pending_count=0)
        assert state.request_rate > 0

    def test_state_to_dict(self):
        """Test state serialization."""
        detector = CongestionDetector()
        state = detector.update(pending_count=50)

        d = state.to_dict()
        assert "pending_count" in d
        assert "level" in d
        assert "factor" in d
        assert d["pending_count"] == 50


# =============================================================================
# CacheConfig Tests
# =============================================================================

class TestCacheConfig:
    """Tests for CacheConfig class."""

    def test_ttl_calculation_no_congestion(self):
        """Test TTL at no congestion."""
        config = CacheConfig(base_ttl=30, max_ttl=120)
        ttl = config.get_ttl(0.0)
        assert ttl == 30

    def test_ttl_calculation_full_congestion(self):
        """Test TTL at full congestion."""
        config = CacheConfig(base_ttl=30, max_ttl=120)
        ttl = config.get_ttl(1.0)
        assert ttl == 120

    def test_ttl_calculation_half_congestion(self):
        """Test TTL at half congestion."""
        config = CacheConfig(base_ttl=30, max_ttl=120)
        ttl = config.get_ttl(0.5)
        assert ttl == 75  # 30 + 45


# =============================================================================
# AdaptiveCache Tests
# =============================================================================

class TestAdaptiveCache:
    """Tests for AdaptiveCache class."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_adaptive_cache()

    def test_initialization(self):
        """Test default initialization."""
        cache = AdaptiveCache()
        assert cache.enabled is True
        assert cache.max_entries > 0

    def test_initialization_disabled(self):
        """Test disabled cache."""
        cache = AdaptiveCache(enabled=False)
        assert cache.enabled is False

        # Operations should be no-ops
        cache.set(CacheCategory.INTENTS, "key", "value")
        assert cache.get(CacheCategory.INTENTS, "key") is None

    def test_set_and_get(self):
        """Test basic set and get."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "test_key", {"data": "test"})
        result = cache.get(CacheCategory.INTENTS, "test_key")

        assert result == {"data": "test"}

    def test_get_nonexistent(self):
        """Test getting nonexistent key."""
        cache = AdaptiveCache()
        result = cache.get(CacheCategory.INTENTS, "nonexistent")
        assert result is None

    def test_expiration(self):
        """Test cache expiration."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "expire_test", "value", ttl=0.1)
        assert cache.get(CacheCategory.INTENTS, "expire_test") == "value"

        time.sleep(0.15)
        assert cache.get(CacheCategory.INTENTS, "expire_test") is None

    def test_get_or_compute(self):
        """Test get_or_compute pattern."""
        cache = AdaptiveCache()
        compute_count = [0]

        def compute():
            compute_count[0] += 1
            return {"computed": True}

        # First call should compute
        result1 = cache.get_or_compute(CacheCategory.INTENTS, "compute_key", compute)
        assert result1 == {"computed": True}
        assert compute_count[0] == 1

        # Second call should return cached
        result2 = cache.get_or_compute(CacheCategory.INTENTS, "compute_key", compute)
        assert result2 == {"computed": True}
        assert compute_count[0] == 1  # Not incremented

    def test_invalidate_single(self):
        """Test invalidating a single key."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "key1", "value1")
        cache.set(CacheCategory.INTENTS, "key2", "value2")

        cache.invalidate(CacheCategory.INTENTS, "key1")

        assert cache.get(CacheCategory.INTENTS, "key1") is None
        assert cache.get(CacheCategory.INTENTS, "key2") == "value2"

    def test_invalidate_category(self):
        """Test invalidating entire category."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "key1", "value1")
        cache.set(CacheCategory.INTENTS, "key2", "value2")
        cache.set(CacheCategory.STATS, "stats1", "stats_value")

        count = cache.invalidate_category(CacheCategory.INTENTS)

        assert count == 2
        assert cache.get(CacheCategory.INTENTS, "key1") is None
        assert cache.get(CacheCategory.INTENTS, "key2") is None
        assert cache.get(CacheCategory.STATS, "stats1") == "stats_value"

    def test_invalidate_all(self):
        """Test invalidating all entries."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "key1", "value1")
        cache.set(CacheCategory.STATS, "key2", "value2")

        count = cache.invalidate_all()

        assert count == 2
        assert cache.get(CacheCategory.INTENTS, "key1") is None
        assert cache.get(CacheCategory.STATS, "key2") is None

    def test_on_new_block(self):
        """Test cache invalidation on new block."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "intent1", "value")
        cache.set(CacheCategory.CONTRACTS, "contract1", "value")
        cache.set(CacheCategory.STATS, "stats1", "value")
        cache.set(CacheCategory.SEARCH, "search1", "value")

        cache.on_new_block()

        # These should be invalidated
        assert cache.get(CacheCategory.INTENTS, "intent1") is None
        assert cache.get(CacheCategory.CONTRACTS, "contract1") is None
        assert cache.get(CacheCategory.STATS, "stats1") is None

        # Search should remain
        assert cache.get(CacheCategory.SEARCH, "search1") == "value"

    def test_on_new_entry(self):
        """Test cache invalidation on new entry."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "intent1", "value")
        cache.set(CacheCategory.STATS, "stats1", "value")

        cache.on_new_entry()

        # Intents should be invalidated
        assert cache.get(CacheCategory.INTENTS, "intent1") is None
        # Stats should remain
        assert cache.get(CacheCategory.STATS, "stats1") == "value"

    def test_on_settlement(self):
        """Test cache invalidation on settlement."""
        cache = AdaptiveCache()

        cache.set(CacheCategory.INTENTS, "intent1", "value")
        cache.set(CacheCategory.CONTRACTS, "contract1", "value")

        cache.on_settlement()

        assert cache.get(CacheCategory.INTENTS, "intent1") is None
        assert cache.get(CacheCategory.CONTRACTS, "contract1") is None

    def test_adaptive_ttl(self):
        """Test that TTL adapts to congestion."""
        cache = AdaptiveCache()

        # Light load - should use base TTL
        cache.congestion.update(pending_count=10)
        ttl_light = cache._get_ttl(CacheCategory.INTENTS)

        # Heavy load - should use higher TTL
        cache.congestion.update(pending_count=300)
        ttl_heavy = cache._get_ttl(CacheCategory.INTENTS)

        assert ttl_heavy > ttl_light
        assert ttl_light >= BASE_TTL_INTENTS
        assert ttl_heavy <= MAX_TTL_INTENTS

    def test_stats_tracking(self):
        """Test statistics tracking."""
        cache = AdaptiveCache()

        # Generate some cache activity
        cache.set(CacheCategory.INTENTS, "key1", "value")
        cache.get(CacheCategory.INTENTS, "key1")  # Hit
        cache.get(CacheCategory.INTENTS, "key1")  # Hit
        cache.get(CacheCategory.INTENTS, "nonexistent")  # Miss

        stats = cache.get_stats()

        assert stats["overall"]["hits"] == 2
        assert stats["overall"]["misses"] == 1
        assert stats["overall"]["hit_rate"] > 0

    def test_eviction_on_full(self):
        """Test eviction when cache is full."""
        cache = AdaptiveCache(max_entries=5)

        # Fill cache
        for i in range(5):
            cache.set(CacheCategory.INTENTS, f"key{i}", f"value{i}")

        # Add one more - should trigger eviction
        cache.set(CacheCategory.INTENTS, "key_new", "value_new")

        # New key should exist
        assert cache.get(CacheCategory.INTENTS, "key_new") == "value_new"

        # Some old keys should be evicted
        stats = cache.get_stats()
        assert stats["size"] <= 5

    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = AdaptiveCache()
        errors = []

        def worker():
            try:
                for i in range(100):
                    cache.set(CacheCategory.INTENTS, f"thread_key_{i}", f"value_{i}")
                    cache.get(CacheCategory.INTENTS, f"thread_key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_make_cache_key_simple(self):
        """Test simple cache key generation."""
        key = make_cache_key("open", 100)
        assert key == "open:100"

    def test_make_cache_key_with_kwargs(self):
        """Test cache key with keyword arguments."""
        key = make_cache_key("pending", limit=50, author="alice")
        assert "limit=50" in key
        assert "author=alice" in key

    def test_make_cache_key_long_hashed(self):
        """Test that long keys are hashed."""
        long_arg = "x" * 250
        key = make_cache_key(long_arg)
        assert len(key) == 32  # MD5 hex length


# =============================================================================
# Environment Configuration Tests
# =============================================================================

class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def setup_method(self):
        """Reset cache and clean env."""
        reset_adaptive_cache()
        for key in ['NATLANGCHAIN_QUERY_CACHE_ENABLED',
                    'NATLANGCHAIN_QUERY_CACHE_MAX_SIZE',
                    'NATLANGCHAIN_CONGESTION_THRESHOLD_LOW',
                    'NATLANGCHAIN_CONGESTION_THRESHOLD_HIGH']:
            os.environ.pop(key, None)

    def test_create_from_env_defaults(self):
        """Test creating cache from environment with defaults."""
        cache = create_cache_from_env()

        assert cache.enabled is True
        assert cache.max_entries == 5000

    def test_create_from_env_custom(self):
        """Test creating cache from custom environment."""
        os.environ['NATLANGCHAIN_QUERY_CACHE_ENABLED'] = 'false'
        os.environ['NATLANGCHAIN_QUERY_CACHE_MAX_SIZE'] = '1000'
        os.environ['NATLANGCHAIN_CONGESTION_THRESHOLD_LOW'] = '25'
        os.environ['NATLANGCHAIN_CONGESTION_THRESHOLD_HIGH'] = '100'

        try:
            cache = create_cache_from_env()

            assert cache.enabled is False
            assert cache.max_entries == 1000
            assert cache.congestion.threshold_low == 25
            assert cache.congestion.threshold_high == 100
        finally:
            for key in ['NATLANGCHAIN_QUERY_CACHE_ENABLED',
                        'NATLANGCHAIN_QUERY_CACHE_MAX_SIZE',
                        'NATLANGCHAIN_CONGESTION_THRESHOLD_LOW',
                        'NATLANGCHAIN_CONGESTION_THRESHOLD_HIGH']:
                os.environ.pop(key, None)


# =============================================================================
# Global Instance Tests
# =============================================================================

class TestGlobalInstance:
    """Tests for global cache instance."""

    def setup_method(self):
        """Reset cache before each test."""
        reset_adaptive_cache()

    def test_get_adaptive_cache_singleton(self):
        """Test that get_adaptive_cache returns singleton."""
        cache1 = get_adaptive_cache()
        cache2 = get_adaptive_cache()

        assert cache1 is cache2

    def test_reset_adaptive_cache(self):
        """Test cache reset."""
        cache1 = get_adaptive_cache()
        cache1.set(CacheCategory.INTENTS, "key", "value")

        reset_adaptive_cache()

        cache2 = get_adaptive_cache()
        assert cache2.get(CacheCategory.INTENTS, "key") is None


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance benchmarks for adaptive cache."""

    def test_get_performance(self):
        """Test get operation performance."""
        cache = AdaptiveCache()

        # Pre-populate
        for i in range(1000):
            cache.set(CacheCategory.INTENTS, f"key{i}", {"data": i})

        # Measure get performance
        start = time.perf_counter()
        for i in range(1000):
            cache.get(CacheCategory.INTENTS, f"key{i}")
        elapsed = time.perf_counter() - start

        ops_per_sec = 1000 / elapsed
        print(f"\nCache get performance: {ops_per_sec:.0f} ops/sec ({elapsed*1000:.2f}ms for 1000 ops)")

        # Should be fast - at least 10k ops/sec
        assert ops_per_sec > 10000

    def test_get_or_compute_cached_performance(self):
        """Test get_or_compute with cached values."""
        cache = AdaptiveCache()

        def compute():
            return {"expensive": True}

        # First call to populate
        cache.get_or_compute(CacheCategory.INTENTS, "perf_key", compute)

        # Measure cached performance
        start = time.perf_counter()
        for _ in range(1000):
            cache.get_or_compute(CacheCategory.INTENTS, "perf_key", compute)
        elapsed = time.perf_counter() - start

        ops_per_sec = 1000 / elapsed
        print(f"\nCached get_or_compute: {ops_per_sec:.0f} ops/sec ({elapsed*1000:.2f}ms for 1000 ops)")

        assert ops_per_sec > 5000

    def test_congestion_detection_overhead(self):
        """Test congestion detection overhead."""
        cache = AdaptiveCache()

        # Measure congestion update overhead
        start = time.perf_counter()
        for _ in range(1000):
            cache.congestion.update(pending_count=100)
        elapsed = time.perf_counter() - start

        ops_per_sec = 1000 / elapsed
        print(f"\nCongestion update: {ops_per_sec:.0f} ops/sec ({elapsed*1000:.2f}ms for 1000 ops)")

        assert ops_per_sec > 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
