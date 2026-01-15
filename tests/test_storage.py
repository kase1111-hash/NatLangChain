"""
Tests for storage backends.
"""

import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from storage import StorageError, get_storage_backend
from storage.base import StorageReadError
from storage.json_file import JSONFileStorage
from storage.memory import MemoryStorage

# Sample chain data for testing
SAMPLE_CHAIN_DATA = {
    "chain": [
        {
            "index": 0,
            "timestamp": 1234567890.0,
            "previous_hash": "0",
            "hash": "abc123",
            "nonce": 0,
            "entries": [],
        },
        {
            "index": 1,
            "timestamp": 1234567900.0,
            "previous_hash": "abc123",
            "hash": "def456",
            "nonce": 42,
            "entries": [
                {
                    "content": "Test entry",
                    "author": "alice",
                    "intent": "testing",
                    "timestamp": 1234567895.0,
                    "fingerprint": "fp123",
                    "metadata": {"key": "value"},
                }
            ],
        },
    ],
    "pending_entries": [
        {
            "content": "Pending entry",
            "author": "bob",
            "intent": "pending",
            "timestamp": 1234567910.0,
        }
    ],
    "difficulty": 2,
}


class TestMemoryStorage:
    """Tests for MemoryStorage backend."""

    def test_init_empty(self):
        """Test that new memory storage is empty."""
        storage = MemoryStorage()
        assert storage.load_chain() is None
        assert storage.is_available() is True

    def test_save_and_load(self):
        """Test saving and loading chain data."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)

        loaded = storage.load_chain()
        assert loaded is not None
        assert loaded["difficulty"] == 2
        assert len(loaded["chain"]) == 2
        assert len(loaded["pending_entries"]) == 1

    def test_deep_copy_isolation(self):
        """Test that modifications don't affect stored data."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)

        # Modify the returned data
        loaded = storage.load_chain()
        loaded["chain"].append({"index": 99})

        # Original should be unchanged
        loaded2 = storage.load_chain()
        assert len(loaded2["chain"]) == 2

    def test_clear(self):
        """Test clearing stored data."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)
        assert storage.load_chain() is not None

        storage.clear()
        assert storage.load_chain() is None

    def test_get_info(self):
        """Test getting storage info."""
        storage = MemoryStorage()
        info = storage.get_info()

        assert info["backend_type"] == "MemoryStorage"
        assert info["available"] is True
        assert info["has_data"] is False

        storage.save_chain(SAMPLE_CHAIN_DATA)
        info = storage.get_info()
        assert info["has_data"] is True
        assert info["block_count"] == 2
        assert info["entry_count"] == 1

    def test_block_count(self):
        """Test getting block count."""
        storage = MemoryStorage()
        assert storage.get_block_count() == 0

        storage.save_chain(SAMPLE_CHAIN_DATA)
        assert storage.get_block_count() == 2

    def test_entry_count(self):
        """Test getting entry count."""
        storage = MemoryStorage()
        assert storage.get_entry_count() == 0

        storage.save_chain(SAMPLE_CHAIN_DATA)
        assert storage.get_entry_count() == 1

    def test_thread_safety(self):
        """Test thread-safe operations."""
        storage = MemoryStorage()
        results = []

        def save_and_load(n):
            data = {"chain": [{"index": n}], "pending_entries": []}
            storage.save_chain(data)
            loaded = storage.load_chain()
            results.append(loaded is not None)

        threads = [threading.Thread(target=save_and_load, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)


class TestJSONFileStorage:
    """Tests for JSONFileStorage backend."""

    def test_init_nonexistent_file(self):
        """Test loading from nonexistent file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = JSONFileStorage(os.path.join(tmpdir, "nonexistent.json"))
            assert storage.load_chain() is None

    def test_save_and_load(self):
        """Test saving and loading chain data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)

            storage.save_chain(SAMPLE_CHAIN_DATA)

            loaded = storage.load_chain()
            assert loaded is not None
            assert loaded["difficulty"] == 2
            assert len(loaded["chain"]) == 2

    def test_file_persistence(self):
        """Test that data persists to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")

            # Save with one instance
            storage1 = JSONFileStorage(filepath)
            storage1.save_chain(SAMPLE_CHAIN_DATA)

            # Load with new instance
            storage2 = JSONFileStorage(filepath)
            loaded = storage2.load_chain()

            assert loaded is not None
            assert len(loaded["chain"]) == 2

    def test_json_format(self):
        """Test that file contains valid JSON (with compression disabled)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            # Disable compression to test raw JSON format
            storage = JSONFileStorage(filepath, compression_enabled=False)
            storage.save_chain(SAMPLE_CHAIN_DATA)

            with open(filepath) as f:
                data = json.load(f)

            assert data["difficulty"] == 2
            assert len(data["chain"]) == 2

    def test_empty_file(self):
        """Test loading from empty file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "empty.json")
            with open(filepath, "w") as f:
                f.write("")

            storage = JSONFileStorage(filepath)
            assert storage.load_chain() is None

    def test_invalid_json(self):
        """Test that invalid JSON raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "invalid.json")
            with open(filepath, "w") as f:
                f.write("not valid json {{{")

            storage = JSONFileStorage(filepath)
            with pytest.raises(StorageReadError):
                storage.load_chain()

    def test_is_available(self):
        """Test availability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)
            assert storage.is_available() is True

            # Nonexistent directory
            storage2 = JSONFileStorage("/nonexistent/path/chain.json")
            assert storage2.is_available() is False

    def test_get_info(self):
        """Test getting storage info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)

            info = storage.get_info()
            assert info["backend_type"] == "JSONFileStorage"
            assert info["file_exists"] is False

            storage.save_chain(SAMPLE_CHAIN_DATA)
            info = storage.get_info()
            assert info["file_exists"] is True
            assert "file_size_bytes" in info

    def test_delete(self):
        """Test deleting storage file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)

            # Delete nonexistent returns False
            assert storage.delete() is False

            storage.save_chain(SAMPLE_CHAIN_DATA)
            assert os.path.exists(filepath)

            assert storage.delete() is True
            assert not os.path.exists(filepath)

    def test_backup(self):
        """Test creating backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            # Disable compression so backup is plain JSON
            storage = JSONFileStorage(filepath, compression_enabled=False)
            storage.save_chain(SAMPLE_CHAIN_DATA)

            backup_path = os.path.join(tmpdir, "backup.json")
            result = storage.backup(backup_path)

            assert result == backup_path
            assert os.path.exists(backup_path)

            with open(backup_path) as f:
                data = json.load(f)
            assert len(data["chain"]) == 2

    def test_atomic_write(self):
        """Test that writes are atomic (no partial files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)

            # Write initial data
            storage.save_chain(SAMPLE_CHAIN_DATA)

            # Verify no temp file remains
            temp_path = f"{filepath}.tmp"
            assert not os.path.exists(temp_path)

    def test_unicode_content(self):
        """Test handling of unicode content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            storage = JSONFileStorage(filepath)

            unicode_data = {
                "chain": [
                    {
                        "index": 0,
                        "entries": [
                            {
                                "content": "Unicode: caf\u00e9 \u2014 \u4e2d\u6587 \U0001f604",
                                "author": "test",
                            }
                        ],
                    }
                ],
                "pending_entries": [],
            }

            storage.save_chain(unicode_data)
            loaded = storage.load_chain()

            assert (
                loaded["chain"][0]["entries"][0]["content"]
                == "Unicode: caf\u00e9 \u2014 \u4e2d\u6587 \U0001f604"
            )


class TestStorageBackendInterface:
    """Test the abstract StorageBackend interface methods."""

    def test_context_manager(self):
        """Test context manager protocol."""
        storage = MemoryStorage()
        with storage as s:
            s.save_chain(SAMPLE_CHAIN_DATA)
            assert s.load_chain() is not None

    def test_get_block(self):
        """Test getting a single block."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)

        block = storage.get_block(0)
        assert block is not None
        assert block["index"] == 0

        block = storage.get_block(1)
        assert block is not None
        assert block["index"] == 1

        block = storage.get_block(99)
        assert block is None

    def test_get_blocks_range(self):
        """Test getting a range of blocks."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)

        blocks = storage.get_blocks_range(0, 1)
        assert len(blocks) == 1
        assert blocks[0]["index"] == 0

        blocks = storage.get_blocks_range(0, 2)
        assert len(blocks) == 2

    def test_search_entries_by_author(self):
        """Test searching entries by author."""
        storage = MemoryStorage()
        storage.save_chain(SAMPLE_CHAIN_DATA)

        results = storage.search_entries_by_author("alice")
        assert len(results) == 1
        assert results[0]["content"] == "Test entry"

        results = storage.search_entries_by_author("unknown")
        assert len(results) == 0


class TestGetStorageBackend:
    """Test the factory function for getting storage backends."""

    def test_default_json(self, monkeypatch):
        """Test default is JSON storage."""
        monkeypatch.delenv("STORAGE_BACKEND", raising=False)
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            monkeypatch.setenv("CHAIN_DATA_FILE", filepath)

            storage = get_storage_backend()
            assert isinstance(storage, JSONFileStorage)

    def test_explicit_json(self, monkeypatch):
        """Test explicit JSON backend selection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "chain.json")
            monkeypatch.setenv("STORAGE_BACKEND", "json")
            monkeypatch.setenv("CHAIN_DATA_FILE", filepath)

            storage = get_storage_backend()
            assert isinstance(storage, JSONFileStorage)

    def test_memory_backend(self, monkeypatch):
        """Test memory backend selection."""
        monkeypatch.setenv("STORAGE_BACKEND", "memory")

        storage = get_storage_backend()
        assert isinstance(storage, MemoryStorage)

    def test_postgresql_without_url(self, monkeypatch):
        """Test PostgreSQL without DATABASE_URL raises error."""
        monkeypatch.setenv("STORAGE_BACKEND", "postgresql")
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(StorageError):
            get_storage_backend()

    def test_unknown_backend(self, monkeypatch):
        """Test unknown backend raises error."""
        monkeypatch.setenv("STORAGE_BACKEND", "unknown")

        with pytest.raises(StorageError):
            get_storage_backend()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
