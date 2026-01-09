"""
NatLangChain - Voluntary Fee & Incentive System

Implements a voluntary processing model where:
- Contracts MAY specify processing fees
- Higher fees get priority processing
- Zero-fee contracts can still be processed voluntarily
- No mandatory fees - all processing is optional

Design Principles:
1. Fee Market: Mediators choose what to process based on value
2. Reputation Building: Zero-fee processing builds mediator reputation
3. Community Pool: Subsidizes processing of important zero-fee contracts
4. Priority Queue: Transparent ordering based on fee + urgency
5. No Gatekeeping: All valid contracts can eventually be processed

This is NOT a gas system - fees are tips for prioritization, not requirements.
"""

import hashlib
import heapq
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Default fee currency (configurable per deployment)
DEFAULT_FEE_CURRENCY = "USDC"

# Reputation bonus for processing zero-fee contracts
ZERO_FEE_REPUTATION_BONUS = 0.02

# Maximum age before zero-fee contracts get priority boost
ZERO_FEE_AGE_BOOST_HOURS = 24

# Community pool contribution percentage from fees
COMMUNITY_POOL_PERCENTAGE = 0.05  # 5% goes to community pool

# Priority score weights
PRIORITY_WEIGHTS = {
    "fee_amount": 0.50,  # Fee is primary factor
    "urgency_score": 0.20,  # Explicit urgency in contract
    "age_factor": 0.15,  # Older contracts get priority
    "complexity_factor": 0.10,  # Simpler contracts slightly preferred
    "community_interest": 0.05,  # Community votes/interest
}

# Fee patterns to extract from contracts
FEE_PATTERNS = [
    # Direct fee specifications
    r"processing[_\s]?fee[:\s]+\$?([\d,]+(?:\.\d{2})?)",
    r"fee[:\s]+\$?([\d,]+(?:\.\d{2})?)",
    r"tip[:\s]+\$?([\d,]+(?:\.\d{2})?)",
    r"incentive[:\s]+\$?([\d,]+(?:\.\d{2})?)",
    # Currency-specific patterns
    r"([\d,]+(?:\.\d{2})?)\s*(?:USDC|USD|ETH|DAI)",
    r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:processing|fee|tip)?",
    # Natural language
    r"offering\s+\$?([\d,]+(?:\.\d{2})?)",
    r"will\s+pay\s+\$?([\d,]+(?:\.\d{2})?)\s+(?:for\s+)?processing",
]


# =============================================================================
# Enums
# =============================================================================


class ProcessingStatus(Enum):
    """Status of contract processing."""

    QUEUED = "queued"  # In queue, awaiting processing
    CLAIMED = "claimed"  # Mediator claimed it
    PROCESSING = "processing"  # Actively being processed
    COMPLETED = "completed"  # Successfully processed
    ABANDONED = "abandoned"  # Mediator abandoned
    EXPIRED = "expired"  # Too old, removed from queue


class IncentiveType(Enum):
    """Types of incentives for processing."""

    DIRECT_FEE = "direct_fee"  # Fee paid by contract submitter
    COMMUNITY_SUBSIDY = "community_subsidy"  # From community pool
    REPUTATION_ONLY = "reputation_only"  # No monetary reward
    BOUNTY = "bounty"  # Special bounty for specific contracts


class ProcessingReason(Enum):
    """Why a mediator chose to process."""

    FEE_INCENTIVE = "fee_incentive"  # For the fee
    REPUTATION = "reputation"  # Building reputation
    COMMUNITY_SERVICE = "community_service"  # Altruistic
    SPECIALTY = "specialty"  # In mediator's domain
    QUEUE_CLEARING = "queue_clearing"  # Helping clear old items


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FeeInfo:
    """Fee information extracted from a contract."""

    amount: float = 0.0
    currency: str = DEFAULT_FEE_CURRENCY
    source: str = "not_specified"  # Where fee was found
    is_explicit: bool = False  # Explicitly stated vs inferred

    def to_dict(self) -> dict[str, Any]:
        """Serialize fee information to a dictionary."""
        return {
            "amount": self.amount,
            "currency": self.currency,
            "source": self.source,
            "is_explicit": self.is_explicit,
        }


@dataclass
class ProcessingMetrics:
    """Metrics for a contract in the queue."""

    fee_score: float = 0.0  # Normalized fee contribution
    urgency_score: float = 0.0  # Urgency from 0-1
    age_factor: float = 0.0  # Age-based boost
    complexity_factor: float = 0.5  # Complexity penalty/bonus
    community_interest: float = 0.0  # Community votes

    @property
    def priority_score(self) -> float:
        """Calculate overall priority score."""
        return (
            PRIORITY_WEIGHTS["fee_amount"] * self.fee_score
            + PRIORITY_WEIGHTS["urgency_score"] * self.urgency_score
            + PRIORITY_WEIGHTS["age_factor"] * self.age_factor
            + PRIORITY_WEIGHTS["complexity_factor"] * self.complexity_factor
            + PRIORITY_WEIGHTS["community_interest"] * self.community_interest
        )


@dataclass
class QueuedContract:
    """A contract in the processing queue."""

    contract_id: str
    content: str
    submitter_id: str
    fee: FeeInfo = field(default_factory=FeeInfo)
    metrics: ProcessingMetrics = field(default_factory=ProcessingMetrics)

    status: ProcessingStatus = ProcessingStatus.QUEUED
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    completed_at: datetime | None = None

    # Processing reason (when claimed)
    processing_reason: ProcessingReason | None = None

    # Incentive tracking
    incentive_type: IncentiveType = IncentiveType.REPUTATION_ONLY
    subsidy_amount: float = 0.0  # Community subsidy if any

    def __lt__(self, other: "QueuedContract") -> bool:
        """For heap comparison - higher priority = lower number."""
        return self.metrics.priority_score > other.metrics.priority_score

    def to_dict(self) -> dict[str, Any]:
        """Serialize queued contract to a dictionary for API response."""
        return {
            "contract_id": self.contract_id,
            "submitter_id": self.submitter_id,
            "fee": self.fee.to_dict(),
            "priority_score": self.metrics.priority_score,
            "status": self.status.value,
            "submitted_at": self.submitted_at.isoformat(),
            "claimed_by": self.claimed_by,
            "incentive_type": self.incentive_type.value,
            "age_hours": (datetime.utcnow() - self.submitted_at).total_seconds() / 3600,
        }


@dataclass
class MediatorEarnings:
    """Track mediator earnings from processing."""

    mediator_id: str
    total_earned: float = 0.0
    fees_collected: float = 0.0
    subsidies_received: float = 0.0
    zero_fee_processed: int = 0
    reputation_bonuses: float = 0.0
    contracts_processed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize mediator earnings to a dictionary for reporting."""
        return {
            "mediator_id": self.mediator_id,
            "total_earned": self.total_earned,
            "fees_collected": self.fees_collected,
            "subsidies_received": self.subsidies_received,
            "zero_fee_processed": self.zero_fee_processed,
            "reputation_bonuses": self.reputation_bonuses,
            "contracts_processed": self.contracts_processed,
        }


@dataclass
class CommunityPool:
    """Community pool for subsidizing zero-fee processing."""

    balance: float = 0.0
    total_contributions: float = 0.0
    total_disbursed: float = 0.0
    currency: str = DEFAULT_FEE_CURRENCY

    # Track subsidized contracts
    subsidies_given: list[dict[str, Any]] = field(default_factory=list)

    def contribute(self, amount: float, source: str) -> None:
        """Add funds to pool."""
        self.balance += amount
        self.total_contributions += amount

    def disburse(self, amount: float, contract_id: str, mediator_id: str) -> bool:
        """Disburse subsidy for a contract."""
        if amount > self.balance:
            return False

        self.balance -= amount
        self.total_disbursed += amount
        self.subsidies_given.append(
            {
                "contract_id": contract_id,
                "mediator_id": mediator_id,
                "amount": amount,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize community pool state to a dictionary for API response."""
        return {
            "balance": self.balance,
            "total_contributions": self.total_contributions,
            "total_disbursed": self.total_disbursed,
            "currency": self.currency,
            "recent_subsidies": self.subsidies_given[-10:],  # Last 10
        }


# =============================================================================
# Fee Extraction
# =============================================================================


class FeeExtractor:
    """Extract fee information from contract content."""

    def __init__(self, patterns: list[str] | None = None):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in (patterns or FEE_PATTERNS)]

    def extract(self, content: str) -> FeeInfo:
        """
        Extract fee information from contract content.

        Returns FeeInfo with amount=0 if no fee found (zero-fee contract).
        """
        # Try each pattern
        for pattern in self.patterns:
            match = pattern.search(content)
            if match:
                try:
                    # Parse amount, removing commas
                    amount_str = match.group(1).replace(",", "")
                    amount = float(amount_str)

                    # Detect currency from context
                    currency = self._detect_currency(content, match.start())

                    return FeeInfo(
                        amount=amount,
                        currency=currency,
                        source=pattern.pattern[:50],  # First 50 chars of pattern
                        is_explicit=True,
                    )
                except (ValueError, IndexError):
                    continue

        # No fee found - this is a zero-fee contract
        return FeeInfo(
            amount=0.0, currency=DEFAULT_FEE_CURRENCY, source="not_specified", is_explicit=False
        )

    def _detect_currency(self, content: str, position: int) -> str:
        """Detect currency from surrounding context."""
        # Check nearby text (50 chars before and after)
        start = max(0, position - 50)
        end = min(len(content), position + 50)
        context = content[start:end].upper()

        if "ETH" in context or "ETHER" in context:
            return "ETH"
        elif "DAI" in context:
            return "DAI"
        elif "USDT" in context:
            return "USDT"
        elif "USDC" in context or "USD" in context or "$" in context:
            return "USDC"

        return DEFAULT_FEE_CURRENCY


# =============================================================================
# Priority Queue Manager
# =============================================================================


class VoluntaryProcessingQueue:
    """
    Manages the priority queue for voluntary contract processing.

    Key features:
    - Priority based on fees + other factors
    - Zero-fee contracts still processed (lower priority)
    - Age-based priority boost for old zero-fee items
    - Community pool for subsidies
    """

    def __init__(
        self,
        fee_currency: str = DEFAULT_FEE_CURRENCY,
        max_claim_duration_hours: int = 4,
        queue_expiry_days: int = 30,
    ):
        self.fee_currency = fee_currency
        self.max_claim_duration = timedelta(hours=max_claim_duration_hours)
        self.queue_expiry = timedelta(days=queue_expiry_days)

        # Priority queue (heap)
        self._queue: list[QueuedContract] = []

        # Fast lookup by contract_id
        self._contracts: dict[str, QueuedContract] = {}

        # Fee extractor
        self._fee_extractor = FeeExtractor()

        # Mediator earnings
        self._earnings: dict[str, MediatorEarnings] = {}

        # Community pool
        self.community_pool = CommunityPool(currency=fee_currency)

        # Statistics
        self._stats = {
            "total_submitted": 0,
            "total_processed": 0,
            "zero_fee_processed": 0,
            "total_fees_collected": 0.0,
            "average_wait_hours": 0.0,
        }

        # Event counter
        self._event_counter = 0

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID."""
        self._event_counter += 1
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{prefix}:{timestamp}:{self._event_counter}"
        return f"{prefix}_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"

    # -------------------------------------------------------------------------
    # Queue Operations
    # -------------------------------------------------------------------------

    def submit_contract(
        self,
        content: str,
        submitter_id: str,
        urgency: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> QueuedContract:
        """
        Submit a contract to the processing queue.

        Args:
            content: Contract text
            submitter_id: Who submitted
            urgency: Optional urgency score (0-1)
            metadata: Optional additional metadata

        Returns:
            QueuedContract in the queue
        """
        contract_id = self._generate_id("CONTRACT")

        # Extract fee from content
        fee = self._fee_extractor.extract(content)

        # Calculate metrics
        metrics = self._calculate_metrics(content, fee, urgency)

        # Determine incentive type
        if fee.amount > 0:
            incentive_type = IncentiveType.DIRECT_FEE
        else:
            incentive_type = IncentiveType.REPUTATION_ONLY

        contract = QueuedContract(
            contract_id=contract_id,
            content=content,
            submitter_id=submitter_id,
            fee=fee,
            metrics=metrics,
            incentive_type=incentive_type,
        )

        # Add to queue
        heapq.heappush(self._queue, contract)
        self._contracts[contract_id] = contract

        # Update stats
        self._stats["total_submitted"] += 1

        # Contribute portion to community pool if fee exists
        if fee.amount > 0:
            pool_contribution = fee.amount * COMMUNITY_POOL_PERCENTAGE
            self.community_pool.contribute(pool_contribution, f"fee:{contract_id}")

        return contract

    def _calculate_metrics(self, content: str, fee: FeeInfo, urgency: float) -> ProcessingMetrics:
        """Calculate processing metrics for a contract."""
        # Normalize fee (assume $1000 is "high")
        fee_score = min(1.0, fee.amount / 1000.0)

        # Complexity based on length and structure
        words = len(content.split())
        if words < 50:
            complexity = 0.8  # Simple = slight priority
        elif words < 200:
            complexity = 0.5  # Medium
        else:
            complexity = 0.3  # Complex = lower priority (more work)

        return ProcessingMetrics(
            fee_score=fee_score,
            urgency_score=min(1.0, max(0.0, urgency)),
            age_factor=0.0,  # Will be updated over time
            complexity_factor=complexity,
            community_interest=0.0,  # Can be updated by votes
        )

    def update_age_factors(self) -> int:
        """
        Update age-based priority for all contracts.

        Zero-fee contracts get priority boost after waiting.
        Call this periodically (e.g., hourly).

        Returns:
            Number of contracts updated
        """
        updated = 0
        now = datetime.utcnow()

        for contract in self._contracts.values():
            if contract.status != ProcessingStatus.QUEUED:
                continue

            age_hours = (now - contract.submitted_at).total_seconds() / 3600

            # Zero-fee contracts get increasing priority over time
            if contract.fee.amount == 0:
                # After 24 hours, start boosting
                if age_hours > ZERO_FEE_AGE_BOOST_HOURS:
                    excess_hours = age_hours - ZERO_FEE_AGE_BOOST_HOURS
                    # Boost up to 1.0 over next 48 hours
                    contract.metrics.age_factor = min(1.0, excess_hours / 48.0)
                    updated += 1
            else:
                # Paid contracts also get small age boost
                contract.metrics.age_factor = min(0.5, age_hours / 168.0)  # Max 0.5 over 1 week
                updated += 1

        # Re-heapify after updates
        heapq.heapify(self._queue)

        return updated

    def get_next_contracts(self, count: int = 10) -> list[QueuedContract]:
        """
        Get next contracts available for processing.

        Returns contracts in priority order that are available to claim.
        """
        available = []

        for contract in sorted(self._queue, reverse=True):
            if contract.status == ProcessingStatus.QUEUED:
                available.append(contract)
                if len(available) >= count:
                    break

        return available

    def get_zero_fee_contracts(
        self, min_age_hours: float = 0.0, limit: int = 20
    ) -> list[QueuedContract]:
        """
        Get zero-fee contracts for voluntary processing.

        Mediators building reputation may want to specifically
        target zero-fee contracts.
        """
        now = datetime.utcnow()
        zero_fee = []

        for contract in self._contracts.values():
            if contract.status != ProcessingStatus.QUEUED:
                continue
            if contract.fee.amount > 0:
                continue

            age_hours = (now - contract.submitted_at).total_seconds() / 3600
            if age_hours >= min_age_hours:
                zero_fee.append(contract)

        # Sort by age (oldest first)
        zero_fee.sort(key=lambda c: c.submitted_at)
        return zero_fee[:limit]

    # -------------------------------------------------------------------------
    # Claim & Process
    # -------------------------------------------------------------------------

    def claim_contract(
        self,
        contract_id: str,
        mediator_id: str,
        reason: ProcessingReason = ProcessingReason.FEE_INCENTIVE,
    ) -> tuple[bool, str]:
        """
        Mediator claims a contract for processing.

        Args:
            contract_id: Contract to claim
            mediator_id: Mediator claiming
            reason: Why they're processing it

        Returns:
            (success, message)
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            return (False, f"Contract {contract_id} not found")

        if contract.status != ProcessingStatus.QUEUED:
            return (False, f"Contract is {contract.status.value}, not available")

        contract.status = ProcessingStatus.CLAIMED
        contract.claimed_by = mediator_id
        contract.claimed_at = datetime.utcnow()
        contract.processing_reason = reason

        return (True, f"Contract claimed by {mediator_id}")

    def complete_processing(
        self, contract_id: str, mediator_id: str, apply_community_subsidy: bool = False
    ) -> tuple[bool, dict[str, Any]]:
        """
        Mark contract as processed and distribute incentives.

        Args:
            contract_id: Contract that was processed
            mediator_id: Mediator who processed
            apply_community_subsidy: Request subsidy for zero-fee

        Returns:
            (success, earnings_info)
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            return (False, {"error": f"Contract {contract_id} not found"})

        if contract.claimed_by != mediator_id:
            return (
                False,
                {"error": f"Contract claimed by {contract.claimed_by}, not {mediator_id}"},
            )

        if contract.status not in (ProcessingStatus.CLAIMED, ProcessingStatus.PROCESSING):
            return (False, {"error": f"Contract is {contract.status.value}"})

        contract.status = ProcessingStatus.COMPLETED
        contract.completed_at = datetime.utcnow()

        # Calculate earnings
        earnings = self._get_or_create_earnings(mediator_id)
        fee_amount = contract.fee.amount
        subsidy_amount = 0.0
        reputation_bonus = 0.0

        # Fee-based earning
        if fee_amount > 0:
            # Deduct community pool contribution
            net_fee = fee_amount * (1 - COMMUNITY_POOL_PERCENTAGE)
            earnings.fees_collected += net_fee
            earnings.total_earned += net_fee
            self._stats["total_fees_collected"] += net_fee
        else:
            # Zero-fee processing
            earnings.zero_fee_processed += 1

            # Reputation bonus
            reputation_bonus = ZERO_FEE_REPUTATION_BONUS
            earnings.reputation_bonuses += reputation_bonus

            # Optional community subsidy
            if apply_community_subsidy and self.community_pool.balance > 0:
                # Small fixed subsidy for zero-fee
                subsidy_amount = min(10.0, self.community_pool.balance)
                if self.community_pool.disburse(subsidy_amount, contract_id, mediator_id):
                    contract.subsidy_amount = subsidy_amount
                    contract.incentive_type = IncentiveType.COMMUNITY_SUBSIDY
                    earnings.subsidies_received += subsidy_amount
                    earnings.total_earned += subsidy_amount

            self._stats["zero_fee_processed"] += 1

        earnings.contracts_processed += 1
        self._stats["total_processed"] += 1

        # Update average wait time
        wait_hours = (contract.completed_at - contract.submitted_at).total_seconds() / 3600
        total = self._stats["total_processed"]
        avg = self._stats["average_wait_hours"]
        self._stats["average_wait_hours"] = (avg * (total - 1) + wait_hours) / total

        return (
            True,
            {
                "contract_id": contract_id,
                "mediator_id": mediator_id,
                "fee_earned": fee_amount * (1 - COMMUNITY_POOL_PERCENTAGE) if fee_amount > 0 else 0,
                "subsidy_earned": subsidy_amount,
                "reputation_bonus": reputation_bonus,
                "is_zero_fee": fee_amount == 0,
                "wait_hours": wait_hours,
            },
        )

    def abandon_contract(self, contract_id: str, mediator_id: str) -> tuple[bool, str]:
        """
        Mediator abandons a claimed contract.

        Contract goes back to queue for someone else.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            return (False, f"Contract {contract_id} not found")

        if contract.claimed_by != mediator_id:
            return (False, f"Contract claimed by {contract.claimed_by}")

        # Reset to queued
        contract.status = ProcessingStatus.QUEUED
        contract.claimed_by = None
        contract.claimed_at = None
        contract.processing_reason = None

        # Re-add to heap
        heapq.heappush(self._queue, contract)

        return (True, "Contract returned to queue")

    def release_stale_claims(self) -> int:
        """
        Release contracts that were claimed but not processed in time.

        Returns number of contracts released.
        """
        released = 0
        now = datetime.utcnow()

        for contract in self._contracts.values():
            if contract.status == ProcessingStatus.CLAIMED:
                if contract.claimed_at and (now - contract.claimed_at) > self.max_claim_duration:
                    contract.status = ProcessingStatus.QUEUED
                    contract.claimed_by = None
                    contract.claimed_at = None
                    heapq.heappush(self._queue, contract)
                    released += 1

        return released

    # -------------------------------------------------------------------------
    # Earnings Management
    # -------------------------------------------------------------------------

    def _get_or_create_earnings(self, mediator_id: str) -> MediatorEarnings:
        """Get or create earnings record for mediator."""
        if mediator_id not in self._earnings:
            self._earnings[mediator_id] = MediatorEarnings(mediator_id=mediator_id)
        return self._earnings[mediator_id]

    def get_mediator_earnings(self, mediator_id: str) -> dict[str, Any]:
        """Get earnings summary for a mediator."""
        earnings = self._earnings.get(mediator_id)
        if not earnings:
            return {"mediator_id": mediator_id, "error": "No earnings record"}
        return earnings.to_dict()

    def get_top_earners(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top earning mediators."""
        sorted_earnings = sorted(
            self._earnings.values(), key=lambda e: e.total_earned, reverse=True
        )
        return [e.to_dict() for e in sorted_earnings[:limit]]

    # -------------------------------------------------------------------------
    # Community Pool
    # -------------------------------------------------------------------------

    def fund_community_pool(self, amount: float, funder_id: str) -> dict[str, Any]:
        """Add funds to community pool."""
        self.community_pool.contribute(amount, f"donation:{funder_id}")
        return {
            "success": True,
            "amount": amount,
            "funder": funder_id,
            "new_balance": self.community_pool.balance,
        }

    def add_bounty(self, contract_id: str, amount: float, funder_id: str) -> tuple[bool, str]:
        """
        Add bounty to a specific contract.

        Anyone can add a bounty to incentivize processing.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            return (False, f"Contract {contract_id} not found")

        if contract.status != ProcessingStatus.QUEUED:
            return (False, "Contract is no longer available")

        # Add to fee
        contract.fee.amount += amount
        contract.fee.is_explicit = True
        contract.incentive_type = IncentiveType.BOUNTY

        # Recalculate metrics
        contract.metrics.fee_score = min(1.0, contract.fee.amount / 1000.0)

        # Re-heapify
        heapq.heapify(self._queue)

        return (True, f"Bounty of {amount} added to contract")

    def vote_for_contract(self, contract_id: str, voter_id: str) -> bool:
        """
        Vote for a contract to increase community interest.

        Increases priority for zero-fee contracts the community cares about.
        """
        contract = self._contracts.get(contract_id)
        if not contract:
            return False

        # Increase community interest (diminishing returns)
        current = contract.metrics.community_interest
        contract.metrics.community_interest = min(1.0, current + 0.1)

        # Re-heapify
        heapq.heapify(self._queue)

        return True

    # -------------------------------------------------------------------------
    # Statistics & Reporting
    # -------------------------------------------------------------------------

    def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        queued = [c for c in self._contracts.values() if c.status == ProcessingStatus.QUEUED]
        claimed = [c for c in self._contracts.values() if c.status == ProcessingStatus.CLAIMED]

        zero_fee_queued = [c for c in queued if c.fee.amount == 0]
        paid_queued = [c for c in queued if c.fee.amount > 0]

        return {
            "total_in_queue": len(queued),
            "claimed_processing": len(claimed),
            "zero_fee_waiting": len(zero_fee_queued),
            "paid_waiting": len(paid_queued),
            "average_fee": sum(c.fee.amount for c in paid_queued) / len(paid_queued)
            if paid_queued
            else 0,
            "total_submitted": self._stats["total_submitted"],
            "total_processed": self._stats["total_processed"],
            "zero_fee_processed": self._stats["zero_fee_processed"],
            "total_fees_collected": self._stats["total_fees_collected"],
            "average_wait_hours": self._stats["average_wait_hours"],
            "community_pool_balance": self.community_pool.balance,
        }

    def get_contract_status(self, contract_id: str) -> dict[str, Any] | None:
        """Get status of a specific contract."""
        contract = self._contracts.get(contract_id)
        if not contract:
            return None
        return contract.to_dict()

    def expire_old_contracts(self) -> int:
        """
        Expire contracts that have been in queue too long.

        Returns number of expired contracts.
        """
        expired = 0
        now = datetime.utcnow()

        for contract in list(self._contracts.values()):
            if contract.status == ProcessingStatus.QUEUED:
                age = now - contract.submitted_at
                if age > self.queue_expiry:
                    contract.status = ProcessingStatus.EXPIRED
                    expired += 1

        # Remove expired from queue
        self._queue = [c for c in self._queue if c.status == ProcessingStatus.QUEUED]
        heapq.heapify(self._queue)

        return expired


# =============================================================================
# Integration with Mediator Reputation
# =============================================================================


def apply_zero_fee_reputation_bonus(
    mediator_id: str,
    reputation_manager: Any,  # MediatorReputationManager
) -> float | None:
    """
    Apply reputation bonus to mediator for processing zero-fee contract.

    Args:
        mediator_id: The mediator who processed
        reputation_manager: MediatorReputationManager instance

    Returns:
        New acceptance rate, or None if mediator not found
    """
    profile = reputation_manager.mediators.get(mediator_id)
    if not profile:
        return None

    # Boost acceptance rate slightly
    new_ar = min(1.0, profile.scores.acceptance_rate + ZERO_FEE_REPUTATION_BONUS)
    profile.scores.acceptance_rate = new_ar

    # Recalculate CTS
    profile.composite_trust_score = reputation_manager._calculate_cts(profile)

    return new_ar


# =============================================================================
# Module-level convenience
# =============================================================================

_default_queue: VoluntaryProcessingQueue | None = None


def get_processing_queue() -> VoluntaryProcessingQueue:
    """Get the default processing queue singleton."""
    global _default_queue
    if _default_queue is None:
        _default_queue = VoluntaryProcessingQueue()
    return _default_queue


def reset_processing_queue() -> None:
    """Reset the default processing queue (useful for testing)."""
    global _default_queue
    _default_queue = None


def get_fee_system_config() -> dict[str, Any]:
    """Get fee system configuration."""
    return {
        "version": "1.0",
        "fee_currency": DEFAULT_FEE_CURRENCY,
        "community_pool_percentage": COMMUNITY_POOL_PERCENTAGE,
        "zero_fee_reputation_bonus": ZERO_FEE_REPUTATION_BONUS,
        "zero_fee_age_boost_hours": ZERO_FEE_AGE_BOOST_HOURS,
        "priority_weights": PRIORITY_WEIGHTS,
        "is_mandatory": False,
        "design_principle": "Fees are tips for prioritization, not requirements. All valid contracts can be processed.",
    }
