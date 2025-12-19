"""
Tests for the Observance Burn Protocol implementation.
"""

import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from observance_burn import ObservanceBurnManager, BurnReason


class TestObservanceBurnManager(unittest.TestCase):
    """Tests for ObservanceBurnManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ObservanceBurnManager(initial_supply=1_000_000.0)

    def test_initial_state(self):
        """Test initial manager state."""
        self.assertEqual(self.manager.total_supply, 1_000_000.0)
        self.assertEqual(self.manager.total_burned, 0.0)
        self.assertEqual(len(self.manager.burns), 0)

    def test_perform_voluntary_burn(self):
        """Test performing a voluntary signal burn."""
        success, result = self.manager.perform_voluntary_burn(
            burner="0xAlice",
            amount=100.0,
            epitaph="For the long-term health of NatLangChain"
        )

        self.assertTrue(success)
        self.assertEqual(result["status"], "burned")
        self.assertEqual(result["amount"], 100.0)
        self.assertEqual(result["reason"], BurnReason.VOLUNTARY_SIGNAL.value)
        self.assertEqual(self.manager.total_supply, 999_900.0)
        self.assertEqual(self.manager.total_burned, 100.0)

    def test_perform_escalation_burn(self):
        """Test performing an escalation commitment burn."""
        success, result = self.manager.perform_burn(
            burner="0xAlice",
            amount=5.0,
            reason=BurnReason.ESCALATION_COMMITMENT,
            intent_hash="0xabc123def456",
            epitaph="Burned to fairly escalate"
        )

        self.assertTrue(success)
        self.assertEqual(result["reason"], "EscalationCommitment")
        self.assertIn("tx_hash", result)

    def test_reject_zero_amount(self):
        """Test that zero amount burns are rejected."""
        success, result = self.manager.perform_burn(
            burner="0xAlice",
            amount=0,
            reason=BurnReason.VOLUNTARY_SIGNAL
        )

        self.assertFalse(success)
        self.assertIn("error", result)

    def test_reject_exceeding_supply(self):
        """Test that burns exceeding supply are rejected."""
        success, result = self.manager.perform_burn(
            burner="0xAlice",
            amount=2_000_000.0,  # More than total supply
            reason=BurnReason.VOLUNTARY_SIGNAL
        )

        self.assertFalse(success)
        self.assertIn("exceeds total supply", result["error"])

    def test_epitaph_max_length(self):
        """Test that epitaphs exceeding max length are rejected."""
        long_epitaph = "x" * 300  # 300 chars, exceeds 280 limit

        success, result = self.manager.perform_burn(
            burner="0xAlice",
            amount=10.0,
            reason=BurnReason.VOLUNTARY_SIGNAL,
            epitaph=long_epitaph
        )

        self.assertFalse(success)
        self.assertIn("maximum length", result["error"])


class TestBurnReasons(unittest.TestCase):
    """Tests for different burn reasons."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ObservanceBurnManager(initial_supply=1_000_000.0)

    def test_all_burn_reasons(self):
        """Test that all burn reasons work."""
        reasons = [
            BurnReason.VOLUNTARY_SIGNAL,
            BurnReason.ESCALATION_COMMITMENT,
            BurnReason.RATE_LIMIT_EXCESS,
            BurnReason.PROTOCOL_VIOLATION,
            BurnReason.COMMUNITY_DIRECTIVE
        ]

        for reason in reasons:
            success, result = self.manager.perform_burn(
                burner="0xTest",
                amount=1.0,
                reason=reason,
                intent_hash="0x" + "0" * 64 if reason == BurnReason.ESCALATION_COMMITMENT else None
            )
            self.assertTrue(success, f"Failed for reason: {reason}")

    def test_burns_by_reason_counting(self):
        """Test that burns are counted by reason."""
        # Perform multiple burns
        self.manager.perform_voluntary_burn("0xAlice", 10.0)
        self.manager.perform_voluntary_burn("0xBob", 20.0)
        self.manager.perform_burn(
            burner="0xCharlie",
            amount=5.0,
            reason=BurnReason.ESCALATION_COMMITMENT,
            intent_hash="0x123"
        )

        stats = self.manager.get_statistics()

        self.assertEqual(stats["burns_by_reason"]["VoluntarySignal"], 2)
        self.assertEqual(stats["burns_by_reason"]["EscalationCommitment"], 1)


class TestEscalationBurnCalculation(unittest.TestCase):
    """Tests for escalation burn calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ObservanceBurnManager()

    def test_calculate_escalation_burn(self):
        """Test calculating escalation burn amount."""
        stake = 100.0
        burn_amount = self.manager.calculate_escalation_burn(stake)

        self.assertEqual(burn_amount, 5.0)  # 5% of stake

    def test_verify_escalation_burn(self):
        """Test verifying an escalation burn."""
        # Perform the burn first
        success, burn_result = self.manager.perform_burn(
            burner="0xAlice",
            amount=5.0,
            reason=BurnReason.ESCALATION_COMMITMENT,
            intent_hash="0xDispute123"
        )

        tx_hash = burn_result["tx_hash"]

        # Verify it
        is_valid, verification = self.manager.verify_escalation_burn(
            tx_hash=tx_hash,
            expected_amount=5.0,
            expected_intent_hash="0xDispute123"
        )

        self.assertTrue(is_valid)

    def test_verify_invalid_burn(self):
        """Test verifying non-existent burn fails."""
        is_valid, result = self.manager.verify_escalation_burn(
            tx_hash="0xNonExistent",
            expected_amount=5.0,
            expected_intent_hash="0xTest"
        )

        self.assertFalse(is_valid)
        self.assertIn("not found", result["error"])


class TestBurnStatistics(unittest.TestCase):
    """Tests for burn statistics."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ObservanceBurnManager(initial_supply=1_000_000.0)

    def test_statistics_after_burns(self):
        """Test statistics are accurate after multiple burns."""
        self.manager.perform_voluntary_burn("0xAlice", 100.0)
        self.manager.perform_voluntary_burn("0xBob", 50.0)
        self.manager.perform_burn(
            burner="0xCharlie",
            amount=25.0,
            reason=BurnReason.RATE_LIMIT_EXCESS
        )

        stats = self.manager.get_statistics()

        self.assertEqual(stats["total_burned"], 175.0)
        self.assertEqual(stats["total_burns"], 3)
        self.assertEqual(stats["current_supply"], 999_825.0)

    def test_largest_burn_tracking(self):
        """Test that largest burn is tracked."""
        self.manager.perform_voluntary_burn("0xSmall", 10.0)
        self.manager.perform_voluntary_burn("0xLarge", 1000.0)
        self.manager.perform_voluntary_burn("0xMedium", 100.0)

        stats = self.manager.get_statistics()

        self.assertEqual(stats["largest_burn"]["amount"], 1000.0)
        self.assertEqual(stats["largest_burn"]["burner"], "0xLarge")


class TestBurnHistory(unittest.TestCase):
    """Tests for burn history queries."""

    def setUp(self):
        """Set up test fixtures with burns."""
        self.manager = ObservanceBurnManager(initial_supply=1_000_000.0)

        for i in range(5):
            self.manager.perform_voluntary_burn(
                burner=f"0xUser{i}",
                amount=float(i + 1) * 10,
                epitaph=f"Burn number {i + 1}"
            )

    def test_get_burn_history(self):
        """Test getting burn history."""
        history = self.manager.get_burn_history(limit=3, offset=0)

        self.assertEqual(history["total"], 5)
        self.assertEqual(len(history["burns"]), 3)
        self.assertTrue(history["has_more"])

    def test_get_burns_by_address(self):
        """Test getting burns by address."""
        # Add another burn from same address
        self.manager.perform_voluntary_burn("0xUser0", 5.0)

        burns = self.manager.get_burns_by_address("0xUser0")

        self.assertEqual(len(burns), 2)


class TestBurnForDisplay(unittest.TestCase):
    """Tests for burn display formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = ObservanceBurnManager()

    def test_format_burn_for_display(self):
        """Test formatting burn for explorer display."""
        success, result = self.manager.perform_voluntary_burn(
            burner="0xBeliever",
            amount=100.0,
            epitaph="For the health of NatLangChain"
        )

        tx_hash = result["tx_hash"]
        burn = self.manager.get_burn_by_tx_hash(tx_hash)
        formatted = self.manager.format_burn_for_display(burn)

        self.assertEqual(formatted["icon"], "flame")
        self.assertEqual(formatted["title"], "Observance Burn")
        self.assertIn("100", formatted["subtitle"])
        self.assertIn("Voluntary Signal", formatted["subtitle"])
        self.assertEqual(formatted["body"], "For the health of NatLangChain")

    def test_observance_ledger(self):
        """Test getting observance ledger data."""
        self.manager.perform_voluntary_burn("0xUser1", 10.0, "Test 1")
        self.manager.perform_voluntary_burn("0xUser2", 20.0, "Test 2")

        ledger = self.manager.get_observance_ledger(limit=5)

        self.assertEqual(ledger["title"], "OBSERVANCE LEDGER")
        self.assertEqual(ledger["total_burns"], 2)
        self.assertEqual(len(ledger["recent_observances"]), 2)


class TestRedistributionEffect(unittest.TestCase):
    """Tests for redistribution effect calculation."""

    def test_redistribution_effect(self):
        """Test that redistribution effect is calculated correctly."""
        manager = ObservanceBurnManager(initial_supply=1_000_000.0)

        success, result = manager.perform_voluntary_burn(
            burner="0xAlice",
            amount=100.0
        )

        # After burning 100 from 1,000,000:
        # New supply: 999,900
        # Effect: (1,000,000 / 999,900 - 1) * 100 = ~0.01%

        burn = manager.get_burn_by_tx_hash(result["tx_hash"])
        self.assertAlmostEqual(
            burn["redistribution_effect_percent"],
            0.01001,  # Approximately
            places=3
        )


class TestEventEmission(unittest.TestCase):
    """Tests for Solidity event emission format."""

    def test_emit_observance_burn_event(self):
        """Test event emission in Solidity-compatible format."""
        manager = ObservanceBurnManager()

        success, result = manager.perform_burn(
            burner="0xAlice",
            amount=5.0,
            reason=BurnReason.ESCALATION_COMMITMENT,
            intent_hash="0xabc123",
            epitaph="Burned for escalation"
        )

        burn = manager.get_burn_by_tx_hash(result["tx_hash"])
        event = manager.emit_observance_burn_event(burn)

        self.assertEqual(event["name"], "ObservanceBurn")
        self.assertEqual(len(event["inputs"]), 5)

        # Check input names
        input_names = [inp["name"] for inp in event["inputs"]]
        self.assertIn("burner", input_names)
        self.assertIn("amount", input_names)
        self.assertIn("reason", input_names)
        self.assertIn("intentHash", input_names)
        self.assertIn("epitaph", input_names)


class TestRateLimitBurn(unittest.TestCase):
    """Tests for rate limit excess burns."""

    def test_perform_rate_limit_burn(self):
        """Test performing rate limit excess burn."""
        manager = ObservanceBurnManager()

        success, result = manager.perform_rate_limit_burn(
            address="0xPowerUser",
            excess_contracts=5
        )

        self.assertTrue(success)
        self.assertEqual(result["amount"], 0.5)  # 5 * 0.1 = 0.5
        self.assertEqual(result["reason"], "RateLimitExcess")


if __name__ == '__main__':
    unittest.main()
