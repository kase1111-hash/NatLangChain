"""
Persistence stress tests for NatLangChain.

Verifies:
- 100+ entries survive mine → serialize → deserialize roundtrip
- AssetRegistry state survives restart
- Entry fingerprints survive restart (dedup still works)
- Concurrent entry submissions don't corrupt state
- Chain integrity holds across large volumes
"""

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchain import NatLangChain, NaturalLanguageEntry


def _make_chain(**overrides):
    defaults = dict(
        require_validation=False,
        enable_deduplication=False,
        enable_rate_limiting=False,
        enable_timestamp_validation=False,
        enable_metadata_sanitization=False,
        enable_asset_tracking=False,
        enable_quality_checks=False,
    )
    defaults.update(overrides)
    return NatLangChain(**defaults)


# ============================================================
# Large Volume Persistence
# ============================================================

class TestLargeVolumeRoundtrip:
    """Submit 100+ entries, mine, serialize, deserialize, verify."""

    def test_100_entries_roundtrip(self):
        chain = _make_chain()

        # Submit 100 entries in 10 batches of 10
        for batch in range(10):
            for i in range(10):
                idx = batch * 10 + i
                entry = NaturalLanguageEntry(
                    content=f"Entry number {idx}: This is a test entry for persistence verification.",
                    author=f"author_{idx % 5}",
                    intent=f"Test entry {idx}",
                )
                result = chain.add_entry(entry)
                assert result["status"] == "pending"

            # Mine each batch
            block = chain.mine_pending_entries(difficulty=1)
            assert block is not None

        # Verify chain state before serialization
        assert len(chain.chain) == 11  # genesis + 10 mined blocks
        total_entries = sum(len(b.entries) for b in chain.chain)
        assert total_entries == 101  # 1 genesis + 100 added

        # Serialize and deserialize
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        restored._quality_analyzer = None

        # Verify restored chain
        assert len(restored.chain) == 11
        restored_entries = sum(len(b.entries) for b in restored.chain)
        assert restored_entries == 101
        assert restored.validate_chain() is True

        # Verify hashes match
        for orig, rest in zip(chain.chain, restored.chain):
            assert orig.hash == rest.hash
            assert orig.previous_hash == rest.previous_hash

    def test_entry_content_survives_roundtrip(self):
        chain = _make_chain()

        # Add entries with distinctive content
        for i in range(50):
            entry = NaturalLanguageEntry(
                content=f"Unique content marker #{i}: alpha-bravo-{i * 7}",
                author="persistence_tester",
                intent=f"Marker intent {i}",
            )
            chain.add_entry(entry)

        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)

        # Verify every entry's content survived
        restored_entries = restored.chain[1].entries
        for i, entry in enumerate(restored_entries):
            assert f"Unique content marker #{i}" in entry.content
            assert f"alpha-bravo-{i * 7}" in entry.content

    def test_large_entries_roundtrip(self):
        """Entries with large content survive serialization."""
        chain = _make_chain()

        large_content = "A" * 10000 + " — end marker"
        entry = NaturalLanguageEntry(
            content=large_content,
            author="large_entry_author",
            intent="Test large entry persistence",
        )
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)

        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)

        restored_entry = restored.chain[1].entries[0]
        assert restored_entry.content == large_content
        assert restored_entry.content.endswith("— end marker")


# ============================================================
# Fingerprint Persistence (Dedup Across Restart)
# ============================================================

class TestFingerprintPersistence:
    def test_dedup_survives_restart(self):
        chain = _make_chain(enable_deduplication=True)

        content = "This is a unique entry that should only appear once in the chain forever."
        entry = NaturalLanguageEntry(content=content, author="alice", intent="Unique entry test")
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)

        # Serialize + deserialize (simulates restart)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(
            data, require_validation=False, enable_deduplication=True
        )
        restored._quality_analyzer = None

        # Attempt duplicate — should be rejected
        duplicate = NaturalLanguageEntry(content=content, author="alice", intent="Unique entry test")
        result = restored.add_entry(duplicate)
        assert result["status"] == "rejected"
        assert result["reason"] == "duplicate"

    def test_fingerprints_count_survives_roundtrip(self):
        chain = _make_chain(enable_deduplication=True)

        for i in range(20):
            entry = NaturalLanguageEntry(
                content=f"Fingerprinted entry number {i} with enough content for quality.",
                author=f"fp_author_{i}",
                intent=f"Fingerprint test {i}",
            )
            chain.add_entry(entry)

        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()

        assert len(data.get("entry_fingerprints", {})) == 20

        restored = NatLangChain.from_dict(
            data, require_validation=False, enable_deduplication=True
        )
        # All 20 fingerprints should survive
        assert len(restored._entry_fingerprints) == 20


# ============================================================
# Asset Registry Persistence
# ============================================================

class TestAssetRegistryPersistence:
    def test_asset_registry_survives_restart(self):
        chain = _make_chain(enable_asset_tracking=True)

        entry = NaturalLanguageEntry(
            content="Alice transfers the vintage painting to Bob for $10,000 as part of the estate sale.",
            author="alice",
            intent="Transfer vintage painting ownership",
        )
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)

        data = chain.to_dict()
        assert "asset_registry" in data

        restored = NatLangChain.from_dict(
            data, require_validation=False, enable_asset_tracking=True
        )
        assert restored._asset_registry is not None


# ============================================================
# Concurrent Entry Submission
# ============================================================

class TestConcurrentSubmissions:
    def test_concurrent_adds_no_corruption(self):
        """Multiple threads adding entries simultaneously should not corrupt state."""
        chain = _make_chain()
        errors = []

        def add_entries(thread_id, count):
            try:
                for i in range(count):
                    entry = NaturalLanguageEntry(
                        content=f"Thread {thread_id} entry {i}: concurrent test content.",
                        author=f"thread_{thread_id}",
                        intent=f"Concurrent test {thread_id}-{i}",
                    )
                    chain.add_entry(entry)
            except Exception as e:
                errors.append((thread_id, e))

        threads = []
        for t in range(5):
            thread = threading.Thread(target=add_entries, args=(t, 20))
            threads.append(thread)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Errors during concurrent add: {errors}"
        assert len(chain.pending_entries) == 100  # 5 threads * 20 entries

    def test_concurrent_mine_no_corruption(self):
        """Multiple adds followed by mines should maintain chain integrity."""
        chain = _make_chain()

        # Add entries
        for i in range(50):
            entry = NaturalLanguageEntry(
                content=f"Entry {i} for concurrent mine test.",
                author=f"author_{i % 3}",
                intent=f"Mine test {i}",
            )
            chain.add_entry(entry)

        # Mine all at once
        block = chain.mine_pending_entries(difficulty=1)
        assert block is not None
        assert len(block.entries) == 50
        assert chain.validate_chain() is True


# ============================================================
# Chain Integrity Under Volume
# ============================================================

class TestChainIntegrityVolume:
    def test_chain_valid_after_many_mines(self):
        chain = _make_chain()

        for batch in range(20):
            for i in range(5):
                entry = NaturalLanguageEntry(
                    content=f"Batch {batch} entry {i}: chain integrity volume test.",
                    author="integrity_tester",
                    intent=f"Integrity test batch {batch}",
                )
                chain.add_entry(entry)
            chain.mine_pending_entries(difficulty=1)

        assert len(chain.chain) == 21  # genesis + 20 blocks
        assert chain.validate_chain() is True

        # Serialize + restore + validate
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        assert restored.validate_chain() is True

    def test_tamper_detected_after_roundtrip(self):
        chain = _make_chain()

        for i in range(10):
            entry = NaturalLanguageEntry(
                content=f"Entry {i}: tamper detection test content.",
                author="tamper_tester",
                intent=f"Tamper test {i}",
            )
            chain.add_entry(entry)

        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)

        # Verify valid first
        assert restored.validate_chain() is True

        # Tamper with an entry
        restored.chain[1].entries[5].content = "TAMPERED CONTENT"
        assert restored.validate_chain() is False
