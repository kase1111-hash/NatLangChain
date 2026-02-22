"""
Tests for NatLangChain blockchain functionality.

Covers:
- Genesis block creation
- Entry creation and pipeline rejections
- Block mining (including edge cases)
- Chain validation and integrity
- Serialization/deserialization roundtrips
- Asset registry persistence
- Entry fingerprint persistence
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchain import (
    AssetRegistry,
    Block,
    NatLangChain,
    NaturalLanguageEntry,
    compute_entry_fingerprint,
)


# ============================================================
# Helpers
# ============================================================

def _make_chain(**overrides):
    """Create a blockchain with all validation disabled (safe for unit tests)."""
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


def _make_entry(content="Test entry.", author="alice", intent="Test"):
    return NaturalLanguageEntry(content=content, author=author, intent=intent)


# ============================================================
# Genesis Block
# ============================================================

class TestGenesisBlock:
    def test_genesis_created_on_init(self):
        chain = _make_chain()
        assert len(chain.chain) == 1

    def test_genesis_index_is_zero(self):
        chain = _make_chain()
        assert chain.chain[0].index == 0

    def test_genesis_previous_hash_is_zero(self):
        chain = _make_chain()
        assert chain.chain[0].previous_hash == "0"

    def test_genesis_has_hash(self):
        chain = _make_chain()
        assert chain.chain[0].hash
        assert len(chain.chain[0].hash) == 64  # SHA-256 hex


# ============================================================
# Entry Addition — Happy Path
# ============================================================

class TestAddEntry:
    def test_entry_goes_to_pending(self):
        chain = _make_chain()
        result = chain.add_entry(_make_entry())
        assert result["status"] == "pending"
        assert len(chain.pending_entries) == 1

    def test_entry_preserves_fields(self):
        chain = _make_chain()
        entry = _make_entry(content="Unique content", author="bob", intent="Record")
        chain.add_entry(entry)
        pending = chain.pending_entries[0]
        assert pending.content == "Unique content"
        assert pending.author == "bob"
        assert pending.intent == "Record"

    def test_multiple_entries_queue(self):
        chain = _make_chain()
        for i in range(5):
            chain.add_entry(_make_entry(content=f"Entry {i}"))
        assert len(chain.pending_entries) == 5


# ============================================================
# Pipeline Rejections
# ============================================================

class TestRateLimitRejection:
    def test_author_rate_limit(self):
        chain = _make_chain(enable_rate_limiting=True, max_entries_per_author=2)
        chain.add_entry(_make_entry(content="First", author="alice"))
        chain.add_entry(_make_entry(content="Second", author="alice"))
        result = chain.add_entry(_make_entry(content="Third", author="alice"))
        assert result["status"] == "rejected"
        assert result["reason"] == "rate_limit"

    def test_other_author_unaffected(self):
        chain = _make_chain(enable_rate_limiting=True, max_entries_per_author=1)
        chain.add_entry(_make_entry(content="Alice entry", author="alice"))
        result = chain.add_entry(_make_entry(content="Bob entry", author="bob"))
        assert result["status"] == "pending"


class TestTimestampRejection:
    def test_far_future_entry_rejected(self):
        chain = _make_chain(enable_timestamp_validation=True)
        entry = _make_entry()
        # Force timestamp 10 minutes into the future
        entry.timestamp = time.time() + 600
        result = chain.add_entry(entry)
        assert result["status"] == "rejected"
        assert result["reason"] == "invalid_timestamp"

    def test_normal_timestamp_accepted(self):
        chain = _make_chain(enable_timestamp_validation=True)
        result = chain.add_entry(_make_entry())
        assert result["status"] == "pending"


class TestMetadataRejection:
    def test_forbidden_field_in_reject_mode(self):
        chain = _make_chain(
            enable_metadata_sanitization=True,
            metadata_sanitize_mode="reject",
        )
        entry = NaturalLanguageEntry(
            content="Test entry",
            author="alice",
            intent="Test",
            metadata={"validation_status": "hacked"},
        )
        result = chain.add_entry(entry)
        assert result["status"] == "rejected"
        assert result["reason"] == "forbidden_metadata"

    def test_clean_metadata_accepted(self):
        chain = _make_chain(enable_metadata_sanitization=True)
        entry = NaturalLanguageEntry(
            content="Test entry",
            author="alice",
            intent="Test",
            metadata={"note": "completely fine"},
        )
        result = chain.add_entry(entry)
        assert result["status"] == "pending"


class TestDuplicateRejection:
    def test_exact_duplicate_rejected(self):
        chain = _make_chain(enable_deduplication=True)
        entry1 = _make_entry(content="Same content", author="alice", intent="Same intent")
        entry2 = _make_entry(content="Same content", author="alice", intent="Same intent")
        chain.add_entry(entry1)
        result = chain.add_entry(entry2)
        assert result["status"] == "rejected"
        assert result["reason"] == "duplicate"

    def test_different_content_not_duplicate(self):
        chain = _make_chain(enable_deduplication=True)
        chain.add_entry(_make_entry(content="First content"))
        result = chain.add_entry(_make_entry(content="Different content"))
        assert result["status"] == "pending"

    def test_duplicate_in_mined_block(self):
        chain = _make_chain(enable_deduplication=True)
        entry = _make_entry(content="Mined entry", author="alice", intent="Test")
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)
        # Try to re-add the exact same entry
        duplicate = _make_entry(content="Mined entry", author="alice", intent="Test")
        result = chain.add_entry(duplicate)
        assert result["status"] == "rejected"
        assert result["reason"] == "duplicate"


# ============================================================
# Mining
# ============================================================

class TestMining:
    def test_mine_creates_new_block(self):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        block = chain.mine_pending_entries(difficulty=1)
        assert block is not None
        assert len(chain.chain) == 2

    def test_mine_clears_pending(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Entry 1"))
        chain.add_entry(_make_entry(content="Entry 2"))
        chain.mine_pending_entries(difficulty=1)
        assert len(chain.pending_entries) == 0

    def test_mine_empty_returns_none(self):
        chain = _make_chain()
        result = chain.mine_pending_entries(difficulty=1)
        assert result is None
        assert len(chain.chain) == 1  # Only genesis

    def test_mine_preserves_entries_in_block(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Entry A"))
        chain.add_entry(_make_entry(content="Entry B"))
        block = chain.mine_pending_entries(difficulty=1)
        assert len(block.entries) == 2
        contents = {e.content for e in block.entries}
        assert "Entry A" in contents
        assert "Entry B" in contents

    def test_mine_difficulty_affects_hash(self):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        block = chain.mine_pending_entries(difficulty=2)
        assert block.hash.startswith("00")

    def test_multiple_mines(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Batch 1"))
        chain.mine_pending_entries(difficulty=1)
        chain.add_entry(_make_entry(content="Batch 2"))
        chain.mine_pending_entries(difficulty=1)
        assert len(chain.chain) == 3  # Genesis + 2 mined


# ============================================================
# Chain Validation
# ============================================================

class TestChainValidation:
    def test_fresh_chain_valid(self):
        chain = _make_chain()
        assert chain.validate_chain() is True

    def test_chain_with_blocks_valid(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Entry 1"))
        chain.mine_pending_entries(difficulty=1)
        chain.add_entry(_make_entry(content="Entry 2"))
        chain.mine_pending_entries(difficulty=1)
        assert chain.validate_chain() is True

    def test_tampered_block_detected(self):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        chain.mine_pending_entries(difficulty=1)
        # Tamper with block data
        chain.chain[1].entries[0].content = "TAMPERED CONTENT"
        assert chain.validate_chain() is False


# ============================================================
# Queries
# ============================================================

class TestQueries:
    def test_get_entries_by_author(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Alice entry 1", author="alice"))
        chain.add_entry(_make_entry(content="Bob entry", author="bob"))
        chain.add_entry(_make_entry(content="Alice entry 2", author="alice"))
        chain.mine_pending_entries(difficulty=1)

        alice_entries = chain.get_entries_by_author("alice")
        assert len(alice_entries) == 2

    def test_get_entries_unknown_author(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(author="alice"))
        chain.mine_pending_entries(difficulty=1)
        assert chain.get_entries_by_author("unknown") == []

    def test_narrative_generation(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Narrative test entry.", author="narrator", intent="Narrate"))
        chain.mine_pending_entries(difficulty=1)
        narrative = chain.get_full_narrative()
        assert "NatLangChain Narrative History" in narrative
        assert "narrator" in narrative


# ============================================================
# Serialization / Deserialization
# ============================================================

class TestSerialization:
    def test_roundtrip_chain_length(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Entry 1"))
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        assert len(restored.chain) == len(chain.chain)

    def test_roundtrip_block_hashes(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Hash test"))
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        for orig, rest in zip(chain.chain, restored.chain):
            assert orig.hash == rest.hash

    def test_roundtrip_entry_content(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Specific content to verify", author="bob"))
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        mined_entries = restored.chain[1].entries
        assert mined_entries[0].content == "Specific content to verify"
        assert mined_entries[0].author == "bob"

    def test_roundtrip_pending_entries(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Unmined entry"))
        data = chain.to_dict()
        assert len(data["pending_entries"]) == 1
        restored = NatLangChain.from_dict(data, require_validation=False)
        assert len(restored.pending_entries) == 1
        assert restored.pending_entries[0].content == "Unmined entry"

    def test_roundtrip_preserves_chain_validity(self):
        chain = _make_chain()
        chain.add_entry(_make_entry(content="Validity roundtrip"))
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        restored = NatLangChain.from_dict(data, require_validation=False)
        assert restored.validate_chain() is True

    def test_from_dict_with_missing_pending(self):
        """from_dict should handle missing pending_entries gracefully."""
        chain = _make_chain()
        data = chain.to_dict()
        del data["pending_entries"]
        restored = NatLangChain.from_dict(data, require_validation=False)
        assert len(restored.pending_entries) == 0

    def test_from_dict_with_corrupted_block_entries(self):
        """from_dict should raise on corrupted block data."""
        data = {
            "chain": [{"this_is": "not a valid block"}],
        }
        with pytest.raises((KeyError, TypeError, ValueError)):
            NatLangChain.from_dict(data, require_validation=False)


# ============================================================
# Entry Fingerprint Persistence
# ============================================================

class TestFingerprintPersistence:
    def test_fingerprints_in_to_dict(self):
        chain = _make_chain(enable_deduplication=True)
        chain.add_entry(_make_entry(content="Fingerprint test", author="alice", intent="Test"))
        data = chain.to_dict()
        assert "entry_fingerprints" in data
        assert len(data["entry_fingerprints"]) == 1

    def test_fingerprints_restored_from_dict(self):
        chain = _make_chain(enable_deduplication=True)
        entry = _make_entry(
            content="This is a sufficiently long entry for dedup persistence testing purposes.",
            author="alice",
            intent="Test deduplication persistence",
        )
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()

        restored = NatLangChain.from_dict(
            data,
            require_validation=False,
            enable_deduplication=True,
        )
        # Disable quality checks on restored chain for testing
        restored._quality_analyzer = None
        # The restored chain should reject a duplicate
        duplicate = _make_entry(
            content="This is a sufficiently long entry for dedup persistence testing purposes.",
            author="alice",
            intent="Test deduplication persistence",
        )
        result = restored.add_entry(duplicate)
        assert result["status"] == "rejected"
        assert result["reason"] == "duplicate"


# ============================================================
# Asset Registry Persistence
# ============================================================

class TestAssetRegistryPersistence:
    def test_asset_registry_in_to_dict(self):
        chain = _make_chain(enable_asset_tracking=True)
        # Add a transfer entry
        entry = NaturalLanguageEntry(
            content="Alice transfers the vintage painting to Bob for $10,000.",
            author="alice",
            intent="Transfer art ownership",
        )
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()
        # asset_registry should appear if asset tracking is enabled
        assert "asset_registry" in data

    def test_asset_registry_roundtrip(self):
        chain = _make_chain(enable_asset_tracking=True)
        entry = NaturalLanguageEntry(
            content="Alice sells the house to Bob for $100,000.",
            author="alice",
            intent="Transfer property",
        )
        chain.add_entry(entry)
        chain.mine_pending_entries(difficulty=1)
        data = chain.to_dict()

        restored = NatLangChain.from_dict(
            data,
            require_validation=False,
            enable_asset_tracking=True,
        )
        # Restored chain should have asset registry
        assert restored._asset_registry is not None

    def test_asset_registry_standalone_roundtrip(self):
        """AssetRegistry.to_dict / from_dict work correctly."""
        registry = AssetRegistry()
        registry_data = registry.to_dict()
        restored = AssetRegistry.from_dict(registry_data)
        assert restored is not None


# ============================================================
# Block Structure
# ============================================================

class TestBlockStructure:
    def test_block_has_expected_fields(self):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        block = chain.mine_pending_entries(difficulty=1)
        block_dict = block.to_dict()
        assert "index" in block_dict
        assert "hash" in block_dict
        assert "previous_hash" in block_dict
        assert "entries" in block_dict
        assert "timestamp" in block_dict

    def test_block_links_to_previous(self):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        chain.mine_pending_entries(difficulty=1)
        assert chain.chain[1].previous_hash == chain.chain[0].hash


# ============================================================
# Entry Fingerprint Function
# ============================================================

class TestComputeFingerprint:
    def test_same_inputs_same_fingerprint(self):
        fp1 = compute_entry_fingerprint("content", "author", "intent")
        fp2 = compute_entry_fingerprint("content", "author", "intent")
        assert fp1 == fp2

    def test_different_inputs_different_fingerprint(self):
        fp1 = compute_entry_fingerprint("content A", "author", "intent")
        fp2 = compute_entry_fingerprint("content B", "author", "intent")
        assert fp1 != fp2

    def test_fingerprint_is_hex_string(self):
        fp = compute_entry_fingerprint("test", "author", "intent")
        assert isinstance(fp, str)
        int(fp, 16)  # Should not raise — valid hex


# ============================================================
# Parametrized Boundary Tests
# ============================================================

class TestEntryBoundaryConditions:
    @pytest.mark.parametrize("content", [
        "a",
        "x" * 10_000,
        "Hello\nWorld\n",
        "Unicode: \u00e9\u00e8\u00ea \u2603 \u2764\ufe0f",
        "   leading/trailing whitespace   ",
    ])
    def test_add_entry_various_content(self, content):
        chain = _make_chain()
        result = chain.add_entry(_make_entry(content=content))
        assert result["status"] == "pending"
        assert chain.pending_entries[0].content == content

    @pytest.mark.parametrize("author", [
        "a",
        "alice",
        "user-with-dashes",
        "user_with_underscores",
        "CamelCaseUser",
    ])
    def test_add_entry_various_authors(self, author):
        chain = _make_chain()
        result = chain.add_entry(_make_entry(author=author))
        assert result["status"] == "pending"
        assert chain.pending_entries[0].author == author

    @pytest.mark.parametrize("count", [1, 2, 10])
    def test_mine_with_varying_entry_counts(self, count):
        chain = _make_chain()
        for i in range(count):
            chain.add_entry(_make_entry(content=f"Entry {i}"))
        block = chain.mine_pending_entries(difficulty=1)
        assert block is not None
        assert len(block.entries) == count
        assert len(chain.pending_entries) == 0

    @pytest.mark.parametrize("difficulty", [1, 2, 3])
    def test_mine_with_varying_difficulty(self, difficulty):
        chain = _make_chain()
        chain.add_entry(_make_entry())
        block = chain.mine_pending_entries(difficulty=difficulty)
        assert block.hash.startswith("0" * difficulty)
