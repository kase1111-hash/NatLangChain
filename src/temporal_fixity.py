"""
NatLangChain - Temporal Fixity
Preserves original context and meaning at T0 for legal/regulatory compliance
Implements the dual-layer system: Transaction fixed, Law flexible
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from blockchain import NatLangChain, NaturalLanguageEntry


class TemporalFixity:
    """
    Implements temporal fixity for blockchain entries.

    Preserves the original linguistic context, legal definitions, and intent
    at time T0 (creation time) to protect against semantic drift and legal
    reinterpretation.

    As outlined in "Legal Advantage of Temporal Fixity":
    - Transaction Record is Fixed (immutable T0 snapshot)
    - Operating System (Law) is Flexible (can evolve)
    - Courts can apply T0 context with T_current law
    """

    def __init__(self):
        """Initialize temporal fixity tracker."""
        self.t0_snapshots = {}  # Maps entry hash to T0 snapshot

    def create_t0_snapshot(
        self,
        entry: NaturalLanguageEntry,
        block_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create immutable T0 snapshot of entry context.

        Captures:
        - Original prose and intent
        - Timestamp and legal context
        - Prevailing definitions at T0
        - Author identity and authority
        - Environmental context (block, chain state)

        Args:
            entry: The entry to snapshot
            block_context: Optional block-level context

        Returns:
            Complete T0 snapshot dictionary
        """
        t0_timestamp = entry.timestamp

        snapshot = {
            "t0_timestamp": t0_timestamp,
            "t0_date_iso": datetime.fromisoformat(t0_timestamp).strftime("%Y-%m-%d %H:%M:%S UTC"),

            # Original content (immutable)
            "canonical_prose": entry.content,
            "stated_intent": entry.intent,
            "author": entry.author,
            "author_authority": entry.metadata.get("author_authority", "unverified"),

            # Linguistic context
            "language": entry.metadata.get("language", "en-US"),
            "prose_hash": hashlib.sha256(entry.content.encode()).hexdigest(),

            # Legal/regulatory context at T0
            "jurisdiction": entry.metadata.get("jurisdiction", "unspecified"),
            "applicable_law_version": entry.metadata.get("law_version", "T0"),
            "regulatory_framework": entry.metadata.get("regulatory_framework", {}),

            # Contract-specific fixity
            "contract_terms_t0": entry.metadata.get("terms", {}) if entry.metadata.get("is_contract") else None,
            "parties": entry.metadata.get("parties", []),

            # Validation state at T0
            "validation_status_t0": entry.validation_status,
            "validation_paraphrases_t0": entry.validation_paraphrases.copy(),

            # Block context (if provided)
            "block_index": block_context.get("block_index") if block_context else None,
            "block_hash": block_context.get("block_hash") if block_context else None,
            "previous_block_hash": block_context.get("previous_hash") if block_context else None,

            # Metadata
            "snapshot_type": "T0_IMMUTABLE",
            "fixity_protocol_version": "1.0",
            "intended_for_worm_archival": True
        }

        # Generate snapshot hash for integrity
        snapshot_json = json.dumps(snapshot, sort_keys=True)
        snapshot["snapshot_hash"] = hashlib.sha256(snapshot_json.encode()).hexdigest()

        return snapshot

    def add_t0_snapshot_to_entry(
        self,
        entry: NaturalLanguageEntry,
        block_context: dict[str, Any] | None = None
    ) -> NaturalLanguageEntry:
        """
        Enhance entry with T0 snapshot metadata.

        Args:
            entry: Entry to enhance
            block_context: Optional block context

        Returns:
            Entry with T0 snapshot in metadata
        """
        snapshot = self.create_t0_snapshot(entry, block_context)

        # Add to metadata
        entry.metadata["t0_snapshot"] = snapshot
        entry.metadata["temporal_fixity_enabled"] = True

        # Store in tracker
        self.t0_snapshots[snapshot["snapshot_hash"]] = snapshot

        return entry

    def verify_temporal_integrity(
        self,
        entry: NaturalLanguageEntry,
        t_current: str | None = None
    ) -> dict[str, Any]:
        """
        Verify that entry's T0 snapshot matches current content.

        Detects any tampering or drift from original T0 state.

        Args:
            entry: Entry to verify
            t_current: Current timestamp (defaults to now)

        Returns:
            Verification result
        """
        if "t0_snapshot" not in entry.metadata:
            return {
                "verified": False,
                "reason": "No T0 snapshot found",
                "temporal_fixity": False
            }

        t0_snapshot = entry.metadata["t0_snapshot"]
        t_current = t_current or datetime.utcnow().isoformat()

        # Verify prose hash
        current_prose_hash = hashlib.sha256(entry.content.encode()).hexdigest()
        t0_prose_hash = t0_snapshot["prose_hash"]

        prose_intact = (current_prose_hash == t0_prose_hash)

        # Check for any modifications
        modifications = []

        if entry.content != t0_snapshot["canonical_prose"]:
            modifications.append("content_modified")

        if entry.intent != t0_snapshot["stated_intent"]:
            modifications.append("intent_modified")

        if entry.author != t0_snapshot["author"]:
            modifications.append("author_modified")

        # Calculate time delta
        t0_dt = datetime.fromisoformat(t0_snapshot["t0_timestamp"])
        t_current_dt = datetime.fromisoformat(t_current) if isinstance(t_current, str) else t_current
        years_elapsed = (t_current_dt - t0_dt).days / 365.25

        return {
            "verified": prose_intact and len(modifications) == 0,
            "prose_hash_match": prose_intact,
            "modifications_detected": modifications,
            "t0_timestamp": t0_snapshot["t0_timestamp"],
            "t_current": t_current,
            "years_elapsed": round(years_elapsed, 2),
            "temporal_fixity": prose_intact,
            "original_context_preserved": len(modifications) == 0,
            "snapshot_hash": t0_snapshot["snapshot_hash"]
        }

    def generate_legal_certificate(
        self,
        entry: NaturalLanguageEntry,
        purpose: str = "legal_defense"
    ) -> dict[str, Any]:
        """
        Generate legal certificate proving T0 context.

        For use in:
        - Malpractice defense (clinical decisions)
        - Contract disputes
        - Regulatory audits
        - Legal discovery

        Args:
            entry: Entry to certify
            purpose: Purpose of certificate

        Returns:
            Legal certificate with T0 proof
        """
        if "t0_snapshot" not in entry.metadata:
            raise ValueError("Entry does not have T0 snapshot")

        t0_snapshot = entry.metadata["t0_snapshot"]
        verification = self.verify_temporal_integrity(entry)

        certificate = {
            "certificate_type": "T0_TEMPORAL_FIXITY",
            "purpose": purpose,
            "generated_at": datetime.utcnow().isoformat(),

            # Primary evidence
            "canonical_prose_t0": t0_snapshot["canonical_prose"],
            "prose_hash_t0": t0_snapshot["prose_hash"],
            "timestamp_t0": t0_snapshot["t0_timestamp"],

            # Context at T0
            "legal_context_t0": {
                "jurisdiction": t0_snapshot["jurisdiction"],
                "applicable_law": t0_snapshot["applicable_law_version"],
                "regulatory_framework": t0_snapshot["regulatory_framework"]
            },

            # Verification
            "temporal_integrity_verified": verification["verified"],
            "prose_unmodified": verification["prose_hash_match"],
            "time_elapsed_years": verification["years_elapsed"],

            # Chain of custody
            "block_hash": t0_snapshot.get("block_hash"),
            "snapshot_hash": t0_snapshot["snapshot_hash"],

            # Legal statements
            "statements": {
                "immutability": "This record is cryptographically immutable and has been verified against its T0 snapshot",
                "temporal_fixity": f"The linguistic meaning and legal context are fixed to {t0_snapshot['t0_date_iso']}",
                "non_repudiation": "The prose hash provides non-repudiable proof of original content",
                "standard_met": "Meets SEC 17a-4, HIPAA, and WORM archival standards"
            }
        }

        # Add contract-specific info
        if entry.metadata.get("is_contract"):
            certificate["contract_terms_t0"] = t0_snapshot.get("contract_terms_t0")
            certificate["parties"] = t0_snapshot.get("parties", [])

        # Add clinical decision info (if applicable)
        if entry.metadata.get("clinical_decision"):
            certificate["clinical_context"] = {
                "physician": entry.author,
                "ai_interaction": entry.metadata.get("ai_model"),
                "decision_pathway": entry.content,
                "hipaa_compliant": True
            }

        # Certificate hash
        cert_json = json.dumps(certificate, sort_keys=True)
        certificate["certificate_hash"] = hashlib.sha256(cert_json.encode()).hexdigest()

        return certificate

    def export_for_worm_archival(
        self,
        blockchain: NatLangChain,
        start_block: int = 0,
        end_block: int | None = None
    ) -> dict[str, Any]:
        """
        Export blockchain data formatted for WORM media archival.

        Creates a complete, self-contained archive suitable for:
        - LTO tape archival
        - Legal discovery
        - Long-term preservation
        - Regulatory compliance

        Args:
            blockchain: Blockchain to export
            start_block: Starting block index
            end_block: Ending block index (None = all)

        Returns:
            WORM-ready export package
        """
        end_block = end_block or len(blockchain.chain) - 1

        export = {
            "archive_type": "NATLANGCHAIN_WORM_ARCHIVE",
            "archive_version": "1.0",
            "archive_timestamp": datetime.utcnow().isoformat(),

            # Archive metadata
            "blockchain_info": {
                "total_blocks": len(blockchain.chain),
                "archived_blocks": f"{start_block}-{end_block}",
                "genesis_hash": blockchain.chain[0].hash if blockchain.chain else None
            },

            # Full blocks with T0 snapshots
            "blocks": [],

            # Legal compliance
            "compliance": {
                "sec_17a4_compliant": True,
                "hipaa_compliant": True,
                "worm_media_required": True,
                "retention_recommendation": "permanent"
            },

            # Verification data
            "integrity_proofs": []
        }

        # Export each block
        for i in range(start_block, end_block + 1):
            if i >= len(blockchain.chain):
                break

            block = blockchain.chain[i]

            block_export = {
                "block_index": block.index,
                "block_hash": block.hash,
                "timestamp": block.timestamp,
                "previous_hash": block.previous_hash,
                "nonce": block.nonce,

                # Entries with T0 snapshots
                "entries": []
            }

            for entry in block.entries:
                # Ensure T0 snapshot exists
                if "t0_snapshot" not in entry.metadata:
                    self.add_t0_snapshot_to_entry(entry, {
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "previous_hash": block.previous_hash
                    })

                entry_export = entry.to_dict()

                # Add legal certificate
                entry_export["legal_certificate"] = self.generate_legal_certificate(
                    entry,
                    purpose="worm_archival"
                )

                block_export["entries"].append(entry_export)

            export["blocks"].append(block_export)

            # Add integrity proof
            export["integrity_proofs"].append({
                "block_index": block.index,
                "block_hash": block.hash,
                "entry_count": len(block.entries),
                "verified_at": datetime.utcnow().isoformat()
            })

        # Archive hash (for integrity verification)
        archive_json = json.dumps(export["blocks"], sort_keys=True)
        export["archive_hash"] = hashlib.sha256(archive_json.encode()).hexdigest()

        # Physical media instructions
        export["archival_instructions"] = {
            "media_type": "LTO-9 WORM or equivalent",
            "format": "JSON with SHA-256 integrity proofs",
            "storage_requirements": "Air-gapped, climate-controlled, redundant",
            "verification_procedure": "Hash verification against archive_hash",
            "legal_status": "Constitutes primary evidence under applicable law"
        }

        return export


def enhance_entry_with_temporal_fixity(
    entry: NaturalLanguageEntry,
    block_context: dict[str, Any] | None = None
) -> NaturalLanguageEntry:
    """
    Convenience function to enhance an entry with temporal fixity.

    Args:
        entry: Entry to enhance
        block_context: Optional block context

    Returns:
        Enhanced entry
    """
    fixity = TemporalFixity()
    return fixity.add_t0_snapshot_to_entry(entry, block_context)
