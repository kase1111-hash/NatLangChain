"""
Tests for NatLangChain Dispute Protocol (MP-03)
Tests dispute filing, evidence handling, escalation, and resolution
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from blockchain import NatLangChain, NaturalLanguageEntry
from dispute import DisputeManager


class TestDisputeManager(unittest.TestCase):
    """Test the DisputeManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.blockchain = NatLangChain()
        self.dispute_manager = DisputeManager()  # No LLM for basic tests

        # Add some entries to dispute
        entry1 = NaturalLanguageEntry(
            content="I offer web development services at $100/hour",
            author="alice",
            intent="Offer services",
            metadata={"is_contract": True, "contract_type": "offer"}
        )
        entry1.validation_status = "valid"
        self.blockchain.add_entry(entry1)
        self.blockchain.mine_pending_entries()

    def test_create_dispute(self):
        """Test creating a new dispute."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the service terms. The agreed rate was $80/hour, not $100/hour.",
            escalation_path=DisputeManager.ESCALATION_MEDIATOR
        )

        self.assertIn("dispute_id", dispute_data)
        self.assertTrue(dispute_data["dispute_id"].startswith("DISPUTE-"))
        self.assertEqual(dispute_data["claimant"], "bob")
        self.assertEqual(dispute_data["respondent"], "alice")
        self.assertEqual(dispute_data["status"], DisputeManager.STATUS_OPEN)
        self.assertTrue(dispute_data["evidence_frozen"])

    def test_dispute_id_uniqueness(self):
        """Test that dispute IDs are unique."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute1 = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="First dispute about terms"
        )

        dispute2 = self.dispute_manager.create_dispute(
            claimant="charlie",
            respondent="alice",
            contested_refs=contested_refs,
            description="Second dispute about terms"
        )

        self.assertNotEqual(dispute1["dispute_id"], dispute2["dispute_id"])

    def test_evidence_freezing(self):
        """Test that entries are frozen when dispute is filed."""
        contested_refs = [{"block": 1, "entry": 0}]

        self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute this contract entry."
        )

        is_frozen, dispute_id = self.dispute_manager.is_entry_frozen(1, 0)
        self.assertTrue(is_frozen)
        self.assertIsNotNone(dispute_id)

    def test_add_evidence(self):
        """Test adding evidence to a dispute."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the terms."
        )

        evidence_data = self.dispute_manager.add_evidence(
            dispute_id=dispute_data["dispute_id"],
            author="bob",
            evidence_content="Email chain showing agreed rate of $80/hour",
            evidence_type="document"
        )

        self.assertEqual(evidence_data["dispute_type"], DisputeManager.TYPE_EVIDENCE)
        self.assertEqual(evidence_data["dispute_id"], dispute_data["dispute_id"])
        self.assertIn("evidence_hash", evidence_data)

    def test_escalate_dispute(self):
        """Test escalating a dispute."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the terms."
        )

        escalation_data = self.dispute_manager.escalate_dispute(
            dispute_id=dispute_data["dispute_id"],
            escalating_party="bob",
            escalation_path=DisputeManager.ESCALATION_ARBITRATOR,
            escalation_reason="Mediation failed, need arbitration"
        )

        self.assertEqual(escalation_data["dispute_type"], DisputeManager.TYPE_ESCALATION)
        self.assertEqual(escalation_data["status"], DisputeManager.STATUS_ESCALATED)
        self.assertEqual(escalation_data["escalation_path"], DisputeManager.ESCALATION_ARBITRATOR)

    def test_resolve_dispute(self):
        """Test resolving a dispute."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the terms."
        )

        # Verify entry is frozen
        is_frozen, _ = self.dispute_manager.is_entry_frozen(1, 0)
        self.assertTrue(is_frozen)

        # Resolve the dispute
        resolution_data = self.dispute_manager.record_resolution(
            dispute_id=dispute_data["dispute_id"],
            resolution_authority="mediator_node_1",
            resolution_type="settled",
            resolution_content="Parties agreed to $90/hour rate as compromise.",
            findings={"agreed_rate": "$90/hour"},
            remedies=["Update contract to reflect $90/hour"]
        )

        self.assertEqual(resolution_data["dispute_type"], DisputeManager.TYPE_RESOLUTION)
        self.assertEqual(resolution_data["status"], DisputeManager.STATUS_RESOLVED)

        # Verify entry is unfrozen
        is_frozen, _ = self.dispute_manager.is_entry_frozen(1, 0)
        self.assertFalse(is_frozen)

    def test_request_clarification(self):
        """Test requesting clarification."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the terms."
        )

        clarification_data = self.dispute_manager.request_clarification(
            dispute_id=dispute_data["dispute_id"],
            author="mediator",
            clarification_request="Please provide the original email with rate discussion.",
            directed_to="bob"
        )

        self.assertEqual(clarification_data["dispute_type"], DisputeManager.TYPE_CLARIFICATION)
        self.assertEqual(clarification_data["status"], DisputeManager.STATUS_CLARIFYING)
        self.assertEqual(clarification_data["directed_to"], "bob")

    def test_generate_dispute_package(self):
        """Test generating a dispute package for external arbitration."""
        # Add entry to blockchain
        entry = NaturalLanguageEntry(
            content="Test service agreement",
            author="alice",
            intent="Agreement"
        )
        entry.validation_status = "valid"
        self.blockchain.add_entry(entry)
        self.blockchain.mine_pending_entries()

        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute this agreement."
        )

        # Add the dispute entry to blockchain
        dispute_entry = NaturalLanguageEntry(
            content="[DISPUTE: DISPUTE_DECLARATION] I dispute this agreement.",
            author="bob",
            intent="File dispute",
            metadata=dispute_data
        )
        self.blockchain.add_entry(dispute_entry)
        self.blockchain.mine_pending_entries()

        # Generate package
        package = self.dispute_manager.generate_dispute_package(
            dispute_id=dispute_data["dispute_id"],
            blockchain=self.blockchain,
            include_frozen_entries=True
        )

        self.assertIn("package_id", package)
        self.assertIn("integrity_hash", package)
        self.assertIn("chain_verification", package)
        self.assertTrue(package["chain_verification"]["chain_valid"])

    def test_get_dispute_status(self):
        """Test getting dispute status."""
        contested_refs = [{"block": 1, "entry": 0}]

        dispute_data = self.dispute_manager.create_dispute(
            claimant="bob",
            respondent="alice",
            contested_refs=contested_refs,
            description="I dispute the terms."
        )

        # Add the dispute entry to blockchain
        dispute_entry = NaturalLanguageEntry(
            content="[DISPUTE: DISPUTE_DECLARATION] I dispute the terms.",
            author="bob",
            intent="File dispute",
            metadata=dispute_data
        )
        self.blockchain.add_entry(dispute_entry)
        self.blockchain.mine_pending_entries()

        status = self.dispute_manager.get_dispute_status(
            dispute_data["dispute_id"],
            self.blockchain
        )

        self.assertIsNotNone(status)
        self.assertEqual(status["dispute_id"], dispute_data["dispute_id"])
        self.assertIn("declaration", status)
        self.assertFalse(status["is_resolved"])

    def test_validate_dispute_clarity(self):
        """Test dispute clarity validation."""
        # Too short
        is_valid, reason = self.dispute_manager.validate_dispute_clarity("Too short")
        self.assertFalse(is_valid)
        self.assertIn("brief", reason.lower())

        # No dispute language - must have at least one dispute keyword
        is_valid, reason = self.dispute_manager.validate_dispute_clarity(
            "This is a regular message without any specific language about problems."
        )
        # Without LLM, basic validation only checks for length and keywords
        # The message above is long enough but has no dispute keywords
        self.assertFalse(is_valid)

        # Valid dispute with clear dispute language
        is_valid, reason = self.dispute_manager.validate_dispute_clarity(
            "I contest and dispute the terms of the agreement. The issue is that the rate was misrepresented."
        )
        self.assertTrue(is_valid)

    def test_format_dispute_entry(self):
        """Test dispute entry formatting."""
        formatted = self.dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_DECLARATION,
            "I dispute this contract.",
            "DISPUTE-ABC123"
        )

        self.assertIn("[DISPUTE: DISPUTE_DECLARATION]", formatted)
        self.assertIn("[REF: DISPUTE-ABC123]", formatted)
        self.assertIn("I dispute this contract.", formatted)


class TestDisputeTypes(unittest.TestCase):
    """Test dispute type constants."""

    def test_dispute_types_defined(self):
        """Test that all dispute types are defined."""
        self.assertEqual(DisputeManager.TYPE_DECLARATION, "dispute_declaration")
        self.assertEqual(DisputeManager.TYPE_EVIDENCE, "dispute_evidence")
        self.assertEqual(DisputeManager.TYPE_ESCALATION, "dispute_escalation")
        self.assertEqual(DisputeManager.TYPE_RESOLUTION, "dispute_resolution")
        self.assertEqual(DisputeManager.TYPE_CLARIFICATION, "dispute_clarification")

    def test_status_types_defined(self):
        """Test that all status types are defined."""
        self.assertEqual(DisputeManager.STATUS_OPEN, "open")
        self.assertEqual(DisputeManager.STATUS_CLARIFYING, "clarifying")
        self.assertEqual(DisputeManager.STATUS_ESCALATED, "escalated")
        self.assertEqual(DisputeManager.STATUS_RESOLVED, "resolved")
        self.assertEqual(DisputeManager.STATUS_WITHDRAWN, "withdrawn")

    def test_escalation_paths_defined(self):
        """Test that all escalation paths are defined."""
        self.assertEqual(DisputeManager.ESCALATION_MEDIATOR, "mediator_node")
        self.assertEqual(DisputeManager.ESCALATION_ARBITRATOR, "external_arbitrator")
        self.assertEqual(DisputeManager.ESCALATION_COURT, "legal_court")


if __name__ == '__main__':
    unittest.main()
