"""
In-memory storage backend.

This backend stores blockchain data in memory only, useful for:
- Unit testing
- Development
- Temporary/ephemeral chains
"""

import copy
import threading
from typing import Any

from storage.base import StorageBackend


class MemoryStorage(StorageBackend):
    """
    In-memory storage backend.

    All data is lost when the process exits. Thread-safe operations.
    """

    def __init__(self):
        """Initialize empty memory storage."""
        self._data: dict[str, Any] | None = None
        # Use RLock to allow reentrant locking (get_info calls get_block_count, etc.)
        self._lock = threading.RLock()

    def load_chain(self) -> dict[str, Any] | None:
        """
        Load blockchain data from memory.

        Returns:
            Copy of stored data, or None if empty
        """
        with self._lock:
            if self._data is None:
                return None
            # Return a deep copy to prevent external modification
            return copy.deepcopy(self._data)

    def save_chain(self, chain_data: dict[str, Any]) -> None:
        """
        Save blockchain data to memory.

        Args:
            chain_data: Dictionary containing the complete chain state
        """
        with self._lock:
            # Store a deep copy to prevent external modification
            self._data = copy.deepcopy(chain_data)

    def is_available(self) -> bool:
        """Memory storage is always available."""
        return True

    def get_info(self) -> dict[str, Any]:
        """Get storage backend information."""
        info = super().get_info()
        with self._lock:
            info.update(
                {
                    "has_data": self._data is not None,
                    "block_count": self.get_block_count(),
                    "entry_count": self.get_entry_count(),
                }
            )
        return info

    def clear(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._data = None

    def get_block_count(self) -> int:
        """Get number of blocks."""
        with self._lock:
            if self._data and "chain" in self._data:
                return len(self._data["chain"])
            return 0

    def get_entry_count(self) -> int:
        """Get total number of entries."""
        with self._lock:
            if self._data and "chain" in self._data:
                return sum(len(block.get("entries", [])) for block in self._data["chain"])
            return 0
