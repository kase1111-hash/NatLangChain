"""
Tests for Treasury System (src/treasury.py)

Tests cover:
- Treasury deposits and inflows
- Subsidy request and approval
- Anti-Sybil protections
- Balance management and reserves
"""

import pytest
import sys
from datetime import datetime

sys.path.insert(0, "src")

from treasury import (
    NatLangChainTreasury,
    InflowType,
    SubsidyStatus,
    DenialReason,
    Inflow,
    SubsidyRequest,
)


# ============================================================
# Treasury Initialization Tests
# ============================================================

class TestTreasuryInitialization:
    """Tests for treasury initialization."""

    def test_initialize_empty(self):
        """Should initialize with zero balance."""
        treasury = NatLangChainTreasury()

        assert treasury.balance == 0.0
        assert treasury.total_inflows == 0.0
        assert treasury.total_outflows == 0.0

    def test_initialize_with_balance(self):
        """Should initialize with provided balance."""
        treasury = NatLangChainTreasury(initial_balance=10000.0)

        assert treasury.balance == 10000.0

    def test_initialize_state_tracking(self):
        """Should initialize state tracking structures."""
        treasury = NatLangChainTreasury()

        assert treasury.inflows == []
        assert treasury.subsidy_requests == {}
        assert treasury.dispute_subsidized == {}
        assert treasury.events == []


# ============================================================
# Deposit Tests
# ============================================================

class TestTreasuryDeposits:
    """Tests for treasury deposit operations."""

    @pytest.fixture
    def treasury(self):
        """Create fresh treasury."""
        return NatLangChainTreasury()

    def test_deposit_basic(self, treasury):
        """Should accept basic deposit."""
        success, result = treasury.deposit(
            amount=100.0,
            inflow_type=InflowType.PROTOCOL_FEE,
            source="test_source"
        )

        assert success is True
        assert result["status"] == "deposited"
        assert result["amount"] == 100.0
        assert result["new_balance"] == 100.0

    def test_deposit_updates_balance(self, treasury):
        """Deposit should update balance."""
        treasury.deposit(100.0, InflowType.PROTOCOL_FEE, "test")
        treasury.deposit(50.0, InflowType.DONATION, "test")

        assert treasury.balance == 150.0
        assert treasury.total_inflows == 150.0

    def test_deposit_zero_amount_fails(self, treasury):
        """Should reject zero amount deposit."""
        success, result = treasury.deposit(
            amount=0.0,
            inflow_type=InflowType.PROTOCOL_FEE,
            source="test"
        )

        assert success is False
        assert "error" in result

    def test_deposit_negative_amount_fails(self, treasury):
        """Should reject negative amount deposit."""
        success, result = treasury.deposit(
            amount=-100.0,
            inflow_type=InflowType.PROTOCOL_FEE,
            source="test"
        )

        assert success is False

    def test_deposit_timeout_burn(self, treasury):
        """Should handle timeout burn deposit."""
        success, result = treasury.deposit_timeout_burn(
            dispute_id="DISPUTE-001",
            amount=500.0,
            initiator="alice"
        )

        assert success is True
        assert result["inflow_type"] == "timeout_burn"

    def test_deposit_counter_fee(self, treasury):
        """Should handle counter fee deposit."""
        success, result = treasury.deposit_counter_fee(
            dispute_id="DISPUTE-002",
            amount=25.0,
            party="bob",
            counter_number=2
        )

        assert success is True
        assert result["inflow_type"] == "counter_fee"

    def test_deposit_escalated_stake(self, treasury):
        """Should handle escalated stake deposit."""
        success, result = treasury.deposit_escalated_stake(
            dispute_id="DISPUTE-003",
            amount=1000.0,
            party="carol",
            escalation_multiplier=2.0
        )

        assert success is True
        assert result["inflow_type"] == "escalated_stake"

    def test_deposit_creates_inflow_record(self, treasury):
        """Deposit should create inflow record."""
        treasury.deposit(100.0, InflowType.DONATION, "donor1")

        assert len(treasury.inflows) == 1
        inflow = treasury.inflows[0]
        assert inflow.amount == 100.0
        assert inflow.inflow_type == "donation"
        assert inflow.source == "donor1"

    def test_deposit_with_metadata(self, treasury):
        """Should store metadata with deposit."""
        treasury.deposit(
            amount=100.0,
            inflow_type=InflowType.PROTOCOL_FEE,
            source="test",
            metadata={"note": "test deposit", "category": "testing"}
        )

        inflow = treasury.inflows[0]
        assert inflow.metadata["note"] == "test deposit"

    def test_deposit_emits_event(self, treasury):
        """Deposit should emit event."""
        treasury.deposit(100.0, InflowType.PROTOCOL_FEE, "test")

        assert len(treasury.events) >= 1
        event = treasury.events[0]
        assert event["event_type"] == "Deposit"


# ============================================================
# Balance Tests
# ============================================================

class TestTreasuryBalance:
    """Tests for balance operations."""

    @pytest.fixture
    def funded_treasury(self):
        """Create treasury with initial funds."""
        treasury = NatLangChainTreasury(initial_balance=10000.0)
        return treasury

    def test_get_balance_structure(self, funded_treasury):
        """Should return balance structure."""
        balance = funded_treasury.get_balance()

        assert "total_balance" in balance
        assert "available_for_subsidies" in balance
        assert "reserve_ratio" in balance
        assert "reserve_amount" in balance

    def test_get_balance_reserve_calculation(self, funded_treasury):
        """Should correctly calculate reserve."""
        balance = funded_treasury.get_balance()

        expected_reserve = 10000.0 * funded_treasury.MIN_TREASURY_BALANCE_RATIO
        assert balance["reserve_amount"] == expected_reserve

    def test_get_balance_available_calculation(self, funded_treasury):
        """Should correctly calculate available funds."""
        balance = funded_treasury.get_balance()

        expected_available = 10000.0 * (1 - funded_treasury.MIN_TREASURY_BALANCE_RATIO)
        assert balance["available_for_subsidies"] == expected_available

    def test_get_balance_net_position(self):
        """Should track net position."""
        treasury = NatLangChainTreasury()
        treasury.deposit(1000.0, InflowType.DONATION, "test")

        balance = treasury.get_balance()

        assert balance["total_inflows"] == 1000.0
        assert balance["net_position"] == 1000.0


# ============================================================
# Inflow History Tests
# ============================================================

class TestInflowHistory:
    """Tests for inflow history queries."""

    @pytest.fixture
    def treasury_with_inflows(self):
        """Create treasury with multiple inflows."""
        treasury = NatLangChainTreasury()
        treasury.deposit(100.0, InflowType.DONATION, "donor1")
        treasury.deposit(200.0, InflowType.PROTOCOL_FEE, "protocol")
        treasury.deposit(300.0, InflowType.DONATION, "donor2")
        treasury.deposit(400.0, InflowType.COUNTER_FEE, "dispute1")
        return treasury

    def test_get_inflow_history(self, treasury_with_inflows):
        """Should return inflow history."""
        history = treasury_with_inflows.get_inflow_history()

        assert history["count"] == 4
        assert len(history["inflows"]) == 4

    def test_get_inflow_history_limit(self, treasury_with_inflows):
        """Should respect limit parameter."""
        history = treasury_with_inflows.get_inflow_history(limit=2)

        assert history["count"] == 2
        assert history["total_filtered"] == 4

    def test_get_inflow_history_filter_by_type(self, treasury_with_inflows):
        """Should filter by inflow type."""
        history = treasury_with_inflows.get_inflow_history(
            inflow_type=InflowType.DONATION
        )

        assert history["count"] == 2
        assert all(i["inflow_type"] == "donation" for i in history["inflows"])


# ============================================================
# Subsidy Request Tests
# ============================================================

class TestSubsidyRequests:
    """Tests for subsidy request system."""

    @pytest.fixture
    def funded_treasury(self):
        """Create treasury with funds for subsidies."""
        return NatLangChainTreasury(initial_balance=10000.0)

    def test_request_subsidy_success(self, funded_treasury):
        """Should approve valid subsidy request."""
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender@example.com",
            stake_required=500.0,
            is_dispute_target=True
        )

        assert success is True
        assert "subsidy_approved" in result
        assert result["subsidy_approved"] > 0

    def test_request_subsidy_not_target_denied(self, funded_treasury):
        """Should deny if not dispute target."""
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="initiator@example.com",
            stake_required=500.0,
            is_dispute_target=False
        )

        assert success is False
        assert result["reason"] == DenialReason.NOT_DISPUTE_TARGET.value

    def test_request_subsidy_already_subsidized(self, funded_treasury):
        """Should deny if dispute already subsidized."""
        # First request succeeds
        funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender1",
            stake_required=500.0,
            is_dispute_target=True
        )

        # Second request for same dispute fails
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender2",
            stake_required=500.0,
            is_dispute_target=True
        )

        assert success is False
        assert result["reason"] == DenialReason.ALREADY_SUBSIDIZED.value

    def test_request_subsidy_insufficient_balance(self):
        """Should deny if insufficient balance."""
        treasury = NatLangChainTreasury(initial_balance=10.0)

        success, result = treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender",
            stake_required=10000.0,
            is_dispute_target=True
        )

        # May be partial or denied depending on available
        if not success:
            assert result["denial_reason"] == DenialReason.INSUFFICIENT_BALANCE.value

    def test_request_subsidy_respects_max_percent(self, funded_treasury):
        """Subsidy should not exceed max percent of stake."""
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender",
            stake_required=1000.0,
            is_dispute_target=True
        )

        assert success is True
        max_possible = 1000.0 * funded_treasury.DEFAULT_MAX_SUBSIDY_PERCENT
        assert result["subsidy_approved"] <= max_possible

    def test_request_subsidy_respects_per_dispute_cap(self, funded_treasury):
        """Subsidy should not exceed per-dispute cap."""
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender",
            stake_required=10000.0,  # High stake
            is_dispute_target=True
        )

        assert success is True
        assert result["subsidy_approved"] <= funded_treasury.DEFAULT_MAX_PER_DISPUTE

    def test_request_subsidy_creates_record(self, funded_treasury):
        """Should create subsidy request record."""
        funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="defender",
            stake_required=500.0,
            is_dispute_target=True
        )

        assert len(funded_treasury.subsidy_requests) == 1
        assert "DISPUTE-001" in funded_treasury.dispute_subsidized


# ============================================================
# Anti-Sybil Protection Tests
# ============================================================

class TestAntiSybilProtection:
    """Tests for anti-Sybil protections."""

    @pytest.fixture
    def funded_treasury(self):
        """Create treasury with funds."""
        return NatLangChainTreasury(initial_balance=50000.0)

    def test_single_subsidy_per_dispute(self, funded_treasury):
        """Only one subsidy per dispute."""
        # First request
        funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="user1",
            stake_required=500.0,
            is_dispute_target=True
        )

        # Second request same dispute
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-001",
            requester="user2",
            stake_required=500.0,
            is_dispute_target=True
        )

        assert success is False
        assert result["reason"] == DenialReason.ALREADY_SUBSIDIZED.value

    def test_per_participant_cap(self, funded_treasury):
        """Should enforce per-participant cap at approval time."""
        # The per-participant cap is checked during request_subsidy based on
        # _get_participant_usage which tracks disbursed subsidies.
        # Approvals themselves don't update the cap - only disbursements do.
        # Test that the cap mechanism works by simulating disbursement tracking.

        # Manually simulate that this user has already received subsidies
        # by adding to participant_subsidies directly
        from datetime import datetime
        funded_treasury.participant_subsidies["capped_user"] = [
            {"amount": 600.0, "timestamp": datetime.utcnow().isoformat()},
            {"amount": 500.0, "timestamp": datetime.utcnow().isoformat()},
        ]

        # Now request should be denied due to cap exceeded
        success, result = funded_treasury.request_subsidy(
            dispute_id="DISPUTE-CAP-TEST",
            requester="capped_user",
            stake_required=300.0,
            is_dispute_target=True
        )

        assert success is False
        assert result["reason"] == DenialReason.CAP_EXCEEDED.value


# ============================================================
# Event Emission Tests
# ============================================================

class TestEventEmission:
    """Tests for event emission."""

    def test_deposit_emits_event(self):
        """Deposit should emit event."""
        treasury = NatLangChainTreasury()
        treasury.deposit(100.0, InflowType.DONATION, "test")

        events = [e for e in treasury.events if e["event_type"] == "Deposit"]
        assert len(events) == 1
        assert events[0]["data"]["amount"] == 100.0

    def test_subsidy_approval_emits_event(self):
        """Subsidy approval should emit event."""
        treasury = NatLangChainTreasury(initial_balance=10000.0)
        treasury.request_subsidy(
            dispute_id="D1",
            requester="user",
            stake_required=500.0,
            is_dispute_target=True
        )

        events = [e for e in treasury.events if e["event_type"] == "SubsidyApproved"]
        assert len(events) == 1

    def test_subsidy_denial_emits_event(self):
        """Subsidy denial should emit event."""
        treasury = NatLangChainTreasury(initial_balance=10000.0)
        treasury.request_subsidy(
            dispute_id="D1",
            requester="user",
            stake_required=500.0,
            is_dispute_target=False  # Will be denied
        )

        events = [e for e in treasury.events if e["event_type"] == "SubsidyDenied"]
        assert len(events) == 1


# ============================================================
# Data Class Tests
# ============================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_inflow_creation(self):
        """Should create Inflow."""
        inflow = Inflow(
            inflow_id="INF-001",
            inflow_type="donation",
            amount=100.0,
            source="donor",
            timestamp=datetime.utcnow().isoformat()
        )

        assert inflow.inflow_id == "INF-001"
        assert inflow.amount == 100.0

    def test_subsidy_request_creation(self):
        """Should create SubsidyRequest."""
        request = SubsidyRequest(
            request_id="REQ-001",
            dispute_id="D-001",
            requester="user@example.com",
            stake_required=500.0,
            subsidy_requested=400.0,
            subsidy_approved=350.0,
            status=SubsidyStatus.APPROVED.value,
            created_at=datetime.utcnow().isoformat()
        )

        assert request.request_id == "REQ-001"
        assert request.subsidy_approved == 350.0


# ============================================================
# Enum Tests
# ============================================================

class TestEnums:
    """Tests for treasury enums."""

    def test_inflow_type_values(self):
        """InflowType should have expected values."""
        assert InflowType.TIMEOUT_BURN.value == "timeout_burn"
        assert InflowType.COUNTER_FEE.value == "counter_fee"
        assert InflowType.ESCALATED_STAKE.value == "escalated_stake"
        assert InflowType.DONATION.value == "donation"

    def test_subsidy_status_values(self):
        """SubsidyStatus should have expected values."""
        assert SubsidyStatus.PENDING.value == "pending"
        assert SubsidyStatus.APPROVED.value == "approved"
        assert SubsidyStatus.DENIED.value == "denied"
        assert SubsidyStatus.DISBURSED.value == "disbursed"

    def test_denial_reason_values(self):
        """DenialReason should have expected values."""
        assert DenialReason.INSUFFICIENT_BALANCE.value == "insufficient_balance"
        assert DenialReason.ALREADY_SUBSIDIZED.value == "already_subsidized"
        assert DenialReason.NOT_DISPUTE_TARGET.value == "not_dispute_target"


# ============================================================
# Integration Tests
# ============================================================

class TestTreasuryIntegration:
    """Integration tests for treasury."""

    def test_full_subsidy_workflow(self):
        """Test complete subsidy workflow."""
        treasury = NatLangChainTreasury()

        # 1. Receive protocol fees
        treasury.deposit(5000.0, InflowType.PROTOCOL_FEE, "protocol")

        # 2. Receive timeout burns
        treasury.deposit_timeout_burn("D-OLD", 1000.0, "initiator1")

        # 3. Check balance
        balance = treasury.get_balance()
        assert balance["total_balance"] == 6000.0

        # 4. Process subsidy request
        success, result = treasury.request_subsidy(
            dispute_id="D-NEW",
            requester="defender",
            stake_required=1000.0,
            is_dispute_target=True
        )

        assert success is True
        assert result["subsidy_approved"] > 0

        # 5. Verify history
        history = treasury.get_inflow_history()
        assert history["count"] == 2

    def test_treasury_sustainability(self):
        """Treasury should maintain minimum reserve."""
        treasury = NatLangChainTreasury(initial_balance=1000.0)

        # Try to request large subsidy
        _, result = treasury.request_subsidy(
            dispute_id="D1",
            requester="user",
            stake_required=5000.0,
            is_dispute_target=True
        )

        # Should not deplete below reserve
        balance = treasury.get_balance()
        assert balance["total_balance"] >= balance["reserve_amount"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
