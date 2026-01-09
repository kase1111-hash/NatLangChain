"""
NatLangChain - Observance Burn Protocol
Ceremonial destruction mechanism for economic and signaling purposes.

"Models propose the possible.
 Humans ratify the actual.
 Burns consecrate the boundary."

Note: NatLangChain is currency-agnostic. This module operates on whatever
staking currency is configured for the deployment (e.g., ETH, USDC, DAI).
The "burn" mechanism permanently removes value from circulation, with the
economic effect redistributed proportionally to remaining stakeholders.
"""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any


class BurnReason(Enum):
    """Valid reasons for Observance Burn."""

    VOLUNTARY_SIGNAL = "VoluntarySignal"  # Pure belief in the system
    ESCALATION_COMMITMENT = "EscalationCommitment"  # Triggering an escalation fork
    RATE_LIMIT_EXCESS = "RateLimitExcess"  # Exceeding daily contract threshold
    PROTOCOL_VIOLATION = "ProtocolViolation"  # Enforced burns for violations
    COMMUNITY_DIRECTIVE = "CommunityDirective"  # Governance-initiated burns


class ObservanceBurnManager:
    """
    Manages the Observance Burn protocol for ceremonial value destruction.

    Note: NatLangChain is currency-agnostic. Burns operate on whatever
    staking currency is configured (ETH, USDC, DAI, etc.). The "total_supply"
    tracking is for proportional redistribution calculations only.

    Core purposes:
    - Economic Deflation: Permanently removes value from circulation
    - Redistribution: Proportionally benefits remaining stakeholders
    - Signaling: Provides credible, costly proof of commitment
    - Anti-Abuse: Discourages system gaming through meaningful cost
    - Ceremony: Elevates protocol actions to meaningful observances
    """

    # Configuration
    DEFAULT_ESCALATION_BURN_PERCENTAGE = 0.05  # 5% of mediation stake
    DEFAULT_RATE_LIMIT_BURN_PER_EXCESS = 0.1  # 0.1 tokens per excess contract
    MAXIMUM_EPITAPH_LENGTH = 280  # Twitter-length epitaphs
    MINIMUM_EPITAPH_LENGTH = 0  # Optional

    def __init__(self, initial_supply: float = 1_000_000.0):
        """
        Initialize burn manager.

        Args:
            initial_supply: Initial circulating supply for redistribution calculations.
                           This represents the total staked/circulating value in the
                           configured currency (ETH, USDC, etc.), not a native token.
        """
        # Token tracking (in production, this would be on-chain)
        self.total_supply = initial_supply
        self.total_burned = 0.0

        # Burn records
        self.burns: list[dict[str, Any]] = []

        # Burn counts by reason
        self.burns_by_reason: dict[str, int] = {reason.value: 0 for reason in BurnReason}

        # Rate limiting (address -> daily contract count)
        self.daily_contract_counts: dict[str, int] = {}
        self.rate_limit_threshold = 10  # contracts per day

    def perform_burn(
        self,
        burner: str,
        amount: float,
        reason: BurnReason,
        intent_hash: str | None = None,
        epitaph: str | None = None,
        signature: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Perform an Observance Burn.

        Args:
            burner: Address performing the burn
            amount: Amount to burn
            reason: Reason for the burn
            intent_hash: Hash of related intent/mediation (0x0 if voluntary)
            epitaph: Optional message from burner
            signature: Cryptographic signature authorizing burn

        Returns:
            Tuple of (success, burn record or error)
        """
        # Validate amount
        if amount <= 0:
            return False, {"error": "Burn amount must be positive"}

        if amount > self.total_supply:
            return False, {"error": "Burn amount exceeds total supply"}

        # Validate epitaph
        if epitaph and len(epitaph) > self.MAXIMUM_EPITAPH_LENGTH:
            return False, {
                "error": f"Epitaph exceeds maximum length ({self.MAXIMUM_EPITAPH_LENGTH})"
            }

        # Generate transaction hash
        tx_hash = self._generate_tx_hash(burner, amount, reason, intent_hash, epitaph)
        block_number = len(self.burns) + 1

        # Calculate redistribution effect
        supply_before = self.total_supply
        supply_after = self.total_supply - amount
        redistribution_effect = (
            ((supply_before / supply_after) - 1) * 100 if supply_after > 0 else 100
        )

        # Create burn record
        burn_record = {
            "tx_hash": tx_hash,
            "block_number": block_number,
            "burner": burner,
            "amount": amount,
            "reason": reason.value if isinstance(reason, BurnReason) else reason,
            "intent_hash": intent_hash or "0x" + "0" * 64,
            "epitaph": epitaph or "",
            "timestamp": datetime.utcnow().isoformat(),
            "supply_before": supply_before,
            "supply_after": supply_after,
            "redistribution_effect_percent": round(redistribution_effect, 6),
        }

        # Execute burn
        self.total_supply -= amount
        self.total_burned += amount
        self.burns.append(burn_record)

        reason_value = reason.value if isinstance(reason, BurnReason) else reason
        if reason_value in self.burns_by_reason:
            self.burns_by_reason[reason_value] += 1

        return True, {
            "status": "burned",
            "tx_hash": tx_hash,
            "block_number": block_number,
            "amount": amount,
            "reason": reason_value,
            "new_total_supply": self.total_supply,
            "redistribution_effect": f"{redistribution_effect:.4f}%",
        }

    def _generate_tx_hash(
        self,
        burner: str,
        amount: float,
        reason: BurnReason,
        intent_hash: str | None,
        epitaph: str | None,
    ) -> str:
        """Generate unique transaction hash for burn."""
        data = {
            "burner": burner,
            "amount": str(amount),
            "reason": reason.value if isinstance(reason, BurnReason) else reason,
            "intent_hash": intent_hash,
            "epitaph": epitaph,
            "timestamp": datetime.utcnow().isoformat(),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return "0x" + hashlib.sha256(hash_input.encode()).hexdigest()

    def calculate_escalation_burn(self, mediation_stake: float) -> float:
        """
        Calculate required burn amount for escalation commitment.

        Args:
            mediation_stake: Original mediation stake

        Returns:
            Required burn amount (5% of stake)
        """
        return mediation_stake * self.DEFAULT_ESCALATION_BURN_PERCENTAGE

    def verify_escalation_burn(
        self, tx_hash: str, expected_amount: float, expected_intent_hash: str
    ) -> tuple[bool, dict[str, Any] | None]:
        """
        Verify that an escalation burn was performed correctly.

        Args:
            tx_hash: Transaction hash to verify
            expected_amount: Expected burn amount
            expected_intent_hash: Expected intent hash

        Returns:
            Tuple of (is_valid, burn record if found)
        """
        for burn in self.burns:
            if burn["tx_hash"] == tx_hash:
                # Verify amount and reason
                reason_match = burn["reason"] == BurnReason.ESCALATION_COMMITMENT.value
                amount_match = burn["amount"] >= expected_amount
                intent_match = burn["intent_hash"] == expected_intent_hash

                if reason_match and amount_match and intent_match:
                    return True, burn
                else:
                    return False, {
                        "error": "Burn verification failed",
                        "reason_match": reason_match,
                        "amount_match": amount_match,
                        "intent_match": intent_match,
                    }

        return False, {"error": "Burn transaction not found"}

    def perform_rate_limit_burn(
        self, address: str, excess_contracts: int
    ) -> tuple[bool, dict[str, Any]]:
        """
        Perform burn for exceeding rate limit.

        Args:
            address: Address that exceeded limit
            excess_contracts: Number of contracts over limit

        Returns:
            Tuple of (success, result)
        """
        burn_amount = excess_contracts * self.DEFAULT_RATE_LIMIT_BURN_PER_EXCESS

        return self.perform_burn(
            burner=address,
            amount=burn_amount,
            reason=BurnReason.RATE_LIMIT_EXCESS,
            intent_hash=None,
            epitaph=f"Rate limit exceeded by {excess_contracts} contracts",
        )

    def perform_voluntary_burn(
        self, burner: str, amount: float, epitaph: str | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Perform a voluntary signal burn.

        Args:
            burner: Address performing the burn
            amount: Amount to burn
            epitaph: Optional message

        Returns:
            Tuple of (success, result)
        """
        return self.perform_burn(
            burner=burner,
            amount=amount,
            reason=BurnReason.VOLUNTARY_SIGNAL,
            intent_hash=None,
            epitaph=epitaph,
        )

    def get_burn_by_tx_hash(self, tx_hash: str) -> dict[str, Any] | None:
        """Get a specific burn by transaction hash."""
        for burn in self.burns:
            if burn["tx_hash"] == tx_hash:
                return burn
        return None

    def get_burns_by_address(self, address: str) -> list[dict[str, Any]]:
        """Get all burns by a specific address."""
        return [burn for burn in self.burns if burn["burner"] == address]

    def get_burns_by_reason(self, reason: BurnReason) -> list[dict[str, Any]]:
        """Get all burns of a specific reason."""
        reason_value = reason.value if isinstance(reason, BurnReason) else reason
        return [burn for burn in self.burns if burn["reason"] == reason_value]

    def get_statistics(self) -> dict[str, Any]:
        """Get burn statistics."""
        # Calculate last 24 hours and 7 days burns
        now = datetime.utcnow()
        last_24h = 0.0
        last_7d = 0.0

        for burn in self.burns:
            burn_time = datetime.fromisoformat(burn["timestamp"])
            hours_ago = (now - burn_time).total_seconds() / 3600

            if hours_ago <= 24:
                last_24h += burn["amount"]
            if hours_ago <= 168:  # 7 days
                last_7d += burn["amount"]

        # Find largest burn
        largest_burn = None
        if self.burns:
            largest_burn = max(self.burns, key=lambda b: b["amount"])

        return {
            "total_burned": self.total_burned,
            "total_burns": len(self.burns),
            "current_supply": self.total_supply,
            "burns_by_reason": self.burns_by_reason.copy(),
            "last_24_hours": last_24h,
            "last_7_days": last_7d,
            "largest_burn": {
                "amount": largest_burn["amount"],
                "burner": largest_burn["burner"],
                "epitaph": largest_burn["epitaph"],
                "timestamp": largest_burn["timestamp"],
            }
            if largest_burn
            else None,
        }

    def get_burn_history(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        Get paginated burn history.

        Args:
            limit: Maximum number of burns to return
            offset: Starting offset

        Returns:
            Paginated burn history
        """
        # Sort by timestamp descending (most recent first)
        sorted_burns = sorted(self.burns, key=lambda b: b["timestamp"], reverse=True)

        total = len(sorted_burns)
        page_burns = sorted_burns[offset : offset + limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "burns": page_burns,
            "has_more": offset + limit < total,
        }

    def format_burn_for_display(self, burn: dict[str, Any]) -> dict[str, Any]:
        """
        Format a burn record for explorer/dashboard display.

        Returns:
            Formatted burn for UI
        """
        reason = burn["reason"]
        reason_labels = {
            "VoluntarySignal": "Voluntary Signal",
            "EscalationCommitment": "Escalation Commitment",
            "RateLimitExcess": "Rate Limit Excess",
            "ProtocolViolation": "Protocol Violation",
            "CommunityDirective": "Community Directive",
        }

        return {
            "icon": "flame",
            "title": "Observance Burn",
            "subtitle": f"{burn['amount']} tokens sacrificed — {reason_labels.get(reason, reason)}",
            "body": burn["epitaph"] if burn["epitaph"] else "(no epitaph)",
            "footer": "Redistributed proportionally to all remaining holders",
            "burner": burn["burner"],
            "block_number": burn["block_number"],
            "timestamp": burn["timestamp"],
            "tx_hash": burn["tx_hash"],
        }

    def get_observance_ledger(self, limit: int = 20) -> dict[str, Any]:
        """
        Get data for the Observance Ledger explorer tab.

        Returns:
            Complete ledger view data
        """
        stats = self.get_statistics()
        history = self.get_burn_history(limit=limit)

        formatted_burns = [self.format_burn_for_display(burn) for burn in history["burns"]]

        return {
            "title": "OBSERVANCE LEDGER",
            "total_supply_reduction": self.total_burned,
            "total_burns": len(self.burns),
            "last_24h_burned": stats["last_24_hours"],
            "recent_observances": formatted_burns,
        }

    def emit_observance_burn_event(self, burn: dict[str, Any]) -> dict[str, Any]:
        """
        Emit an ObservanceBurn event in Solidity-compatible format.

        Returns:
            Event data structure matching Solidity event schema
        """
        return {
            "name": "ObservanceBurn",
            "anonymous": False,
            "inputs": [
                {"name": "burner", "type": "address", "indexed": True, "value": burn["burner"]},
                {
                    "name": "amount",
                    "type": "uint256",
                    "indexed": False,
                    "value": int(burn["amount"] * 10**18),  # Convert to wei equivalent
                },
                {
                    "name": "reason",
                    "type": "uint8",
                    "indexed": False,
                    "value": list(BurnReason).index(BurnReason(burn["reason"]))
                    if burn["reason"] in [r.value for r in BurnReason]
                    else 0,
                },
                {
                    "name": "intentHash",
                    "type": "bytes32",
                    "indexed": True,
                    "value": burn["intent_hash"],
                },
                {"name": "epitaph", "type": "string", "indexed": False, "value": burn["epitaph"]},
            ],
            "emittedAt": burn["timestamp"],
            "txHash": burn["tx_hash"],
            "blockNumber": burn["block_number"],
        }
