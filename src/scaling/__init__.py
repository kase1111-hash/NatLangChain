"""
Horizontal scaling infrastructure for NatLangChain.

This package provides components for running multiple API instances:
- Distributed locking for coordinating concurrent operations
- Cache abstraction for shared state across instances
- Instance coordination and health tracking
- Configuration for load-balanced deployments

Usage:
    from scaling import get_lock_manager, get_cache

    # Distributed locking
    lock_manager = get_lock_manager()
    with lock_manager.lock("mining"):
        mine_block()

    # Distributed caching
    cache = get_cache()
    cache.set("key", value, ttl=300)
"""

import os
from typing import TYPE_CHECKING

from scaling.cache import Cache, LocalCache
from scaling.coordinator import InstanceCoordinator
from scaling.locking import LocalLockManager, LockManager

if TYPE_CHECKING:
    from scaling.cache import RedisCache
    from scaling.locking import RedisLockManager

__all__ = [
    "Cache",
    "InstanceCoordinator",
    "LocalCache",
    "LocalLockManager",
    "LockManager",
    "get_cache",
    "get_coordinator",
    "get_lock_manager",
]

# Singleton instances
_lock_manager: LockManager | None = None
_cache: Cache | None = None
_coordinator: InstanceCoordinator | None = None


def get_lock_manager() -> LockManager:
    """
    Get the configured lock manager.

    Uses Redis for distributed locking if REDIS_URL is set,
    otherwise falls back to local threading locks.
    """
    global _lock_manager
    if _lock_manager is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from scaling.locking import RedisLockManager

                _lock_manager = RedisLockManager(redis_url)
            except ImportError:
                _lock_manager = LocalLockManager()
        else:
            _lock_manager = LocalLockManager()
    return _lock_manager


def get_cache() -> Cache:
    """
    Get the configured cache backend.

    Uses Redis if REDIS_URL is set, otherwise uses local in-memory cache.
    """
    global _cache
    if _cache is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from scaling.cache import RedisCache

                _cache = RedisCache(redis_url)
            except ImportError:
                _cache = LocalCache()
        else:
            _cache = LocalCache()
    return _cache


def get_coordinator() -> InstanceCoordinator:
    """
    Get the instance coordinator for multi-instance deployments.
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = InstanceCoordinator()
    return _coordinator
