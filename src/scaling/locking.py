"""
Distributed locking for NatLangChain.

Provides lock managers for coordinating concurrent operations across
multiple API instances:
- LocalLockManager: Thread-based locks for single-instance deployments
- RedisLockManager: Distributed locks using Redis for multi-instance

Usage:
    from scaling import get_lock_manager

    lock_manager = get_lock_manager()

    # Context manager (recommended)
    with lock_manager.lock("mining", timeout=30):
        mine_block()

    # Manual acquire/release
    if lock_manager.acquire("resource", timeout=10):
        try:
            do_work()
        finally:
            lock_manager.release("resource")
"""

import threading
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class LockInfo:
    """Information about a held lock."""

    name: str
    holder_id: str
    acquired_at: float
    ttl: float | None = None
    expires_at: float | None = None


class LockManager(ABC):
    """
    Abstract base class for lock managers.

    All lock managers must implement acquire/release/lock methods
    for coordinating concurrent operations.
    """

    @abstractmethod
    def acquire(
        self,
        name: str,
        timeout: float = 30.0,
        ttl: float = 60.0,
    ) -> bool:
        """
        Acquire a named lock.

        Args:
            name: Lock identifier
            timeout: Maximum time to wait for lock (seconds)
            ttl: Lock time-to-live (auto-release after this time)

        Returns:
            True if lock acquired, False if timeout
        """
        pass

    @abstractmethod
    def release(self, name: str) -> bool:
        """
        Release a named lock.

        Args:
            name: Lock identifier

        Returns:
            True if lock was held and released, False otherwise
        """
        pass

    @abstractmethod
    def is_locked(self, name: str) -> bool:
        """Check if a lock is currently held."""
        pass

    @contextmanager
    def lock(self, name: str, timeout: float = 30.0, ttl: float = 60.0):
        """
        Context manager for acquiring a lock.

        Args:
            name: Lock identifier
            timeout: Maximum time to wait for lock
            ttl: Lock time-to-live

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        if not self.acquire(name, timeout=timeout, ttl=ttl):
            raise TimeoutError(f"Could not acquire lock '{name}' within {timeout}s")
        try:
            yield
        finally:
            self.release(name)

    def get_info(self, name: str) -> LockInfo | None:
        """Get information about a lock (if held)."""
        return None


class LocalLockManager(LockManager):
    """
    Thread-based lock manager for single-instance deployments.

    Uses threading.RLock for reentrant locking within the same process.
    """

    def __init__(self):
        self._locks: dict[str, threading.RLock] = {}
        self._lock_info: dict[str, LockInfo] = {}
        self._meta_lock = threading.Lock()
        self._instance_id = str(uuid.uuid4())[:8]

    def _get_lock(self, name: str) -> threading.RLock:
        """Get or create a lock by name."""
        with self._meta_lock:
            if name not in self._locks:
                self._locks[name] = threading.RLock()
            return self._locks[name]

    def acquire(
        self,
        name: str,
        timeout: float = 30.0,
        ttl: float = 60.0,
    ) -> bool:
        """Acquire a named lock."""
        lock = self._get_lock(name)
        acquired = lock.acquire(timeout=timeout)

        if acquired:
            now = time.time()
            self._lock_info[name] = LockInfo(
                name=name,
                holder_id=f"{self._instance_id}:{threading.current_thread().name}",
                acquired_at=now,
                ttl=ttl,
                expires_at=now + ttl if ttl else None,
            )

        return acquired

    def release(self, name: str) -> bool:
        """Release a named lock."""
        lock = self._get_lock(name)
        try:
            lock.release()
            self._lock_info.pop(name, None)
            return True
        except RuntimeError:
            # Lock not held by this thread
            return False

    def is_locked(self, name: str) -> bool:
        """Check if a lock is currently held."""
        return name in self._lock_info

    def get_info(self, name: str) -> LockInfo | None:
        """Get information about a lock."""
        return self._lock_info.get(name)

    def get_all_locks(self) -> list[LockInfo]:
        """Get information about all held locks."""
        return list(self._lock_info.values())


class RedisLockManager(LockManager):
    """
    Distributed lock manager using Redis.

    Implements the Redlock algorithm for distributed locking.
    Requires redis package: pip install redis

    Features:
    - Distributed across multiple instances
    - Automatic TTL-based expiration
    - Atomic acquire/release operations
    - Deadlock prevention via TTL
    """

    def __init__(
        self,
        redis_url: str,
        key_prefix: str = "natlangchain:lock:",
    ):
        """
        Initialize Redis lock manager.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for lock keys in Redis
        """
        try:
            import redis
        except ImportError:
            raise ImportError("redis package required: pip install redis")

        self._redis = redis.from_url(redis_url)
        self._key_prefix = key_prefix
        self._instance_id = str(uuid.uuid4())
        self._held_locks: dict[str, str] = {}  # name -> lock_value

    def _key(self, name: str) -> str:
        """Get Redis key for a lock."""
        return f"{self._key_prefix}{name}"

    def acquire(
        self,
        name: str,
        timeout: float = 30.0,
        ttl: float = 60.0,
    ) -> bool:
        """
        Acquire a distributed lock.

        Uses SET NX with expiration for atomic acquire.
        """
        key = self._key(name)
        lock_value = f"{self._instance_id}:{time.time()}"
        ttl_ms = int(ttl * 1000)

        deadline = time.time() + timeout
        retry_delay = 0.1

        while time.time() < deadline:
            # Attempt atomic acquire
            if self._redis.set(key, lock_value, nx=True, px=ttl_ms):
                self._held_locks[name] = lock_value
                return True

            # Wait before retry
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 1.0)

        return False

    def release(self, name: str) -> bool:
        """
        Release a distributed lock.

        Uses Lua script for atomic check-and-delete.
        """
        key = self._key(name)
        lock_value = self._held_locks.get(name)

        if not lock_value:
            return False

        # Lua script for atomic release (only if we hold the lock)
        release_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = self._redis.eval(release_script, 1, key, lock_value)
        if result:
            self._held_locks.pop(name, None)
            return True
        return False

    def is_locked(self, name: str) -> bool:
        """Check if a lock is currently held."""
        key = self._key(name)
        return self._redis.exists(key) > 0

    def get_info(self, name: str) -> LockInfo | None:
        """Get information about a lock."""
        key = self._key(name)
        value = self._redis.get(key)
        ttl = self._redis.ttl(key)

        if not value:
            return None

        try:
            holder_id, acquired_str = value.decode().split(":", 1)
            acquired_at = float(acquired_str)
        except (ValueError, AttributeError):
            holder_id = value.decode() if value else "unknown"
            acquired_at = 0

        return LockInfo(
            name=name,
            holder_id=holder_id,
            acquired_at=acquired_at,
            ttl=float(ttl) if ttl > 0 else None,
        )

    def extend(self, name: str, ttl: float = 60.0) -> bool:
        """
        Extend the TTL of a held lock.

        Args:
            name: Lock identifier
            ttl: New TTL in seconds

        Returns:
            True if extended, False if lock not held
        """
        key = self._key(name)
        lock_value = self._held_locks.get(name)

        if not lock_value:
            return False

        # Lua script for atomic extend (only if we hold the lock)
        extend_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("pexpire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        ttl_ms = int(ttl * 1000)
        result = self._redis.eval(extend_script, 1, key, lock_value, ttl_ms)
        return bool(result)

    def close(self):
        """Close the Redis connection."""
        self._redis.close()


# Lock decorator
def with_lock(
    name: str,
    timeout: float = 30.0,
    ttl: float = 60.0,
    lock_manager: LockManager | None = None,
):
    """
    Decorator for executing a function with a distributed lock.

    Args:
        name: Lock identifier
        timeout: Maximum time to wait for lock
        ttl: Lock time-to-live
        lock_manager: Optional specific lock manager to use

    Usage:
        @with_lock("mining")
        def mine_block():
            ...
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            from scaling import get_lock_manager

            manager = lock_manager or get_lock_manager()
            with manager.lock(name, timeout=timeout, ttl=ttl):
                return func(*args, **kwargs)

        return wrapper

    return decorator
