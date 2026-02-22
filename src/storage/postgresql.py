"""
PostgreSQL storage backend.

This backend stores blockchain data in PostgreSQL for production
scalability, supporting:
- ACID transactions
- Concurrent access
- Efficient queries
- Horizontal scaling (read replicas)
"""

import json
import threading
from typing import Any
from urllib.parse import urlparse

from storage.base import (
    StorageBackend,
    StorageConnectionError,
    StorageReadError,
    StorageWriteError,
)

# SQL for creating tables
CREATE_TABLES_SQL = """
-- Chain metadata table
CREATE TABLE IF NOT EXISTS chain_metadata (
    id INTEGER PRIMARY KEY DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    difficulty INTEGER DEFAULT 2,
    pending_entries_count INTEGER DEFAULT 0,
    CONSTRAINT single_row CHECK (id = 1)
);

-- Blocks table
CREATE TABLE IF NOT EXISTS blocks (
    id SERIAL PRIMARY KEY,
    block_index INTEGER UNIQUE NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) NOT NULL,
    nonce INTEGER NOT NULL DEFAULT 0,
    entries_json JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Entries table (denormalized for efficient queries)
CREATE TABLE IF NOT EXISTS entries (
    id SERIAL PRIMARY KEY,
    block_id INTEGER REFERENCES blocks(id) ON DELETE CASCADE,
    block_index INTEGER NOT NULL,
    entry_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    intent TEXT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    fingerprint VARCHAR(64),
    validation_status VARCHAR(50),
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (block_index, entry_index)
);

-- Pending entries table
CREATE TABLE IF NOT EXISTS pending_entries (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    intent TEXT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    fingerprint VARCHAR(64),
    validation_status VARCHAR(50),
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index);
CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);
CREATE INDEX IF NOT EXISTS idx_entries_author ON entries(author);
CREATE INDEX IF NOT EXISTS idx_entries_block ON entries(block_index);
CREATE INDEX IF NOT EXISTS idx_entries_timestamp ON entries(timestamp);

-- Initialize metadata if not exists
INSERT INTO chain_metadata (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
"""


class PostgreSQLStorage(StorageBackend):
    """
    PostgreSQL storage backend for production deployments.

    Requires psycopg2 or psycopg2-binary package.
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        auto_create_tables: bool = True,
    ):
        """
        Initialize PostgreSQL storage.

        Args:
            database_url: PostgreSQL connection URL
                Format: postgresql://user:password@host:port/database
            pool_size: Connection pool size
            auto_create_tables: Create tables if they don't exist
        """
        self.database_url = database_url
        self.pool_size = pool_size
        self._pool = None
        self._lock = threading.Lock()

        # Parse URL for info
        parsed = urlparse(database_url)
        self._host = parsed.hostname or "localhost"
        self._port = parsed.port or 5432
        self._database = parsed.path.lstrip("/") if parsed.path else ""

        # Initialize connection pool
        self._init_pool()

        if auto_create_tables:
            self._create_tables()

    def _init_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            import psycopg2
            from psycopg2 import pool
        except ImportError:
            raise StorageConnectionError(
                "psycopg2 not installed. Install with: pip install psycopg2-binary"
            )

        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.pool_size,
                dsn=self.database_url,
            )
        except psycopg2.Error as e:
            raise StorageConnectionError(f"Failed to connect to PostgreSQL: {e}")

    def _get_conn(self):
        """Get a connection from the pool (thread-safe).
        # TODO: add connection health check / reconnect on stale connections
        """
        with self._lock:
            if self._pool is None:
                raise StorageConnectionError("Connection pool not initialized")
            return self._pool.getconn()

    def _put_conn(self, conn):
        """Return a connection to the pool (thread-safe)."""
        with self._lock:
            if self._pool:
                self._pool.putconn(conn)

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLES_SQL)
            conn.commit()
        except (OSError, ValueError) as e:
            conn.rollback()
            raise StorageConnectionError(f"Failed to create tables: {e}")
        finally:
            self._put_conn(conn)

    def load_chain(self) -> dict[str, Any] | None:
        """
        Load blockchain data from PostgreSQL.

        Returns:
            Dictionary containing chain data, or None if empty
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                # Get metadata
                cur.execute("""
                    SELECT difficulty, pending_entries_count
                    FROM chain_metadata WHERE id = 1
                """)
                metadata = cur.fetchone()
                if not metadata:
                    return None

                difficulty, pending_count = metadata

                # Get blocks with entries
                cur.execute("""
                    SELECT block_index, timestamp, previous_hash, hash, nonce, entries_json
                    FROM blocks ORDER BY block_index ASC
                """)
                blocks_rows = cur.fetchall()

                if not blocks_rows:
                    return None

                # Build chain structure
                chain = []
                for row in blocks_rows:
                    block_index, timestamp, prev_hash, hash_val, nonce, entries_json = row
                    chain.append(
                        {
                            "index": block_index,
                            "timestamp": timestamp,
                            "previous_hash": prev_hash,
                            "hash": hash_val,
                            "nonce": nonce,
                            "entries": entries_json if entries_json else [],
                        }
                    )

                # Get pending entries
                cur.execute("""
                    SELECT content, author, intent, timestamp, fingerprint,
                           validation_status, metadata_json
                    FROM pending_entries ORDER BY id ASC
                """)
                pending_rows = cur.fetchall()

                pending_entries = []
                for row in pending_rows:
                    content, author, intent, ts, fp, status, meta = row
                    pending_entries.append(
                        {
                            "content": content,
                            "author": author,
                            "intent": intent,
                            "timestamp": ts,
                            "fingerprint": fp,
                            "validation_status": status,
                            "metadata": meta if meta else {},
                        }
                    )

                return {
                    "chain": chain,
                    "pending_entries": pending_entries,
                    "difficulty": difficulty,
                }

        except (OSError, KeyError, ValueError) as e:
            raise StorageReadError(f"Failed to load chain: {e}")
        finally:
            self._put_conn(conn)

    def save_chain(self, chain_data: dict[str, Any]) -> None:
        """
        Save blockchain data to PostgreSQL.

        Uses a transaction with UPSERT pattern to prevent data loss.
        Blocks and entries are upserted, and orphaned records are cleaned up
        only after successful inserts.

        Args:
            chain_data: Dictionary containing the complete chain state
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                chain = chain_data.get("chain", [])
                block_indices = []

                # Upsert blocks
                for block in chain:
                    block_index = block.get("index", 0)
                    block_indices.append(block_index)
                    entries_json = json.dumps(block.get("entries", []))
                    cur.execute(
                        """
                        INSERT INTO blocks
                            (block_index, timestamp, previous_hash, hash, nonce, entries_json)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (block_index) DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            previous_hash = EXCLUDED.previous_hash,
                            hash = EXCLUDED.hash,
                            nonce = EXCLUDED.nonce,
                            entries_json = EXCLUDED.entries_json
                        RETURNING id
                    """,
                        (
                            block_index,
                            block.get("timestamp", 0),
                            block.get("previous_hash", ""),
                            block.get("hash", ""),
                            block.get("nonce", 0),
                            entries_json,
                        ),
                    )
                    block_id = cur.fetchone()[0]

                    # Delete existing entries for this block and insert new ones
                    cur.execute(
                        "DELETE FROM entries WHERE block_index = %s", (block_index,)
                    )

                    # Insert entries (denormalized for queries)
                    for i, entry in enumerate(block.get("entries", [])):
                        cur.execute(
                            """
                            INSERT INTO entries
                                (block_id, block_index, entry_index, content, author,
                                 intent, timestamp, fingerprint, validation_status,
                                 metadata_json)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                block_id,
                                block_index,
                                i,
                                entry.get("content", ""),
                                entry.get("author", ""),
                                entry.get("intent", ""),
                                entry.get("timestamp", 0),
                                entry.get("fingerprint"),
                                entry.get("validation_status"),
                                json.dumps(entry.get("metadata", {})),
                            ),
                        )

                # Clean up blocks that are no longer in the chain (only after successful upserts)
                if block_indices:
                    cur.execute(
                        "DELETE FROM blocks WHERE block_index NOT IN %s",
                        (tuple(block_indices),)
                    )
                else:
                    # If no blocks, clear all (chain reset scenario)
                    cur.execute("DELETE FROM blocks")

                # Handle pending entries: clear and re-insert
                cur.execute("DELETE FROM pending_entries")
                for entry in chain_data.get("pending_entries", []):
                    cur.execute(
                        """
                        INSERT INTO pending_entries
                            (content, author, intent, timestamp, fingerprint,
                             validation_status, metadata_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            entry.get("content", ""),
                            entry.get("author", ""),
                            entry.get("intent", ""),
                            entry.get("timestamp", 0),
                            entry.get("fingerprint"),
                            entry.get("validation_status"),
                            json.dumps(entry.get("metadata", {})),
                        ),
                    )

                # Update metadata
                cur.execute(
                    """
                    UPDATE chain_metadata SET
                        difficulty = %s,
                        pending_entries_count = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """,
                    (
                        chain_data.get("difficulty", 2),
                        len(chain_data.get("pending_entries", [])),
                    ),
                )

            conn.commit()

        except (OSError, ValueError) as e:
            conn.rollback()
            raise StorageWriteError(f"Failed to save chain: {e}")
        finally:
            self._put_conn(conn)

    def save_block(self, block_data: dict[str, Any]) -> None:
        """
        Save a single block (incremental update).

        Args:
            block_data: Dictionary containing block data
        """
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                entries_json = json.dumps(block_data.get("entries", []))
                cur.execute(
                    """
                    INSERT INTO blocks
                        (block_index, timestamp, previous_hash, hash, nonce, entries_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (block_index) DO UPDATE SET
                        timestamp = EXCLUDED.timestamp,
                        previous_hash = EXCLUDED.previous_hash,
                        hash = EXCLUDED.hash,
                        nonce = EXCLUDED.nonce,
                        entries_json = EXCLUDED.entries_json
                    RETURNING id
                """,
                    (
                        block_data.get("index", 0),
                        block_data.get("timestamp", 0),
                        block_data.get("previous_hash", ""),
                        block_data.get("hash", ""),
                        block_data.get("nonce", 0),
                        entries_json,
                    ),
                )
                block_id = cur.fetchone()[0]

                # Update entries
                cur.execute(
                    "DELETE FROM entries WHERE block_index = %s", (block_data.get("index", 0),)
                )

                for i, entry in enumerate(block_data.get("entries", [])):
                    cur.execute(
                        """
                        INSERT INTO entries
                            (block_id, block_index, entry_index, content, author,
                             intent, timestamp, fingerprint, validation_status,
                             metadata_json)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                        (
                            block_id,
                            block_data.get("index", 0),
                            i,
                            entry.get("content", ""),
                            entry.get("author", ""),
                            entry.get("intent", ""),
                            entry.get("timestamp", 0),
                            entry.get("fingerprint"),
                            entry.get("validation_status"),
                            json.dumps(entry.get("metadata", {})),
                        ),
                    )

            conn.commit()

        except (OSError, ValueError) as e:
            conn.rollback()
            raise StorageWriteError(f"Failed to save block: {e}")
        finally:
            self._put_conn(conn)

    def is_available(self) -> bool:
        """Check if PostgreSQL is available."""
        conn = None
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except (OSError, RuntimeError):
            return False
        finally:
            if conn is not None:
                self._put_conn(conn)

    def get_info(self) -> dict[str, Any]:
        """Get storage backend information."""
        info = super().get_info()
        info.update(
            {
                "host": self._host,
                "port": self._port,
                "database": self._database,
                "pool_size": self.pool_size,
            }
        )

        if self.is_available():
            conn = self._get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM blocks")
                    info["block_count"] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM entries")
                    info["entry_count"] = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM pending_entries")
                    info["pending_count"] = cur.fetchone()[0]
            finally:
                self._put_conn(conn)

        return info

    def get_block(self, index: int) -> dict[str, Any] | None:
        """Get a single block by index."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT block_index, timestamp, previous_hash, hash, nonce, entries_json
                    FROM blocks WHERE block_index = %s
                """,
                    (index,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                block_index, timestamp, prev_hash, hash_val, nonce, entries_json = row
                return {
                    "index": block_index,
                    "timestamp": timestamp,
                    "previous_hash": prev_hash,
                    "hash": hash_val,
                    "nonce": nonce,
                    "entries": entries_json if entries_json else [],
                }
        finally:
            self._put_conn(conn)

    def get_block_count(self) -> int:
        """Get number of blocks."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM blocks")
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def get_entry_count(self) -> int:
        """Get total number of entries."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM entries")
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def search_entries_by_author(self, author: str, limit: int = 100) -> list[dict[str, Any]]:
        """Search entries by author using database index."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT content, author, intent, timestamp, fingerprint,
                           validation_status, metadata_json, block_index, entry_index
                    FROM entries
                    WHERE author = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """,
                    (author, limit),
                )

                results = []
                for row in cur.fetchall():
                    content, auth, intent, ts, fp, status, meta, bi, ei = row
                    results.append(
                        {
                            "content": content,
                            "author": auth,
                            "intent": intent,
                            "timestamp": ts,
                            "fingerprint": fp,
                            "validation_status": status,
                            "metadata": meta if meta else {},
                            "block_index": bi,
                            "entry_index": ei,
                        }
                    )
                return results
        finally:
            self._put_conn(conn)

    def close(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            if self._pool:
                self._pool.closeall()
                self._pool = None
