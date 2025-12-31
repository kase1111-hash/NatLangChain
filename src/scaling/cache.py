"""
Distributed cache for NatLangChain.

Provides cache backends for sharing state across multiple API instances:
- LocalCache: In-memory cache for single-instance deployments
- RedisCache: Distributed cache using Redis for multi-instance

Usage:
    from scaling import get_cache

    cache = get_cache()

    # Basic operations
    cache.set("key", {"data": "value"}, ttl=300)
    value = cache.get("key")
    cache.delete("key")

    # Atomic operations
    cache.incr("counter")
    cache.decr("counter")
"""

import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """A cache entry with value and expiration."""
    value: Any
    expires_at: float | None = None

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class Cache(ABC):
    """
    Abstract base class for cache backends.

    All cache implementations must provide get/set/delete operations
    with optional TTL support.
    """

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Value to return if key not found

        Returns:
            Cached value or default
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Get multiple values from the cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key -> value for found keys
        """
        return {k: v for k, v in ((k, self.get(k)) for k in keys) if v is not None}

    def set_many(self, items: dict[str, Any], ttl: float | None = None) -> bool:
        """
        Set multiple values in the cache.

        Args:
            items: Dictionary of key -> value
            ttl: Time-to-live in seconds

        Returns:
            True if all successful
        """
        return all(self.set(k, v, ttl) for k, v in items.items())

    def delete_many(self, keys: list[str]) -> int:
        """
        Delete multiple keys from the cache.

        Args:
            keys: List of keys to delete

        Returns:
            Number of keys deleted
        """
        return sum(1 for k in keys if self.delete(k))

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a numeric value.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment
        """
        current = self.get(key, 0)
        new_value = int(current) + amount
        self.set(key, new_value)
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a numeric value.

        Args:
            key: Cache key
            amount: Amount to decrement by

        Returns:
            New value after decrement
        """
        return self.incr(key, -amount)

    def clear(self) -> None:
        """Clear all cached values."""
        pass

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {}


class LocalCache(Cache):
    """
    In-memory cache for single-instance deployments.

    Thread-safe with automatic expiration cleanup.
    """

    def __init__(self, max_size: int = 10000, cleanup_interval: float = 60.0):
        """
        Initialize local cache.

        Args:
            max_size: Maximum number of entries
            cleanup_interval: Seconds between cleanup runs
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def _maybe_cleanup(self) -> None:
        """Periodically remove expired entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired:
            self._cache.pop(key, None)

    def _evict_if_needed(self) -> None:
        """Evict oldest entries if cache is full."""
        if len(self._cache) < self._max_size:
            return

        # Remove expired first
        self._maybe_cleanup()

        # If still full, remove oldest entries (FIFO)
        while len(self._cache) >= self._max_size:
            try:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            except (StopIteration, KeyError):
                break

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache."""
        with self._lock:
            self._maybe_cleanup()
            entry = self._cache.get(key)

            if entry is None:
                self._misses += 1
                return default

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return default

            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """Set a value in the cache."""
        with self._lock:
            self._evict_if_needed()

            expires_at = None
            if ttl is not None:
                expires_at = time.time() + ttl

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            return True

    def delete(self, key: str) -> bool:
        """Delete a value from the cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    def incr(self, key: str, amount: int = 1) -> int:
        """Atomic increment."""
        with self._lock:
            entry = self._cache.get(key)
            current = 0
            expires_at = None

            if entry and not entry.is_expired():
                current = int(entry.value)
                expires_at = entry.expires_at

            new_value = current + amount
            self._cache[key] = CacheEntry(value=new_value, expires_at=expires_at)
            return new_value

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "type": "LocalCache",
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self._hits / total if total > 0 else 0,
            }


class RedisCache(Cache):
    """
    Distributed cache using Redis.

    Provides shared cache across multiple API instances.
    Requires redis package: pip install redis
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "natlangchain:cache:",
        default_ttl: float = 3600.0,
    ):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for cache keys
            default_ttl: Default TTL for entries without explicit TTL
        """
        try:
            import redis
        except ImportError:
            raise ImportError("redis package required: pip install redis")

        self._redis = redis.from_url(redis_url)
        self._key_prefix = key_prefix
        self._default_ttl = default_ttl

    def _key(self, key: str) -> str:
        """Get Redis key with prefix."""
        return f"{self._key_prefix}{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value)

    def _deserialize(self, data: bytes | str | None) -> Any:
        """Deserialize value from JSON string."""
        if data is None:
            return None
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from Redis."""
        data = self._redis.get(self._key(key))
        if data is None:
            return default
        try:
            return self._deserialize(data)
        except (json.JSONDecodeError, TypeError):
            return default

    def set(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """Set a value in Redis."""
        try:
            data = self._serialize(value)
            if ttl is None:
                ttl = self._default_ttl

            if ttl:
                self._redis.setex(self._key(key), int(ttl), data)
            else:
                self._redis.set(self._key(key), data)
            return True
        except (TypeError, json.JSONEncodeError):
            return False

    def delete(self, key: str) -> bool:
        """Delete a value from Redis."""
        return self._redis.delete(self._key(key)) > 0

    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        return self._redis.exists(self._key(key)) > 0

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple values from Redis (optimized with MGET)."""
        if not keys:
            return {}

        redis_keys = [self._key(k) for k in keys]
        values = self._redis.mget(redis_keys)

        result = {}
        for key, value in zip(keys, values):
            if value is not None:
                try:
                    result[key] = self._deserialize(value)
                except (json.JSONDecodeError, TypeError):
                    pass
        return result

    def delete_many(self, keys: list[str]) -> int:
        """Delete multiple keys from Redis."""
        if not keys:
            return 0
        redis_keys = [self._key(k) for k in keys]
        return self._redis.delete(*redis_keys)

    def incr(self, key: str, amount: int = 1) -> int:
        """Atomic increment in Redis."""
        return self._redis.incrby(self._key(key), amount)

    def clear(self) -> None:
        """Clear all cached values with our prefix."""
        pattern = f"{self._key_prefix}*"
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor, match=pattern, count=100)
            if keys:
                self._redis.delete(*keys)
            if cursor == 0:
                break

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        info = self._redis.info("stats")
        return {
            "type": "RedisCache",
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "connected": self._redis.ping(),
        }

    def close(self):
        """Close the Redis connection."""
        self._redis.close()


def cached(
    ttl: float = 300.0,
    key_prefix: str = "",
    cache: Cache | None = None,
):
    """
    Decorator for caching function results.

    Args:
        ttl: Cache TTL in seconds
        key_prefix: Prefix for cache keys
        cache: Optional specific cache to use

    Usage:
        @cached(ttl=300)
        def expensive_computation(x, y):
            return x + y
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            from scaling import get_cache
            c = cache or get_cache()

            # Build cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))

            # Try to get from cache
            result = c.get(cache_key)
            if result is not None:
                return result

            # Compute and cache
            result = func(*args, **kwargs)
            c.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
