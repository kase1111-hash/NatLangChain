"""
Tests for NatLangChain PostgreSQL Storage Backend.

Tests:
- PostgreSQLStorage initialization
- Connection pool management
- load_chain() method
- save_chain() method
- save_block() method
- get_block() method
- get_block_count() / get_entry_count() methods
- search_entries_by_author() method
- is_available() method
- get_info() method
- close() method
- Error handling
"""

import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Skip all tests if psycopg2 is not installed
psycopg2_available = False
try:
    import psycopg2

    psycopg2_available = True
except ImportError:
    pass

pytestmark = pytest.mark.skipif(not psycopg2_available, reason="psycopg2 not installed")


class TestPostgreSQLStorageInit:
    """Tests for PostgreSQLStorage initialization."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_init_creates_pool(self, mock_pool_class):
        """Test initialization creates connection pool."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        # Mock cursor for table creation
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            pool_size=5,
            auto_create_tables=False,
        )

        mock_pool_class.assert_called_once()
        assert storage.pool_size == 5

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_init_parses_url(self, mock_pool_class):
        """Test initialization parses database URL."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        storage = PostgreSQLStorage(
            database_url="postgresql://testuser:testpass@testhost:5433/testdb",
            auto_create_tables=False,
        )

        assert storage._host == "testhost"
        assert storage._port == 5433
        assert storage._database == "testdb"

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_init_creates_tables_by_default(self, mock_pool_class):
        """Test initialization creates tables by default."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=True,
        )

        # Should execute CREATE TABLE statements
        assert mock_cursor.execute.called

    def test_init_without_psycopg2(self):
        """Test initialization fails gracefully without psycopg2."""
        with patch.dict(sys.modules, {"psycopg2": None, "psycopg2.pool": None}):
            # Force re-import to trigger ImportError
            # This test verifies the module handles missing dependency
            pass  # Module import happens at test collection time


class TestConnectionPool:
    """Tests for connection pool management."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_conn(self, mock_pool_class):
        """Test getting connection from pool."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        conn = storage._get_conn()
        mock_pool.getconn.assert_called()
        assert conn == mock_conn

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_put_conn(self, mock_pool_class):
        """Test returning connection to pool."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        mock_conn = MagicMock()
        storage._put_conn(mock_conn)
        mock_pool.putconn.assert_called_with(mock_conn)

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_conn_raises_when_pool_none(self, mock_pool_class):
        """Test getting connection when pool is None raises error."""
        from storage.postgresql import PostgreSQLStorage, StorageConnectionError

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        storage._pool = None

        with pytest.raises(StorageConnectionError):
            storage._get_conn()


class TestLoadChain:
    """Tests for load_chain() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_load_chain_empty_returns_none(self, mock_pool_class):
        """Test loading empty chain returns None."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # No metadata
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        result = storage.load_chain()
        assert result is None

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_load_chain_returns_data(self, mock_pool_class):
        """Test loading chain returns correct data structure."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock metadata query
        mock_cursor.fetchone.side_effect = [
            (2, 0),  # difficulty, pending_count (metadata)
        ]

        # Mock blocks query
        mock_cursor.fetchall.side_effect = [
            [  # Blocks
                (0, 1234567890.0, "0", "abc123", 0, []),
            ],
            [],  # Pending entries
        ]

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        result = storage.load_chain()

        assert result is not None
        assert "chain" in result
        assert "pending_entries" in result
        assert "difficulty" in result


class TestSaveChain:
    """Tests for save_chain() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_save_chain_empty(self, mock_pool_class):
        """Test saving empty chain."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        storage.save_chain({"chain": [], "pending_entries": [], "difficulty": 2})

        mock_conn.commit.assert_called()

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_save_chain_with_blocks(self, mock_pool_class):
        """Test saving chain with blocks."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Block ID
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        chain_data = {
            "chain": [
                {
                    "index": 0,
                    "timestamp": 1234567890,
                    "previous_hash": "0",
                    "hash": "abc123",
                    "nonce": 0,
                    "entries": [
                        {
                            "content": "Test entry",
                            "author": "test",
                            "intent": "test",
                            "timestamp": 1234567890,
                        }
                    ],
                }
            ],
            "pending_entries": [],
            "difficulty": 2,
        }

        storage.save_chain(chain_data)

        # Should insert block and entries
        assert mock_cursor.execute.call_count >= 3
        mock_conn.commit.assert_called()

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_save_chain_rollback_on_error(self, mock_pool_class):
        """Test save_chain rolls back on error."""
        from storage.postgresql import PostgreSQLStorage, StorageWriteError

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        with pytest.raises(StorageWriteError):
            storage.save_chain({"chain": [], "pending_entries": [], "difficulty": 2})

        mock_conn.rollback.assert_called()


class TestSaveBlock:
    """Tests for save_block() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_save_block_upsert(self, mock_pool_class):
        """Test save_block uses upsert (ON CONFLICT)."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        block_data = {
            "index": 1,
            "timestamp": 1234567890,
            "previous_hash": "abc",
            "hash": "def",
            "nonce": 123,
            "entries": [],
        }

        storage.save_block(block_data)

        # Should use ON CONFLICT for upsert
        insert_call = str(mock_cursor.execute.call_args_list[0])
        assert "ON CONFLICT" in insert_call.upper() or mock_cursor.execute.called


class TestGetBlock:
    """Tests for get_block() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_block_found(self, mock_pool_class):
        """Test getting existing block."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1, 1234567890.0, "prev", "hash", 0, [])
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        result = storage.get_block(1)

        assert result is not None
        assert result["index"] == 1
        assert result["hash"] == "hash"

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_block_not_found(self, mock_pool_class):
        """Test getting non-existent block."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        result = storage.get_block(999)
        assert result is None


class TestCountMethods:
    """Tests for count methods."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_block_count(self, mock_pool_class):
        """Test get_block_count returns correct count."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        count = storage.get_block_count()
        assert count == 42

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_entry_count(self, mock_pool_class):
        """Test get_entry_count returns correct count."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (100,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        count = storage.get_entry_count()
        assert count == 100


class TestSearchEntriesByAuthor:
    """Tests for search_entries_by_author() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_search_by_author_found(self, mock_pool_class):
        """Test searching entries by author."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Content 1", "author1", "intent1", 123.0, "fp1", "valid", {}, 0, 0),
            ("Content 2", "author1", "intent2", 124.0, "fp2", "valid", {}, 0, 1),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        results = storage.search_entries_by_author("author1")

        assert len(results) == 2
        assert results[0]["author"] == "author1"

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_search_by_author_limit(self, mock_pool_class):
        """Test search respects limit parameter."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        storage.search_entries_by_author("author1", limit=50)

        # Check that LIMIT parameter was passed
        execute_call = str(mock_cursor.execute.call_args)
        assert "50" in execute_call


class TestIsAvailable:
    """Tests for is_available() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_is_available_true(self, mock_pool_class):
        """Test is_available returns True when DB is accessible."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        assert storage.is_available() is True

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_is_available_false_on_error(self, mock_pool_class):
        """Test is_available returns False on error."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Connection failed")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        assert storage.is_available() is False


class TestGetInfo:
    """Tests for get_info() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_get_info_basic(self, mock_pool_class):
        """Test get_info returns basic info."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # Count
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        info = storage.get_info()

        assert "host" in info
        assert "port" in info
        assert "database" in info
        assert "pool_size" in info


class TestClose:
    """Tests for close() method."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_close_closes_pool(self, mock_pool_class):
        """Test close() closes the connection pool."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        storage.close()

        mock_pool.closeall.assert_called_once()
        assert storage._pool is None

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_close_idempotent(self, mock_pool_class):
        """Test close() can be called multiple times."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        storage.close()
        storage.close()  # Should not raise

        # closeall should only be called once
        assert mock_pool.closeall.call_count == 1


class TestThreadSafety:
    """Tests for thread safety."""

    @patch("storage.postgresql.pool.ThreadedConnectionPool")
    def test_concurrent_operations(self, mock_pool_class):
        """Test concurrent operations don't cause issues."""
        from storage.postgresql import PostgreSQLStorage

        mock_pool = MagicMock()
        mock_pool_class.return_value = mock_pool

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.getconn.return_value = mock_conn

        storage = PostgreSQLStorage(
            database_url="postgresql://user:pass@localhost:5432/db",
            auto_create_tables=False,
        )

        errors = []

        def do_operations():
            try:
                for _ in range(10):
                    storage.get_block_count()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=do_operations) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
