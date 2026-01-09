"""
Tests for NatLangChain Rate Limiter Module

Tests rate limiting with memory backend, sliding window algorithm,
configuration, and rate limit results.
"""

import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rate_limiter import (
    MemoryRateLimitStore,
    RateLimitBackend,
    RateLimitConfig,
    RateLimitResult,
    RateLimitStore,
    RedisRateLimitStore,
)


class TestRateLimitConfig(unittest.TestCase):
    """Tests for RateLimitConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        self.assertEqual(config.backend, "memory")
        self.assertEqual(config.requests_per_window, 100)
        self.assertEqual(config.window_seconds, 60)
        self.assertEqual(config.burst_multiplier, 1.5)

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            backend="redis",
            requests_per_window=50,
            window_seconds=30,
            burst_multiplier=2.0,
            redis_url="redis://custom:6379/1",
        )

        self.assertEqual(config.backend, "redis")
        self.assertEqual(config.requests_per_window, 50)
        self.assertEqual(config.window_seconds, 30)
        self.assertEqual(config.burst_multiplier, 2.0)
        self.assertEqual(config.redis_url, "redis://custom:6379/1")

    def test_from_env_defaults(self):
        """Test configuration from environment with defaults."""
        # Clear any existing env vars
        for key in ["RATE_LIMIT_BACKEND", "RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW"]:
            os.environ.pop(key, None)

        config = RateLimitConfig.from_env()

        self.assertEqual(config.backend, "memory")
        self.assertEqual(config.requests_per_window, 100)
        self.assertEqual(config.window_seconds, 60)

    def test_from_env_custom(self):
        """Test configuration from environment with custom values."""
        os.environ["RATE_LIMIT_BACKEND"] = "redis"
        os.environ["RATE_LIMIT_REQUESTS"] = "200"
        os.environ["RATE_LIMIT_WINDOW"] = "120"

        try:
            config = RateLimitConfig.from_env()

            self.assertEqual(config.backend, "redis")
            self.assertEqual(config.requests_per_window, 200)
            self.assertEqual(config.window_seconds, 120)
        finally:
            # Cleanup
            os.environ.pop("RATE_LIMIT_BACKEND", None)
            os.environ.pop("RATE_LIMIT_REQUESTS", None)
            os.environ.pop("RATE_LIMIT_WINDOW", None)


class TestRateLimitResult(unittest.TestCase):
    """Tests for RateLimitResult."""

    def test_create_result(self):
        """Test creating a rate limit result."""
        result = RateLimitResult(
            exceeded=False, remaining=95, limit=100, reset_at=time.time() + 60, retry_after=0
        )

        self.assertFalse(result.exceeded)
        self.assertEqual(result.remaining, 95)
        self.assertEqual(result.limit, 100)
        self.assertEqual(result.retry_after, 0)

    def test_exceeded_result(self):
        """Test rate limit exceeded result."""
        result = RateLimitResult(
            exceeded=True, remaining=0, limit=100, reset_at=time.time() + 30, retry_after=30
        )

        self.assertTrue(result.exceeded)
        self.assertEqual(result.remaining, 0)
        self.assertEqual(result.retry_after, 30)

    def test_to_headers(self):
        """Test converting result to HTTP headers."""
        reset_time = time.time() + 60
        result = RateLimitResult(
            exceeded=False, remaining=95, limit=100, reset_at=reset_time, retry_after=0
        )

        headers = result.to_headers()

        self.assertEqual(headers["X-RateLimit-Limit"], "100")
        self.assertEqual(headers["X-RateLimit-Remaining"], "95")
        self.assertEqual(headers["X-RateLimit-Reset"], str(int(reset_time)))

    def test_to_headers_zero_remaining(self):
        """Test headers with zero remaining."""
        result = RateLimitResult(
            exceeded=True,
            remaining=-5,  # Could go negative if burst allowed
            limit=100,
            reset_at=time.time() + 60,
            retry_after=60,
        )

        headers = result.to_headers()

        # Should clamp to 0
        self.assertEqual(headers["X-RateLimit-Remaining"], "0")


class TestMemoryRateLimitStore(unittest.TestCase):
    """Tests for MemoryRateLimitStore."""

    def setUp(self):
        """Set up test fixtures."""
        self.store = MemoryRateLimitStore()

    def test_is_available(self):
        """Test that memory store is always available."""
        self.assertTrue(self.store.is_available())

    def test_increment_new_key(self):
        """Test incrementing a new key."""
        count, reset_at = self.store.increment("test_key", window_seconds=60)

        self.assertEqual(count, 1)
        self.assertGreater(reset_at, time.time())

    def test_increment_existing_key(self):
        """Test incrementing an existing key."""
        self.store.increment("test_key", window_seconds=60)
        self.store.increment("test_key", window_seconds=60)
        count, _ = self.store.increment("test_key", window_seconds=60)

        self.assertEqual(count, 3)

    def test_get_count(self):
        """Test getting current count."""
        self.store.increment("test_key", window_seconds=60)
        self.store.increment("test_key", window_seconds=60)

        count = self.store.get_count("test_key")

        self.assertEqual(count, 2)

    def test_get_count_nonexistent_key(self):
        """Test getting count for nonexistent key."""
        count = self.store.get_count("nonexistent")

        self.assertEqual(count, 0)

    def test_window_reset(self):
        """Test that window resets after expiry."""
        # Use a very short window for testing
        self.store.increment("test_key", window_seconds=1)
        self.store.increment("test_key", window_seconds=1)

        # Wait for window to expire
        time.sleep(1.1)

        # Should reset to 1
        count, _ = self.store.increment("test_key", window_seconds=1)

        self.assertEqual(count, 1)

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        # Add some entries with very short window
        self.store.increment("key1", window_seconds=1)
        self.store.increment("key2", window_seconds=1)

        # Wait for window to expire AND for cleanup threshold (2x window)
        time.sleep(2.5)

        # Cleanup expired entries (threshold is 2x window_seconds)
        self.store.cleanup_expired(window_seconds=1)

        # Entries should be cleaned up (removed from store)
        # After cleanup, get_count returns 0 for non-existent keys
        count1 = self.store.get_count("key1")
        count2 = self.store.get_count("key2")

        # Should be 0 after cleanup
        self.assertEqual(count1, 0)
        self.assertEqual(count2, 0)

    def test_thread_safety(self):
        """Test that store is thread-safe."""
        import threading

        results = []

        def increment():
            for _ in range(100):
                count, _ = self.store.increment("concurrent_key", window_seconds=60)
                results.append(count)

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 500 total increments
        final_count = self.store.get_count("concurrent_key")
        self.assertEqual(final_count, 500)


class TestRedisRateLimitStore(unittest.TestCase):
    """Tests for RedisRateLimitStore."""

    def test_init(self):
        """Test initialization."""
        store = RedisRateLimitStore(url="redis://localhost:6379/0", prefix="test:", timeout=1.0)

        self.assertEqual(store.url, "redis://localhost:6379/0")
        self.assertEqual(store.prefix, "test:")
        self.assertEqual(store.timeout, 1.0)

    def test_full_key(self):
        """Test key prefixing."""
        store = RedisRateLimitStore(url="redis://localhost:6379/0", prefix="ratelimit:")

        full_key = store._full_key("client:123")

        self.assertEqual(full_key, "ratelimit:client:123")

    def test_not_available_without_redis(self):
        """Test that store reports unavailable when Redis not connected."""
        store = RedisRateLimitStore(url="redis://nonexistent:6379/0", timeout=0.1)

        # Force client creation attempt
        store._get_client()

        # Should not be available
        self.assertFalse(store.is_available())


class TestRateLimitBackendEnum(unittest.TestCase):
    """Tests for RateLimitBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        self.assertEqual(RateLimitBackend.MEMORY.value, "memory")
        self.assertEqual(RateLimitBackend.REDIS.value, "redis")


if __name__ == "__main__":
    unittest.main()
