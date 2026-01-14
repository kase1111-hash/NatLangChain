"""
NatLangChain - Revenue Sharing & Royalty Distribution

Implements programmable royalties for derivative intent chains,
inspired by Story Protocol's IP royalty system.

Key Concepts:
- Original content creators earn royalties from derivatives
- Royalty rates are configurable per entry/contract
- Revenue flows up the derivative chain automatically
- Supports multiple royalty tiers (direct, indirect)
- Transparent on-chain tracking of all payments

Use Cases:
- Contract template creators earn when templates are used
- Original intent authors earn from amendments/extensions
- Collaborative revenue sharing in multi-party derivatives
- Automated creator economy for natural language assets
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Default royalty rates (as percentages)
DEFAULT_ROYALTY_RATE = Decimal("5.0")  # 5% default royalty
MAX_ROYALTY_RATE = Decimal("50.0")  # Max 50% royalty
MIN_ROYALTY_RATE = Decimal("0.0")  # Can be 0 (no royalty)

# Chain depth configuration
MAX_ROYALTY_DEPTH = 10  # Max depth for royalty propagation
DEPTH_DECAY_FACTOR = Decimal("0.5")  # Each level gets 50% of previous

# Revenue pool configuration
MIN_DISTRIBUTION_AMOUNT = Decimal("0.01")  # Minimum claimable amount
CLAIM_EXPIRY_DAYS = 365  # Claims expire after 1 year

# Currency precision
CURRENCY_DECIMAL_PLACES = 8


# =============================================================================
# Enums
# =============================================================================


class RoyaltyType(Enum):
    """Types of royalty configurations."""

    FIXED = "fixed"  # Fixed percentage
    TIERED = "tiered"  # Different rates by derivative type
    SPLIT = "split"  # Split among multiple recipients
    NONE = "none"  # No royalties


class RevenueEventType(Enum):
    """Types of revenue-generating events."""

    DERIVATIVE_CREATED = "derivative_created"  # New derivative registered
    CONTRACT_EXECUTED = "contract_executed"  # Contract fulfilled
    LICENSE_PURCHASED = "license_purchased"  # License/access purchased
    TIP = "tip"  # Voluntary tip/donation
    BOUNTY = "bounty"  # Bounty fulfilled
    MARKETPLACE_SALE = "marketplace_sale"  # Sold in marketplace
    CUSTOM = "custom"  # Custom event


class PaymentStatus(Enum):
    """Status of royalty payments."""

    PENDING = "pending"  # Calculated but not distributed
    DISTRIBUTED = "distributed"  # Sent to recipient pool
    CLAIMED = "claimed"  # Claimed by recipient
    EXPIRED = "expired"  # Expired unclaimed
    FAILED = "failed"  # Distribution failed


class ClaimStatus(Enum):
    """Status of revenue claims."""

    AVAILABLE = "available"  # Can be claimed
    CLAIMED = "claimed"  # Already claimed
    EXPIRED = "expired"  # Claim expired
    PENDING = "pending"  # Processing


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RoyaltyConfig:
    """Royalty configuration for an entry/contract."""

    config_id: str
    entry_ref: dict[str, int]  # {block_index, entry_index}
    owner: str  # DID of the owner
    royalty_type: RoyaltyType = RoyaltyType.FIXED
    # Base royalty rate (percentage)
    base_rate: Decimal = field(default_factory=lambda: DEFAULT_ROYALTY_RATE)
    # Tiered rates by derivative type
    tiered_rates: dict[str, Decimal] = field(default_factory=dict)
    # Split recipients (DID -> percentage)
    split_recipients: dict[str, Decimal] = field(default_factory=dict)
    # Whether royalties propagate through derivative chains
    chain_propagation: bool = True
    # Maximum depth for propagation
    max_depth: int = MAX_ROYALTY_DEPTH
    # Decay factor per level
    depth_decay: Decimal = field(default_factory=lambda: DEPTH_DECAY_FACTOR)
    # Minimum payment threshold
    min_payment: Decimal = field(default_factory=lambda: MIN_DISTRIBUTION_AMOUNT)
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True

    def get_rate_for_type(self, derivative_type: str) -> Decimal:
        """Get the royalty rate for a specific derivative type."""
        if self.royalty_type == RoyaltyType.NONE:
            return Decimal("0")
        if self.royalty_type == RoyaltyType.TIERED and derivative_type in self.tiered_rates:
            return self.tiered_rates[derivative_type]
        return self.base_rate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "config_id": self.config_id,
            "entry_ref": self.entry_ref,
            "owner": self.owner,
            "royalty_type": self.royalty_type.value,
            "base_rate": str(self.base_rate),
            "tiered_rates": {k: str(v) for k, v in self.tiered_rates.items()},
            "split_recipients": {k: str(v) for k, v in self.split_recipients.items()},
            "chain_propagation": self.chain_propagation,
            "max_depth": self.max_depth,
            "depth_decay": str(self.depth_decay),
            "min_payment": str(self.min_payment),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }


@dataclass
class RevenueEvent:
    """A revenue-generating event."""

    event_id: str
    event_type: RevenueEventType
    # Source of the revenue
    source_entry_ref: dict[str, int]  # Entry that generated revenue
    # Amount and currency
    amount: Decimal
    currency: str = "NLC"  # Native token or other
    # Payer info
    payer: str | None = None  # DID of payer
    # Event metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    derivative_type: str | None = None  # If triggered by derivative
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_entry_ref": self.source_entry_ref,
            "amount": str(self.amount),
            "currency": self.currency,
            "payer": self.payer,
            "metadata": self.metadata,
            "derivative_type": self.derivative_type,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
        }


@dataclass
class RoyaltyPayment:
    """A calculated royalty payment."""

    payment_id: str
    event_id: str  # Revenue event that triggered this
    # Recipient info
    recipient: str  # DID of recipient
    entry_ref: dict[str, int]  # Entry earning the royalty
    # Payment details
    amount: Decimal
    currency: str = "NLC"
    rate_applied: Decimal = field(default_factory=lambda: Decimal("0"))
    # Chain info
    depth: int = 0  # 0 = direct, 1+ = via derivative chain
    chain_path: list[dict[str, int]] = field(default_factory=list)
    # Status
    status: PaymentStatus = PaymentStatus.PENDING
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    distributed_at: str | None = None
    claimed_at: str | None = None
    expires_at: str = field(
        default_factory=lambda: (datetime.utcnow() + timedelta(days=CLAIM_EXPIRY_DAYS)).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "payment_id": self.payment_id,
            "event_id": self.event_id,
            "recipient": self.recipient,
            "entry_ref": self.entry_ref,
            "amount": str(self.amount),
            "currency": self.currency,
            "rate_applied": str(self.rate_applied),
            "depth": self.depth,
            "chain_path": self.chain_path,
            "status": self.status.value,
            "created_at": self.created_at,
            "distributed_at": self.distributed_at,
            "claimed_at": self.claimed_at,
            "expires_at": self.expires_at,
        }


@dataclass
class RevenuePool:
    """Accumulated revenue for a recipient."""

    pool_id: str
    recipient: str  # DID
    # Balances by currency
    balances: dict[str, Decimal] = field(default_factory=dict)
    # Totals
    total_earned: dict[str, Decimal] = field(default_factory=dict)
    total_claimed: dict[str, Decimal] = field(default_factory=dict)
    # Payment history
    pending_payments: list[str] = field(default_factory=list)  # Payment IDs
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_claim_at: str | None = None

    def add_payment(self, amount: Decimal, currency: str, payment_id: str) -> None:
        """Add a payment to the pool."""
        if currency not in self.balances:
            self.balances[currency] = Decimal("0")
            self.total_earned[currency] = Decimal("0")

        self.balances[currency] += amount
        self.total_earned[currency] += amount
        self.pending_payments.append(payment_id)

    def claim(self, amount: Decimal, currency: str) -> bool:
        """Claim an amount from the pool."""
        if currency not in self.balances or self.balances[currency] < amount:
            return False

        self.balances[currency] -= amount
        if currency not in self.total_claimed:
            self.total_claimed[currency] = Decimal("0")
        self.total_claimed[currency] += amount
        self.last_claim_at = datetime.utcnow().isoformat()
        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pool_id": self.pool_id,
            "recipient": self.recipient,
            "balances": {k: str(v) for k, v in self.balances.items()},
            "total_earned": {k: str(v) for k, v in self.total_earned.items()},
            "total_claimed": {k: str(v) for k, v in self.total_claimed.items()},
            "pending_payment_count": len(self.pending_payments),
            "created_at": self.created_at,
            "last_claim_at": self.last_claim_at,
        }


@dataclass
class Claim:
    """A claim request for accumulated revenue."""

    claim_id: str
    recipient: str  # DID
    amount: Decimal
    currency: str = "NLC"
    status: ClaimStatus = ClaimStatus.PENDING
    # Destination
    destination_address: str | None = None  # Optional external address
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processed_at: str | None = None
    # Transaction reference
    tx_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_id": self.claim_id,
            "recipient": self.recipient,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "destination_address": self.destination_address,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "tx_ref": self.tx_ref,
        }


@dataclass
class RoyaltyChainNode:
    """A node in the royalty distribution chain."""

    entry_ref: dict[str, int]
    owner: str
    rate: Decimal
    depth: int
    amount: Decimal  # Calculated amount at this node
    children: list["RoyaltyChainNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_ref": self.entry_ref,
            "owner": self.owner,
            "rate": str(self.rate),
            "depth": self.depth,
            "amount": str(self.amount),
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class RevenueShareEvent:
    """Internal event for audit trail."""

    event_id: str
    event_type: str
    timestamp: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }


# =============================================================================
# Revenue Sharing Service
# =============================================================================


class RevenueSharingService:
    """
    Service for managing royalty configurations and revenue distribution.

    Integrates with the derivative tracking system to automatically
    calculate and distribute royalties through intent chains.
    """

    def __init__(self, derivative_registry: Any = None):
        """
        Initialize the revenue sharing service.

        Args:
            derivative_registry: Optional DerivativeRegistry for chain lookups
        """
        self.derivative_registry = derivative_registry

        # Storage
        self.royalty_configs: dict[str, RoyaltyConfig] = {}  # config_id -> config
        self.entry_configs: dict[str, str] = {}  # entry_key -> config_id
        self.revenue_events: dict[str, RevenueEvent] = {}
        self.payments: dict[str, RoyaltyPayment] = {}
        self.pools: dict[str, RevenuePool] = {}  # recipient -> pool
        self.claims: dict[str, Claim] = {}

        # Audit trail
        self.events: list[RevenueShareEvent] = []

    # =========================================================================
    # Royalty Configuration
    # =========================================================================

    def configure_royalties(
        self,
        block_index: int,
        entry_index: int,
        owner: str,
        royalty_type: RoyaltyType = RoyaltyType.FIXED,
        base_rate: Decimal | None = None,
        tiered_rates: dict[str, Decimal] | None = None,
        split_recipients: dict[str, Decimal] | None = None,
        chain_propagation: bool = True,
        max_depth: int = MAX_ROYALTY_DEPTH,
        depth_decay: Decimal | None = None,
        min_payment: Decimal | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Configure royalties for an entry/contract.

        Args:
            block_index: Block index of the entry
            entry_index: Entry index
            owner: Owner DID
            royalty_type: Type of royalty configuration
            base_rate: Base royalty rate percentage (0-50)
            tiered_rates: Rates by derivative type
            split_recipients: Split percentages by recipient DID
            chain_propagation: Whether to propagate through chains
            max_depth: Maximum chain depth
            depth_decay: Decay factor per level
            min_payment: Minimum payment threshold
            metadata: Additional metadata

        Returns:
            Tuple of (success, config_info)
        """
        entry_key = f"{block_index}:{entry_index}"

        # Check for existing config
        if entry_key in self.entry_configs:
            existing_config_id = self.entry_configs[entry_key]
            existing_config = self.royalty_configs.get(existing_config_id)
            if existing_config and existing_config.owner != owner:
                return False, {"error": "Not authorized to modify royalty config"}

        # Validate rates
        if base_rate is None:
            base_rate = DEFAULT_ROYALTY_RATE
        if base_rate < MIN_ROYALTY_RATE or base_rate > MAX_ROYALTY_RATE:
            return False, {"error": f"Base rate must be between {MIN_ROYALTY_RATE} and {MAX_ROYALTY_RATE}"}

        # Validate split recipients
        if split_recipients:
            total_split = sum(split_recipients.values())
            if total_split > Decimal("100"):
                return False, {"error": "Split percentages cannot exceed 100%"}

        config_id = f"royalty_{secrets.token_hex(12)}"
        entry_ref = {"block_index": block_index, "entry_index": entry_index}

        config = RoyaltyConfig(
            config_id=config_id,
            entry_ref=entry_ref,
            owner=owner,
            royalty_type=royalty_type,
            base_rate=base_rate,
            tiered_rates=tiered_rates or {},
            split_recipients=split_recipients or {},
            chain_propagation=chain_propagation,
            max_depth=max_depth,
            depth_decay=depth_decay if depth_decay is not None else DEPTH_DECAY_FACTOR,
            min_payment=min_payment if min_payment is not None else MIN_DISTRIBUTION_AMOUNT,
            metadata=metadata or {},
        )

        self.royalty_configs[config_id] = config
        self.entry_configs[entry_key] = config_id

        # Emit event
        self._emit_event("royalty_configured", {
            "config_id": config_id,
            "entry_ref": entry_ref,
            "owner": owner,
            "royalty_type": royalty_type.value,
            "base_rate": str(base_rate),
        })

        return True, config.to_dict()

    def get_royalty_config(self, block_index: int, entry_index: int) -> RoyaltyConfig | None:
        """Get royalty configuration for an entry."""
        entry_key = f"{block_index}:{entry_index}"
        config_id = self.entry_configs.get(entry_key)
        if config_id:
            return self.royalty_configs.get(config_id)
        return None

    def update_royalty_config(
        self,
        block_index: int,
        entry_index: int,
        owner: str,
        updates: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """Update royalty configuration."""
        entry_key = f"{block_index}:{entry_index}"
        config_id = self.entry_configs.get(entry_key)

        if not config_id:
            return False, {"error": "No royalty config found for entry"}

        config = self.royalty_configs.get(config_id)
        if not config:
            return False, {"error": "Config not found"}

        if config.owner != owner:
            return False, {"error": "Not authorized to update config"}

        # Apply updates
        if "base_rate" in updates:
            rate = Decimal(str(updates["base_rate"]))
            if rate < MIN_ROYALTY_RATE or rate > MAX_ROYALTY_RATE:
                return False, {"error": "Invalid rate"}
            config.base_rate = rate

        if "tiered_rates" in updates:
            config.tiered_rates = {k: Decimal(str(v)) for k, v in updates["tiered_rates"].items()}

        if "split_recipients" in updates:
            splits = {k: Decimal(str(v)) for k, v in updates["split_recipients"].items()}
            if sum(splits.values()) > Decimal("100"):
                return False, {"error": "Split percentages exceed 100%"}
            config.split_recipients = splits

        if "chain_propagation" in updates:
            config.chain_propagation = updates["chain_propagation"]

        if "max_depth" in updates:
            config.max_depth = min(updates["max_depth"], MAX_ROYALTY_DEPTH)

        if "is_active" in updates:
            config.is_active = updates["is_active"]

        config.updated_at = datetime.utcnow().isoformat()

        self._emit_event("royalty_updated", {
            "config_id": config_id,
            "updates": list(updates.keys()),
        })

        return True, config.to_dict()

    def disable_royalties(
        self,
        block_index: int,
        entry_index: int,
        owner: str,
    ) -> tuple[bool, dict[str, Any]]:
        """Disable royalties for an entry."""
        entry_key = f"{block_index}:{entry_index}"
        config_id = self.entry_configs.get(entry_key)

        if not config_id:
            return False, {"error": "No royalty config found"}

        config = self.royalty_configs.get(config_id)
        if not config:
            return False, {"error": "Config not found"}

        if config.owner != owner:
            return False, {"error": "Not authorized"}

        config.is_active = False
        config.updated_at = datetime.utcnow().isoformat()

        self._emit_event("royalty_disabled", {
            "config_id": config_id,
            "entry_ref": config.entry_ref,
        })

        return True, {"config_id": config_id, "disabled": True}

    # =========================================================================
    # Revenue Event Processing
    # =========================================================================

    def record_revenue_event(
        self,
        block_index: int,
        entry_index: int,
        event_type: RevenueEventType,
        amount: Decimal,
        currency: str = "NLC",
        payer: str | None = None,
        derivative_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Record a revenue-generating event and calculate royalties.

        Args:
            block_index: Entry that generated revenue
            entry_index: Entry index
            event_type: Type of event
            amount: Revenue amount
            currency: Currency type
            payer: Optional payer DID
            derivative_type: If triggered by derivative creation
            metadata: Additional metadata

        Returns:
            Tuple of (success, event_info with calculated royalties)
        """
        if amount <= 0:
            return False, {"error": "Amount must be positive"}

        event_id = f"rev_{secrets.token_hex(12)}"
        entry_ref = {"block_index": block_index, "entry_index": entry_index}

        event = RevenueEvent(
            event_id=event_id,
            event_type=event_type,
            source_entry_ref=entry_ref,
            amount=amount,
            currency=currency,
            payer=payer,
            derivative_type=derivative_type,
            metadata=metadata or {},
        )

        self.revenue_events[event_id] = event

        # Calculate and distribute royalties
        royalty_result = self._calculate_and_distribute(event)

        event.processed_at = datetime.utcnow().isoformat()

        self._emit_event("revenue_recorded", {
            "event_id": event_id,
            "entry_ref": entry_ref,
            "amount": str(amount),
            "currency": currency,
            "royalty_payments": royalty_result.get("payment_count", 0),
        })

        result = event.to_dict()
        result["royalties"] = royalty_result

        return True, result

    def _calculate_and_distribute(self, event: RevenueEvent) -> dict[str, Any]:
        """Calculate royalties and distribute to pools."""
        payments: list[RoyaltyPayment] = []
        remaining_amount = event.amount

        # Get the lineage of the source entry
        lineage = self._get_royalty_chain(
            event.source_entry_ref["block_index"],
            event.source_entry_ref["entry_index"],
            event.derivative_type,
        )

        # Process each node in the chain
        for node in lineage:
            if remaining_amount <= MIN_DISTRIBUTION_AMOUNT:
                break

            # Calculate payment for this node
            royalty_amount = self._calculate_royalty(
                remaining_amount,
                node["rate"],
                node["depth"],
                node.get("config"),
            )

            if royalty_amount < MIN_DISTRIBUTION_AMOUNT:
                continue

            # Handle split recipients
            recipients = self._get_recipients(node.get("config"), node["owner"])

            for recipient, share in recipients.items():
                recipient_amount = (royalty_amount * share / Decimal("100")).quantize(
                    Decimal("0." + "0" * CURRENCY_DECIMAL_PLACES),
                    rounding=ROUND_HALF_UP,
                )

                if recipient_amount < MIN_DISTRIBUTION_AMOUNT:
                    continue

                payment = RoyaltyPayment(
                    payment_id=f"pay_{secrets.token_hex(12)}",
                    event_id=event.event_id,
                    recipient=recipient,
                    entry_ref=node["entry_ref"],
                    amount=recipient_amount,
                    currency=event.currency,
                    rate_applied=node["rate"],
                    depth=node["depth"],
                    chain_path=node.get("path", []),
                    status=PaymentStatus.PENDING,
                )

                payments.append(payment)
                self.payments[payment.payment_id] = payment

                # Add to recipient's pool
                self._add_to_pool(recipient, recipient_amount, event.currency, payment.payment_id)

                remaining_amount -= recipient_amount

        # Update payment statuses
        for payment in payments:
            payment.status = PaymentStatus.DISTRIBUTED
            payment.distributed_at = datetime.utcnow().isoformat()

        return {
            "payment_count": len(payments),
            "total_distributed": str(event.amount - remaining_amount),
            "remaining": str(remaining_amount),
            "payments": [p.to_dict() for p in payments],
        }

    def _get_royalty_chain(
        self,
        block_index: int,
        entry_index: int,
        derivative_type: str | None,
    ) -> list[dict[str, Any]]:
        """Get the chain of entries eligible for royalties."""
        chain = []

        if not self.derivative_registry:
            # No derivative tracking, just check direct config
            config = self.get_royalty_config(block_index, entry_index)
            if config and config.is_active:
                chain.append({
                    "entry_ref": {"block_index": block_index, "entry_index": entry_index},
                    "owner": config.owner,
                    "rate": config.get_rate_for_type(derivative_type or ""),
                    "depth": 0,
                    "config": config,
                    "path": [],
                })
            return chain

        # Get lineage from derivative registry
        lineage = self.derivative_registry.get_lineage(block_index, entry_index)

        # Build chain with configs
        for idx, ancestor in enumerate(lineage):
            config = self.get_royalty_config(
                ancestor["block_index"],
                ancestor["entry_index"],
            )

            if not config or not config.is_active:
                continue

            if not config.chain_propagation and idx > 0:
                continue

            if idx >= config.max_depth:
                continue

            # Calculate effective rate with decay
            effective_rate = config.get_rate_for_type(derivative_type or "")
            if idx > 0:
                decay = config.depth_decay ** idx
                effective_rate = (effective_rate * decay).quantize(
                    Decimal("0.0001"),
                    rounding=ROUND_HALF_UP,
                )

            chain.append({
                "entry_ref": {"block_index": ancestor["block_index"], "entry_index": ancestor["entry_index"]},
                "owner": config.owner,
                "rate": effective_rate,
                "depth": idx,
                "config": config,
                "path": lineage[:idx + 1],
            })

        return chain

    def _calculate_royalty(
        self,
        amount: Decimal,
        rate: Decimal,
        depth: int,
        config: RoyaltyConfig | None,
    ) -> Decimal:
        """Calculate royalty amount."""
        royalty = (amount * rate / Decimal("100")).quantize(
            Decimal("0." + "0" * CURRENCY_DECIMAL_PLACES),
            rounding=ROUND_HALF_UP,
        )
        return royalty

    def _get_recipients(
        self,
        config: RoyaltyConfig | None,
        default_owner: str,
    ) -> dict[str, Decimal]:
        """Get recipients and their shares."""
        if not config or not config.split_recipients:
            return {default_owner: Decimal("100")}

        # Use split if configured
        recipients = dict(config.split_recipients)

        # Ensure owner gets remainder if splits don't total 100%
        total_split = sum(recipients.values())
        if total_split < Decimal("100"):
            if default_owner in recipients:
                recipients[default_owner] += Decimal("100") - total_split
            else:
                recipients[default_owner] = Decimal("100") - total_split

        return recipients

    def _add_to_pool(
        self,
        recipient: str,
        amount: Decimal,
        currency: str,
        payment_id: str,
    ) -> None:
        """Add payment to recipient's pool."""
        if recipient not in self.pools:
            self.pools[recipient] = RevenuePool(
                pool_id=f"pool_{secrets.token_hex(8)}",
                recipient=recipient,
            )

        self.pools[recipient].add_payment(amount, currency, payment_id)

    # =========================================================================
    # Revenue Pool & Claims
    # =========================================================================

    def get_pool(self, recipient: str) -> RevenuePool | None:
        """Get revenue pool for a recipient."""
        return self.pools.get(recipient)

    def get_balance(self, recipient: str, currency: str = "NLC") -> Decimal:
        """Get available balance for a recipient."""
        pool = self.pools.get(recipient)
        if not pool:
            return Decimal("0")
        return pool.balances.get(currency, Decimal("0"))

    def claim_revenue(
        self,
        recipient: str,
        amount: Decimal | None = None,
        currency: str = "NLC",
        destination_address: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Claim accumulated revenue.

        Args:
            recipient: DID of the claimant
            amount: Amount to claim (None = all available)
            currency: Currency to claim
            destination_address: Optional external address

        Returns:
            Tuple of (success, claim_info)
        """
        pool = self.pools.get(recipient)
        if not pool:
            return False, {"error": "No revenue pool found"}

        available = pool.balances.get(currency, Decimal("0"))
        if available < MIN_DISTRIBUTION_AMOUNT:
            return False, {"error": "Insufficient balance", "available": str(available)}

        claim_amount = amount if amount is not None else available
        if claim_amount > available:
            return False, {"error": "Insufficient balance", "requested": str(claim_amount), "available": str(available)}

        if claim_amount < MIN_DISTRIBUTION_AMOUNT:
            return False, {"error": f"Minimum claim amount is {MIN_DISTRIBUTION_AMOUNT}"}

        # Create claim
        claim_id = f"claim_{secrets.token_hex(12)}"
        claim = Claim(
            claim_id=claim_id,
            recipient=recipient,
            amount=claim_amount,
            currency=currency,
            destination_address=destination_address,
        )

        # Process claim
        if pool.claim(claim_amount, currency):
            claim.status = ClaimStatus.CLAIMED
            claim.processed_at = datetime.utcnow().isoformat()
            claim.tx_ref = f"tx_{secrets.token_hex(16)}"  # Simulated tx reference

            self.claims[claim_id] = claim

            self._emit_event("revenue_claimed", {
                "claim_id": claim_id,
                "recipient": recipient,
                "amount": str(claim_amount),
                "currency": currency,
            })

            return True, claim.to_dict()
        else:
            claim.status = ClaimStatus.PENDING
            return False, {"error": "Claim processing failed"}

    def get_claims(
        self,
        recipient: str | None = None,
        status: ClaimStatus | None = None,
    ) -> list[Claim]:
        """Get claims with optional filters."""
        results = []
        for claim in self.claims.values():
            if recipient and claim.recipient != recipient:
                continue
            if status and claim.status != status:
                continue
            results.append(claim)
        return results

    # =========================================================================
    # Revenue Analytics
    # =========================================================================

    def get_entry_earnings(
        self,
        block_index: int,
        entry_index: int,
    ) -> dict[str, Any]:
        """Get total earnings for an entry."""
        entry_ref = {"block_index": block_index, "entry_index": entry_index}

        earnings: dict[str, Decimal] = {}
        payment_count = 0

        for payment in self.payments.values():
            if payment.entry_ref == entry_ref:
                currency = payment.currency
                if currency not in earnings:
                    earnings[currency] = Decimal("0")
                earnings[currency] += payment.amount
                payment_count += 1

        return {
            "entry_ref": entry_ref,
            "earnings": {k: str(v) for k, v in earnings.items()},
            "payment_count": payment_count,
        }

    def get_chain_revenue(
        self,
        block_index: int,
        entry_index: int,
    ) -> dict[str, Any]:
        """Get total revenue generated by an entry and its derivatives."""
        total_revenue: dict[str, Decimal] = {}
        direct_revenue: dict[str, Decimal] = {}
        derivative_revenue: dict[str, Decimal] = {}

        entry_key = f"{block_index}:{entry_index}"

        for event in self.revenue_events.values():
            source_key = f"{event.source_entry_ref['block_index']}:{event.source_entry_ref['entry_index']}"

            if source_key == entry_key:
                # Direct revenue
                if event.currency not in direct_revenue:
                    direct_revenue[event.currency] = Decimal("0")
                direct_revenue[event.currency] += event.amount

            # Check if source is a derivative
            if self.derivative_registry:
                lineage = self.derivative_registry.get_lineage(
                    event.source_entry_ref["block_index"],
                    event.source_entry_ref["entry_index"],
                )
                for ancestor in lineage:
                    ancestor_key = f"{ancestor['block_index']}:{ancestor['entry_index']}"
                    if ancestor_key == entry_key:
                        if event.currency not in derivative_revenue:
                            derivative_revenue[event.currency] = Decimal("0")
                        derivative_revenue[event.currency] += event.amount
                        break

        # Calculate totals
        for currency in set(list(direct_revenue.keys()) + list(derivative_revenue.keys())):
            total_revenue[currency] = (
                direct_revenue.get(currency, Decimal("0")) +
                derivative_revenue.get(currency, Decimal("0"))
            )

        return {
            "entry_ref": {"block_index": block_index, "entry_index": entry_index},
            "total_revenue": {k: str(v) for k, v in total_revenue.items()},
            "direct_revenue": {k: str(v) for k, v in direct_revenue.items()},
            "derivative_revenue": {k: str(v) for k, v in derivative_revenue.items()},
        }

    def estimate_royalties(
        self,
        block_index: int,
        entry_index: int,
        amount: Decimal,
        derivative_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Estimate royalty distribution for a potential revenue event.

        Args:
            block_index: Entry generating revenue
            entry_index: Entry index
            amount: Potential revenue amount
            derivative_type: Type of derivative if applicable

        Returns:
            Estimated distribution breakdown
        """
        chain = self._get_royalty_chain(block_index, entry_index, derivative_type)

        distributions = []
        remaining = amount

        for node in chain:
            royalty_amount = self._calculate_royalty(
                remaining,
                node["rate"],
                node["depth"],
                node.get("config"),
            )

            if royalty_amount >= MIN_DISTRIBUTION_AMOUNT:
                distributions.append({
                    "entry_ref": node["entry_ref"],
                    "recipient": node["owner"],
                    "rate": str(node["rate"]),
                    "depth": node["depth"],
                    "estimated_amount": str(royalty_amount),
                })
                remaining -= royalty_amount

        return {
            "input_amount": str(amount),
            "total_royalties": str(amount - remaining),
            "remaining_after_royalties": str(remaining),
            "distribution_count": len(distributions),
            "distributions": distributions,
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get revenue sharing statistics."""
        # Payment status counts
        payment_status_counts: dict[str, int] = {}
        total_distributed: dict[str, Decimal] = {}

        for payment in self.payments.values():
            status = payment.status.value
            payment_status_counts[status] = payment_status_counts.get(status, 0) + 1

            if payment.status == PaymentStatus.DISTRIBUTED:
                currency = payment.currency
                if currency not in total_distributed:
                    total_distributed[currency] = Decimal("0")
                total_distributed[currency] += payment.amount

        # Pool statistics
        total_balances: dict[str, Decimal] = {}
        for pool in self.pools.values():
            for currency, balance in pool.balances.items():
                if currency not in total_balances:
                    total_balances[currency] = Decimal("0")
                total_balances[currency] += balance

        # Event type counts
        event_type_counts: dict[str, int] = {}
        for event in self.revenue_events.values():
            evt_type = event.event_type.value
            event_type_counts[evt_type] = event_type_counts.get(evt_type, 0) + 1

        return {
            "royalty_configs": {
                "total": len(self.royalty_configs),
                "active": sum(1 for c in self.royalty_configs.values() if c.is_active),
            },
            "revenue_events": {
                "total": len(self.revenue_events),
                "by_type": event_type_counts,
            },
            "payments": {
                "total": len(self.payments),
                "by_status": payment_status_counts,
                "total_distributed": {k: str(v) for k, v in total_distributed.items()},
            },
            "pools": {
                "total": len(self.pools),
                "total_balances": {k: str(v) for k, v in total_balances.items()},
            },
            "claims": {
                "total": len(self.claims),
                "claimed": sum(1 for c in self.claims.values() if c.status == ClaimStatus.CLAIMED),
            },
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an internal event for audit trail."""
        event = RevenueShareEvent(
            event_id=f"evt_{secrets.token_hex(8)}",
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            data=data,
        )
        self.events.append(event)

    def set_derivative_registry(self, registry: Any) -> None:
        """Set the derivative registry for chain lookups."""
        self.derivative_registry = registry
