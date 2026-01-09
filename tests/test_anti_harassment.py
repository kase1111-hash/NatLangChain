"""
Tests for the Anti-Harassment Economic Layer.

Tests the economic pressure mechanisms that make harassment strictly more
expensive for the harasser than for the target.
"""

import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, "src")

from anti_harassment import (
    AntiHarassmentManager,
    DisputeResolution,
    HarassmentProfile,
    InitiationPath,
    StakeEscrow,
)


class TestBreachDisputeInitiation(unittest.TestCase):
    """Tests for initiating breach/drift disputes with symmetric staking."""

    def setUp(self):
        self.manager = AntiHarassmentManager()

    def test_initiate_breach_dispute_success(self):
        """Test successful breach dispute initiation."""
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[{"type": "drift", "ref": "DRIFT-001"}],
            description="Semantic drift detected in clause 3",
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "escrow_created")
        self.assertIn("escrow_id", result)
        self.assertIn("dispute_ref", result)
        self.assertEqual(result["stake_amount"], 100.0)
        self.assertEqual(result["path"], InitiationPath.BREACH_DISPUTE.value)

    def test_initiate_breach_dispute_creates_escrow(self):
        """Test that escrow is properly created."""
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )

        escrow_id = result["escrow_id"]
        escrow = self.manager.escrows[escrow_id]

        self.assertEqual(escrow.initiator, "alice")
        self.assertEqual(escrow.counterparty, "bob")
        self.assertEqual(escrow.stake_amount, 100.0)
        self.assertEqual(escrow.status, "pending_match")

    def test_cooldown_prevents_rapid_disputes(self):
        """Test that cooldown prevents rapid disputes on same contract."""
        # First dispute succeeds
        success1, _ = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="First dispute",
        )
        self.assertTrue(success1)

        # Manually set cooldown on the profile
        profile = self.manager._get_or_create_profile("alice")
        profile.contract_cooldowns["CONTRACT-001"] = (
            datetime.utcnow() + timedelta(days=30)
        ).isoformat()

        # Second dispute on same contract should fail due to cooldown
        success2, result2 = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Second dispute",
        )

        self.assertFalse(success2)
        self.assertIn("error", result2)


class TestStakeMatching(unittest.TestCase):
    """Tests for stake matching by counterparty."""

    def setUp(self):
        self.manager = AntiHarassmentManager()
        # Create a dispute to match
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )
        self.escrow_id = result["escrow_id"]

    def test_match_stake_success(self):
        """Test successful stake matching."""
        success, result = self.manager.match_stake(
            escrow_id=self.escrow_id, counterparty="bob", stake_amount=100.0
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "stakes_matched")
        self.assertEqual(result["total_escrowed"], 200.0)

    def test_match_stake_wrong_counterparty(self):
        """Test that only designated counterparty can match."""
        success, result = self.manager.match_stake(
            escrow_id=self.escrow_id, counterparty="charlie", stake_amount=100.0
        )

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertIn("counterparty", result["error"].lower())

    def test_match_stake_insufficient_amount(self):
        """Test that stake must match required amount."""
        success, result = self.manager.match_stake(
            escrow_id=self.escrow_id, counterparty="bob", stake_amount=50.0
        )

        self.assertFalse(success)
        self.assertIn("error", result)
        self.assertEqual(result["required"], 100.0)
        self.assertEqual(result["provided"], 50.0)

    def test_match_stake_escrow_not_found(self):
        """Test error when escrow doesn't exist."""
        success, result = self.manager.match_stake(
            escrow_id="NONEXISTENT", counterparty="bob", stake_amount=100.0
        )

        self.assertFalse(success)
        self.assertIn("not found", result["error"].lower())


class TestDeclineStake(unittest.TestCase):
    """Tests for declining to match stake (free for counterparty)."""

    def setUp(self):
        self.manager = AntiHarassmentManager()
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )
        self.escrow_id = result["escrow_id"]

    def test_decline_stake_success(self):
        """Test successful stake decline triggers fallback."""
        success, result = self.manager.decline_stake(escrow_id=self.escrow_id, counterparty="bob")

        self.assertTrue(success)
        self.assertEqual(result["status"], "resolved_fallback")

        # Verify escrow status
        escrow = self.manager.escrows[self.escrow_id]
        self.assertEqual(escrow.status, "fallback")
        self.assertEqual(escrow.resolution, DisputeResolution.FALLBACK.value)

    def test_decline_stake_wrong_party(self):
        """Test that only counterparty can decline."""
        success, result = self.manager.decline_stake(
            escrow_id=self.escrow_id, counterparty="charlie"
        )

        self.assertFalse(success)
        self.assertIn("counterparty", result["error"].lower())


class TestVoluntaryRequests(unittest.TestCase):
    """Tests for voluntary negotiation requests (can be ignored for free)."""

    def setUp(self):
        self.manager = AntiHarassmentManager()

    def test_initiate_voluntary_request_success(self):
        """Test successful voluntary request initiation."""
        success, result = self.manager.initiate_voluntary_request(
            initiator="alice",
            recipient="bob",
            request_type="modification",
            description="I would like to modify clause 3",
            burn_fee=0.1,
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "request_sent")
        self.assertIn("request_id", result)
        self.assertEqual(result["path"], InitiationPath.VOLUNTARY_REQUEST.value)

    def test_voluntary_request_can_be_ignored(self):
        """Test that voluntary requests document they can be ignored."""
        success, result = self.manager.initiate_voluntary_request(
            initiator="alice",
            recipient="bob",
            request_type="modification",
            description="Please review",
            burn_fee=0.1,
        )

        self.assertIn("ignore", result["recipient_obligation"].lower())

    def test_respond_to_voluntary_request_accept(self):
        """Test accepting a voluntary request."""
        # Create request
        success, result = self.manager.initiate_voluntary_request(
            initiator="alice",
            recipient="bob",
            request_type="modification",
            description="Please review",
            burn_fee=0.1,
        )
        request_id = result["request_id"]

        # Accept
        success, result = self.manager.respond_to_voluntary_request(
            request_id=request_id, recipient="bob", accept=True, response="I accept this request"
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "responded")
        self.assertTrue(result["accepted"])

    def test_respond_to_voluntary_request_decline(self):
        """Test declining a voluntary request (free)."""
        success, result = self.manager.initiate_voluntary_request(
            initiator="alice",
            recipient="bob",
            request_type="modification",
            description="Please review",
            burn_fee=0.1,
        )
        request_id = result["request_id"]

        # Decline
        success, result = self.manager.respond_to_voluntary_request(
            request_id=request_id, recipient="bob", accept=False, response="Not interested"
        )

        self.assertTrue(success)
        # Status is "responded" regardless of accept value
        self.assertIn("status", result)


class TestCounterProposalLimits(unittest.TestCase):
    """Tests for counter-proposal griefing limits."""

    def setUp(self):
        self.manager = AntiHarassmentManager()
        # Create a matched dispute
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )
        self.escrow_id = result["escrow_id"]
        self.dispute_ref = result["dispute_ref"]
        self.manager.match_stake(self.escrow_id, "bob", 100.0)

    def test_counter_proposal_increments_count(self):
        """Test that counter proposals increment count."""
        success, result = self.manager.submit_counter_proposal(
            dispute_ref=self.dispute_ref, party="alice", proposal_content="new terms"
        )

        self.assertTrue(success)
        self.assertEqual(result["counter_number"], 1)

    def test_counter_proposal_fee_escalation(self):
        """Test that counter proposal fees escalate exponentially."""
        fees = []
        for i in range(3):
            success, result = self.manager.submit_counter_proposal(
                dispute_ref=self.dispute_ref, party="alice", proposal_content=f"proposal {i + 1}"
            )
            fees.append(result.get("fee_burned", 0))

        # Fees should escalate (base_fee × 2^n pattern: 1.0, 2.0, 4.0)
        self.assertGreater(fees[1], fees[0])
        self.assertGreater(fees[2], fees[1])

    def test_counter_proposal_limit_exceeded(self):
        """Test that exceeding counter proposal limit is blocked."""
        # Submit max counter proposals
        for i in range(self.manager.MAX_COUNTER_PROPOSALS):
            self.manager.submit_counter_proposal(
                dispute_ref=self.dispute_ref, party="alice", proposal_content=f"proposal {i + 1}"
            )

        # Next should fail
        success, result = self.manager.submit_counter_proposal(
            dispute_ref=self.dispute_ref, party="alice", proposal_content="one too many"
        )

        self.assertFalse(success)
        self.assertIn("limit", result["error"].lower())


class TestHarassmentScoring(unittest.TestCase):
    """Tests for harassment scoring and reputation."""

    def setUp(self):
        self.manager = AntiHarassmentManager()

    def test_new_address_has_zero_score(self):
        """Test that new addresses start with zero harassment score."""
        result = self.manager.get_harassment_score("new_user")

        self.assertEqual(result["harassment_score"], 0.0)
        self.assertEqual(result["severity"], "none")

    def test_non_resolving_disputes_increase_score(self):
        """Test that non-resolving disputes increase harassment score."""
        # Create and decline a dispute (non-resolving)
        success, result = self.manager.initiate_breach_dispute(
            initiator="harasser",
            counterparty="victim",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Frivolous dispute",
        )
        escrow_id = result["escrow_id"]
        self.manager.decline_stake(escrow_id, "victim")

        # Score should have increased
        result = self.manager.get_harassment_score("harasser")
        self.assertGreater(result["harassment_score"], 0.0)

    def test_veto_increases_score(self):
        """Test that using vetoes increases harassment score."""
        self.manager.record_veto("user", "DISPUTE-001")

        result = self.manager.get_harassment_score("user")
        self.assertGreater(result["harassment_score"], 0.0)

    def test_harassment_levels(self):
        """Test that harassment levels are correctly categorized."""
        profile = self.manager._get_or_create_profile("user")

        # Low (0 non_resolving_disputes = score 0)
        profile.non_resolving_disputes = 0
        self.manager._recalculate_harassment_score(profile)
        self.assertLess(profile.harassment_score, self.manager.HARASSMENT_THRESHOLD_MODERATE)

        # Moderate (3 non_resolving_disputes × 10 = 30, between 25 and 50)
        profile.non_resolving_disputes = 3
        self.manager._recalculate_harassment_score(profile)

        result = self.manager.get_harassment_score("user")
        self.assertGreaterEqual(
            result["harassment_score"], self.manager.HARASSMENT_THRESHOLD_MODERATE
        )
        self.assertLess(result["harassment_score"], self.manager.HARASSMENT_THRESHOLD_HIGH)
        self.assertEqual(result["severity"], "moderate")


class TestStakeTimeouts(unittest.TestCase):
    """Tests for stake window timeouts."""

    def setUp(self):
        self.manager = AntiHarassmentManager()

    def test_check_stake_timeouts_finds_expired(self):
        """Test that expired stakes are detected."""
        # Create a dispute
        success, result = self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )
        escrow_id = result["escrow_id"]

        # Manually expire the stake window
        escrow = self.manager.escrows[escrow_id]
        escrow.stake_window_ends = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        # Check timeouts
        expired = self.manager.check_stake_timeouts()

        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["escrow_id"], escrow_id)
        self.assertEqual(expired[0]["resolution"], DisputeResolution.TIMEOUT.value)


class TestAuditTrail(unittest.TestCase):
    """Tests for audit trail functionality."""

    def setUp(self):
        self.manager = AntiHarassmentManager()

    def test_actions_are_recorded(self):
        """Test that actions are recorded in audit trail."""
        self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )

        trail = self.manager.get_audit_trail()

        self.assertGreater(len(trail), 0)
        self.assertEqual(trail[0]["action_type"], "breach_dispute_initiated")

    def test_get_statistics(self):
        """Test that statistics are computed correctly."""
        # Create some activity
        self.manager.initiate_breach_dispute(
            initiator="alice",
            counterparty="bob",
            contract_ref="CONTRACT-001",
            stake_amount=100.0,
            evidence_refs=[],
            description="Test dispute",
        )

        stats = self.manager.get_statistics()

        self.assertIn("escrows", stats)
        self.assertIn("harassment_profiles", stats)
        self.assertEqual(stats["escrows"]["total"], 1)


class TestEscrowDataclass(unittest.TestCase):
    """Tests for StakeEscrow dataclass."""

    def test_stake_escrow_creation(self):
        """Test StakeEscrow creation with defaults."""
        escrow = StakeEscrow(
            escrow_id="ESC-001",
            dispute_ref="DISPUTE-001",
            initiator="alice",
            stake_amount=100.0,
            created_at="2024-01-01T00:00:00",
            stake_window_ends="2024-01-04T00:00:00",
            counterparty="bob",
        )

        self.assertEqual(escrow.counterparty_stake, 0.0)
        self.assertIsNone(escrow.counterparty_staked_at)
        self.assertEqual(escrow.status, "pending_match")
        self.assertIsNone(escrow.resolution)


class TestHarassmentProfile(unittest.TestCase):
    """Tests for HarassmentProfile dataclass."""

    def test_profile_creation_defaults(self):
        """Test HarassmentProfile creation with defaults."""
        profile = HarassmentProfile(address="user")

        self.assertEqual(profile.initiated_disputes, 0)
        self.assertEqual(profile.non_resolving_disputes, 0)
        self.assertEqual(profile.harassment_score, 0.0)
        self.assertEqual(profile.contract_cooldowns, {})


if __name__ == "__main__":
    unittest.main()
