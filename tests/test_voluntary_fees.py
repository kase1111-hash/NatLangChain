"""
Tests for the voluntary fee and incentive system.

Tests priority queue, fee extraction, zero-fee processing,
community pool, and mediator incentives.
"""

import pytest
from datetime import datetime, timedelta

from src.voluntary_fees import (
    CommunityPool,
    FeeExtractor,
    FeeInfo,
    IncentiveType,
    MediatorEarnings,
    ProcessingReason,
    ProcessingStatus,
    QueuedContract,
    VoluntaryProcessingQueue,
    ZERO_FEE_REPUTATION_BONUS,
    COMMUNITY_POOL_PERCENTAGE,
    get_fee_system_config,
    get_processing_queue,
    reset_processing_queue,
)


# =============================================================================
# Fee Extraction Tests
# =============================================================================


class TestFeeExtraction:
    """Tests for fee extraction from contract content."""

    def test_extract_explicit_fee(self):
        """Test extracting explicit processing fee."""
        extractor = FeeExtractor()
        content = "Alice agrees to pay Bob. Processing fee: $50"
        fee = extractor.extract(content)

        assert fee.amount == 50.0
        assert fee.is_explicit is True

    def test_extract_fee_with_comma(self):
        """Test extracting fee with comma separator."""
        extractor = FeeExtractor()
        content = "Contract with fee: $1,500"
        fee = extractor.extract(content)

        assert fee.amount == 1500.0

    def test_extract_fee_with_currency(self):
        """Test extracting fee with explicit currency."""
        extractor = FeeExtractor()
        content = "Payment of 100 USDC for processing"
        fee = extractor.extract(content)

        assert fee.amount == 100.0
        assert fee.currency == "USDC"

    def test_extract_tip(self):
        """Test extracting tip specification."""
        extractor = FeeExtractor()
        content = "I will tip: $25 for fast processing"
        fee = extractor.extract(content)

        assert fee.amount == 25.0

    def test_no_fee_specified(self):
        """Test that missing fee returns zero."""
        extractor = FeeExtractor()
        content = "Alice agrees to provide consulting services to Bob."
        fee = extractor.extract(content)

        assert fee.amount == 0.0
        assert fee.is_explicit is False
        assert fee.source == "not_specified"

    def test_extract_offering_pattern(self):
        """Test 'offering' pattern for fees."""
        extractor = FeeExtractor()
        content = "I am offering $75 for this contract to be processed quickly."
        fee = extractor.extract(content)

        assert fee.amount == 75.0

    def test_extract_will_pay_pattern(self):
        """Test 'will pay' pattern."""
        extractor = FeeExtractor()
        content = "Bob will pay $200 for processing this agreement."
        fee = extractor.extract(content)

        assert fee.amount == 200.0


# =============================================================================
# Priority Queue Tests
# =============================================================================


class TestPriorityQueue:
    """Tests for the processing priority queue."""

    def setup_method(self):
        """Reset queue before each test."""
        reset_processing_queue()

    def test_submit_contract_with_fee(self):
        """Test submitting a contract with fee."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract(
            content="Agreement with processing fee: $100",
            submitter_id="alice"
        )

        assert contract.contract_id.startswith("CONTRACT_")
        assert contract.fee.amount == 100.0
        assert contract.incentive_type == IncentiveType.DIRECT_FEE
        assert contract.status == ProcessingStatus.QUEUED

    def test_submit_zero_fee_contract(self):
        """Test submitting a zero-fee contract."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract(
            content="Simple agreement between Alice and Bob.",
            submitter_id="bob"
        )

        assert contract.fee.amount == 0.0
        assert contract.incentive_type == IncentiveType.REPUTATION_ONLY

    def test_higher_fee_gets_priority(self):
        """Test that higher fees get higher priority."""
        queue = VoluntaryProcessingQueue()

        # Submit contracts with same base text but different fees
        base_text = "This is a standard agreement between parties with processing"
        low = queue.submit_contract(f"{base_text}. Fee: $10", "alice")
        high = queue.submit_contract(f"{base_text}. Fee: $500", "bob")
        medium = queue.submit_contract(f"{base_text}. Fee: $100", "charlie")

        # Get next contracts
        next_contracts = queue.get_next_contracts(3)

        # Verify fee scores are in correct order
        assert high.metrics.fee_score > medium.metrics.fee_score
        assert medium.metrics.fee_score > low.metrics.fee_score

        # High fee should have highest priority score
        assert high.metrics.priority_score > medium.metrics.priority_score
        assert medium.metrics.priority_score > low.metrics.priority_score

    def test_zero_fee_still_in_queue(self):
        """Test that zero-fee contracts are still in queue."""
        queue = VoluntaryProcessingQueue()

        # Mix of paid and zero-fee
        paid = queue.submit_contract("Agreement. Fee: $50", "alice")
        free = queue.submit_contract("Free agreement.", "bob")

        next_contracts = queue.get_next_contracts(10)

        # Both should be in queue
        assert len(next_contracts) == 2
        assert any(c.contract_id == paid.contract_id for c in next_contracts)
        assert any(c.contract_id == free.contract_id for c in next_contracts)

    def test_get_zero_fee_contracts(self):
        """Test getting only zero-fee contracts."""
        queue = VoluntaryProcessingQueue()

        queue.submit_contract("Paid. Fee: $100", "alice")
        free1 = queue.submit_contract("Free contract 1.", "bob")
        free2 = queue.submit_contract("Free contract 2.", "charlie")

        zero_fee = queue.get_zero_fee_contracts()

        assert len(zero_fee) == 2
        assert all(c.fee.amount == 0 for c in zero_fee)


# =============================================================================
# Claim & Process Tests
# =============================================================================


class TestClaimAndProcess:
    """Tests for claiming and processing contracts."""

    def test_claim_contract(self):
        """Test claiming a contract."""
        queue = VoluntaryProcessingQueue()
        contract = queue.submit_contract("Agreement. Fee: $50", "alice")

        success, msg = queue.claim_contract(
            contract.contract_id,
            "mediator1",
            ProcessingReason.FEE_INCENTIVE
        )

        assert success
        assert contract.status == ProcessingStatus.CLAIMED
        assert contract.claimed_by == "mediator1"

    def test_cannot_claim_already_claimed(self):
        """Test that already claimed contracts can't be re-claimed."""
        queue = VoluntaryProcessingQueue()
        contract = queue.submit_contract("Agreement.", "alice")

        queue.claim_contract(contract.contract_id, "mediator1")
        success, msg = queue.claim_contract(contract.contract_id, "mediator2")

        assert not success
        assert "claimed" in msg.lower() or "not available" in msg.lower()

    def test_complete_processing_with_fee(self):
        """Test completing a paid contract."""
        queue = VoluntaryProcessingQueue()
        contract = queue.submit_contract("Agreement. Fee: $100", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")

        success, result = queue.complete_processing(
            contract.contract_id, "mediator1"
        )

        assert success
        assert contract.status == ProcessingStatus.COMPLETED
        # Fee earned = 100 - 5% community pool = 95
        expected_fee = 100 * (1 - COMMUNITY_POOL_PERCENTAGE)
        assert result["fee_earned"] == expected_fee

    def test_complete_zero_fee_gives_reputation(self):
        """Test that zero-fee processing gives reputation bonus."""
        queue = VoluntaryProcessingQueue()
        contract = queue.submit_contract("Free agreement.", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")

        success, result = queue.complete_processing(
            contract.contract_id, "mediator1"
        )

        assert success
        assert result["is_zero_fee"] is True
        assert result["reputation_bonus"] == ZERO_FEE_REPUTATION_BONUS

    def test_abandon_returns_to_queue(self):
        """Test that abandoning returns contract to queue."""
        queue = VoluntaryProcessingQueue()
        contract = queue.submit_contract("Agreement.", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")

        success, msg = queue.abandon_contract(contract.contract_id, "mediator1")

        assert success
        assert contract.status == ProcessingStatus.QUEUED
        assert contract.claimed_by is None


# =============================================================================
# Community Pool Tests
# =============================================================================


class TestCommunityPool:
    """Tests for the community subsidy pool."""

    def test_pool_gets_percentage_of_fees(self):
        """Test that community pool gets percentage of fees."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract("Agreement. Fee: $100", "alice")

        # Pool should have 5% of fee
        expected = 100 * COMMUNITY_POOL_PERCENTAGE
        assert queue.community_pool.balance == expected

    def test_fund_community_pool(self):
        """Test manually funding the pool."""
        queue = VoluntaryProcessingQueue()
        initial = queue.community_pool.balance

        result = queue.fund_community_pool(500.0, "donor1")

        assert result["success"]
        assert queue.community_pool.balance == initial + 500.0

    def test_community_subsidy_for_zero_fee(self):
        """Test applying community subsidy to zero-fee processing."""
        queue = VoluntaryProcessingQueue()

        # Fund the pool
        queue.fund_community_pool(100.0, "donor")

        # Submit and process zero-fee
        contract = queue.submit_contract("Free agreement.", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")

        success, result = queue.complete_processing(
            contract.contract_id,
            "mediator1",
            apply_community_subsidy=True
        )

        assert success
        assert result["subsidy_earned"] > 0
        assert queue.community_pool.balance < 100.0


# =============================================================================
# Bounty Tests
# =============================================================================


class TestBounties:
    """Tests for adding bounties to contracts."""

    def test_add_bounty_increases_priority(self):
        """Test that bounties increase contract priority."""
        queue = VoluntaryProcessingQueue()

        # Submit zero-fee contract
        contract = queue.submit_contract("Free agreement.", "alice")
        initial_priority = contract.metrics.priority_score

        # Add bounty
        success, msg = queue.add_bounty(contract.contract_id, 100.0, "benefactor")

        assert success
        assert contract.fee.amount == 100.0
        assert contract.incentive_type == IncentiveType.BOUNTY
        assert contract.metrics.priority_score > initial_priority

    def test_vote_increases_community_interest(self):
        """Test that voting increases community interest."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract("Community contract.", "alice")
        initial_interest = contract.metrics.community_interest

        queue.vote_for_contract(contract.contract_id, "voter1")
        queue.vote_for_contract(contract.contract_id, "voter2")

        assert contract.metrics.community_interest > initial_interest


# =============================================================================
# Earnings Tests
# =============================================================================


class TestEarnings:
    """Tests for mediator earnings tracking."""

    def test_track_earnings_from_fees(self):
        """Test that fee earnings are tracked."""
        queue = VoluntaryProcessingQueue()

        # Process paid contract
        contract = queue.submit_contract("Agreement. Fee: $200", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")
        queue.complete_processing(contract.contract_id, "mediator1")

        earnings = queue.get_mediator_earnings("mediator1")

        assert earnings["contracts_processed"] == 1
        expected = 200 * (1 - COMMUNITY_POOL_PERCENTAGE)
        assert earnings["fees_collected"] == expected

    def test_track_zero_fee_count(self):
        """Test that zero-fee processing is counted."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract("Free agreement.", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")
        queue.complete_processing(contract.contract_id, "mediator1")

        earnings = queue.get_mediator_earnings("mediator1")

        assert earnings["zero_fee_processed"] == 1
        assert earnings["reputation_bonuses"] == ZERO_FEE_REPUTATION_BONUS

    def test_get_top_earners(self):
        """Test getting top earning mediators."""
        queue = VoluntaryProcessingQueue()

        # Mediator1 processes $300
        c1 = queue.submit_contract("Fee: $300", "alice")
        queue.claim_contract(c1.contract_id, "mediator1")
        queue.complete_processing(c1.contract_id, "mediator1")

        # Mediator2 processes $100
        c2 = queue.submit_contract("Fee: $100", "bob")
        queue.claim_contract(c2.contract_id, "mediator2")
        queue.complete_processing(c2.contract_id, "mediator2")

        top = queue.get_top_earners(limit=5)

        assert len(top) == 2
        assert top[0]["mediator_id"] == "mediator1"
        assert top[1]["mediator_id"] == "mediator2"


# =============================================================================
# Age Priority Tests
# =============================================================================


class TestAgePriority:
    """Tests for age-based priority adjustments."""

    def test_zero_fee_age_boost(self):
        """Test that old zero-fee contracts get priority boost."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract("Free agreement.", "alice")

        # Manually set submitted_at to 48 hours ago
        contract.submitted_at = datetime.utcnow() - timedelta(hours=48)

        # Update age factors
        queue.update_age_factors()

        # Should have age boost
        assert contract.metrics.age_factor > 0


# =============================================================================
# Statistics Tests
# =============================================================================


class TestStatistics:
    """Tests for queue statistics."""

    def test_queue_stats(self):
        """Test getting queue statistics."""
        queue = VoluntaryProcessingQueue()

        queue.submit_contract("Free 1.", "alice")
        queue.submit_contract("Free 2.", "bob")
        queue.submit_contract("Paid. Fee: $50", "charlie")

        stats = queue.get_queue_stats()

        assert stats["total_in_queue"] == 3
        assert stats["zero_fee_waiting"] == 2
        assert stats["paid_waiting"] == 1
        assert stats["total_submitted"] == 3

    def test_contract_status(self):
        """Test getting individual contract status."""
        queue = VoluntaryProcessingQueue()

        contract = queue.submit_contract("Agreement. Fee: $100", "alice")
        status = queue.get_contract_status(contract.contract_id)

        assert status is not None
        assert status["contract_id"] == contract.contract_id
        assert status["fee"]["amount"] == 100.0
        assert status["status"] == "queued"


# =============================================================================
# Stale Claim Tests
# =============================================================================


class TestStaleClaims:
    """Tests for releasing stale claims."""

    def test_release_stale_claims(self):
        """Test that stale claims are released."""
        queue = VoluntaryProcessingQueue(max_claim_duration_hours=1)

        contract = queue.submit_contract("Agreement.", "alice")
        queue.claim_contract(contract.contract_id, "mediator1")

        # Manually set claimed_at to 2 hours ago
        contract.claimed_at = datetime.utcnow() - timedelta(hours=2)

        released = queue.release_stale_claims()

        assert released == 1
        assert contract.status == ProcessingStatus.QUEUED
        assert contract.claimed_by is None


# =============================================================================
# Module Function Tests
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_processing_queue_singleton(self):
        """Test that get_processing_queue returns singleton."""
        reset_processing_queue()

        q1 = get_processing_queue()
        q2 = get_processing_queue()

        assert q1 is q2

    def test_reset_processing_queue(self):
        """Test resetting the queue."""
        q1 = get_processing_queue()
        q1.submit_contract("Test", "alice")

        reset_processing_queue()
        q2 = get_processing_queue()

        assert q1 is not q2
        assert q2.get_queue_stats()["total_submitted"] == 0

    def test_get_fee_system_config(self):
        """Test getting fee system configuration."""
        config = get_fee_system_config()

        assert config["version"] == "1.0"
        assert config["is_mandatory"] is False
        assert "priority_weights" in config
        assert "design_principle" in config


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for the full workflow."""

    def test_full_paid_workflow(self):
        """Test complete workflow for paid contract."""
        reset_processing_queue()
        queue = get_processing_queue()

        # Submit
        contract = queue.submit_contract(
            "Alice agrees to pay Bob $1000. Processing fee: $25",
            "alice"
        )
        assert contract.fee.amount == 25.0

        # View queue
        available = queue.get_next_contracts(5)
        assert len(available) == 1

        # Claim
        success, _ = queue.claim_contract(
            contract.contract_id,
            "mediator1",
            ProcessingReason.FEE_INCENTIVE
        )
        assert success

        # Complete
        success, result = queue.complete_processing(
            contract.contract_id, "mediator1"
        )
        assert success
        assert result["fee_earned"] > 0

        # Check earnings
        earnings = queue.get_mediator_earnings("mediator1")
        assert earnings["contracts_processed"] == 1

    def test_full_zero_fee_workflow(self):
        """Test complete workflow for zero-fee contract."""
        reset_processing_queue()
        queue = get_processing_queue()

        # Fund community pool
        queue.fund_community_pool(50.0, "benefactor")

        # Submit zero-fee
        contract = queue.submit_contract(
            "Simple agreement between friends.",
            "alice"
        )
        assert contract.fee.amount == 0.0

        # Claim for reputation building
        success, _ = queue.claim_contract(
            contract.contract_id,
            "new_mediator",
            ProcessingReason.REPUTATION
        )
        assert success

        # Complete with subsidy
        success, result = queue.complete_processing(
            contract.contract_id,
            "new_mediator",
            apply_community_subsidy=True
        )
        assert success
        assert result["is_zero_fee"]
        assert result["reputation_bonus"] > 0
        assert result["subsidy_earned"] > 0

        # Check earnings
        earnings = queue.get_mediator_earnings("new_mediator")
        assert earnings["zero_fee_processed"] == 1
        assert earnings["reputation_bonuses"] > 0
