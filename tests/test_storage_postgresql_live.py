"""
Live PostgreSQL round-trip tests.

These run only when NATLANGCHAIN_TEST_DATABASE_URL points at a reachable
PostgreSQL database (CI provides one via a service container). They exercise
the real driver and schema, unlike test_storage_postgresql.py which mocks
psycopg2. Every test uses its own schema-free tables created by the backend
and truncates them on exit, so the database only needs to exist.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

DATABASE_URL = os.getenv("NATLANGCHAIN_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="NATLANGCHAIN_TEST_DATABASE_URL not set")


def _make_chain():
    from blockchain import NatLangChain

    return NatLangChain(
        require_validation=False,
        enable_deduplication=False,
        enable_rate_limiting=False,
        enable_timestamp_validation=False,
        enable_metadata_sanitization=False,
        enable_asset_tracking=False,
        enable_quality_checks=False,
    )


@pytest.fixture
def storage():
    from storage.postgresql import PostgreSQLStorage

    store = PostgreSQLStorage(DATABASE_URL, pool_size=2)
    yield store
    conn = store._get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE entries, pending_entries, blocks, chain_metadata")
        conn.commit()
    finally:
        store._put_conn(conn)
        store.close()


def test_is_available_and_info(storage):
    assert storage.is_available() is True
    info = storage.get_info()
    assert info["backend_type"] == "PostgreSQLStorage"
    assert info["available"] is True


def test_empty_database_loads_as_none(storage):
    assert storage.load_chain() is None


def test_chain_round_trip_preserves_blocks_and_pending(storage):
    from blockchain import NatLangChain, NaturalLanguageEntry

    chain = _make_chain()
    chain.add_entry(NaturalLanguageEntry("Alice sells a bicycle to Bob.", "alice", "sale"))
    chain.mine_pending_entries()
    chain.add_entry(NaturalLanguageEntry("Bob pays Alice forty dollars.", "bob", "payment"))
    assert len(chain.chain) == 2
    assert len(chain.pending_entries) == 1

    storage.save_chain(chain.to_dict())

    loaded = storage.load_chain()
    assert loaded is not None
    restored = NatLangChain.from_dict(loaded)

    assert [b.hash for b in restored.chain] == [b.hash for b in chain.chain]
    assert restored.get_latest_block().hash == chain.get_latest_block().hash
    assert [e.content for e in restored.pending_entries] == ["Bob pays Alice forty dollars."]
    assert restored.validate_chain() is True

    assert storage.get_block_count() == 2
    assert storage.get_entry_count() == 2  # genesis + alice's mined entry
    assert storage.get_block(1)["hash"] == chain.chain[1].hash
    assert storage.get_block(99) is None


def test_resave_upserts_and_drops_orphans(storage):
    from blockchain import NaturalLanguageEntry

    chain = _make_chain()
    chain.add_entry(NaturalLanguageEntry("First entry on the ledger.", "alice", "note"))
    chain.mine_pending_entries()
    storage.save_chain(chain.to_dict())
    assert storage.get_block_count() == 2

    chain.add_entry(NaturalLanguageEntry("Second entry on the ledger.", "bob", "note"))
    chain.mine_pending_entries()
    storage.save_chain(chain.to_dict())
    assert storage.get_block_count() == 3

    # Saving a shorter chain must not leave orphaned blocks behind
    shorter = chain.to_dict()
    shorter["chain"] = shorter["chain"][:2]
    storage.save_chain(shorter)
    assert storage.get_block_count() == 2
    assert storage.load_chain()["chain"][-1]["hash"] == chain.chain[1].hash


def test_search_entries_by_author(storage):
    from blockchain import NaturalLanguageEntry

    chain = _make_chain()
    chain.add_entry(NaturalLanguageEntry("Carol posts an offer for tutoring.", "carol", "offer"))
    chain.add_entry(NaturalLanguageEntry("Dave posts a request for tutoring.", "dave", "request"))
    chain.mine_pending_entries()
    storage.save_chain(chain.to_dict())

    carol = storage.search_entries_by_author("carol")
    assert len(carol) == 1
    assert carol[0]["content"] == "Carol posts an offer for tutoring."
    assert storage.search_entries_by_author("nobody") == []
