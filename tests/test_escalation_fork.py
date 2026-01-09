"""
Tests for the Escalation Fork Protocol implementation.
"""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from escalation_fork import EscalationForkManager, ForkStatus, TriggerReason


class TestEscalationForkManager(unittest.TestCase):
    """Tests for EscalationForkManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = EscalationForkManager()

    def test_trigger_fork(self):
        """Test triggering an escalation fork."""
        fork_data = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_node_1",
            original_pool=100.0,
            burn_tx_hash="0xabc123",
            evidence_of_failure={"failed_proposals": ["PROP-001"]},
        )

        self.assertIn("fork_id", fork_data)
        self.assertTrue(fork_data["fork_id"].startswith("FORK-"))
        self.assertEqual(fork_data["status"], ForkStatus.ACTIVE.value)
        self.assertEqual(fork_data["original_pool"], 100.0)
        self.assertEqual(fork_data["mediator_retained"], 50.0)
        self.assertEqual(fork_data["bounty_pool"], 50.0)
        self.assertTrue(fork_data["observance_burn_verified"])

    def test_fork_id_uniqueness(self):
        """Test that fork IDs are unique."""
        fork1 = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0x111",
        )

        fork2 = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST002",
            trigger_reason=TriggerReason.REFUSAL_TO_MEDIATE,
            triggering_party="bob",
            original_mediator="mediator_2",
            original_pool=200.0,
            burn_tx_hash="0x222",
        )

        self.assertNotEqual(fork1["fork_id"], fork2["fork_id"])


class TestProposalSubmission(unittest.TestCase):
    """Tests for proposal submission."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = EscalationForkManager()
        self.fork_data = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )
        self.fork_id = self.fork_data["fork_id"]

    def test_submit_valid_proposal(self):
        """Test submitting a valid proposal."""
        # Create a proposal with 500+ words
        proposal_content = " ".join(["word"] * 600)

        success, result = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["rate_dispute", "timeline"],
        )

        self.assertTrue(success)
        self.assertIn("proposal_id", result)
        self.assertEqual(result["solver"], "solver_1")
        self.assertEqual(result["word_count"], 600)
        self.assertEqual(result["iteration"], 1)

    def test_reject_short_proposal(self):
        """Test that short proposals are rejected."""
        short_proposal = "This is too short."

        success, result = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=short_proposal,
            addresses_concerns=["concern"],
        )

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertIn("500 words", result["error"])

    def test_iteration_counting(self):
        """Test that proposal iterations are counted correctly."""
        proposal_content = " ".join(["word"] * 600)

        # First proposal
        _success1, result1 = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )

        # Second proposal from same solver
        _success2, result2 = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=proposal_content + " additional content",
            addresses_concerns=["concern", "new_concern"],
        )

        self.assertEqual(result1["iteration"], 1)
        self.assertEqual(result2["iteration"], 2)


class TestRatification(unittest.TestCase):
    """Tests for proposal ratification."""

    def setUp(self):
        """Set up test fixtures with a proposal."""
        self.manager = EscalationForkManager()
        self.fork_data = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )
        self.fork_id = self.fork_data["fork_id"]

        # Submit a proposal
        proposal_content = " ".join(["word"] * 600)
        _success, self.proposal_data = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )
        self.proposal_id = self.proposal_data["proposal_id"]

    def test_single_ratification(self):
        """Test single party ratification."""
        success, result = self.manager.ratify_proposal(
            fork_id=self.fork_id,
            proposal_id=self.proposal_id,
            ratifying_party="alice",
            satisfaction_rating=85,
            comments="Good proposal",
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "ratification_recorded")

    def test_dual_ratification_resolves_fork(self):
        """Test that dual ratification resolves the fork."""
        # First ratification
        self.manager.ratify_proposal(
            fork_id=self.fork_id,
            proposal_id=self.proposal_id,
            ratifying_party="alice",
            satisfaction_rating=85,
        )

        # Second ratification
        success, result = self.manager.ratify_proposal(
            fork_id=self.fork_id,
            proposal_id=self.proposal_id,
            ratifying_party="bob",
            satisfaction_rating=90,
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "resolved")
        self.assertTrue(result["bounty_distributed"])
        self.assertIn("distribution", result)


class TestVeto(unittest.TestCase):
    """Tests for proposal veto functionality."""

    def setUp(self):
        """Set up test fixtures with a proposal."""
        self.manager = EscalationForkManager()
        self.fork_data = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )
        self.fork_id = self.fork_data["fork_id"]

        proposal_content = " ".join(["word"] * 600)
        _success, self.proposal_data = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )
        self.proposal_id = self.proposal_data["proposal_id"]

    def test_valid_veto(self):
        """Test valid veto with sufficient reasoning."""
        veto_reason = " ".join(["reasoning"] * 150)  # 150 words

        success, result = self.manager.veto_proposal(
            fork_id=self.fork_id,
            proposal_id=self.proposal_id,
            vetoing_party="bob",
            veto_reason=veto_reason,
            evidence_refs=["EVIDENCE-001"],
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "vetoed")
        self.assertEqual(result["remaining_vetoes"], 2)

    def test_reject_short_veto_reason(self):
        """Test that short veto reasons are rejected."""
        short_reason = "Too short"

        success, result = self.manager.veto_proposal(
            fork_id=self.fork_id,
            proposal_id=self.proposal_id,
            vetoing_party="bob",
            veto_reason=short_reason,
        )

        self.assertFalse(success)
        self.assertIn("100 words", result["error"])

    def test_veto_limit(self):
        """Test that veto limit is enforced."""
        veto_reason = " ".join(["reasoning"] * 150)

        # Create multiple proposals and veto them
        proposal_content = " ".join(["word"] * 600)

        for i in range(3):
            success, prop = self.manager.submit_proposal(
                fork_id=self.fork_id,
                solver=f"solver_{i}",
                proposal_content=proposal_content,
                addresses_concerns=["concern"],
            )
            self.manager.veto_proposal(
                fork_id=self.fork_id,
                proposal_id=prop["proposal_id"],
                vetoing_party="bob",
                veto_reason=veto_reason,
            )

        # Fourth veto should fail
        success, prop4 = self.manager.submit_proposal(
            fork_id=self.fork_id,
            solver="solver_4",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )
        success, result = self.manager.veto_proposal(
            fork_id=self.fork_id,
            proposal_id=prop4["proposal_id"],
            vetoing_party="bob",
            veto_reason=veto_reason,
        )

        self.assertFalse(success)
        self.assertIn("Maximum vetoes", result["error"])


class TestForkStatus(unittest.TestCase):
    """Tests for fork status queries."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = EscalationForkManager()

    def test_get_fork_status(self):
        """Test getting fork status."""
        fork_data = self.manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )

        status = self.manager.get_fork_status(fork_data["fork_id"])

        self.assertIsNotNone(status)
        self.assertEqual(status["status"], ForkStatus.ACTIVE.value)
        self.assertEqual(status["total_proposals"], 0)

    def test_list_active_forks(self):
        """Test listing active forks."""
        # Create two forks
        self.manager.trigger_fork(
            dispute_id="DISPUTE-001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0x111",
        )

        self.manager.trigger_fork(
            dispute_id="DISPUTE-002",
            trigger_reason=TriggerReason.MUTUAL_REQUEST,
            triggering_party="bob",
            original_mediator="mediator_2",
            original_pool=200.0,
            burn_tx_hash="0x222",
        )

        active_forks = self.manager.list_active_forks()

        self.assertEqual(len(active_forks), 2)


class TestAuditTrail(unittest.TestCase):
    """Tests for fork audit trail."""

    def test_audit_trail_integrity(self):
        """Test that audit trail has proper hash chain."""
        manager = EscalationForkManager()

        fork_data = manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )

        fork_id = fork_data["fork_id"]

        # Submit a proposal
        proposal_content = " ".join(["word"] * 600)
        manager.submit_proposal(
            fork_id=fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )

        trail = manager.get_fork_audit_trail(fork_id)

        self.assertGreater(len(trail), 0)

        # Verify hash chain
        for i, entry in enumerate(trail):
            self.assertIn("action_hash", entry)
            self.assertIn("previous_action_hash", entry)

            if i == 0:
                self.assertEqual(entry["previous_action_hash"], "0" * 64)


class TestEffortCalculation(unittest.TestCase):
    """Tests for effort-based distribution calculation."""

    def test_distribution_single_solver(self):
        """Test distribution with single winning solver."""
        manager = EscalationForkManager()

        fork_data = manager.trigger_fork(
            dispute_id="DISPUTE-TEST001",
            trigger_reason=TriggerReason.FAILED_RATIFICATION,
            triggering_party="alice",
            original_mediator="mediator_1",
            original_pool=100.0,
            burn_tx_hash="0xabc",
        )

        fork_id = fork_data["fork_id"]

        # Submit proposal
        proposal_content = " ".join(["word"] * 1000)
        success, proposal = manager.submit_proposal(
            fork_id=fork_id,
            solver="solver_1",
            proposal_content=proposal_content,
            addresses_concerns=["concern"],
        )

        # Dual ratification
        manager.ratify_proposal(
            fork_id=fork_id,
            proposal_id=proposal["proposal_id"],
            ratifying_party="alice",
            satisfaction_rating=85,
        )

        _success, result = manager.ratify_proposal(
            fork_id=fork_id,
            proposal_id=proposal["proposal_id"],
            ratifying_party="bob",
            satisfaction_rating=90,
        )

        # Single solver should get full bounty
        self.assertEqual(result["distribution"]["solver_1"], 50.0)


if __name__ == "__main__":
    unittest.main()
