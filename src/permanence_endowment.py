"""
NatLangChain - Permanence Endowment System

Inspired by Arweave's "pay once, store forever" economic model.

This module implements a sustainable storage funding mechanism where:
- Entry submitters pay a one-time permanence fee
- A portion goes to immediate storage costs
- The remainder goes into an endowment pool
- The endowment earns yield over time
- Yield pays for ongoing storage costs indefinitely

Key Concepts:
1. Endowment Principal: Locked funds that generate yield
2. Yield Generation: Configurable strategies (staking, lending, etc.)
3. Storage Cost Model: Estimates long-term storage costs with declining curves
4. Permanence Guarantee: Cryptographic proof of permanence commitment

Economic Model:
- Storage costs decline ~30% annually (Moore's Law for storage)
- Endowment yields ~3-5% annually (conservative DeFi yields)
- If yield > storage cost decline rate, permanence is sustainable
- 200-year horizon calculations ensure multi-generational storage
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol

# =============================================================================
# Constants
# =============================================================================

# Storage cost model constants
BYTES_PER_ENTRY_ESTIMATE = 2048  # Average entry size in bytes
STORAGE_COST_PER_GB_YEAR = 0.10  # Current cost per GB per year in USD
STORAGE_COST_DECLINE_RATE = 0.30  # 30% annual decline (conservative)
MIN_STORAGE_COST_FLOOR = 0.001  # Minimum cost floor per GB/year

# Endowment model constants
DEFAULT_YIELD_RATE = 0.04  # 4% annual yield (conservative DeFi)
MIN_YIELD_RATE = 0.01  # Minimum yield assumption for safety
MAX_YIELD_RATE = 0.10  # Maximum yield cap

# Permanence calculation constants
PERMANENCE_HORIZON_YEARS = 200  # Calculate for 200 years
SAFETY_MULTIPLIER = 1.5  # 50% safety buffer on calculations
IMMEDIATE_COST_RATIO = 0.10  # 10% for immediate storage, 90% to endowment

# Fee allocation
ENDOWMENT_FEE_RATIO = 0.90  # 90% of permanence fee to endowment
IMMEDIATE_STORAGE_RATIO = 0.10  # 10% for immediate storage costs


# =============================================================================
# Enums
# =============================================================================


class PermanenceStatus(Enum):
    """Status of an entry's permanence guarantee."""

    PENDING = "pending"  # Fee paid, not yet confirmed
    GUARANTEED = "guaranteed"  # Full permanence guarantee active
    PARTIAL = "partial"  # Partial guarantee (underfunded)
    EXPIRED = "expired"  # Guarantee expired (shouldn't happen if funded)
    REVOKED = "revoked"  # Revoked due to policy violation


class YieldStrategyType(Enum):
    """Types of yield generation strategies."""

    STAKING = "staking"  # Proof-of-stake yields
    LENDING = "lending"  # DeFi lending protocols
    LIQUIDITY = "liquidity"  # Liquidity provision
    TREASURY_BILLS = "treasury_bills"  # Traditional T-bills (hybrid)
    COMPOSITE = "composite"  # Multiple strategies combined


class EndowmentEventType(Enum):
    """Types of endowment events."""

    DEPOSIT = "deposit"
    YIELD_ACCRUAL = "yield_accrual"
    STORAGE_PAYOUT = "storage_payout"
    REBALANCE = "rebalance"
    GUARANTEE_ISSUED = "guarantee_issued"
    GUARANTEE_RENEWED = "guarantee_renewed"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StorageCostProjection:
    """Projected storage costs over time."""

    entry_size_bytes: int
    current_annual_cost: float
    total_lifetime_cost: float  # NPV of all future costs
    required_endowment: float  # Amount needed to fund forever
    years_projected: int
    cost_by_decade: dict[int, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_size_bytes": self.entry_size_bytes,
            "current_annual_cost": round(self.current_annual_cost, 8),
            "total_lifetime_cost": round(self.total_lifetime_cost, 6),
            "required_endowment": round(self.required_endowment, 6),
            "years_projected": self.years_projected,
            "cost_by_decade": {k: round(v, 6) for k, v in self.cost_by_decade.items()},
        }


@dataclass
class PermanenceGuarantee:
    """Cryptographic guarantee of entry permanence."""

    guarantee_id: str
    entry_hash: str
    entry_size_bytes: int
    fee_paid: float
    endowment_allocated: float
    immediate_storage_paid: float
    status: str
    created_at: str
    expires_at: str | None  # None = perpetual
    yield_strategy: str
    projected_sustainability_years: int
    guarantee_hash: str  # Cryptographic commitment

    def to_dict(self) -> dict[str, Any]:
        return {
            "guarantee_id": self.guarantee_id,
            "entry_hash": self.entry_hash,
            "entry_size_bytes": self.entry_size_bytes,
            "fee_paid": self.fee_paid,
            "endowment_allocated": self.endowment_allocated,
            "immediate_storage_paid": self.immediate_storage_paid,
            "status": self.status,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "yield_strategy": self.yield_strategy,
            "projected_sustainability_years": self.projected_sustainability_years,
            "guarantee_hash": self.guarantee_hash,
        }


@dataclass
class YieldAccrual:
    """Record of yield accrued on endowment."""

    accrual_id: str
    period_start: str
    period_end: str
    principal_at_start: float
    yield_rate: float
    yield_amount: float
    strategy: str
    reinvested: bool


@dataclass
class StoragePayout:
    """Record of storage cost payout from endowment."""

    payout_id: str
    period: str
    storage_provider: str
    entries_covered: int
    bytes_stored: int
    amount: float
    funded_from: str  # "yield" or "principal"


# =============================================================================
# Protocols (Interfaces)
# =============================================================================


class YieldStrategy(Protocol):
    """Protocol for yield generation strategies."""

    def get_current_rate(self) -> float:
        """Get current annual yield rate."""
        ...

    def calculate_yield(self, principal: float, days: int) -> float:
        """Calculate yield for given principal and time period."""
        ...

    def get_strategy_type(self) -> YieldStrategyType:
        """Get the strategy type."""
        ...


# =============================================================================
# Yield Strategy Implementations
# =============================================================================


class ConservativeYieldStrategy:
    """
    Conservative yield strategy using blended DeFi yields.

    Assumes a diversified approach:
    - 40% staking (3-5% APY)
    - 30% lending (2-4% APY)
    - 30% stable liquidity (1-3% APY)

    Conservative estimate: 3% base + market adjustment
    """

    def __init__(self, base_rate: float = 0.03, market_adjustment: float = 0.01):
        self.base_rate = base_rate
        self.market_adjustment = market_adjustment
        self._rate_history: list[dict] = []

    def get_current_rate(self) -> float:
        """Get current blended yield rate."""
        rate = self.base_rate + self.market_adjustment
        return max(MIN_YIELD_RATE, min(rate, MAX_YIELD_RATE))

    def calculate_yield(self, principal: float, days: int) -> float:
        """Calculate yield using daily compounding."""
        daily_rate = self.get_current_rate() / 365
        return principal * ((1 + daily_rate) ** days - 1)

    def get_strategy_type(self) -> YieldStrategyType:
        return YieldStrategyType.COMPOSITE

    def update_market_conditions(self, adjustment: float) -> None:
        """Update market adjustment factor."""
        self.market_adjustment = max(-0.02, min(adjustment, 0.03))
        self._rate_history.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "rate": self.get_current_rate(),
                "adjustment": adjustment,
            }
        )


# =============================================================================
# Storage Cost Estimator
# =============================================================================


class StorageCostEstimator:
    """
    Estimates long-term storage costs with declining cost curves.

    Based on historical trends:
    - Storage costs have declined ~30% annually
    - Trend expected to continue due to technology improvements
    - Uses NPV calculations to determine total lifetime cost
    """

    def __init__(
        self,
        current_cost_per_gb_year: float = STORAGE_COST_PER_GB_YEAR,
        decline_rate: float = STORAGE_COST_DECLINE_RATE,
        cost_floor: float = MIN_STORAGE_COST_FLOOR,
    ):
        self.current_cost_per_gb_year = current_cost_per_gb_year
        self.decline_rate = decline_rate
        self.cost_floor = cost_floor

    def estimate_annual_cost(self, size_bytes: int, years_from_now: int = 0) -> float:
        """
        Estimate annual storage cost for given size at future year.

        Args:
            size_bytes: Size of data in bytes
            years_from_now: Years into the future

        Returns:
            Annual storage cost in USD
        """
        size_gb = size_bytes / (1024**3)

        # Apply declining cost curve
        future_cost_per_gb = self.current_cost_per_gb_year * (
            (1 - self.decline_rate) ** years_from_now
        )

        # Apply cost floor
        future_cost_per_gb = max(future_cost_per_gb, self.cost_floor)

        return size_gb * future_cost_per_gb

    def calculate_lifetime_cost(
        self, size_bytes: int, horizon_years: int = PERMANENCE_HORIZON_YEARS
    ) -> StorageCostProjection:
        """
        Calculate total lifetime storage cost using NPV.

        Uses declining cost curve and sums all annual costs.

        Args:
            size_bytes: Size of data in bytes
            horizon_years: Years to project

        Returns:
            StorageCostProjection with detailed breakdown
        """
        total_cost = 0.0
        cost_by_decade = {}
        current_decade_cost = 0.0

        for year in range(horizon_years):
            annual_cost = self.estimate_annual_cost(size_bytes, year)
            total_cost += annual_cost

            current_decade_cost += annual_cost

            # Record decade summaries
            if (year + 1) % 10 == 0:
                decade = (year + 1) // 10
                cost_by_decade[decade * 10] = current_decade_cost
                current_decade_cost = 0.0

        # Add remaining years to last decade
        if current_decade_cost > 0:
            last_decade = ((horizon_years - 1) // 10 + 1) * 10
            cost_by_decade[last_decade] = current_decade_cost

        current_annual = self.estimate_annual_cost(size_bytes, 0)

        return StorageCostProjection(
            entry_size_bytes=size_bytes,
            current_annual_cost=current_annual,
            total_lifetime_cost=total_cost,
            required_endowment=total_cost * SAFETY_MULTIPLIER,
            years_projected=horizon_years,
            cost_by_decade=cost_by_decade,
        )

    def calculate_required_endowment(
        self, size_bytes: int, yield_rate: float, horizon_years: int = PERMANENCE_HORIZON_YEARS
    ) -> float:
        """
        Calculate endowment required to fund storage perpetually.

        Uses the formula:
        If yield_rate > cost_decline_rate: perpetual funding is possible
        Required = First_Year_Cost / (yield_rate - cost_decline_rate + small_buffer)

        Args:
            size_bytes: Size of data in bytes
            yield_rate: Expected annual yield rate
            horizon_years: Backup horizon if perpetual not possible

        Returns:
            Required endowment amount in USD
        """
        first_year_cost = self.estimate_annual_cost(size_bytes, 0)

        # Effective rate difference
        effective_rate = yield_rate - (1 - (1 - self.decline_rate))

        if effective_rate > 0.005:  # Perpetual is possible
            # Present value of perpetuity with growing payments
            # PV = C / (r - g) where g is negative (costs declining)
            required = first_year_cost / effective_rate
        else:
            # Fall back to NPV calculation
            projection = self.calculate_lifetime_cost(size_bytes, horizon_years)
            required = projection.total_lifetime_cost

        return required * SAFETY_MULTIPLIER


# =============================================================================
# Main Endowment Pool
# =============================================================================


class PermanenceEndowment:
    """
    Manages the permanence endowment pool for NatLangChain.

    Inspired by Arweave's economic model:
    - One-time fee for permanent storage
    - Endowment generates yield to pay ongoing costs
    - Storage costs decline over time (Moore's Law)
    - Yield exceeds cost decline = sustainable permanence

    Key Features:
    - Transparent fund management with full audit trail
    - Cryptographic permanence guarantees
    - Configurable yield strategies
    - Storage provider payment system
    - Sustainability projections and health metrics
    """

    def __init__(
        self,
        yield_strategy: YieldStrategy | None = None,
        cost_estimator: StorageCostEstimator | None = None,
        initial_principal: float = 0.0,
    ):
        """
        Initialize the permanence endowment.

        Args:
            yield_strategy: Strategy for generating yield
            cost_estimator: Storage cost estimator
            initial_principal: Initial endowment principal
        """
        self.yield_strategy = yield_strategy or ConservativeYieldStrategy()
        self.cost_estimator = cost_estimator or StorageCostEstimator()

        # Fund tracking
        self.principal = initial_principal
        self.accrued_yield = 0.0
        self.total_deposits = 0.0
        self.total_payouts = 0.0
        self.total_yield_generated = 0.0

        # Guarantee tracking
        self.guarantees: dict[str, PermanenceGuarantee] = {}
        self.entry_to_guarantee: dict[str, str] = {}  # entry_hash -> guarantee_id

        # Historical records
        self.yield_accruals: list[YieldAccrual] = []
        self.storage_payouts: list[StoragePayout] = []
        self.events: list[dict[str, Any]] = []

        # Metrics
        self.total_bytes_guaranteed = 0
        self.total_entries_guaranteed = 0
        self.last_yield_accrual: str | None = None
        self.last_storage_payout: str | None = None

    # =========================================================================
    # Core Endowment Operations
    # =========================================================================

    def calculate_permanence_fee(self, entry_size_bytes: int) -> dict[str, Any]:
        """
        Calculate the one-time fee for permanent storage.

        Args:
            entry_size_bytes: Size of entry in bytes

        Returns:
            Fee breakdown with endowment allocation
        """
        yield_rate = self.yield_strategy.get_current_rate()

        # Calculate required endowment
        required_endowment = self.cost_estimator.calculate_required_endowment(
            entry_size_bytes, yield_rate
        )

        # Total fee includes safety buffer
        total_fee = required_endowment / ENDOWMENT_FEE_RATIO

        # Breakdown
        endowment_portion = total_fee * ENDOWMENT_FEE_RATIO
        immediate_portion = total_fee * IMMEDIATE_STORAGE_RATIO

        # Get cost projection for transparency
        projection = self.cost_estimator.calculate_lifetime_cost(entry_size_bytes)

        return {
            "entry_size_bytes": entry_size_bytes,
            "total_fee": round(total_fee, 6),
            "fee_breakdown": {
                "endowment_allocation": round(endowment_portion, 6),
                "immediate_storage": round(immediate_portion, 6),
            },
            "storage_projection": projection.to_dict(),
            "yield_assumptions": {
                "current_rate": yield_rate,
                "strategy": self.yield_strategy.get_strategy_type().value,
            },
            "sustainability": {
                "projected_years": PERMANENCE_HORIZON_YEARS,
                "safety_multiplier": SAFETY_MULTIPLIER,
            },
        }

    def deposit_for_permanence(
        self,
        entry_hash: str,
        entry_size_bytes: int,
        fee_amount: float,
        payer: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Deposit fee and create permanence guarantee.

        Args:
            entry_hash: Hash of the entry being guaranteed
            entry_size_bytes: Size of entry in bytes
            fee_amount: Amount paid for permanence
            payer: Address/identifier of payer
            metadata: Optional additional metadata

        Returns:
            Tuple of (success, result with guarantee details)
        """
        # Check if entry already has guarantee
        if entry_hash in self.entry_to_guarantee:
            existing_id = self.entry_to_guarantee[entry_hash]
            return False, {
                "error": "Entry already has permanence guarantee",
                "existing_guarantee_id": existing_id,
            }

        # Calculate required fee
        fee_calc = self.calculate_permanence_fee(entry_size_bytes)
        required_fee = fee_calc["total_fee"]

        # Determine guarantee status based on funding
        if fee_amount >= required_fee:
            status = PermanenceStatus.GUARANTEED
            sustainability_years = PERMANENCE_HORIZON_YEARS
        elif fee_amount >= required_fee * 0.5:
            status = PermanenceStatus.PARTIAL
            sustainability_years = int(PERMANENCE_HORIZON_YEARS * (fee_amount / required_fee))
        else:
            return False, {
                "error": "Insufficient fee for permanence guarantee",
                "required_minimum": round(required_fee * 0.5, 6),
                "provided": fee_amount,
            }

        # Allocate fee
        endowment_amount = fee_amount * ENDOWMENT_FEE_RATIO
        immediate_amount = fee_amount * IMMEDIATE_STORAGE_RATIO

        # Generate guarantee
        guarantee_id = self._generate_guarantee_id(entry_hash, fee_amount)
        guarantee_hash = self._generate_guarantee_hash(
            entry_hash, entry_size_bytes, fee_amount, guarantee_id
        )

        guarantee = PermanenceGuarantee(
            guarantee_id=guarantee_id,
            entry_hash=entry_hash,
            entry_size_bytes=entry_size_bytes,
            fee_paid=fee_amount,
            endowment_allocated=endowment_amount,
            immediate_storage_paid=immediate_amount,
            status=status.value,
            created_at=datetime.utcnow().isoformat(),
            expires_at=None
            if status == PermanenceStatus.GUARANTEED
            else self._calculate_expiry(sustainability_years),
            yield_strategy=self.yield_strategy.get_strategy_type().value,
            projected_sustainability_years=sustainability_years,
            guarantee_hash=guarantee_hash,
        )

        # Update state
        self.principal += endowment_amount
        self.total_deposits += fee_amount
        self.total_bytes_guaranteed += entry_size_bytes
        self.total_entries_guaranteed += 1

        self.guarantees[guarantee_id] = guarantee
        self.entry_to_guarantee[entry_hash] = guarantee_id

        # Emit event
        self._emit_event(
            EndowmentEventType.DEPOSIT,
            {
                "guarantee_id": guarantee_id,
                "entry_hash": entry_hash,
                "fee_paid": fee_amount,
                "endowment_allocated": endowment_amount,
                "status": status.value,
                "payer": payer,
            },
        )

        self._emit_event(
            EndowmentEventType.GUARANTEE_ISSUED,
            {
                "guarantee_id": guarantee_id,
                "entry_hash": entry_hash,
                "status": status.value,
                "sustainability_years": sustainability_years,
                "guarantee_hash": guarantee_hash,
            },
        )

        return True, {
            "status": "success",
            "guarantee": guarantee.to_dict(),
            "pool_status": self.get_pool_status(),
            "message": f"Permanence guarantee issued: {status.value}",
        }

    def top_up_guarantee(
        self, entry_hash: str, additional_fee: float, payer: str
    ) -> tuple[bool, dict[str, Any]]:
        """
        Top up an existing partial guarantee.

        Args:
            entry_hash: Hash of the entry
            additional_fee: Additional fee to add
            payer: Address/identifier of payer

        Returns:
            Tuple of (success, result)
        """
        if entry_hash not in self.entry_to_guarantee:
            return False, {"error": "No existing guarantee for entry"}

        guarantee_id = self.entry_to_guarantee[entry_hash]
        guarantee = self.guarantees[guarantee_id]

        if guarantee.status == PermanenceStatus.GUARANTEED.value:
            return False, {"error": "Guarantee already at full permanence status"}

        # Calculate new totals
        new_total_fee = guarantee.fee_paid + additional_fee
        endowment_addition = additional_fee * ENDOWMENT_FEE_RATIO

        # Recalculate sustainability
        fee_calc = self.calculate_permanence_fee(guarantee.entry_size_bytes)
        required_fee = fee_calc["total_fee"]

        if new_total_fee >= required_fee:
            new_status = PermanenceStatus.GUARANTEED
            new_sustainability = PERMANENCE_HORIZON_YEARS
            new_expires = None
        else:
            new_status = PermanenceStatus.PARTIAL
            new_sustainability = int(PERMANENCE_HORIZON_YEARS * (new_total_fee / required_fee))
            new_expires = self._calculate_expiry(new_sustainability)

        # Update guarantee
        guarantee.fee_paid = new_total_fee
        guarantee.endowment_allocated += endowment_addition
        guarantee.status = new_status.value
        guarantee.expires_at = new_expires
        guarantee.projected_sustainability_years = new_sustainability

        # Update pool
        self.principal += endowment_addition
        self.total_deposits += additional_fee

        self._emit_event(
            EndowmentEventType.GUARANTEE_RENEWED,
            {
                "guarantee_id": guarantee_id,
                "entry_hash": entry_hash,
                "additional_fee": additional_fee,
                "new_status": new_status.value,
                "new_sustainability_years": new_sustainability,
                "payer": payer,
            },
        )

        return True, {
            "status": "success",
            "guarantee": guarantee.to_dict(),
            "upgrade_summary": {
                "previous_status": PermanenceStatus.PARTIAL.value,
                "new_status": new_status.value,
                "additional_fee_paid": additional_fee,
                "new_sustainability_years": new_sustainability,
            },
        }

    # =========================================================================
    # Yield Management
    # =========================================================================

    def accrue_yield(self, days_elapsed: int | None = None) -> dict[str, Any]:
        """
        Accrue yield on the endowment principal.

        Should be called periodically (daily, weekly, or on-demand).

        Args:
            days_elapsed: Days since last accrual (auto-calculated if None)

        Returns:
            Yield accrual details
        """
        now = datetime.utcnow()

        if days_elapsed is None:
            if self.last_yield_accrual:
                last = datetime.fromisoformat(self.last_yield_accrual)
                days_elapsed = (now - last).days
            else:
                days_elapsed = 1  # First accrual

        if days_elapsed <= 0:
            return {"status": "no_accrual_needed", "days_elapsed": 0}

        # Calculate yield
        yield_amount = self.yield_strategy.calculate_yield(self.principal, days_elapsed)
        yield_rate = self.yield_strategy.get_current_rate()

        # Record accrual
        accrual_id = self._generate_accrual_id(yield_amount)
        accrual = YieldAccrual(
            accrual_id=accrual_id,
            period_start=self.last_yield_accrual or now.isoformat(),
            period_end=now.isoformat(),
            principal_at_start=self.principal,
            yield_rate=yield_rate,
            yield_amount=yield_amount,
            strategy=self.yield_strategy.get_strategy_type().value,
            reinvested=True,
        )

        self.yield_accruals.append(accrual)

        # Update state - reinvest yield into principal
        self.accrued_yield += yield_amount
        self.total_yield_generated += yield_amount
        self.principal += yield_amount  # Compound
        self.last_yield_accrual = now.isoformat()

        self._emit_event(
            EndowmentEventType.YIELD_ACCRUAL,
            {
                "accrual_id": accrual_id,
                "days_elapsed": days_elapsed,
                "yield_amount": yield_amount,
                "yield_rate": yield_rate,
                "new_principal": self.principal,
            },
        )

        return {
            "status": "accrued",
            "accrual_id": accrual_id,
            "days_elapsed": days_elapsed,
            "yield_amount": round(yield_amount, 8),
            "yield_rate": yield_rate,
            "new_principal": round(self.principal, 6),
            "total_yield_generated": round(self.total_yield_generated, 6),
        }

    def process_storage_payout(
        self, storage_provider: str, entries_stored: int, bytes_stored: int
    ) -> tuple[bool, dict[str, Any]]:
        """
        Process payout to storage provider for storing entries.

        Args:
            storage_provider: Identifier of storage provider
            entries_stored: Number of entries stored
            bytes_stored: Total bytes stored

        Returns:
            Tuple of (success, payout details)
        """
        # Calculate payout based on current storage costs
        payout_amount = self.cost_estimator.estimate_annual_cost(bytes_stored, 0) / 12  # Monthly

        # Determine funding source
        if self.accrued_yield >= payout_amount:
            funded_from = "yield"
            self.accrued_yield -= payout_amount
        elif self.principal >= payout_amount:
            funded_from = "principal"
            self.principal -= payout_amount
        else:
            return False, {
                "error": "Insufficient funds for storage payout",
                "required": payout_amount,
                "available_yield": self.accrued_yield,
                "available_principal": self.principal,
            }

        self.total_payouts += payout_amount

        # Record payout
        payout_id = self._generate_payout_id(storage_provider, payout_amount)
        period = datetime.utcnow().strftime("%Y-%m")

        payout = StoragePayout(
            payout_id=payout_id,
            period=period,
            storage_provider=storage_provider,
            entries_covered=entries_stored,
            bytes_stored=bytes_stored,
            amount=payout_amount,
            funded_from=funded_from,
        )

        self.storage_payouts.append(payout)
        self.last_storage_payout = datetime.utcnow().isoformat()

        self._emit_event(
            EndowmentEventType.STORAGE_PAYOUT,
            {
                "payout_id": payout_id,
                "storage_provider": storage_provider,
                "amount": payout_amount,
                "entries_covered": entries_stored,
                "bytes_stored": bytes_stored,
                "funded_from": funded_from,
            },
        )

        return True, {
            "status": "paid",
            "payout_id": payout_id,
            "amount": round(payout_amount, 8),
            "storage_provider": storage_provider,
            "entries_covered": entries_stored,
            "bytes_stored": bytes_stored,
            "funded_from": funded_from,
            "remaining_yield": round(self.accrued_yield, 6),
            "remaining_principal": round(self.principal, 6),
        }

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_guarantee(self, entry_hash: str) -> dict[str, Any] | None:
        """Get permanence guarantee for an entry."""
        if entry_hash not in self.entry_to_guarantee:
            return None

        guarantee_id = self.entry_to_guarantee[entry_hash]
        return self.guarantees[guarantee_id].to_dict()

    def verify_guarantee(self, entry_hash: str, guarantee_hash: str) -> dict[str, Any]:
        """
        Verify a permanence guarantee cryptographically.

        Args:
            entry_hash: Hash of the entry
            guarantee_hash: Claimed guarantee hash

        Returns:
            Verification result
        """
        if entry_hash not in self.entry_to_guarantee:
            return {"valid": False, "error": "No guarantee found for entry"}

        guarantee_id = self.entry_to_guarantee[entry_hash]
        guarantee = self.guarantees[guarantee_id]

        if guarantee.guarantee_hash != guarantee_hash:
            return {
                "valid": False,
                "error": "Guarantee hash mismatch",
                "expected": guarantee.guarantee_hash,
                "provided": guarantee_hash,
            }

        return {
            "valid": True,
            "guarantee": guarantee.to_dict(),
            "verification_time": datetime.utcnow().isoformat(),
        }

    def get_pool_status(self) -> dict[str, Any]:
        """Get current status of the endowment pool."""
        yield_rate = self.yield_strategy.get_current_rate()
        annual_yield_projection = self.principal * yield_rate

        # Calculate storage cost projection
        annual_storage_cost = self.cost_estimator.estimate_annual_cost(
            self.total_bytes_guaranteed, 0
        )

        # Sustainability ratio
        sustainability_ratio = (
            annual_yield_projection / annual_storage_cost
            if annual_storage_cost > 0
            else float("inf")
        )

        return {
            "principal": round(self.principal, 6),
            "accrued_yield": round(self.accrued_yield, 6),
            "total_funds": round(self.principal + self.accrued_yield, 6),
            "total_deposits": round(self.total_deposits, 6),
            "total_payouts": round(self.total_payouts, 6),
            "total_yield_generated": round(self.total_yield_generated, 6),
            "entries_guaranteed": self.total_entries_guaranteed,
            "bytes_guaranteed": self.total_bytes_guaranteed,
            "yield_rate": yield_rate,
            "annual_yield_projection": round(annual_yield_projection, 6),
            "annual_storage_cost": round(annual_storage_cost, 8),
            "sustainability_ratio": round(sustainability_ratio, 2),
            "health_status": self._calculate_health_status(sustainability_ratio),
            "last_yield_accrual": self.last_yield_accrual,
            "last_storage_payout": self.last_storage_payout,
        }

    def get_sustainability_report(self) -> dict[str, Any]:
        """
        Generate comprehensive sustainability report.

        Returns:
            Detailed sustainability analysis
        """
        yield_rate = self.yield_strategy.get_current_rate()

        # Project 10-year outlook
        projections = []
        principal = self.principal
        bytes_stored = self.total_bytes_guaranteed

        for year in range(1, 11):
            annual_yield = principal * yield_rate
            annual_cost = self.cost_estimator.estimate_annual_cost(bytes_stored, year - 1)

            net_position = annual_yield - annual_cost
            principal = principal + net_position  # Simplified projection

            projections.append(
                {
                    "year": year,
                    "projected_principal": round(principal, 2),
                    "annual_yield": round(annual_yield, 4),
                    "annual_cost": round(annual_cost, 6),
                    "net_position": round(net_position, 4),
                    "sustainable": net_position >= 0,
                }
            )

        # Calculate years until depletion (if any)
        years_sustainable = PERMANENCE_HORIZON_YEARS
        for i, proj in enumerate(projections):
            if proj["projected_principal"] <= 0:
                years_sustainable = i
                break

        return {
            "current_status": self.get_pool_status(),
            "yield_assumptions": {
                "current_rate": yield_rate,
                "strategy": self.yield_strategy.get_strategy_type().value,
                "min_assumed": MIN_YIELD_RATE,
            },
            "cost_assumptions": {
                "current_cost_per_gb": STORAGE_COST_PER_GB_YEAR,
                "annual_decline_rate": STORAGE_COST_DECLINE_RATE,
                "cost_floor": MIN_STORAGE_COST_FLOOR,
            },
            "ten_year_projection": projections,
            "sustainability_summary": {
                "years_projected_sustainable": years_sustainable,
                "is_perpetually_sustainable": years_sustainable >= PERMANENCE_HORIZON_YEARS,
                "confidence": "high"
                if years_sustainable >= 50
                else "medium"
                if years_sustainable >= 20
                else "low",
            },
            "recommendations": self._generate_recommendations(projections),
        }

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive endowment statistics."""
        guarantee_status_counts = {}
        for g in self.guarantees.values():
            status = g.status
            guarantee_status_counts[status] = guarantee_status_counts.get(status, 0) + 1

        return {
            "pool": self.get_pool_status(),
            "guarantees": {
                "total": len(self.guarantees),
                "by_status": guarantee_status_counts,
                "total_entries": self.total_entries_guaranteed,
                "total_bytes": self.total_bytes_guaranteed,
                "average_entry_size": (
                    self.total_bytes_guaranteed / self.total_entries_guaranteed
                    if self.total_entries_guaranteed > 0
                    else 0
                ),
            },
            "yield_history": {
                "total_accruals": len(self.yield_accruals),
                "total_generated": self.total_yield_generated,
                "average_rate": (
                    sum(a.yield_rate for a in self.yield_accruals) / len(self.yield_accruals)
                    if self.yield_accruals
                    else 0
                ),
            },
            "payouts": {
                "total_count": len(self.storage_payouts),
                "total_amount": self.total_payouts,
                "from_yield": sum(
                    p.amount for p in self.storage_payouts if p.funded_from == "yield"
                ),
                "from_principal": sum(
                    p.amount for p in self.storage_payouts if p.funded_from == "principal"
                ),
            },
            "events_count": len(self.events),
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_guarantee_id(self, entry_hash: str, fee: float) -> str:
        """Generate unique guarantee ID."""
        data = f"{entry_hash}:{fee}:{datetime.utcnow().isoformat()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:12]
        return f"PERM-{hash_val.upper()}"

    def _generate_guarantee_hash(
        self, entry_hash: str, size_bytes: int, fee: float, guarantee_id: str
    ) -> str:
        """Generate cryptographic guarantee hash."""
        data = {
            "entry_hash": entry_hash,
            "size_bytes": size_bytes,
            "fee": str(fee),
            "guarantee_id": guarantee_id,
            "timestamp": datetime.utcnow().isoformat(),
            "yield_rate": self.yield_strategy.get_current_rate(),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return "0x" + hashlib.sha256(hash_input.encode()).hexdigest()

    def _generate_accrual_id(self, amount: float) -> str:
        """Generate unique accrual ID."""
        data = f"accrual:{amount}:{datetime.utcnow().isoformat()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:10]
        return f"YIELD-{hash_val.upper()}"

    def _generate_payout_id(self, provider: str, amount: float) -> str:
        """Generate unique payout ID."""
        data = f"payout:{provider}:{amount}:{datetime.utcnow().isoformat()}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()[:10]
        return f"PAY-{hash_val.upper()}"

    def _calculate_expiry(self, years: int) -> str:
        """Calculate expiry date from years."""
        expiry = datetime.utcnow() + timedelta(days=years * 365)
        return expiry.isoformat()

    def _calculate_health_status(self, sustainability_ratio: float) -> str:
        """Calculate pool health status."""
        if sustainability_ratio >= 2.0:
            return "excellent"
        elif sustainability_ratio >= 1.5:
            return "healthy"
        elif sustainability_ratio >= 1.0:
            return "stable"
        elif sustainability_ratio >= 0.8:
            return "warning"
        else:
            return "critical"

    def _generate_recommendations(self, projections: list[dict]) -> list[str]:
        """Generate recommendations based on projections."""
        recommendations = []

        # Check sustainability
        negative_years = [p for p in projections if not p["sustainable"]]
        if negative_years:
            recommendations.append(
                f"Warning: Projected deficit starting year {negative_years[0]['year']}. "
                "Consider increasing permanence fees or diversifying yield strategy."
            )

        # Check yield
        current_rate = self.yield_strategy.get_current_rate()
        if current_rate < 0.03:
            recommendations.append(
                "Yield rate below 3%. Consider reviewing yield strategy diversification."
            )

        # Check principal
        if self.principal < 1000:
            recommendations.append(
                "Low principal balance. Endowment may benefit from additional deposits."
            )

        # Check ratio of yield to principal payouts
        from_principal = sum(p.amount for p in self.storage_payouts if p.funded_from == "principal")
        if from_principal > self.total_payouts * 0.2:
            recommendations.append("Over 20% of payouts from principal. Yield may be insufficient.")

        if not recommendations:
            recommendations.append("Endowment is healthy. No immediate action required.")

        return recommendations

    def _emit_event(self, event_type: EndowmentEventType, data: dict[str, Any]) -> None:
        """Emit an event for audit trail."""
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        self.events.append(event)

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize endowment state to dictionary."""
        return {
            "principal": self.principal,
            "accrued_yield": self.accrued_yield,
            "total_deposits": self.total_deposits,
            "total_payouts": self.total_payouts,
            "total_yield_generated": self.total_yield_generated,
            "total_bytes_guaranteed": self.total_bytes_guaranteed,
            "total_entries_guaranteed": self.total_entries_guaranteed,
            "last_yield_accrual": self.last_yield_accrual,
            "last_storage_payout": self.last_storage_payout,
            "guarantees": {k: v.to_dict() for k, v in self.guarantees.items()},
            "entry_to_guarantee": self.entry_to_guarantee,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PermanenceEndowment":
        """Deserialize endowment from dictionary."""
        endowment = cls(initial_principal=data.get("principal", 0.0))
        endowment.accrued_yield = data.get("accrued_yield", 0.0)
        endowment.total_deposits = data.get("total_deposits", 0.0)
        endowment.total_payouts = data.get("total_payouts", 0.0)
        endowment.total_yield_generated = data.get("total_yield_generated", 0.0)
        endowment.total_bytes_guaranteed = data.get("total_bytes_guaranteed", 0)
        endowment.total_entries_guaranteed = data.get("total_entries_guaranteed", 0)
        endowment.last_yield_accrual = data.get("last_yield_accrual")
        endowment.last_storage_payout = data.get("last_storage_payout")
        endowment.entry_to_guarantee = data.get("entry_to_guarantee", {})

        # Restore guarantees
        for gid, gdata in data.get("guarantees", {}).items():
            endowment.guarantees[gid] = PermanenceGuarantee(**gdata)

        return endowment
