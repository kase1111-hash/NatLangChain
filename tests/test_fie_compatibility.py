"""
Tests for NatLangChain ↔ Finite-Intent-Executor (FIE) Compatibility
Tests delayed intent recording, trigger handling, execution recording, and revocation
Per integration spec: FINITE-INTENT-EXECUTOR-INTEGRATION.md
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from datetime import datetime

from blockchain import NatLangChain, NaturalLanguageEntry


class TestFIEDelayedIntentRecording(unittest.TestCase):
    """Test recording delayed/posthumous intents for FIE consumption."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

    def test_posthumous_intent_recording(self):
        """Test recording a posthumous IP transfer intent."""
        entry = NaturalLanguageEntry(
            content="Posthumous IP Transfer: Upon my passing, I direct that all intellectual "
                    "property rights to my repositories at github.com/alice/* be transferred "
                    "to the Open Source Foundation. This includes all code, documentation, "
                    "and associated assets. The Foundation shall maintain these as open "
                    "source under MIT license.",
            author="alice",
            intent="Posthumous IP transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "trigger": {
                    "type": "death",
                    "verification_method": "death_certificate_oracle",
                    "verification_sources": [
                        "social_security_death_index",
                        "legal_executor_declaration"
                    ],
                    "minimum_confirmations": 2
                },
                "executor": {
                    "primary": "finite_intent_executor_mainnet",
                    "backup": "finite_intent_executor_backup",
                    "legal_executor": "law_firm_xyz"
                },
                "beneficiary": {
                    "name": "Open Source Foundation",
                    "identifier": "osf_org",
                    "wallet": "0xOSF123..."
                },
                "actions": [
                    {
                        "action_type": "ip_transfer",
                        "subject": "github.com/alice/*",
                        "to": "osf_org",
                        "license": "MIT"
                    },
                    {
                        "action_type": "notification",
                        "notify": ["family@example.com", "osf_legal@example.com"]
                    }
                ],
                "revocation": {
                    "revocable": True,
                    "revocation_method": "author_signature",
                    "last_updated": datetime.utcnow().isoformat()
                },
                "witnesses": [
                    {
                        "witness": "bob",
                        "timestamp": datetime.utcnow().isoformat(),
                        "signature": "0xWITNESS_SIG..."
                    }
                ]
            }
        )
        entry.validation_status = "valid"

        result = self.blockchain.add_entry(entry)
        self.assertEqual(result["status"], "pending")

        # Mine the block
        block = self.blockchain.mine_pending_entries()
        self.assertIsNotNone(block)

        # Verify entry is stored correctly
        stored_entry = block.entries[0]
        self.assertTrue(stored_entry.metadata.get("is_delayed_intent"))
        self.assertEqual(stored_entry.metadata.get("delayed_intent_type"), "posthumous")
        self.assertEqual(stored_entry.metadata["trigger"]["type"], "death")
        self.assertEqual(stored_entry.metadata["trigger"]["minimum_confirmations"], 2)

    def test_time_delayed_intent_recording(self):
        """Test recording a time-delayed publication intent."""
        entry = NaturalLanguageEntry(
            content="Time-Delayed Release: On January 1, 2030, release my research paper "
                    "'Advances in Quantum Computing' to the public domain. Until then, "
                    "maintain confidentiality.",
            author="alice",
            intent="Delayed publication",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "time_delayed",
                "trigger": {
                    "type": "datetime",
                    "trigger_at": "2030-01-01T00:00:00Z",
                    "timezone": "UTC"
                },
                "executor": {
                    "primary": "finite_intent_executor_mainnet"
                },
                "actions": [
                    {
                        "action_type": "publish",
                        "subject": "vault://alice/research/quantum_paper.pdf",
                        "destination": "public_archive",
                        "license": "CC0"
                    }
                ],
                "revocation": {
                    "revocable": True,
                    "revocation_deadline": "2029-12-31T23:59:59Z"
                }
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored_entry = block.entries[0]
        self.assertEqual(stored_entry.metadata["trigger"]["type"], "datetime")
        self.assertEqual(stored_entry.metadata["trigger"]["trigger_at"], "2030-01-01T00:00:00Z")

    def test_conditional_intent_recording(self):
        """Test recording a conditional intent."""
        entry = NaturalLanguageEntry(
            content="Conditional Intent: If my company is acquired by any entity, immediately "
                    "release all my personal projects under open source license and donate "
                    "50% of my equity proceeds to the Electronic Frontier Foundation.",
            author="alice",
            intent="Conditional asset disposition",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "conditional",
                "trigger": {
                    "type": "event",
                    "event_description": "Company acquisition",
                    "verification_method": "sec_filing_oracle",
                    "conditions": [
                        "company_id=ACME_CORP",
                        "transaction_type=acquisition"
                    ]
                },
                "actions": [
                    {
                        "action_type": "license_release",
                        "subject": "personal_projects/*",
                        "license": "Apache-2.0"
                    },
                    {
                        "action_type": "donation",
                        "recipient": "Electronic Frontier Foundation",
                        "amount_formula": "0.5 * equity_proceeds"
                    }
                ]
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored_entry = block.entries[0]
        self.assertEqual(stored_entry.metadata["trigger"]["type"], "event")


class TestFIEExecutionRecording(unittest.TestCase):
    """Test recording execution proofs from FIE."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

        # Add a delayed intent first
        intent_entry = NaturalLanguageEntry(
            content="Posthumous IP Transfer to Foundation",
            author="alice",
            intent="Posthumous transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "delayed_intent_id": "DI-001"
            }
        )
        intent_entry.validation_status = "valid"
        self.blockchain.add_entry(intent_entry)
        self.blockchain.mine_pending_entries()

    def test_execution_record(self):
        """Test recording execution proof from FIE."""
        execution_entry = NaturalLanguageEntry(
            content="Execution Record for Delayed Intent DI-001: On June 20, 2035, following "
                    "verified death of Alice Johnson, the following actions were executed: "
                    "(1) IP rights for github.com/alice/* transferred to Open Source Foundation "
                    "under MIT license. (2) Notifications sent to designated parties. This "
                    "execution was performed by finite_intent_executor_mainnet in accordance "
                    "with the original intent recorded on block 1.",
            author="finite_intent_executor_mainnet",
            intent="Record execution",
            metadata={
                "is_execution_record": True,
                "delayed_intent_ref": {"block": 1, "entry": 0},
                "execution_id": "EXEC-001",
                "delayed_intent_id": "DI-001",
                "trigger_evidence": {
                    "type": "death",
                    "verification_id": "VERIFY-001",
                    "confirmations": 2,
                    "sources": [
                        "social_security_death_index",
                        "legal_executor_declaration"
                    ]
                },
                "actions_completed": [
                    {
                        "action": "ip_transfer",
                        "status": "success",
                        "timestamp": "2035-06-20T10:00:00Z",
                        "transaction_hash": "0xABC123..."
                    },
                    {
                        "action": "notification",
                        "status": "success",
                        "timestamp": "2035-06-20T10:00:05Z",
                        "recipients_notified": 2
                    }
                ],
                "legal_certificate_available": True
            }
        )
        execution_entry.validation_status = "valid"

        self.blockchain.add_entry(execution_entry)
        block = self.blockchain.mine_pending_entries()

        stored_entry = block.entries[0]
        self.assertTrue(stored_entry.metadata.get("is_execution_record"))
        self.assertEqual(stored_entry.metadata["execution_id"], "EXEC-001")
        self.assertEqual(len(stored_entry.metadata["actions_completed"]), 2)
        self.assertEqual(stored_entry.metadata["trigger_evidence"]["confirmations"], 2)


class TestFIERevocation(unittest.TestCase):
    """Test intent revocation handling."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

        # Add original intent
        intent_entry = NaturalLanguageEntry(
            content="Original posthumous intent",
            author="alice",
            intent="Posthumous transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_id": "DI-001",
                "revocation": {"revocable": True}
            }
        )
        intent_entry.validation_status = "valid"
        self.blockchain.add_entry(intent_entry)
        self.blockchain.mine_pending_entries()

    def test_intent_revocation(self):
        """Test revoking a delayed intent."""
        revocation_entry = NaturalLanguageEntry(
            content="Revocation of Delayed Intent DI-001: I hereby revoke the posthumous "
                    "IP transfer intent recorded on block 1. This revocation supersedes "
                    "all previous instructions.",
            author="alice",
            intent="Revoke delayed intent",
            metadata={
                "is_revocation": True,
                "revokes_intent": {"block": 1, "entry": 0},
                "delayed_intent_id": "DI-001",
                "revocation_reason": "Changed beneficiary to different organization",
                "revocation_timestamp": datetime.utcnow().isoformat(),
                "signature": "0xALICE_SIGNATURE..."
            }
        )
        revocation_entry.validation_status = "valid"

        self.blockchain.add_entry(revocation_entry)
        block = self.blockchain.mine_pending_entries()

        stored_entry = block.entries[0]
        self.assertTrue(stored_entry.metadata.get("is_revocation"))
        self.assertEqual(stored_entry.metadata["delayed_intent_id"], "DI-001")


class TestFIEQueryCapabilities(unittest.TestCase):
    """Test querying delayed intents."""

    def setUp(self):
        """Set up test fixtures with multiple intents."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

        # Add various delayed intents
        intents = [
            {"author": "alice", "type": "posthumous", "id": "DI-001"},
            {"author": "alice", "type": "time_delayed", "id": "DI-002"},
            {"author": "bob", "type": "posthumous", "id": "DI-003"},
        ]

        for intent in intents:
            entry = NaturalLanguageEntry(
                content=f"Delayed intent {intent['id']}",
                author=intent["author"],
                intent=f"{intent['type']} intent",
                metadata={
                    "is_delayed_intent": True,
                    "delayed_intent_type": intent["type"],
                    "delayed_intent_id": intent["id"]
                }
            )
            entry.validation_status = "valid"
            self.blockchain.add_entry(entry)

        self.blockchain.mine_pending_entries()

    def test_query_by_author(self):
        """Test querying delayed intents by author."""
        entries = self.blockchain.get_entries_by_author("alice")
        delayed_intents = [
            e for e in entries
            if e["entry"].get("metadata", {}).get("is_delayed_intent")
        ]
        self.assertEqual(len(delayed_intents), 2)

    def test_query_by_intent_type(self):
        """Test querying by intent keyword."""
        entries = self.blockchain.get_entries_by_intent("posthumous")
        self.assertGreater(len(entries), 0)


class TestFIEMetadataIntegrity(unittest.TestCase):
    """Test metadata integrity for FIE requirements."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

    def test_complex_metadata_preservation(self):
        """Test that complex nested metadata is preserved correctly."""
        complex_metadata = {
            "is_delayed_intent": True,
            "delayed_intent_type": "posthumous",
            "delayed_intent_id": "DI-COMPLEX-001",
            "trigger": {
                "type": "death",
                "verification_method": "death_certificate_oracle",
                "verification_sources": [
                    {"name": "SSDI", "reliability": 0.99},
                    {"name": "Legal Executor", "reliability": 0.95}
                ],
                "minimum_confirmations": 2,
                "consensus_rules": {
                    "minimum_sources": 2,
                    "minimum_reliability_sum": 1.8,
                    "challenge_period": "30_days"
                }
            },
            "executor": {
                "primary": "finite_intent_executor_mainnet",
                "backup": "finite_intent_executor_backup",
                "config": {
                    "retry_attempts": 3,
                    "timeout_hours": 24
                }
            },
            "actions": [
                {
                    "action_type": "ip_transfer",
                    "subject": "github.com/alice/*",
                    "to": "osf_org",
                    "conditions": ["verify_ownership", "check_liens"],
                    "fallback": "retain_until_resolved"
                },
                {
                    "action_type": "financial_transfer",
                    "amount": 50000,
                    "currency": "USD",
                    "recipient": {
                        "name": "Charity Foundation",
                        "account_type": "wire",
                        "verification_required": True
                    }
                }
            ],
            "witnesses": [
                {"witness": "bob", "role": "primary"},
                {"witness": "carol", "role": "secondary"}
            ],
            "legal": {
                "jurisdiction": "California, USA",
                "notarized": True,
                "attorney_record": "LAW-12345"
            }
        }

        entry = NaturalLanguageEntry(
            content="Complex posthumous intent with multiple actions",
            author="alice",
            intent="Complex posthumous transfer",
            metadata=complex_metadata
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        # Verify all nested data is preserved
        stored = block.entries[0].metadata

        self.assertEqual(stored["delayed_intent_id"], "DI-COMPLEX-001")
        self.assertEqual(len(stored["trigger"]["verification_sources"]), 2)
        self.assertEqual(stored["trigger"]["consensus_rules"]["challenge_period"], "30_days")
        self.assertEqual(len(stored["actions"]), 2)
        self.assertEqual(stored["actions"][1]["recipient"]["account_type"], "wire")
        self.assertEqual(stored["legal"]["jurisdiction"], "California, USA")

    def test_blockchain_chain_integrity_with_fie_entries(self):
        """Test that blockchain remains valid with FIE entries."""
        # Add multiple FIE entries
        for i in range(5):
            entry = NaturalLanguageEntry(
                content=f"Delayed intent {i}",
                author="alice",
                intent="Test intent",
                metadata={
                    "is_delayed_intent": True,
                    "delayed_intent_id": f"DI-TEST-{i}"
                }
            )
            entry.validation_status = "valid"
            self.blockchain.add_entry(entry)

        self.blockchain.mine_pending_entries()

        # Verify chain integrity
        self.assertTrue(self.blockchain.validate_chain())


class TestFIESunsetAndPublicDomain(unittest.TestCase):
    """Test 20-year sunset handling per FIE specification."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable validation and security checks for unit testing
        self.blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

    def test_sunset_metadata(self):
        """Test recording sunset/public domain transition metadata."""
        sunset_entry = NaturalLanguageEntry(
            content="20-Year Sunset Notification: Intent DI-001 has reached its mandatory "
                    "20-year sunset period. Per FIE protocol, all associated IP has "
                    "transitioned to public domain as of 2045-12-19.",
            author="finite_intent_executor_mainnet",
            intent="Record sunset transition",
            metadata={
                "is_sunset_record": True,
                "delayed_intent_id": "DI-001",
                "sunset_date": "2045-12-19T00:00:00Z",
                "original_creation_date": "2025-12-19T00:00:00Z",
                "sunset_duration_years": 20,
                "transition_type": "public_domain",
                "assets_transitioned": [
                    {"type": "ip_rights", "subject": "github.com/alice/*"},
                    {"type": "documentation", "subject": "research_papers/*"}
                ],
                "archive_location": "public_archive://fie/DI-001"
            }
        )
        sunset_entry.validation_status = "valid"

        self.blockchain.add_entry(sunset_entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0].metadata
        self.assertTrue(stored.get("is_sunset_record"))
        self.assertEqual(stored["sunset_duration_years"], 20)
        self.assertEqual(stored["transition_type"], "public_domain")


class TestFIECompatibilitySummary(unittest.TestCase):
    """Summary test that validates overall FIE compatibility."""

    def test_full_fie_workflow(self):
        """Test complete FIE workflow: intent -> execution -> proof."""
        # Disable validation and security checks for unit testing
        blockchain = NatLangChain(
            require_validation=False,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_metadata_sanitization=False
        )

        # Step 1: Record delayed intent
        intent = NaturalLanguageEntry(
            content="Upon my passing, transfer all IP to Foundation",
            author="alice",
            intent="Posthumous IP transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "delayed_intent_id": "DI-WORKFLOW-001",
                "trigger": {"type": "death", "minimum_confirmations": 2}
            }
        )
        intent.validation_status = "valid"
        blockchain.add_entry(intent)
        intent_block = blockchain.mine_pending_entries()
        self.assertIsNotNone(intent_block)

        # Step 2: Record trigger verification (simulated)
        verification = NaturalLanguageEntry(
            content="Trigger verification: Death confirmed by 2 sources",
            author="fie_oracle_network",
            intent="Verify trigger",
            metadata={
                "is_trigger_verification": True,
                "delayed_intent_id": "DI-WORKFLOW-001",
                "verification_id": "VERIFY-WORKFLOW-001",
                "trigger_verified": True,
                "confirmations": 2
            }
        )
        verification.validation_status = "valid"
        blockchain.add_entry(verification)
        blockchain.mine_pending_entries()

        # Step 3: Record execution
        execution = NaturalLanguageEntry(
            content="Execution completed for DI-WORKFLOW-001",
            author="finite_intent_executor_mainnet",
            intent="Record execution",
            metadata={
                "is_execution_record": True,
                "delayed_intent_id": "DI-WORKFLOW-001",
                "execution_id": "EXEC-WORKFLOW-001",
                "verification_ref": "VERIFY-WORKFLOW-001",
                "actions_completed": [{"action": "ip_transfer", "status": "success"}]
            }
        )
        execution.validation_status = "valid"
        blockchain.add_entry(execution)
        execution_block = blockchain.mine_pending_entries()
        self.assertIsNotNone(execution_block)

        # Verify chain integrity
        self.assertTrue(blockchain.validate_chain())

        # Verify we can query the workflow
        entries = blockchain.get_entries_by_author("finite_intent_executor_mainnet")
        self.assertEqual(len(entries), 1)

        print("\n✅ Full FIE workflow test passed!")
        print("   - Delayed intent recorded on block 1")
        print("   - Trigger verification recorded on block 2")
        print("   - Execution proof recorded on block 3")
        print("   - Chain integrity verified")


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
