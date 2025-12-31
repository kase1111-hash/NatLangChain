"""
Abstract base class for storage backends.

This module defines the interface that all storage backends must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class StorageError(Exception):
    """Base exception for storage-related errors."""
    pass


class StorageConnectionError(StorageError):
    """Raised when connection to storage backend fails."""
    pass


class StorageReadError(StorageError):
    """Raised when reading from storage fails."""
    pass


class StorageWriteError(StorageError):
    """Raised when writing to storage fails."""
    pass


class StorageBackend(ABC):
    """
    Abstract base class for blockchain storage backends.

    All storage backends must implement these methods to provide
    a consistent interface for chain persistence.
    """

    @abstractmethod
    def load_chain(self) -> dict[str, Any] | None:
        """
        Load the blockchain data from storage.

        Returns:
            Dictionary containing chain data, or None if no data exists.

        Raises:
            StorageReadError: If reading fails
        """
        pass

    @abstractmethod
    def save_chain(self, chain_data: dict[str, Any]) -> None:
        """
        Save the blockchain data to storage.

        Args:
            chain_data: Dictionary containing the complete chain state

        Raises:
            StorageWriteError: If writing fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the storage backend is available and ready.

        Returns:
            True if storage is accessible, False otherwise
        """
        pass

    def get_info(self) -> dict[str, Any]:
        """
        Get information about the storage backend.

        Returns:
            Dictionary with backend type, status, and configuration
        """
        return {
            "backend_type": self.__class__.__name__,
            "available": self.is_available(),
        }

    # Optional methods with default implementations

    def save_block(self, block_data: dict[str, Any]) -> None:
        """
        Save a single block (for incremental updates).

        Default implementation does nothing - backends that support
        incremental updates should override this.

        Args:
            block_data: Dictionary containing block data
        """
        pass

    def save_entry(self, entry_data: dict[str, Any]) -> None:
        """
        Save a single entry (for pending entries).

        Default implementation does nothing - backends that support
        incremental updates should override this.

        Args:
            entry_data: Dictionary containing entry data
        """
        pass

    def get_block(self, index: int) -> dict[str, Any] | None:
        """
        Get a single block by index.

        Default implementation loads entire chain - backends should
        override for efficiency.

        Args:
            index: Block index

        Returns:
            Block data dictionary or None if not found
        """
        chain_data = self.load_chain()
        if chain_data and "chain" in chain_data:
            chain = chain_data["chain"]
            if 0 <= index < len(chain):
                return chain[index]
        return None

    def get_blocks_range(
        self, start: int, end: int
    ) -> list[dict[str, Any]]:
        """
        Get a range of blocks.

        Default implementation loads entire chain - backends should
        override for efficiency.

        Args:
            start: Start index (inclusive)
            end: End index (exclusive)

        Returns:
            List of block data dictionaries
        """
        chain_data = self.load_chain()
        if chain_data and "chain" in chain_data:
            return chain_data["chain"][start:end]
        return []

    def get_entry_count(self) -> int:
        """
        Get total number of entries across all blocks.

        Returns:
            Total entry count
        """
        chain_data = self.load_chain()
        if chain_data and "chain" in chain_data:
            return sum(
                len(block.get("entries", []))
                for block in chain_data["chain"]
            )
        return 0

    def get_block_count(self) -> int:
        """
        Get total number of blocks.

        Returns:
            Block count
        """
        chain_data = self.load_chain()
        if chain_data and "chain" in chain_data:
            return len(chain_data["chain"])
        return 0

    def search_entries_by_author(
        self, author: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Search entries by author.

        Default implementation loads entire chain - backends should
        override for efficiency.

        Args:
            author: Author identifier
            limit: Maximum results

        Returns:
            List of matching entries
        """
        results = []
        chain_data = self.load_chain()
        if chain_data and "chain" in chain_data:
            for block in chain_data["chain"]:
                for entry in block.get("entries", []):
                    if entry.get("author") == author:
                        results.append(entry)
                        if len(results) >= limit:
                            return results
        return results

    def close(self) -> None:
        """
        Close the storage connection and release resources.

        Default implementation does nothing - backends with connections
        should override this.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
        return False
