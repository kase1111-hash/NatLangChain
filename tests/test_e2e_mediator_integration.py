"""
NatLangChain - End-to-End Mediator-Node Integration Tests
Comprehensive tests for the full negotiation flow with reputation scoring.

Tests the complete cycle:
1. Intent posting and fetching
2. Alignment detection
3. Settlement proposal
4. Party acceptance
5. Fee claim and payout
6. Reputation scoring updates

Uses MockChainInterface for unit testing and can optionally
connect to a real mediator-node for integration testing.
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from chain_interface import (
    ChainInterface,
    MockChainInterface,
    ChainIntent,
    ChainSettlement,
    ChainReputation,
    ChainDelegation,
    IntentStatus,
    EntryType,
    SettlementStatus,
    HMACAuthenticator,
    HMAC_HEADER,
    TIMESTAMP_HEADER,
    NONCE_HEADER
)

from mediator_reputation import (
    MediatorReputationManager,
    MediatorProfile,
    ReputationScores,
    SlashingOffense,
    MediatorStatus,
    MINIMUM_BOND,
    DEFAULT_BOND
)

from negotiation_engine import (
    AutomatedNegotiationEngine,
    NegotiationPhase,
    Intent,
    Offer,
    OfferType,
    ClauseType
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_chain():
    """Create a mock chain interface with test data."""
    interface = MockChainInterface(mediator_id="test_mediator_001")

    # Add test intents that can be aligned
    alice_intent = ChainIntent(
        hash="0xalice123",
        author="user_alice",
        prose="I am offering a high-performance Rust library for fluid dynamics simulation. "
              "400 hours of work. Looking for 500 NLC or equivalent compute time.",
        desires=["compensation", "open-source collaboration"],
        constraints=["attribution required", "legitimate research only"],
        offered_fee=5.0,
        timestamp=int(time.time()) - 3600,
        status=IntentStatus.PENDING,
        branch="Professional/Engineering"
    )

    bob_intent = ChainIntent(
        hash="0xbob456",
        author="user_bob",
        prose="We need a high-resolution ocean current simulation for climate research. "
              "Budget of 800 NLC. Must be fast, auditable, and documented.",
        desires=["performance", "documentation", "auditability"],
        constraints=["60 day deadline", "testing data required"],
        offered_fee=8.0,
        timestamp=int(time.time()) - 1800,
        status=IntentStatus.PENDING,
        branch="Research/Climate"
    )

    charlie_intent = ChainIntent(
        hash="0xcharlie789",
        author="user_charlie",
        prose="Seeking data visualization expert for interactive climate charts. "
              "Budget 300 NLC. Need D3.js or similar.",
        desires=["interactive visualization", "responsive design"],
        constraints=["mobile compatible", "accessibility required"],
        offered_fee=3.0,
        timestamp=int(time.time()) - 7200,
        status=IntentStatus.PENDING,
        branch="Professional/Design"
    )

    interface.add_test_intent(alice_intent)
    interface.add_test_intent(bob_intent)
    interface.add_test_intent(charlie_intent)

    return interface


@pytest.fixture
def reputation_manager():
    """Create a reputation manager with test mediators."""
    manager = MediatorReputationManager()

    # Register test mediators
    manager.register_mediator(
        "test_mediator_001",
        stake_amount=50000,
        supported_domains=["Engineering", "Research"],
        models_used=["claude-3"]
    )

    manager.register_mediator(
        "test_mediator_002",
        stake_amount=30000,
        supported_domains=["Design"],
        models_used=["gpt-4"]
    )

    return manager


@pytest.fixture
def negotiation_engine():
    """Create a negotiation engine (without API key for testing)."""
    return AutomatedNegotiationEngine(api_key=None)


# =============================================================================
# HMAC Authentication Tests
# =============================================================================

class TestHMACAuthentication:
    """Tests for HMAC request authentication."""

    def test_sign_request(self):
        """Test request signing generates valid headers."""
        auth = HMACAuthenticator("test_secret_key")

        headers = auth.sign_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "settlement"}'
        )

        assert HMAC_HEADER in headers
        assert TIMESTAMP_HEADER in headers
        assert NONCE_HEADER in headers
        assert len(headers[HMAC_HEADER]) == 64  # SHA256 hex
        assert len(headers[NONCE_HEADER]) == 32  # 16 bytes hex

    def test_verify_valid_request(self):
        """Test verification of valid request."""
        auth = HMACAuthenticator("test_secret_key")

        timestamp = int(time.time())
        body = '{"test": "data"}'

        headers = auth.sign_request(
            method="POST",
            path="/api/v1/test",
            body=body,
            timestamp=timestamp
        )

        is_valid, message = auth.verify_request(
            method="POST",
            path="/api/v1/test",
            body=body,
            signature=headers[HMAC_HEADER],
            timestamp=headers[TIMESTAMP_HEADER],
            nonce=headers[NONCE_HEADER]
        )

        assert is_valid
        assert message == "OK"

    def test_reject_expired_timestamp(self):
        """Test rejection of expired timestamp."""
        auth = HMACAuthenticator("test_secret_key")

        # Use timestamp from 10 minutes ago
        old_timestamp = int(time.time()) - 600

        headers = auth.sign_request(
            method="GET",
            path="/api/v1/test",
            timestamp=old_timestamp
        )

        is_valid, message = auth.verify_request(
            method="GET",
            path="/api/v1/test",
            body=None,
            signature=headers[HMAC_HEADER],
            timestamp=headers[TIMESTAMP_HEADER],
            nonce=headers[NONCE_HEADER]
        )

        assert not is_valid
        assert "window" in message.lower()

    def test_reject_replay_attack(self):
        """Test rejection of replayed requests."""
        auth = HMACAuthenticator("test_secret_key")

        headers = auth.sign_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "test"}'
        )

        # First request should succeed
        is_valid, _ = auth.verify_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "test"}',
            signature=headers[HMAC_HEADER],
            timestamp=headers[TIMESTAMP_HEADER],
            nonce=headers[NONCE_HEADER]
        )
        assert is_valid

        # Same nonce should be rejected
        is_valid, message = auth.verify_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "test"}',
            signature=headers[HMAC_HEADER],
            timestamp=headers[TIMESTAMP_HEADER],
            nonce=headers[NONCE_HEADER]
        )
        assert not is_valid
        assert "replay" in message.lower()

    def test_reject_invalid_signature(self):
        """Test rejection of tampered signature."""
        auth = HMACAuthenticator("test_secret_key")

        headers = auth.sign_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "test"}'
        )

        # Tamper with signature
        tampered_signature = headers[HMAC_HEADER][:-4] + "0000"

        is_valid, message = auth.verify_request(
            method="POST",
            path="/api/v1/entries",
            body='{"type": "test"}',
            signature=tampered_signature,
            timestamp=headers[TIMESTAMP_HEADER],
            nonce=headers[NONCE_HEADER]
        )

        assert not is_valid
        assert "signature" in message.lower()


# =============================================================================
# Chain Interface Tests
# =============================================================================

class TestChainInterface:
    """Tests for the chain interface."""

    def test_get_pending_intents(self, mock_chain):
        """Test fetching pending intents."""
        success, intents = mock_chain.get_pending_intents()

        assert success
        assert len(intents) == 3
        assert all(i.status == IntentStatus.PENDING for i in intents)

    def test_get_intents_with_filter(self, mock_chain):
        """Test fetching intents with status filter."""
        # All should be pending initially
        success, intents = mock_chain.get_intents(status=IntentStatus.PENDING)
        assert success
        assert len(intents) == 3

        # None should be matched
        success, intents = mock_chain.get_intents(status=IntentStatus.MATCHED)
        assert success
        assert len(intents) == 0

    def test_get_intents_with_limit(self, mock_chain):
        """Test fetching intents with limit."""
        success, intents = mock_chain.get_intents(limit=2)

        assert success
        assert len(intents) == 2

    def test_propose_settlement(self, mock_chain):
        """Test proposing a settlement."""
        success, result = mock_chain.propose_settlement(
            intent_hash_a="0xalice123",
            intent_hash_b="0xbob456",
            terms={
                "deliverable": "Rust fluid dynamics library",
                "compensation": 650,
                "timeline": "45 days",
                "attribution": True
            },
            fee=13.0
        )

        assert success
        assert "entryId" in result

        # Verify settlement was created
        entries = mock_chain.get_submitted_entries()
        assert len(entries) == 1
        assert entries[0]["type"] == "settlement"

    def test_settlement_acceptance_flow(self, mock_chain):
        """Test full settlement acceptance flow."""
        # 1. Propose settlement
        success, result = mock_chain.propose_settlement(
            intent_hash_a="0xalice123",
            intent_hash_b="0xbob456",
            terms={"amount": 500},
            fee=10.0
        )
        assert success

        # Get settlement ID from the entries
        entries = mock_chain.get_submitted_entries()
        settlement_metadata = entries[0].get("metadata", {})
        settlement_id = settlement_metadata.get("id")
        assert settlement_id is not None

        # 2. Check initial status
        success, settlement = mock_chain.get_settlement_status(settlement_id)
        assert success
        assert not settlement.party_a_accepted
        assert not settlement.party_b_accepted

        # 3. Party A accepts
        success, _ = mock_chain.accept_settlement(
            settlement_id=settlement_id,
            party="A",
            party_identifier="user_alice"
        )
        assert success

        # 4. Verify partial acceptance
        success, settlement = mock_chain.get_settlement_status(settlement_id)
        assert success
        assert settlement.party_a_accepted
        assert not settlement.party_b_accepted

        # 5. Party B accepts
        success, _ = mock_chain.accept_settlement(
            settlement_id=settlement_id,
            party="B",
            party_identifier="user_bob"
        )
        assert success

        # 6. Verify full acceptance
        success, both_accepted = mock_chain.is_settlement_accepted(settlement_id)
        assert success
        assert both_accepted

    def test_claim_payout(self, mock_chain):
        """Test claiming payout for accepted settlement."""
        # Create and accept settlement
        mock_chain.propose_settlement(
            intent_hash_a="0xalice123",
            intent_hash_b="0xbob456",
            terms={"amount": 500},
            fee=10.0
        )

        entries = mock_chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # Accept from both parties
        mock_chain.set_test_settlement_accepted(
            settlement_id,
            party_a=True,
            party_b=True
        )

        # Claim payout
        success, result = mock_chain.claim_payout(settlement_id)
        assert success

        # Verify payout entry was created
        entries = mock_chain.get_submitted_entries()
        payout_entries = [e for e in entries if e.get("type") == "payout"]
        assert len(payout_entries) == 1

    def test_get_reputation(self, mock_chain):
        """Test getting mediator reputation."""
        success, reputation = mock_chain.get_reputation("test_mediator_001")

        assert success
        assert reputation.mediator_id == "test_mediator_001"
        assert reputation.weight >= 1.0

    def test_update_reputation(self, mock_chain):
        """Test updating mediator reputation."""
        new_reputation = ChainReputation(
            mediator_id="test_mediator_001",
            successful_closures=5,
            failed_challenges=1,
            weight=1.5
        )

        success, _ = mock_chain.update_reputation(
            "test_mediator_001",
            new_reputation
        )
        assert success

        # Verify update
        success, reputation = mock_chain.get_reputation("test_mediator_001")
        assert success
        assert reputation.successful_closures == 5
        assert reputation.weight == 1.5

    def test_get_delegations(self, mock_chain):
        """Test getting delegations."""
        # Add test delegation
        delegation = ChainDelegation(
            delegator_id="user_dave",
            mediator_id="test_mediator_001",
            amount=1000,
            timestamp=int(time.time())
        )
        mock_chain.add_test_delegation(delegation)

        success, delegations = mock_chain.get_delegations("test_mediator_001")
        assert success
        assert len(delegations) == 1
        assert delegations[0].amount == 1000

    def test_bond_stake(self, mock_chain):
        """Test bonding stake."""
        success, result = mock_chain.bond_stake(50000)
        assert success
        assert result.get("success")

    def test_get_authorities(self, mock_chain):
        """Test getting authority set."""
        success, authorities = mock_chain.get_authorities()
        assert success
        assert len(authorities) >= 1

    def test_audit_log(self, mock_chain):
        """Test audit logging."""
        mock_chain.get_pending_intents()
        mock_chain.get_reputation("test")
        mock_chain.bond_stake(1000)

        log = mock_chain.get_audit_log()
        assert len(log) >= 3
        assert all("timestamp" in entry for entry in log)
        assert all("method" in entry for entry in log)


# =============================================================================
# Full Negotiation Flow Tests
# =============================================================================

class TestFullNegotiationFlow:
    """Tests for the complete negotiation and mediation flow."""

    def test_complete_mediation_cycle(self, mock_chain, reputation_manager):
        """Test the complete mediation cycle from intent to payout."""
        mediator_id = "test_mediator_001"

        # Step 1: Fetch pending intents
        success, intents = mock_chain.get_pending_intents()
        assert success
        assert len(intents) >= 2

        # Step 2: Find alignable intents (Alice offers, Bob needs)
        alice_intent = next(i for i in intents if i.author == "user_alice")
        bob_intent = next(i for i in intents if i.author == "user_bob")

        # Verify these can be aligned
        # Alice: offering fluid dynamics library
        # Bob: needs ocean simulation for climate research
        assert "fluid" in alice_intent.prose.lower()
        assert "ocean" in bob_intent.prose.lower() or "simulation" in bob_intent.prose.lower()

        # Step 3: Propose settlement
        settlement_terms = {
            "deliverable": "High-performance Rust fluid dynamics library",
            "scope": "Ocean current simulation for climate research",
            "compensation": 650,  # Midpoint between Alice's 500 and Bob's 800
            "timeline_days": 45,
            "attribution_required": True,
            "documentation_required": True,
            "testing_data_provided": True
        }

        total_fee = alice_intent.offered_fee + bob_intent.offered_fee
        success, result = mock_chain.propose_settlement(
            intent_hash_a=alice_intent.hash,
            intent_hash_b=bob_intent.hash,
            terms=settlement_terms,
            fee=total_fee
        )
        assert success

        # Get settlement ID
        entries = mock_chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # Step 4: Verify settlement is proposed
        success, settlement = mock_chain.get_settlement_status(settlement_id)
        assert success
        assert settlement.status == SettlementStatus.PROPOSED

        # Step 5: Simulate party acceptances
        mock_chain.accept_settlement(settlement_id, "A", "user_alice")
        mock_chain.accept_settlement(settlement_id, "B", "user_bob")

        # Step 6: Verify both accepted
        success, both_accepted = mock_chain.is_settlement_accepted(settlement_id)
        assert success
        assert both_accepted

        # Step 7: Claim payout
        success, payout_result = mock_chain.claim_payout(settlement_id)
        assert success

        # Step 8: Update mediator reputation
        profile = reputation_manager.get_mediator(mediator_id)
        assert profile is not None

        # Record successful outcome
        result = reputation_manager.record_proposal_outcome(
            mediator_id=mediator_id,
            accepted=True,
            semantic_drift_score=0.1,  # Low drift = high accuracy
            latency_seconds=30,
            coercion_detected=False
        )

        assert result["new_cts"] > profile.composite_trust_score or result["new_cts"] == profile.composite_trust_score
        assert result["accepted_count"] >= 1

        # Step 9: Update chain reputation
        chain_reputation = ChainReputation(
            mediator_id=mediator_id,
            successful_closures=profile.accepted_count,
            weight=profile.composite_trust_score
        )

        success, _ = mock_chain.update_reputation(mediator_id, chain_reputation)
        assert success

    def test_mediation_with_challenge(self, mock_chain, reputation_manager):
        """Test mediation flow with a challenge."""
        mediator_id = "test_mediator_001"

        # Propose settlement
        mock_chain.propose_settlement(
            intent_hash_a="0xalice123",
            intent_hash_b="0xbob456",
            terms={"amount": 500},
            fee=10.0
        )

        entries = mock_chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # Simulate challenge before acceptance
        # In a real scenario, this would be a separate challenge entry
        challenge_entry = {
            "type": "challenge",
            "settlementId": settlement_id,
            "challenger": "user_bob",
            "reason": "Terms do not match stated constraints",
            "evidence": {"constraint_violated": "60 day deadline not addressed"}
        }

        # Record the challenge outcome (mediator lost)
        result = reputation_manager.record_appeal_outcome(
            mediator_id=mediator_id,
            appeal_survived=False
        )

        # Verify reputation decreased
        profile = reputation_manager.get_mediator(mediator_id)
        assert profile.appeal_losses == 1
        assert profile.scores.appeal_survival < 1.0

    def test_multiple_mediators_competing(self, mock_chain, reputation_manager):
        """Test ranking and sampling of multiple mediators."""
        # Register additional mediators
        reputation_manager.register_mediator(
            "mediator_high_rep",
            stake_amount=100000,
            supported_domains=["Engineering", "Research"],  # Multiple domains for diversity bonus
            models_used=["claude-3", "gpt-4"]  # Multi-model for diversity bonus
        )

        reputation_manager.register_mediator(
            "mediator_low_rep",
            stake_amount=15000,
            supported_domains=["General"]
        )

        # Update reputations to create differentiation
        # High rep: fewer proposals but high quality (less volume penalty)
        for _ in range(3):
            reputation_manager.record_proposal_outcome(
                "mediator_high_rep",
                accepted=True,
                semantic_drift_score=0.02,  # Very low drift = high accuracy
                latency_seconds=15  # Fast response
            )

        # Low rep: more proposals but poor quality
        for _ in range(5):
            reputation_manager.record_proposal_outcome(
                "mediator_low_rep",
                accepted=True,
                semantic_drift_score=0.4  # High drift = low accuracy
            )
            reputation_manager.record_proposal_outcome(
                "mediator_low_rep",
                accepted=False
            )

        # Get rankings
        mediator_ids = ["test_mediator_001", "mediator_high_rep", "mediator_low_rep"]
        rankings = reputation_manager.get_proposal_ranking(mediator_ids)

        assert len(rankings) == 3

        # Verify ranking considers CTS
        high_rep_profile = reputation_manager.get_mediator("mediator_high_rep")
        low_rep_profile = reputation_manager.get_mediator("mediator_low_rep")
        assert high_rep_profile.composite_trust_score > low_rep_profile.composite_trust_score

        # High rep mediator should have better CTS due to:
        # 1. 100% acceptance rate vs mixed
        # 2. Higher semantic accuracy
        # 3. Better latency discipline
        # 4. Diversity bonus from multiple domains and models

        # Verify the rankings structure
        for ranking in rankings:
            assert "mediator_id" in ranking
            assert "final_score" in ranking
            assert "cts" in ranking

        # Sample by trust
        samples = reputation_manager.sample_proposals_by_trust(
            mediator_ids,
            sample_size=2
        )

        assert len(samples) == 2

    def test_slashing_for_semantic_manipulation(self, mock_chain, reputation_manager):
        """Test slashing when semantic manipulation is detected."""
        mediator_id = "test_mediator_001"

        profile_before = reputation_manager.get_mediator(mediator_id)
        bond_before = profile_before.bond.amount

        # Slash for semantic manipulation
        event = reputation_manager.slash(
            mediator_id=mediator_id,
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=0.7,
            evidence={"drift_score": 0.85, "threshold": 0.3}
        )

        assert event is not None
        assert event.offense == SlashingOffense.SEMANTIC_MANIPULATION
        assert event.amount_slashed > 0

        profile_after = reputation_manager.get_mediator(mediator_id)
        assert profile_after.bond.amount < bond_before
        assert profile_after.status == MediatorStatus.COOLDOWN

        # Update chain with slashing
        chain_reputation = ChainReputation(
            mediator_id=mediator_id,
            successful_closures=profile_after.accepted_count,
            failed_challenges=profile_after.appeal_losses,
            weight=profile_after.composite_trust_score
        )

        mock_chain.update_reputation(mediator_id, chain_reputation)


# =============================================================================
# Reputation Scoring Tests
# =============================================================================

class TestReputationScoring:
    """Tests for reputation scoring and metrics."""

    def test_cts_calculation(self, reputation_manager):
        """Test Composite Trust Score calculation."""
        mediator_id = "test_mediator_001"

        # Initial CTS should be around 0.5 (neutral starting point)
        profile = reputation_manager.get_mediator(mediator_id)
        initial_cts = profile.composite_trust_score

        assert 0.4 <= initial_cts <= 0.6

        # Record good outcomes
        for _ in range(5):
            reputation_manager.record_proposal_outcome(
                mediator_id,
                accepted=True,
                semantic_drift_score=0.1,
                latency_seconds=20
            )

        profile = reputation_manager.get_mediator(mediator_id)
        improved_cts = profile.composite_trust_score

        # CTS should improve
        assert improved_cts > initial_cts

    def test_acceptance_rate_tracking(self, reputation_manager):
        """Test acceptance rate is tracked correctly."""
        mediator_id = "test_mediator_001"

        # Record 8 accepts and 2 rejects
        for _ in range(8):
            reputation_manager.record_proposal_outcome(mediator_id, accepted=True)
        for _ in range(2):
            reputation_manager.record_proposal_outcome(mediator_id, accepted=False)

        profile = reputation_manager.get_mediator(mediator_id)

        assert profile.proposal_count == 10
        assert profile.accepted_count == 8
        assert profile.rejected_count == 2
        # Acceptance rate should trend toward 0.8
        assert profile.scores.acceptance_rate > 0.5

    def test_semantic_accuracy_scoring(self, reputation_manager):
        """Test semantic accuracy is scored correctly."""
        mediator_id = "test_mediator_001"

        # Low drift = high accuracy
        reputation_manager.record_proposal_outcome(
            mediator_id,
            accepted=True,
            semantic_drift_score=0.05  # Very low drift
        )

        profile = reputation_manager.get_mediator(mediator_id)
        assert profile.scores.semantic_accuracy > 0.5

        # High drift = low accuracy
        mediator_id_2 = "test_mediator_002"
        reputation_manager.record_proposal_outcome(
            mediator_id_2,
            accepted=True,
            semantic_drift_score=0.8  # High drift
        )

        profile_2 = reputation_manager.get_mediator(mediator_id_2)
        assert profile_2.scores.semantic_accuracy < profile.scores.semantic_accuracy

    def test_latency_discipline_scoring(self, reputation_manager):
        """Test latency discipline scoring."""
        mediator_id = "test_mediator_001"

        # Fast response
        reputation_manager.record_proposal_outcome(
            mediator_id,
            accepted=True,
            latency_seconds=30
        )

        profile = reputation_manager.get_mediator(mediator_id)
        high_latency_score = profile.scores.latency_discipline

        # Slow response
        for _ in range(5):
            reputation_manager.record_proposal_outcome(
                mediator_id,
                accepted=True,
                latency_seconds=3000  # 50 minutes
            )

        profile = reputation_manager.get_mediator(mediator_id)
        low_latency_score = profile.scores.latency_discipline

        assert low_latency_score < high_latency_score

    def test_coercion_signal_penalty(self, reputation_manager):
        """Test coercion signal impacts CTS."""
        mediator_id = "test_mediator_001"

        profile_before = reputation_manager.get_mediator(mediator_id)
        cts_before = profile_before.composite_trust_score

        # Record coercion detection
        for _ in range(5):
            reputation_manager.record_proposal_outcome(
                mediator_id,
                accepted=True,
                coercion_detected=True
            )

        profile_after = reputation_manager.get_mediator(mediator_id)
        cts_after = profile_after.composite_trust_score

        # CTS should decrease due to coercion
        assert cts_after < cts_before
        assert profile_after.scores.coercion_signal > 0

    def test_appeal_survival_tracking(self, reputation_manager):
        """Test appeal survival rate tracking."""
        mediator_id = "test_mediator_001"

        # Record appeals - 3 survived, 1 lost
        reputation_manager.record_appeal_outcome(mediator_id, appeal_survived=True)
        reputation_manager.record_appeal_outcome(mediator_id, appeal_survived=True)
        reputation_manager.record_appeal_outcome(mediator_id, appeal_survived=True)
        reputation_manager.record_appeal_outcome(mediator_id, appeal_survived=False)

        profile = reputation_manager.get_mediator(mediator_id)

        assert profile.appeal_count == 4
        assert profile.appeal_losses == 1
        assert profile.scores.appeal_survival == 0.75

    def test_dispute_avoidance_scoring(self, reputation_manager):
        """Test dispute avoidance scoring."""
        mediator_id = "test_mediator_001"

        # Start with perfect dispute avoidance
        profile = reputation_manager.get_mediator(mediator_id)
        assert profile.scores.dispute_avoidance == 1.0

        # Record disputes
        for _ in range(5):
            reputation_manager.record_downstream_dispute(
                mediator_id,
                dispute_occurred=True
            )

        profile = reputation_manager.get_mediator(mediator_id)
        assert profile.scores.dispute_avoidance < 1.0


# =============================================================================
# Integration with Negotiation Engine Tests
# =============================================================================

class TestNegotiationEngineIntegration:
    """Tests for integration between chain interface and negotiation engine."""

    def test_full_negotiation_to_settlement(
        self,
        mock_chain,
        negotiation_engine,
        reputation_manager
    ):
        """Test full flow from negotiation session to chain settlement."""
        # Step 1: Get aligned intents from chain
        success, intents = mock_chain.get_pending_intents()
        assert success

        alice_intent = next(i for i in intents if i.author == "user_alice")
        bob_intent = next(i for i in intents if i.author == "user_bob")

        # Step 2: Create negotiation session
        success, session_data = negotiation_engine.initiate_session(
            initiator="user_alice",
            counterparty="user_bob",
            subject="Fluid dynamics library for climate research",
            initiator_statement=alice_intent.prose,
            initial_terms={
                "compensation_min": 500,
                "compensation_max": 800,
                "timeline_days": 60
            }
        )
        assert success
        session_id = session_data["session_id"]

        # Step 3: Counterparty joins
        success, join_data = negotiation_engine.join_session(
            session_id=session_id,
            counterparty="user_bob",
            counterparty_statement=bob_intent.prose
        )
        assert success
        assert join_data["alignment_score"] > 0

        # Step 4: Add clauses
        success, clause_data = negotiation_engine.add_clause(
            session_id=session_id,
            clause_type=ClauseType.PAYMENT,
            parameters={
                "amount": "650 NLC",
                "method": "NLC transfer",
                "timeline": "upon completion",
                "trigger": "acceptance of deliverables"
            },
            proposed_by="user_alice"
        )
        assert success

        # Step 5: Make and accept offer
        success, offer_data = negotiation_engine.make_offer(
            session_id=session_id,
            from_party="user_alice",
            terms={
                "compensation": 650,
                "timeline_days": 45,
                "deliverables": ["Rust library", "Documentation", "Test suite"]
            },
            message="I propose meeting in the middle on compensation and timeline."
        )
        assert success

        # Step 6: Accept offer
        success, response = negotiation_engine.respond_to_offer(
            session_id=session_id,
            offer_id=offer_data["offer_id"],
            party="user_bob",
            response="accept"
        )
        assert success
        assert response["status"] == "agreed"

        # Step 7: Post settlement to chain
        agreed_terms = response["agreed_terms"]
        success, settlement_result = mock_chain.propose_settlement(
            intent_hash_a=alice_intent.hash,
            intent_hash_b=bob_intent.hash,
            terms=agreed_terms,
            fee=alice_intent.offered_fee + bob_intent.offered_fee
        )
        assert success

        # Step 8: Update reputation
        reputation_manager.record_proposal_outcome(
            "test_mediator_001",
            accepted=True,
            semantic_drift_score=0.15
        )

        profile = reputation_manager.get_mediator("test_mediator_001")
        assert profile.accepted_count >= 1

    def test_negotiation_failure_handling(
        self,
        mock_chain,
        negotiation_engine,
        reputation_manager
    ):
        """Test handling of failed negotiations."""
        mediator_id = "test_mediator_001"

        # Create a session that will fail
        success, session_data = negotiation_engine.initiate_session(
            initiator="user_alice",
            counterparty="user_charlie",
            subject="Incompatible request",
            initiator_statement="I want to sell software",
            initial_terms={}
        )
        assert success
        session_id = session_data["session_id"]

        # Join and make offer that gets rejected
        negotiation_engine.join_session(
            session_id=session_id,
            counterparty="user_charlie",
            counterparty_statement="I want to buy visualization services"
        )

        negotiation_engine.make_offer(
            session_id=session_id,
            from_party="user_alice",
            terms={"price": 10000},
            message="My offer"
        )

        # Record rejection
        reputation_manager.record_proposal_outcome(
            mediator_id,
            accepted=False,
            semantic_drift_score=0.6
        )

        profile = reputation_manager.get_mediator(mediator_id)
        assert profile.rejected_count >= 1


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_settlement_not_found(self, mock_chain):
        """Test handling of non-existent settlement."""
        success, result = mock_chain.get_settlement_status("nonexistent_id")
        assert not success

    def test_duplicate_acceptance(self, mock_chain):
        """Test handling of duplicate acceptance."""
        # Propose settlement
        mock_chain.propose_settlement(
            intent_hash_a="0xalice123",
            intent_hash_b="0xbob456",
            terms={"amount": 500},
            fee=10.0
        )

        entries = mock_chain.get_submitted_entries()
        settlement_id = entries[0]["metadata"]["id"]

        # Accept twice from same party
        mock_chain.accept_settlement(settlement_id, "A", "user_alice")
        mock_chain.accept_settlement(settlement_id, "A", "user_alice")

        # Should still work, just be idempotent
        success, settlement = mock_chain.get_settlement_status(settlement_id)
        assert success
        assert settlement.party_a_accepted

    def test_empty_intents_list(self, mock_chain):
        """Test handling of empty intents."""
        # Create interface with no intents
        empty_interface = MockChainInterface()

        success, intents = empty_interface.get_pending_intents()
        assert success
        assert len(intents) == 0

    def test_minimum_bond_enforcement(self, reputation_manager):
        """Test that minimum bond is enforced."""
        with pytest.raises(ValueError) as exc_info:
            reputation_manager.register_mediator(
                "underbonded_mediator",
                stake_amount=1000  # Below minimum
            )

        assert "below minimum" in str(exc_info.value).lower()

    def test_slashing_reduces_bond_below_minimum(self, reputation_manager):
        """Test behavior when slashing reduces bond below minimum."""
        mediator_id = "test_mediator_001"

        # Slash heavily multiple times
        for _ in range(10):
            reputation_manager.slash(
                mediator_id,
                SlashingOffense.COLLUSION_SIGNALS,
                severity=1.0
            )

        profile = reputation_manager.get_mediator(mediator_id)

        # Should become unbonded when bond < minimum
        if profile.bond.amount < MINIMUM_BOND:
            assert profile.status == MediatorStatus.UNBONDED

    def test_cooldown_prevents_excessive_proposals(self, reputation_manager):
        """Test that cooldown limits proposals."""
        mediator_id = "test_mediator_001"

        # Trigger cooldown via slashing
        reputation_manager.slash(
            mediator_id,
            SlashingOffense.REPEATED_INVALID_PROPOSALS,
            severity=0.5
        )

        profile = reputation_manager.get_mediator(mediator_id)
        assert len([c for c in profile.active_cooldowns if c.is_active]) > 0


# =============================================================================
# Event Callback Tests
# =============================================================================

class TestEventCallbacks:
    """Tests for event callback system."""

    def test_intents_fetched_callback(self, mock_chain):
        """Test callback for intents fetched event."""
        callback_data = []

        def on_intents_fetched(data):
            callback_data.append(data)

        mock_chain.on("intents_fetched", on_intents_fetched)
        mock_chain.get_pending_intents()

        assert len(callback_data) == 1
        assert "count" in callback_data[0]

    def test_entry_submitted_callback(self, mock_chain):
        """Test callback for entry submitted event."""
        callback_data = []

        def on_entry_submitted(data):
            callback_data.append(data)

        mock_chain.on("entry_submitted", on_entry_submitted)

        mock_chain.propose_settlement(
            intent_hash_a="0xtest1",
            intent_hash_b="0xtest2",
            terms={},
            fee=5.0
        )

        assert len(callback_data) == 1
        assert callback_data[0]["type"] == "settlement"

    def test_callback_removal(self, mock_chain):
        """Test removing a callback."""
        callback_count = [0]

        def counter_callback(data):
            callback_count[0] += 1

        mock_chain.on("intents_fetched", counter_callback)
        mock_chain.get_pending_intents()
        assert callback_count[0] == 1

        mock_chain.off("intents_fetched", counter_callback)
        mock_chain.get_pending_intents()
        assert callback_count[0] == 1  # Should not increment


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestPerformance:
    """Basic performance tests."""

    def test_high_volume_intents(self):
        """Test handling many intents."""
        interface = MockChainInterface()

        # Add 1000 intents
        for i in range(1000):
            intent = ChainIntent(
                hash=f"0xhash{i:04d}",
                author=f"user_{i % 100}",
                prose=f"Intent number {i}",
                desires=["test"],
                constraints=[],
                offered_fee=float(i % 10),
                timestamp=int(time.time()) - i,
                status=IntentStatus.PENDING,
                branch="Test"
            )
            interface.add_test_intent(intent)

        # Fetch should complete quickly
        start = time.time()
        success, intents = interface.get_pending_intents()
        elapsed = time.time() - start

        assert success
        assert len(intents) == 1000
        assert elapsed < 1.0  # Should complete in under 1 second

    def test_many_settlements(self):
        """Test handling many settlements."""
        interface = MockChainInterface()

        # Create 100 settlements
        for i in range(100):
            interface.propose_settlement(
                intent_hash_a=f"0xa{i:03d}",
                intent_hash_b=f"0xb{i:03d}",
                terms={"index": i},
                fee=float(i)
            )

        entries = interface.get_submitted_entries()
        assert len(entries) == 100


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
