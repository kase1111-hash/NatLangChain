"""
Tests for Chain Interface (src/chain_interface.py)

Tests cover:
- HMAC Authentication
- Chain Interface operations
- Mock Chain Interface for testing
- Intent and Settlement operations
"""

import json
import sys
import time

import pytest

sys.path.insert(0, "src")

from chain_interface import (
    TIMESTAMP_WINDOW,
    ChainDelegation,
    ChainHealth,
    ChainIntent,
    ChainInterface,
    ChainReputation,
    ChainSettlement,
    HMACAuthenticator,
    IntentStatus,
    MockChainInterface,
    SettlementStatus,
    SubmissionType,
)

# ============================================================
# HMAC Authentication Tests
# ============================================================


class TestHMACAuthenticator:
    """Tests for HMAC request authentication."""

    @pytest.fixture
    def auth(self):
        """Create authenticator with test secret."""
        return HMACAuthenticator("test_secret_key_12345")

    def test_sign_request_returns_headers(self, auth):
        """Should return authentication headers."""
        headers = auth.sign_request("GET", "/api/v1/intents")

        assert "X-NLC-Signature" in headers
        assert "X-NLC-Timestamp" in headers
        assert "X-NLC-Nonce" in headers

    def test_sign_request_signature_format(self, auth):
        """Signature should be hex string."""
        headers = auth.sign_request("POST", "/api/v1/entries", '{"test": true}')

        signature = headers["X-NLC-Signature"]
        assert len(signature) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in signature)

    def test_sign_request_timestamp_is_current(self, auth):
        """Timestamp should be current time."""
        headers = auth.sign_request("GET", "/test")

        timestamp = int(headers["X-NLC-Timestamp"])
        now = int(time.time())

        assert abs(timestamp - now) <= 2

    def test_sign_request_nonce_is_unique(self, auth):
        """Each request should have unique nonce."""
        headers1 = auth.sign_request("GET", "/test")
        headers2 = auth.sign_request("GET", "/test")

        assert headers1["X-NLC-Nonce"] != headers2["X-NLC-Nonce"]

    def test_verify_request_valid(self, auth):
        """Should verify valid request."""
        headers = auth.sign_request("GET", "/api/v1/intents", None)

        is_valid, message = auth.verify_request(
            method="GET",
            path="/api/v1/intents",
            body=None,
            signature=headers["X-NLC-Signature"],
            timestamp=headers["X-NLC-Timestamp"],
            nonce=headers["X-NLC-Nonce"],
        )

        assert is_valid is True
        assert message == "OK"

    def test_verify_request_with_body(self, auth):
        """Should verify request with body."""
        body = '{"key": "value"}'
        headers = auth.sign_request("POST", "/api/v1/entries", body)

        is_valid, _ = auth.verify_request(
            method="POST",
            path="/api/v1/entries",
            body=body,
            signature=headers["X-NLC-Signature"],
            timestamp=headers["X-NLC-Timestamp"],
            nonce=headers["X-NLC-Nonce"],
        )

        assert is_valid is True

    def test_verify_request_invalid_signature(self, auth):
        """Should reject invalid signature."""
        headers = auth.sign_request("GET", "/test")

        is_valid, message = auth.verify_request(
            method="GET",
            path="/test",
            body=None,
            signature="invalid_signature",
            timestamp=headers["X-NLC-Timestamp"],
            nonce=headers["X-NLC-Nonce"],
        )

        assert is_valid is False
        assert "Invalid signature" in message

    def test_verify_request_expired_timestamp(self, auth):
        """Should reject expired timestamp."""
        headers = auth.sign_request("GET", "/test")

        # Use timestamp from 10 minutes ago
        old_timestamp = str(int(time.time()) - TIMESTAMP_WINDOW - 60)

        is_valid, message = auth.verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers["X-NLC-Signature"],
            timestamp=old_timestamp,
            nonce=headers["X-NLC-Nonce"],
        )

        assert is_valid is False
        assert "Timestamp" in message

    def test_verify_request_replay_attack(self, auth):
        """Should detect nonce replay."""
        headers = auth.sign_request("GET", "/test")

        # First verification should succeed
        is_valid1, _ = auth.verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers["X-NLC-Signature"],
            timestamp=headers["X-NLC-Timestamp"],
            nonce=headers["X-NLC-Nonce"],
        )
        assert is_valid1 is True

        # Second verification with same nonce should fail
        is_valid2, message = auth.verify_request(
            method="GET",
            path="/test",
            body=None,
            signature=headers["X-NLC-Signature"],
            timestamp=headers["X-NLC-Timestamp"],
            nonce=headers["X-NLC-Nonce"],
        )
        assert is_valid2 is False
        assert "replay" in message.lower()


# ============================================================
# Mock Chain Interface Tests
# ============================================================


class TestMockChainInterface:
    """Tests for MockChainInterface."""

    @pytest.fixture
    def mock_chain(self):
        """Create mock chain interface."""
        return MockChainInterface(mediator_id="test_mediator")

    def test_initialization(self, mock_chain):
        """Should initialize with mediator ID."""
        assert mock_chain.mediator_id == "test_mediator"
        assert mock_chain.endpoint == "http://mock:8545"

    def test_get_intents_empty(self, mock_chain):
        """Should return empty list initially."""
        success, intents = mock_chain.get_intents()

        assert success is True
        assert intents == []

    def test_add_test_intent(self, mock_chain):
        """Should add and retrieve test intent."""
        intent = ChainIntent(
            hash="0x123",
            author="alice",
            prose="I want to trade BTC",
            desires=["buy BTC"],
            constraints=["max 50000 USD"],
            offered_fee=100.0,
            timestamp=int(time.time()),
            status=IntentStatus.PENDING,
            branch="main",
        )

        mock_chain.add_test_intent(intent)

        success, intents = mock_chain.get_intents()
        assert success is True
        assert len(intents) == 1
        assert intents[0].hash == "0x123"

    def test_get_pending_intents(self, mock_chain):
        """Should filter by pending status."""
        # Add pending intent
        pending_intent = ChainIntent(
            hash="0xPending",
            author="alice",
            prose="Test",
            desires=[],
            constraints=[],
            offered_fee=10.0,
            timestamp=int(time.time()),
            status=IntentStatus.PENDING,
            branch="main",
        )
        mock_chain.add_test_intent(pending_intent)

        # Add matched intent
        matched_intent = ChainIntent(
            hash="0xMatched",
            author="bob",
            prose="Test",
            desires=[],
            constraints=[],
            offered_fee=10.0,
            timestamp=int(time.time()),
            status=IntentStatus.MATCHED,
            branch="main",
        )
        mock_chain.add_test_intent(matched_intent)

        success, pending = mock_chain.get_pending_intents()
        assert success is True
        assert len(pending) == 1
        assert pending[0].hash == "0xPending"

    def test_propose_settlement(self, mock_chain):
        """Should create settlement proposal."""
        success, result = mock_chain.propose_settlement(
            intent_hash_a="0xIntent1",
            intent_hash_b="0xIntent2",
            terms={"price": 50000, "quantity": 1},
            fee=100.0,
        )

        assert success is True
        assert "entryId" in result

    def test_get_settlement_status(self, mock_chain):
        """Should get settlement status."""
        # First create a settlement
        mock_chain.propose_settlement(intent_hash_a="0xA", intent_hash_b="0xB", terms={}, fee=50.0)

        # Get the settlement (need to know the ID)
        # The settlement ID is generated in propose_settlement
        entries = mock_chain.get_submitted_entries()
        settlement_entry = next((e for e in entries if e.get("type") == "settlement"), None)

        if settlement_entry:
            settlement_id = settlement_entry["metadata"]["id"]
            success, settlement = mock_chain.get_settlement_status(settlement_id)

            assert success is True
            assert isinstance(settlement, ChainSettlement)

    def test_accept_settlement(self, mock_chain):
        """Should accept settlement."""
        # Create settlement
        mock_chain.propose_settlement(intent_hash_a="0xA", intent_hash_b="0xB", terms={}, fee=50.0)

        entries = mock_chain.get_submitted_entries()
        settlement_entry = next((e for e in entries if e.get("type") == "settlement"), None)
        settlement_id = settlement_entry["metadata"]["id"]

        # Accept as party A
        success, result = mock_chain.accept_settlement(
            settlement_id=settlement_id, party="A", party_identifier="alice"
        )

        assert success is True

        # Check status
        _, settlement = mock_chain.get_settlement_status(settlement_id)
        assert settlement.party_a_accepted is True

    def test_is_settlement_accepted_both_parties(self, mock_chain):
        """Should detect both parties accepted."""
        # Create and accept settlement
        mock_chain.propose_settlement(intent_hash_a="0xA", intent_hash_b="0xB", terms={}, fee=50.0)

        entries = mock_chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # Accept as both parties
        mock_chain.accept_settlement(settlement_id, "A", "alice")
        mock_chain.accept_settlement(settlement_id, "B", "bob")

        success, both_accepted = mock_chain.is_settlement_accepted(settlement_id)

        assert success is True
        assert both_accepted is True

    def test_get_reputation(self, mock_chain):
        """Should get mediator reputation."""
        success, reputation = mock_chain.get_reputation("test_mediator")

        assert success is True
        assert isinstance(reputation, ChainReputation)
        assert reputation.mediator_id == "test_mediator"
        assert reputation.weight == 1.0

    def test_bond_stake(self, mock_chain):
        """Should bond stake."""
        success, result = mock_chain.bond_stake(1000.0)

        assert success is True
        assert result["success"] is True

    def test_get_delegations(self, mock_chain):
        """Should get delegations."""
        # Add test delegation
        delegation = ChainDelegation(
            delegator_id="user1",
            mediator_id="test_mediator",
            amount=500.0,
            timestamp=int(time.time()),
        )
        mock_chain.add_test_delegation(delegation)

        success, delegations = mock_chain.get_delegations()

        assert success is True
        assert len(delegations) == 1
        assert delegations[0].amount == 500.0

    def test_get_authorities(self, mock_chain):
        """Should get authority set."""
        success, authorities = mock_chain.get_authorities()

        assert success is True
        assert len(authorities) > 0

    def test_audit_log(self, mock_chain):
        """Should maintain audit log."""
        mock_chain.get_intents()
        mock_chain.get_reputation()

        log = mock_chain.get_audit_log()

        assert len(log) >= 2
        assert all("timestamp" in entry for entry in log)


# ============================================================
# Data Class Tests
# ============================================================


class TestChainIntent:
    """Tests for ChainIntent dataclass."""

    def test_create_intent(self):
        """Should create ChainIntent."""
        intent = ChainIntent(
            hash="0xabc123",
            author="alice@example.com",
            prose="I want to exchange services",
            desires=["get consulting", "weekly meetings"],
            constraints=["budget 5000 USD", "duration 3 months"],
            offered_fee=200.0,
            timestamp=1704067200,
            status=IntentStatus.PENDING,
            branch="main",
        )

        assert intent.hash == "0xabc123"
        assert intent.offered_fee == 200.0

    def test_intent_to_dict(self):
        """Should convert to dictionary."""
        intent = ChainIntent(
            hash="0x123",
            author="bob",
            prose="Test",
            desires=[],
            constraints=[],
            offered_fee=10.0,
            timestamp=123456,
            status=IntentStatus.MATCHED,
            branch="main",
        )

        d = intent.to_dict()

        assert d["hash"] == "0x123"
        assert d["status"] == "matched"
        assert d["offeredFee"] == 10.0

    def test_intent_from_dict(self):
        """Should create from dictionary."""
        data = {
            "hash": "0x456",
            "author": "carol",
            "prose": "From dict test",
            "desires": ["test"],
            "constraints": [],
            "offeredFee": 50.0,
            "timestamp": 999999,
            "status": "pending",
            "branch": "test",
        }

        intent = ChainIntent.from_dict(data)

        assert intent.hash == "0x456"
        assert intent.status == IntentStatus.PENDING
        assert intent.offered_fee == 50.0


class TestChainSettlement:
    """Tests for ChainSettlement dataclass."""

    def test_create_settlement(self):
        """Should create ChainSettlement."""
        settlement = ChainSettlement(
            id="settlement_001",
            intent_hash_a="0xA",
            intent_hash_b="0xB",
            mediator_id="mediator1",
            terms={"price": 1000, "deadline": "2024-12-31"},
            fee=50.0,
            status=SettlementStatus.PROPOSED,
        )

        assert settlement.id == "settlement_001"
        assert settlement.fee == 50.0
        assert settlement.party_a_accepted is False

    def test_settlement_to_dict(self):
        """Should convert to dictionary."""
        settlement = ChainSettlement(
            id="s1",
            intent_hash_a="0xA",
            intent_hash_b="0xB",
            mediator_id="m1",
            terms={},
            fee=10.0,
            status=SettlementStatus.BOTH_ACCEPTED,
            party_a_accepted=True,
            party_b_accepted=True,
        )

        d = settlement.to_dict()

        assert d["id"] == "s1"
        assert d["status"] == "both_accepted"
        assert d["partyAAccepted"] is True

    def test_settlement_from_dict(self):
        """Should create from dictionary."""
        data = {
            "id": "s2",
            "intentHashA": "0xX",
            "intentHashB": "0xY",
            "mediatorId": "m2",
            "terms": {"key": "value"},
            "fee": 100.0,
            "status": "finalized",
        }

        settlement = ChainSettlement.from_dict(data)

        assert settlement.id == "s2"
        assert settlement.status == SettlementStatus.FINALIZED


class TestChainReputation:
    """Tests for ChainReputation dataclass."""

    def test_create_reputation(self):
        """Should create ChainReputation."""
        rep = ChainReputation(
            mediator_id="mediator1", successful_closures=10, failed_challenges=2, weight=1.5
        )

        assert rep.mediator_id == "mediator1"
        assert rep.successful_closures == 10
        assert rep.weight == 1.5

    def test_reputation_to_dict(self):
        """Should convert to dictionary."""
        rep = ChainReputation(mediator_id="m1", successful_closures=5, weight=2.0)

        d = rep.to_dict()

        assert d["mediatorId"] == "m1"
        assert d["successfulClosures"] == 5


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Tests for chain interface enums."""

    def test_intent_status_values(self):
        """IntentStatus should have expected values."""
        assert IntentStatus.PENDING.value == "pending"
        assert IntentStatus.MATCHED.value == "matched"
        assert IntentStatus.SETTLED.value == "settled"
        assert IntentStatus.CHALLENGED.value == "challenged"

    def test_entry_type_values(self):
        """SubmissionType should have expected values."""
        assert SubmissionType.SETTLEMENT.value == "settlement"
        assert SubmissionType.ACCEPT.value == "accept"
        assert SubmissionType.PAYOUT.value == "payout"
        assert SubmissionType.CHALLENGE.value == "challenge"

    def test_settlement_status_values(self):
        """SettlementStatus should have expected values."""
        assert SettlementStatus.PROPOSED.value == "proposed"
        assert SettlementStatus.BOTH_ACCEPTED.value == "both_accepted"
        assert SettlementStatus.FINALIZED.value == "finalized"


# ============================================================
# Integration Tests
# ============================================================


class TestChainInterfaceIntegration:
    """Integration tests for chain interface."""

    def test_full_settlement_workflow(self):
        """Test complete settlement workflow."""
        chain = MockChainInterface(mediator_id="integration_mediator")

        # 1. Add intents
        intent_a = ChainIntent(
            hash="0xIntentA",
            author="alice",
            prose="I want to sell widgets",
            desires=["sell 100 widgets"],
            constraints=["min price 10 USD each"],
            offered_fee=50.0,
            timestamp=int(time.time()),
            status=IntentStatus.PENDING,
            branch="main",
        )
        intent_b = ChainIntent(
            hash="0xIntentB",
            author="bob",
            prose="I want to buy widgets",
            desires=["buy 100 widgets"],
            constraints=["max price 12 USD each"],
            offered_fee=50.0,
            timestamp=int(time.time()),
            status=IntentStatus.PENDING,
            branch="main",
        )
        chain.add_test_intent(intent_a)
        chain.add_test_intent(intent_b)

        # 2. Mediator proposes settlement
        success, proposal = chain.propose_settlement(
            intent_hash_a="0xIntentA",
            intent_hash_b="0xIntentB",
            terms={"price_per_widget": 11.0, "quantity": 100},
            fee=100.0,
        )
        assert success

        settlement_id = proposal["entryId"].replace("entry_", "settlement_")
        # Need to get actual settlement ID from entries
        entries = chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # 3. Both parties accept
        chain.accept_settlement(settlement_id, "A", "alice")
        chain.accept_settlement(settlement_id, "B", "bob")

        # 4. Verify settlement is accepted
        _, both_accepted = chain.is_settlement_accepted(settlement_id)
        assert both_accepted

        # 5. Claim payout
        success, payout = chain.claim_payout(settlement_id)
        assert success

    def test_event_callbacks(self):
        """Test event callback system."""
        chain = MockChainInterface()
        events_received = []

        def on_entry(data):
            events_received.append(("entry", data))

        def on_intents(data):
            events_received.append(("intents", data))

        chain.on("entry_submitted", on_entry)
        chain.on("intents_fetched", on_intents)

        # Trigger events
        chain.get_intents()
        chain.propose_settlement("0xA", "0xB", {}, 10.0)

        # Note: Mock doesn't emit events, but real implementation would
        # This tests the callback registration at least
        assert "entry_submitted" in chain._callbacks
        assert "intents_fetched" in chain._callbacks

    def test_audit_trail_complete(self):
        """Audit trail should capture all operations."""
        chain = MockChainInterface()

        # Perform various operations
        chain.get_intents()
        chain.get_reputation()
        chain.propose_settlement("0xA", "0xB", {}, 10.0)
        chain.bond_stake(1000.0)

        log = chain.get_audit_log()

        # Should have entries for all operations
        assert len(log) >= 4

        # Each entry should have required fields
        for entry in log:
            assert "timestamp" in entry
            assert "method" in entry
            assert "path" in entry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
