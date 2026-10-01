"""Regressions for defects surfaced by the year-long operational simulation.

Each test here corresponds to a failure observed in
``simulations/year_simulation.py`` running the engine for 365 simulated days.
The unit suite missed all of them because each needs either accumulated state,
elapsed time, concurrency, or a seam between two modules.

See ``simulations/results/YEAR_REPORT.md`` for the run these came from.
"""

import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from blockchain import (
    Block,
    MockValidator,
    NatLangChain,
    NaturalLanguageEntry,
)
from storage.json_file import JSONFileStorage

TRANSFER_CONTENT = (
    "tallgrass_textiles transferred title in equipment {asset} to "
    "silverpine_packaging under a bill of sale countersigned at the quarterly "
    "review, shipping from the Riverbend hub."
)


def _chain(**overrides):
    settings = {
        "require_validation": True,
        "validator": MockValidator(),
        "enable_deduplication": True,
        "enable_rate_limiting": False,
        "enable_timestamp_validation": False,
        "enable_metadata_sanitization": True,
        "enable_asset_tracking": True,
        "enable_quality_checks": True,
        "enable_derivative_tracking": True,
    }
    settings.update(overrides)
    return NatLangChain(**settings)


class TestDuplicateOfPendingEntry:
    """Resubmitting a still-pending entry after the dedup window expires."""

    def test_duplicate_of_pending_entry_is_rejected_not_crashed(self):
        # A one-second dedup window stands in for "the window expired while the
        # entry was still waiting to be mined" — the normal state on a node that
        # mines less often than the window.
        chain = _chain(dedup_window_seconds=1)
        entry_kwargs = {
            "content": (
                "granite_tooling agreed to supply 640 precision bearings to "
                "lumen_medical under purchase order PO-1. Delivery is due at the "
                "Ashford yard with payment on receipt."
            ),
            "author": "granite_tooling",
            "intent": "Supply agreement signed for purchase order PO-1",
        }
        assert chain.add_entry(NaturalLanguageEntry(**entry_kwargs))["status"] == "pending"
        time.sleep(1.1)  # let the fingerprint expire while the entry is still pending

        result = chain.add_entry(NaturalLanguageEntry(**entry_kwargs))

        assert result["status"] == "rejected"
        assert result["reason"] == "duplicate"
        assert result["duplicate_source"] == "pending_queue"
        # No original timestamp exists for an unmined entry; the field must be
        # present and empty rather than raising KeyError.
        assert result["original_timestamp"] is None
        assert len(chain.pending_entries) == 1

    def test_duplicate_of_mined_entry_still_reports_block_timestamp(self):
        chain = _chain(dedup_window_seconds=1)
        entry_kwargs = {
            "content": (
                "harbor_plastics agreed to supply 1200 injection-molded housings "
                "to atlas_transit under purchase order PO-2, due at the Portland "
                "depot with payment on receipt."
            ),
            "author": "harbor_plastics",
            "intent": "Supply agreement signed for purchase order PO-2",
        }
        chain.add_entry(NaturalLanguageEntry(**entry_kwargs))
        chain.mine_pending_entries(difficulty=1)
        time.sleep(1.1)

        result = chain.add_entry(NaturalLanguageEntry(**entry_kwargs))

        assert result["status"] == "rejected"
        assert result["duplicate_source"] == "mined_block"
        assert result["original_timestamp"] is not None


class TestAssetReservationRelease:
    """A transfer rejected after its reservation must release the asset."""

    def test_rejected_transfer_releases_reservation(self):
        chain = _chain()
        asset_id = "EQ-LOCK-1"
        chain._asset_registry.register_asset(asset_id, "tallgrass_textiles")

        # "irrevocable" is on MockValidator's adversarial list, so the asset check
        # passes and reserves the asset, then validation rejects the entry.
        rejected = chain.add_entry(
            NaturalLanguageEntry(
                content=(
                    f"tallgrass_textiles transferred title in equipment {asset_id} to "
                    f"silverpine_packaging against an irrevocable letter of credit "
                    f"issued by the buyer's bank this week."
                ),
                author="tallgrass_textiles",
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "silverpine_packaging"},
            )
        )
        assert rejected["status"] == "rejected"
        assert not chain._asset_registry.has_pending_transfer(asset_id)

        retry = chain.add_entry(
            NaturalLanguageEntry(
                content=TRANSFER_CONTENT.format(asset=asset_id),
                author="tallgrass_textiles",
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "silverpine_packaging"},
            )
        )
        assert retry["status"] == "pending"

        chain.mine_pending_entries(difficulty=1)
        assert chain._asset_registry.get_owner(asset_id) == "silverpine_packaging"

    def test_accepted_transfer_keeps_its_reservation(self):
        chain = _chain()
        asset_id = "EQ-LOCK-2"
        chain._asset_registry.register_asset(asset_id, "tallgrass_textiles")

        result = chain.add_entry(
            NaturalLanguageEntry(
                content=TRANSFER_CONTENT.format(asset=asset_id),
                author="tallgrass_textiles",
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "silverpine_packaging"},
            )
        )
        assert result["status"] == "pending"
        # The reservation must survive until the block is mined, or a second
        # transfer of the same asset could slip into the same queue.
        assert chain._asset_registry.has_pending_transfer(asset_id)


class TestMiningDoesNotDropConcurrentSubmissions:
    """Entries accepted during proof-of-work must not be discarded."""

    def test_entries_submitted_during_mining_survive(self, monkeypatch):
        chain = _chain(
            require_validation=False,
            enable_deduplication=False,
            enable_quality_checks=False,
            enable_asset_tracking=False,
            enable_derivative_tracking=False,
        )

        def entry(tag, i):
            return NaturalLanguageEntry(
                content=(
                    f"pelican_logistics recorded shipment leg {tag}-{i} moving "
                    f"freight between the Portland depot and the Calloway pier."
                ),
                author="pelican_logistics",
                intent=f"Shipment leg {tag}-{i} recorded",
            )

        preloaded = 120
        for i in range(preloaded):
            chain.add_entry(entry("pre", i))

        # Hold proof-of-work open deterministically: the miner blocks on its
        # first block hash (computed after the queue swap) until the test has
        # submitted its concurrent entries. The previous version relied on a
        # difficulty-4 search for the window, which took under a second on a
        # fast machine and over a minute under coverage tracing in CI.
        original_hash = Block.calculate_hash
        mining_started = threading.Event()
        release = threading.Event()

        def gated_hash(self):
            mining_started.set()
            release.wait(timeout=30)
            return original_hash(self)

        monkeypatch.setattr(Block, "calculate_hash", gated_hash)

        thread = threading.Thread(target=chain.mine_pending_entries, kwargs={"difficulty": 1})
        thread.start()
        assert mining_started.wait(timeout=10), "miner never started hashing"

        submitted_during = 0
        for i in range(30):
            if chain.add_entry(entry("during", i))["status"] == "pending":
                submitted_during += 1

        release.set()
        thread.join(timeout=30)
        assert not thread.is_alive(), "mining did not finish after release"

        on_chain = sum(len(b.entries) for b in chain.chain) - 1  # exclude genesis
        assert on_chain == preloaded, "the mined block must hold exactly the swapped-out queue"
        assert submitted_during == 30, "submissions during proof-of-work must be accepted"
        assert len(chain.pending_entries) == submitted_during, (
            "entries accepted during proof-of-work must stay queued for the next block"
        )
        assert chain.validate_chain(verify_pow=True, difficulty=1)

    def test_mining_is_idempotent_on_empty_queue(self):
        chain = _chain(require_validation=False)
        assert chain.mine_pending_entries(difficulty=1) is None
        assert len(chain.chain) == 1


class TestEncryptedStorageRoundTrip:
    """Encryption at rest has to be readable, not just writable."""

    @pytest.fixture
    def encryption_key(self, monkeypatch):
        monkeypatch.setenv("NATLANGCHAIN_ENCRYPTION_KEY", "test-key-0123456789abcdef")

    @pytest.mark.parametrize("compression", [True, False])
    def test_encrypted_chain_can_be_reloaded(self, tmp_path, encryption_key, compression):
        chain = _chain(require_validation=False)
        chain.add_entry(
            NaturalLanguageEntry(
                content=(
                    "northwind_foundry agreed to supply 4000 machined brackets to "
                    "halcyon_robotics under purchase order PO-9, due at the Portland "
                    "depot with payment on receipt."
                ),
                author="northwind_foundry",
                intent="Supply agreement signed for purchase order PO-9",
            )
        )
        chain.mine_pending_entries(difficulty=1)

        path = tmp_path / f"chain_{compression}.json"
        storage = JSONFileStorage(
            file_path=str(path),
            encryption_enabled=True,
            compression_enabled=compression,
        )
        assert storage.encryption_enabled

        exported = chain.to_dict()
        storage.save_chain(exported)

        on_disk = path.read_bytes()
        assert on_disk.startswith(b"ENC:"), "chain must be written as ciphertext"
        assert b"northwind_foundry" not in on_disk, "no plaintext may reach disk"

        loaded = storage.load_chain()
        assert loaded == exported

        restored = NatLangChain.from_dict(loaded, require_validation=False)
        assert restored.validate_chain(verify_pow=True, difficulty=1)
        assert restored.get_latest_block().hash == chain.get_latest_block().hash


class TestActionMismatchTokenization:
    """High-impact verbs must be caught wherever they sit in a sentence."""

    @pytest.mark.parametrize(
        "content",
        [
            "verdant_agritech banned the supplier from the vendor portal today.",
            "verdant_agritech reviewed the account and the supplier was banned.",
            "verdant_agritech reviewed the account; the supplier was banned!",
            "The vendor portal account was reviewed and the supplier was suspended.",
        ],
    )
    def test_restriction_under_profile_intent_is_rejected(self, content):
        result = MockValidator().validate_entry(
            content=content,
            intent="Update supplier profile record",
            author="verdant_agritech",
        )
        assert result["validation"]["decision"] == "INVALID"

    def test_matching_intent_still_accepted(self):
        result = MockValidator().validate_entry(
            content="verdant_agritech banned the supplier from the vendor portal today.",
            intent="Suspend supplier portal access after review",
            author="verdant_agritech",
        )
        assert result["validation"]["decision"] == "VALID"

    def test_tokenizer_does_not_match_substrings(self):
        # "unbanned" and "reopened" must not register as restriction/creation
        # actions just because they contain "ban"/"open".
        result = MockValidator().validate_entry(
            content="verdant_agritech unbanned the supplier and reopened the account.",
            intent="Update supplier profile record",
            author="verdant_agritech",
        )
        assert result["validation"]["decision"] == "VALID"
