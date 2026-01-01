"""
JSON file storage backend.

This is the default storage backend that persists blockchain data
to a local JSON file. It maintains backward compatibility with
the original NatLangChain storage format.

Features:
- Optional gzip compression (typically 70-90% reduction for prose)
- Optional encryption (applied after compression for best results)
- Atomic writes with temp file + rename
- Thread-safe operations
"""

import gzip
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

# Gzip magic bytes for detection
GZIP_MAGIC = b'\x1f\x8b'


class JSONFileStorage(StorageBackend):
    """
    JSON file storage backend.

    Stores the blockchain as a JSON file with optional compression and encryption.
    Thread-safe operations using a file lock.

    Compression is applied first, then encryption (if enabled).
    This order maximizes compression effectiveness.
    """

    def __init__(
        self,
        file_path: str = "chain_data.json",
        encryption_enabled: bool = False,
        compression_enabled: bool = True,
        compression_level: int = 6,
    ):
        """
        Initialize JSON file storage.

        Args:
            file_path: Path to the JSON file
            encryption_enabled: Whether to use encryption
            compression_enabled: Whether to use gzip compression
            compression_level: Compression level 1-9 (default: 6)
        """
        self.file_path = file_path
        self.encryption_enabled = encryption_enabled
        self.compression_enabled = compression_enabled
        self.compression_level = max(1, min(9, compression_level))
        self._lock = threading.Lock()

        # Compression statistics
        self._compression_stats = {
            "saves": 0,
            "loads": 0,
            "bytes_before": 0,
            "bytes_after": 0,
        }

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

    def _is_gzip_compressed(self, data: bytes) -> bool:
        """Check if data is gzip compressed."""
        return len(data) >= 2 and data[:2] == GZIP_MAGIC

    def load_chain(self) -> dict[str, Any] | None:
        """
        Load blockchain data from JSON file.

        Automatically detects and handles:
        - Plain JSON
        - Gzip compressed JSON
        - Encrypted data (with or without compression)

        Returns:
            Dictionary containing chain data, or None if file doesn't exist.

        Raises:
            StorageReadError: If reading fails
        """
        with self._lock:
            try:
                if not os.path.exists(self.file_path):
                    return None

                # Read file as binary to detect compression
                with open(self.file_path, 'rb') as f:
                    raw_bytes = f.read()

                if not raw_bytes:
                    return None

                # Track for stats
                original_size = len(raw_bytes)

                # Handle encrypted data first (encryption wraps compression)
                if self.encryption_enabled and self._is_encrypted_fn:
                    # Encryption produces text, so decode first
                    raw_data = raw_bytes.decode('utf-8')
                    if self._is_encrypted_fn(raw_data):
                        if self._decrypt_fn:
                            raw_data = self._decrypt_fn(raw_data)
                            # After decryption, might be compressed
                            raw_bytes = raw_data.encode('utf-8') if isinstance(raw_data, str) else raw_data
                        else:
                            raise StorageReadError(
                                "Data is encrypted but decryption not available"
                            )

                # Check for gzip compression
                if self._is_gzip_compressed(raw_bytes):
                    try:
                        raw_bytes = gzip.decompress(raw_bytes)
                        self._compression_stats["loads"] += 1
                    except gzip.BadGzipFile as e:
                        raise StorageReadError(f"Invalid gzip data: {e}") from e

                # Decode and parse JSON
                raw_data = raw_bytes.decode('utf-8')
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

        Order of operations:
        1. Serialize to JSON
        2. Compress with gzip (if enabled)
        3. Encrypt (if enabled)
        4. Write atomically

        Args:
            chain_data: Dictionary containing the complete chain state

        Raises:
            StorageWriteError: If writing fails
        """
        with self._lock:
            try:
                # Serialize to JSON (compact format for compression efficiency)
                json_str = json.dumps(chain_data, separators=(',', ':'), ensure_ascii=False)
                data_bytes = json_str.encode('utf-8')

                # Track uncompressed size
                original_size = len(data_bytes)
                self._compression_stats["bytes_before"] += original_size

                # Compress if enabled
                if self.compression_enabled:
                    data_bytes = gzip.compress(data_bytes, compresslevel=self.compression_level)
                    self._compression_stats["saves"] += 1

                compressed_size = len(data_bytes)
                self._compression_stats["bytes_after"] += compressed_size

                # Encrypt if enabled (encryption works on the compressed bytes)
                if self.encryption_enabled and self._encrypt_fn:
                    # Encryption expects string, encode compressed bytes as base64 or pass through
                    data_bytes = self._encrypt_fn(data_bytes)
                    if isinstance(data_bytes, str):
                        data_bytes = data_bytes.encode('utf-8')

                # Write to file atomically (write to temp, then rename)
                temp_path = f"{self.file_path}.tmp"
                with open(temp_path, 'wb') as f:
                    f.write(data_bytes)

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
            "compression_enabled": self.compression_enabled,
            "compression_level": self.compression_level if self.compression_enabled else None,
        })

        if os.path.exists(self.file_path):
            try:
                stat = os.stat(self.file_path)
                info["file_size_bytes"] = stat.st_size
                info["last_modified"] = stat.st_mtime
            except OSError:
                pass

        # Add compression statistics
        if self._compression_stats["saves"] > 0:
            bytes_before = self._compression_stats["bytes_before"]
            bytes_after = self._compression_stats["bytes_after"]
            if bytes_before > 0:
                ratio = 1.0 - (bytes_after / bytes_before)
                info["compression_stats"] = {
                    "saves": self._compression_stats["saves"],
                    "loads": self._compression_stats["loads"],
                    "bytes_before": bytes_before,
                    "bytes_after": bytes_after,
                    "bytes_saved": bytes_before - bytes_after,
                    "compression_ratio_pct": round(ratio * 100, 2),
                }

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
