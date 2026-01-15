"""
Tests for horizontal scaling infrastructure.
"""

import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from scaling.cache import CacheEntry, LocalCache
from scaling.coordinator import InstanceCoordinator, InstanceInfo
from scaling.locking import LocalLockManager


class TestLocalLockManager:
    """Tests for LocalLockManager."""

    def test_acquire_release(self):
        """Test basic acquire and release."""
        manager = LocalLockManager()

        assert manager.acquire("test_lock")
        assert manager.is_locked("test_lock")
        assert manager.release("test_lock")
        assert not manager.is_locked("test_lock")

    def test_lock_context_manager(self):
        """Test lock as context manager."""
        manager = LocalLockManager()

        with manager.lock("ctx_lock"):
            assert manager.is_locked("ctx_lock")

        assert not manager.is_locked("ctx_lock")

    def test_lock_timeout(self):
        """Test lock timeout behavior."""
        manager = LocalLockManager()

        # Acquire lock in another thread
        def hold_lock():
            manager.acquire("blocked_lock")
            time.sleep(0.5)
            manager.release("blocked_lock")

        thread = threading.Thread(target=hold_lock)
        thread.start()
        time.sleep(0.05)  # Let thread acquire lock

        # Try to acquire with short timeout
        acquired = manager.acquire("blocked_lock", timeout=0.1)
        assert not acquired

        thread.join()

    def test_lock_reentrant(self):
        """Test reentrant locking (same thread can acquire multiple times)."""
        manager = LocalLockManager()

        assert manager.acquire("reentrant_lock")
        assert manager.acquire("reentrant_lock")  # Same thread, should succeed
        manager.release("reentrant_lock")
        manager.release("reentrant_lock")

    def test_multiple_locks(self):
        """Test multiple independent locks."""
        manager = LocalLockManager()

        manager.acquire("lock_a")
        manager.acquire("lock_b")

        assert manager.is_locked("lock_a")
        assert manager.is_locked("lock_b")

        manager.release("lock_a")
        assert not manager.is_locked("lock_a")
        assert manager.is_locked("lock_b")

        manager.release("lock_b")

    def test_get_info(self):
        """Test getting lock info."""
        manager = LocalLockManager()

        assert manager.get_info("nonexistent") is None

        manager.acquire("info_lock", ttl=60)
        info = manager.get_info("info_lock")

        assert info is not None
        assert info.name == "info_lock"
        assert info.ttl == 60
        assert info.expires_at is not None

        manager.release("info_lock")

    def test_thread_safety(self):
        """Test thread-safe locking."""
        manager = LocalLockManager()
        counter = [0]
        lock_name = "thread_safe_lock"

        def increment():
            with manager.lock(lock_name, timeout=5):
                current = counter[0]
                time.sleep(0.001)
                counter[0] = current + 1

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter[0] == 10


class TestLocalCache:
    """Tests for LocalCache."""

    def test_get_set(self):
        """Test basic get and set."""
        cache = LocalCache()

        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"

        cache.set("key", "value")
        assert cache.get("key") == "value"

    def test_delete(self):
        """Test delete operation."""
        cache = LocalCache()

        cache.set("to_delete", "value")
        assert cache.exists("to_delete")

        assert cache.delete("to_delete")
        assert not cache.exists("to_delete")
        assert not cache.delete("to_delete")  # Already deleted

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = LocalCache()

        cache.set("expires", "value", ttl=0.1)
        assert cache.get("expires") == "value"

        time.sleep(0.15)
        assert cache.get("expires") is None

    def test_incr_decr(self):
        """Test atomic increment/decrement."""
        cache = LocalCache()

        assert cache.incr("counter") == 1
        assert cache.incr("counter") == 2
        assert cache.incr("counter", 5) == 7
        assert cache.decr("counter") == 6
        assert cache.decr("counter", 3) == 3

    def test_get_many_set_many(self):
        """Test batch operations."""
        cache = LocalCache()

        cache.set_many({"a": 1, "b": 2, "c": 3})

        result = cache.get_many(["a", "b", "nonexistent"])
        assert result == {"a": 1, "b": 2}

    def test_delete_many(self):
        """Test batch delete."""
        cache = LocalCache()

        cache.set_many({"x": 1, "y": 2, "z": 3})
        deleted = cache.delete_many(["x", "y", "nonexistent"])

        assert deleted == 2
        assert not cache.exists("x")
        assert not cache.exists("y")
        assert cache.exists("z")

    def test_clear(self):
        """Test clearing all entries."""
        cache = LocalCache()

        cache.set_many({"a": 1, "b": 2})
        cache.clear()

        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_get_stats(self):
        """Test cache statistics."""
        cache = LocalCache()

        cache.get("miss")
        cache.set("hit", "value")
        cache.get("hit")
        cache.get("hit")

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_max_size_eviction(self):
        """Test eviction when max size reached."""
        cache = LocalCache(max_size=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict oldest

        assert cache.get_stats()["size"] <= 3

    def test_json_serializable_values(self):
        """Test storing JSON-serializable values."""
        cache = LocalCache()

        cache.set("dict", {"nested": {"data": [1, 2, 3]}})
        cache.set("list", [1, "two", 3.0])
        cache.set("number", 42)
        cache.set("string", "hello")
        cache.set("bool", True)
        cache.set("null", None)

        assert cache.get("dict") == {"nested": {"data": [1, 2, 3]}}
        assert cache.get("list") == [1, "two", 3.0]
        assert cache.get("number") == 42

    def test_thread_safety(self):
        """Test thread-safe operations."""
        cache = LocalCache()
        results = []

        def cache_operations(n):
            key = f"key_{n}"
            cache.set(key, n)
            value = cache.get(key)
            results.append(value == n)

        threads = [threading.Thread(target=cache_operations, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)


class TestInstanceCoordinator:
    """Tests for InstanceCoordinator (local mode)."""

    def test_instance_id_generation(self):
        """Test unique instance ID generation."""
        coord1 = InstanceCoordinator()
        coord2 = InstanceCoordinator()

        assert coord1.instance_id != coord2.instance_id

    def test_custom_instance_id(self):
        """Test custom instance ID."""
        coord = InstanceCoordinator(instance_id="custom-123")
        assert coord.instance_id == "custom-123"

    def test_is_leader_local_mode(self):
        """Test leader status in local (single-instance) mode."""
        coord = InstanceCoordinator()
        # Without Redis, always leader
        assert coord.is_leader()

    def test_get_instances_local_mode(self):
        """Test getting instances in local mode."""
        coord = InstanceCoordinator()
        instances = coord.get_instances()

        assert len(instances) == 1
        assert instances[0].instance_id == coord.instance_id
        assert instances[0].is_leader

    def test_get_info(self):
        """Test getting coordinator info."""
        coord = InstanceCoordinator()
        info = coord.get_info()

        assert "instance_id" in info
        assert "hostname" in info
        assert "is_leader" in info
        assert "uptime_seconds" in info
        assert info["instance_count"] == 1

    def test_run_on_leader(self):
        """Test running function only on leader."""
        coord = InstanceCoordinator()
        result = coord.run_on_leader(lambda x: x * 2, 21)

        assert result == 42

    def test_register_unregister(self):
        """Test register/unregister lifecycle."""
        coord = InstanceCoordinator()

        coord.register(metadata={"version": "1.0"})
        assert coord._metadata["version"] == "1.0"

        coord.unregister()


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired_no_ttl(self):
        """Test entry without TTL never expires."""
        entry = CacheEntry(value="test")
        assert not entry.is_expired()

    def test_not_expired_future(self):
        """Test entry with future expiration."""
        entry = CacheEntry(value="test", expires_at=time.time() + 100)
        assert not entry.is_expired()

    def test_expired_past(self):
        """Test entry with past expiration."""
        entry = CacheEntry(value="test", expires_at=time.time() - 1)
        assert entry.is_expired()


class TestInstanceInfo:
    """Tests for InstanceInfo dataclass."""

    def test_is_healthy_recent(self):
        """Test healthy with recent heartbeat."""
        info = InstanceInfo(
            instance_id="test",
            hostname="localhost",
            port=5000,
            started_at=time.time() - 100,
            last_heartbeat=time.time(),
        )
        assert info.is_healthy(timeout=30)

    def test_is_healthy_stale(self):
        """Test unhealthy with stale heartbeat."""
        info = InstanceInfo(
            instance_id="test",
            hostname="localhost",
            port=5000,
            started_at=time.time() - 100,
            last_heartbeat=time.time() - 60,
        )
        assert not info.is_healthy(timeout=30)


class TestLockDecorator:
    """Tests for @with_lock decorator."""

    def test_with_lock_decorator(self):
        """Test the with_lock decorator."""
        from scaling.locking import with_lock

        call_count = [0]

        @with_lock("decorator_lock")
        def protected_function():
            call_count[0] += 1
            return "result"

        result = protected_function()

        assert result == "result"
        assert call_count[0] == 1


class TestCachedDecorator:
    """Tests for @cached decorator."""

    def test_cached_decorator(self):
        """Test the cached decorator."""
        from scaling.cache import cached

        call_count = [0]

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x, y):
            call_count[0] += 1
            return x + y

        # First call - computes
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count[0] == 1

        # Second call with same args - cached
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count[0] == 1  # Not called again

        # Different args - computes
        result3 = expensive_function(3, 4)
        assert result3 == 7
        assert call_count[0] == 2


class TestScalingFactoryFunctions:
    """Tests for factory functions."""

    def test_get_lock_manager(self):
        """Test get_lock_manager factory."""
        from scaling import get_lock_manager

        manager = get_lock_manager()
        assert manager is not None
        assert isinstance(manager, LocalLockManager)

    def test_get_cache(self):
        """Test get_cache factory."""
        from scaling import get_cache

        cache = get_cache()
        assert cache is not None
        assert isinstance(cache, LocalCache)

    def test_get_coordinator(self):
        """Test get_coordinator factory."""
        from scaling import get_coordinator

        coordinator = get_coordinator()
        assert coordinator is not None
        assert isinstance(coordinator, InstanceCoordinator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
