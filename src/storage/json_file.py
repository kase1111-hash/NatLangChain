"""
JSON file storage backend.

This is the default storage backend that persists blockchain data
to a local JSON file. It maintains backward compatibility with
the original NatLangChain storage format.
"""

import json
import os
import threading
from typing import Any

from storage.base import (
    StorageBackend,
    StorageError,
    StorageReadError,
    StorageWriteError,
)


class JSONFileStorage(StorageBackend):
    """
    JSON file storage backend.

    Stores the blockchain as a JSON file with optional encryption support.
    Thread-safe operations using a file lock.
    """

    def __init__(
        self,
        file_path: str = "chain_data.json",
        encryption_enabled: bool = False,
    ):
        """
        Initialize JSON file storage.

        Args:
            file_path: Path to the JSON file
            encryption_enabled: Whether to use encryption
        """
        self.file_path = file_path
        self.encryption_enabled = encryption_enabled
        self._lock = threading.Lock()

        # Lazy load encryption functions
        self._encrypt_fn = None
        self._decrypt_fn = None
        self._is_encrypted_fn = None

        if encryption_enabled:
            self._init_encryption()

    def _init_encryption(self) -> None:
        """Initialize encryption functions if available."""
        try:
            from encryption import (
                decrypt_chain_data,
                encrypt_chain_data,
                is_encrypted,
            )
            self._encrypt_fn = encrypt_chain_data
            self._decrypt_fn = decrypt_chain_data
            self._is_encrypted_fn = is_encrypted
        except ImportError:
            self.encryption_enabled = False

    def load_chain(self) -> dict[str, Any] | None:
        """
        Load blockchain data from JSON file.

        Returns:
            Dictionary containing chain data, or None if file doesn't exist.

        Raises:
            StorageReadError: If reading fails
        """
        with self._lock:
            try:
                if not os.path.exists(self.file_path):
                    return None

                with open(self.file_path, 'r', encoding='utf-8') as f:
                    raw_data = f.read()

                if not raw_data.strip():
                    return None

                # Handle encrypted data
                if self.encryption_enabled and self._is_encrypted_fn:
                    if self._is_encrypted_fn(raw_data):
                        if self._decrypt_fn:
                            raw_data = self._decrypt_fn(raw_data)
                        else:
                            raise StorageReadError(
                                "Data is encrypted but decryption not available"
                            )

                return json.loads(raw_data)

            except FileNotFoundError:
                return None
            except PermissionError as e:
                raise StorageReadError(f"Permission denied: {self.file_path}") from e
            except json.JSONDecodeError as e:
                raise StorageReadError(f"Invalid JSON format: {e}") from e
            except Exception as e:
                raise StorageReadError(f"Failed to load chain: {e}") from e

    def save_chain(self, chain_data: dict[str, Any]) -> None:
        """
        Save blockchain data to JSON file.

        Args:
            chain_data: Dictionary containing the complete chain state

        Raises:
            StorageWriteError: If writing fails
        """
        with self._lock:
            try:
                # Serialize to JSON
                data = json.dumps(chain_data, indent=2, ensure_ascii=False)

                # Encrypt if enabled
                if self.encryption_enabled and self._encrypt_fn:
                    data = self._encrypt_fn(data)

                # Write to file atomically (write to temp, then rename)
                temp_path = f"{self.file_path}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(data)

                # Atomic rename
                os.replace(temp_path, self.file_path)

            except PermissionError as e:
                raise StorageWriteError(
                    f"Permission denied: {self.file_path}"
                ) from e
            except OSError as e:
                raise StorageWriteError(f"OS error: {e}") from e
            except Exception as e:
                raise StorageWriteError(f"Failed to save chain: {e}") from e

    def is_available(self) -> bool:
        """
        Check if file storage is available.

        Returns:
            True if the file path is writable
        """
        try:
            # Check if directory exists and is writable
            directory = os.path.dirname(self.file_path) or "."
            if not os.path.exists(directory):
                return False
            return os.access(directory, os.W_OK)
        except Exception:
            return False

    def get_info(self) -> dict[str, Any]:
        """Get storage backend information."""
        info = super().get_info()
        info.update({
            "file_path": self.file_path,
            "file_exists": os.path.exists(self.file_path),
            "encryption_enabled": self.encryption_enabled,
        })

        if os.path.exists(self.file_path):
            try:
                stat = os.stat(self.file_path)
                info["file_size_bytes"] = stat.st_size
                info["last_modified"] = stat.st_mtime
            except OSError:
                pass

        return info

    def delete(self) -> bool:
        """
        Delete the storage file.

        Returns:
            True if deleted, False if file didn't exist
        """
        with self._lock:
            try:
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                    return True
                return False
            except OSError:
                return False

    def backup(self, backup_path: str | None = None) -> str:
        """
        Create a backup of the storage file.

        Args:
            backup_path: Path for backup file (default: adds .backup suffix)

        Returns:
            Path to the backup file

        Raises:
            StorageError: If backup fails
        """
        import shutil
        from datetime import datetime

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.file_path}.{timestamp}.backup"

        try:
            with self._lock:
                if os.path.exists(self.file_path):
                    shutil.copy2(self.file_path, backup_path)
                    return backup_path
                else:
                    raise StorageError("No file to backup")
        except OSError as e:
            raise StorageError(f"Backup failed: {e}") from e
