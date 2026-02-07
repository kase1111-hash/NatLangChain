"""
NatLangChain - Anti-Harassment Economic Layer
Implements economic pressure mechanisms that make harassment strictly more
expensive for the harasser than for the target.

Core Principle:
"Any attempt to harass must be strictly more expensive for the harasser than for the target."

This module provides:
- Dual Initiation Paths (Breach/Drift Dispute vs. Voluntary Request)
- Frivolous Breach Claim Protection with escalating stakes
- Counter-Proposal Griefing Limits with exponential fees
- Harassment Scoring for reputation-based cost adjustments
- Cooldown windows per contract
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class InitiationPath(Enum):
    """Two mutually exclusive initiation paths."""

    BREACH_DISPUTE = "breach_dispute"  # Evidence of violation, requires symmetric stake
    VOLUNTARY_REQUEST = "voluntary_request"  # New negotiation, small burn fee, can be ignored


class DisputeResolution(Enum):
    """How a dispute was resolved."""

    FALLBACK = "fallback"  # Counterparty declined to match stake
    MUTUAL = "mutual"  # Both parties reached agreement
    ESCALATED = "escalated"  # Escalated to higher authority
    TIMEOUT = "timeout"  # Stake window expired
    WITHDRAWN = "withdrawn"  # Initiator withdrew


@dataclass
class StakeEscrow:
    """Represents escrowed stake for a breach/drift dispute."""

    escrow_id: str
    dispute_ref: str
    initiator: str
    stake_amount: float
    created_at: str
    stake_window_ends: str
    counterparty: str
    counterparty_stake: float = 0.0
    counterparty_staked_at: str | None = None
    status: str = "pending_match"  # pending_match, matched, fallback, resolved
    resolution: str | None = None


@dataclass
class HarassmentProfile:
    """Tracks harassment-related metrics for an address."""

    address: str
    # Counts
    initiated_disputes: int = 0
    non_resolving_disputes: int = 0  # Timeouts, fallbacks initiated by this party
    ignored_voluntary_requests: int = 0  # As initiator, not responder
    vetoes_used: int = 0
    counter_proposals_made: int = 0
    # Reputation
    harassment_score: float = 0.0
    last_updated: str = ""
    # Cooldowns per contract
    contract_cooldowns: dict[str, str] = field(default_factory=dict)


class AntiHarassmentManager:
    """
    Manages the Anti-Harassment Economic Layer.

    Core Design:
    - Ignoring harassment is always free
    - Engaging is optional and symmetrically priced
    - Executing harassment is expensive, bounded, and self-limiting
    """

    # Configuration - Staking
    DEFAULT_STAKE_WINDOW_HOURS = 72  # 3 days to match stake
    ESCALATING_STAKE_MULTIPLIER = 1.5  # +50% per recent non-resolving dispute
    ESCALATION_LOOKBACK_DAYS = 90  # Window for counting recent non-resolving disputes

    # Configuration - Voluntary Requests
    DEFAULT_VOLUNTARY_BURN_FEE = 0.1  # Small burn fee for voluntary requests

    # Configuration - Counter-Proposal Limits
    MAX_COUNTER_PROPOSALS = 3
    BASE_COUNTER_FEE = 1.0
    COUNTER_FEE_MULTIPLIER = 2  # Exponential: base_fee × 2ⁿ

    # Configuration - Cooldowns
    DEFAULT_COOLDOWN_DAYS = 30

    # Configuration - Harassment Scoring
    SCORE_WEIGHT_NON_RESOLVING = 10.0
    SCORE_WEIGHT_IGNORED_VOLUNTARY = 2.0
    SCORE_WEIGHT_VETO = 5.0
    SCORE_WEIGHT_EXCESSIVE_COUNTER = 3.0
    HARASSMENT_THRESHOLD_MODERATE = 25.0
    HARASSMENT_THRESHOLD_HIGH = 50.0
    HARASSMENT_THRESHOLD_SEVERE = 100.0

    def __init__(self, burn_manager=None):
        """
        Initialize anti-harassment manager.

        Args:
            burn_manager: Optional ObservanceBurnManager for burn operations
        """
        self.burn_manager = burn_manager

        # State tracking (in production, persisted to storage)
        self.escrows: dict[str, StakeEscrow] = {}
        self.profiles: dict[str, HarassmentProfile] = {}
        self.voluntary_requests: dict[str, dict] = {}
        self.counter_proposal_counts: dict[str, dict[str, int]] = {}  # dispute_id -> party -> count

        # Audit trail
        self.actions: list[dict[str, Any]] = []

    # ==================== DUAL INITIATION PATHS ====================

    def initiate_breach_dispute(
        self,
        initiator: str,
        counterparty: str,
        contract_ref: str,
        stake_amount: float,
        evidence_refs: list[dict[str, Any]],
        description: str,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Initiate a Breach/Drift Dispute with symmetric staking.

        The initiator MUST stake first. This path requires on-chain evidence
        of violation or semantic drift in an existing agreement.

        Args:
            initiator: Address initiating the dispute
            counterparty: Address of the other party
            contract_ref: Reference to the contract being disputed
            stake_amount: Amount to stake (will be escrowed)
            evidence_refs: References to evidence of breach/drift
            description: Natural language description

        Returns:
            Tuple of (success, result)
        """
        # Check cooldown for this contract
        cooldown_ok, cooldown_msg = self._check_cooldown(initiator, contract_ref)
        if not cooldown_ok:
            return False, {"error": cooldown_msg}

        # Calculate adjusted stake based on harassment history
        profile = self._get_or_create_profile(initiator)
        adjusted_stake = self._calculate_adjusted_stake(stake_amount, profile, contract_ref)

        if adjusted_stake > stake_amount:
            # Inform initiator of increased stake requirement
            stake_amount = adjusted_stake

        # Generate escrow ID
        escrow_id = self._generate_escrow_id(initiator, counterparty, contract_ref)

        stake_window_ends = datetime.utcnow() + timedelta(hours=self.DEFAULT_STAKE_WINDOW_HOURS)

        escrow = StakeEscrow(
            escrow_id=escrow_id,
            dispute_ref=f"BREACH-{hashlib.sha256(contract_ref.encode()).hexdigest()[:8].upper()}",
            initiator=initiator,
            stake_amount=stake_amount,
            created_at=datetime.utcnow().isoformat(),
            stake_window_ends=stake_window_ends.isoformat(),
            counterparty=counterparty,
        )

        self.escrows[escrow_id] = escrow

        # Update profile
        profile.initiated_disputes += 1
        profile.last_updated = datetime.utcnow().isoformat()

        # Record action
        self._record_action(
            "breach_dispute_initiated",
            {
                "escrow_id": escrow_id,
                "initiator": initiator,
                "counterparty": counterparty,
                "stake_amount": stake_amount,
                "contract_ref": contract_ref,
            },
        )

        return True, {
            "status": "escrow_created",
            "escrow_id": escrow_id,
            "dispute_ref": escrow.dispute_ref,
            "stake_amount": stake_amount,
            "adjusted_from": stake_amount if adjusted_stake == stake_amount else adjusted_stake,
            "stake_window_ends": stake_window_ends.isoformat(),
            "counterparty_must_match": stake_amount,
            "path": InitiationPath.BREACH_DISPUTE.value,
            "message": f"Counterparty must match stake within {self.DEFAULT_STAKE_WINDOW_HOURS} hours or dispute resolves to fallback",
        }

    def match_stake(
        self, escrow_id: str, counterparty: str, stake_amount: float
    ) -> tuple[bool, dict[str, Any]]:
        """
        Match stake to enter symmetric dispute resolution.

        Args:
            escrow_id: The escrow to match
            counterparty: The counterparty matching
            stake_amount: Amount being staked (must match initiator)

        Returns:
            Tuple of (success, result)
        """
        if escrow_id not in self.escrows:
            return False, {"error": "Escrow not found"}

        escrow = self.escrows[escrow_id]

        if escrow.counterparty != counterparty:
            return False, {"error": "Only the designated counterparty can match this stake"}

        if escrow.status != "pending_match":
            return False, {"error": f"Escrow is not pending match (status: {escrow.status})"}

        # Check if window expired
        window_end = datetime.fromisoformat(escrow.stake_window_ends)
        if datetime.utcnow() > window_end:
            return False, {"error": "Stake window has expired. Dispute resolved to fallback."}

        if stake_amount < escrow.stake_amount:
            return False, {
                "error": "Stake amount insufficient",
                "required": escrow.stake_amount,
                "provided": stake_amount,
            }

        # Match the stake
        escrow.counterparty_stake = stake_amount
        escrow.counterparty_staked_at = datetime.utcnow().isoformat()
        escrow.status = "matched"

        self._record_action(
            "stake_matched",
            {"escrow_id": escrow_id, "counterparty": counterparty, "stake_amount": stake_amount},
        )

        return True, {
            "status": "stakes_matched",
            "escrow_id": escrow_id,
            "total_escrowed": escrow.stake_amount + stake_amount,
            "dispute_ref": escrow.dispute_ref,
            "message": "Both parties have staked. Dispute resolution may proceed.",
        }

    def decline_stake(self, escrow_id: str, counterparty: str) -> tuple[bool, dict[str, Any]]:
        """
        Explicitly decline to match stake (immediate fallback resolution).

        This is ALWAYS FREE for the counterparty.

        Args:
            escrow_id: The escrow to decline
            counterparty: The counterparty declining

        Returns:
            Tuple of (success, result)
        """
        if escrow_id not in self.escrows:
            return False, {"error": "Escrow not found"}

        escrow = self.escrows[escrow_id]

        if escrow.counterparty != counterparty:
            return False, {"error": "Only the designated counterparty can decline"}

        if escrow.status != "pending_match":
            return False, {"error": f"Cannot decline, escrow status is: {escrow.status}"}

        # Resolve to fallback
        escrow.status = "fallback"
        escrow.resolution = DisputeResolution.FALLBACK.value

        # Initiator gets no leverage - mark as non-resolving for harassment score
        initiator_profile = self._get_or_create_profile(escrow.initiator)
        initiator_profile.non_resolving_disputes += 1
        self._recalculate_harassment_score(initiator_profile)

        # Set cooldown for initiator on this contract
        cooldown_end = datetime.utcnow() + timedelta(days=self.DEFAULT_COOLDOWN_DAYS)
        initiator_profile.contract_cooldowns[escrow.dispute_ref] = cooldown_end.isoformat()

        self._record_action(
            "stake_declined_fallback",
            {
                "escrow_id": escrow_id,
                "counterparty": counterparty,
                "initiator": escrow.initiator,
                "initiator_stake_returned": escrow.stake_amount,
            },
        )

        return True, {
            "status": "resolved_fallback",
            "escrow_id": escrow_id,
            "resolution": DisputeResolution.FALLBACK.value,
            "initiator_stake_returned": escrow.stake_amount,
            "counterparty_cost": 0,
            "message": "Dispute resolved to fallback. Initiator gains no leverage.",
            "initiator_cooldown_until": cooldown_end.isoformat(),
        }

    def initiate_voluntary_request(
        self,
        initiator: str,
        recipient: str,
        request_type: str,
        description: str,
        burn_fee: float | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Initiate a Voluntary Request (negotiation, amendment, reconciliation).

        Key property: Recipient can ignore indefinitely at ZERO cost.
        Initiator pays a small non-refundable burn fee.

        Args:
            initiator: Address making the request
            recipient: Address receiving the request
            request_type: Type of request (negotiation, amendment, reconciliation)
            description: Natural language description
            burn_fee: Optional burn fee (defaults to DEFAULT_VOLUNTARY_BURN_FEE)

        Returns:
            Tuple of (success, result)
        """
        burn_fee = burn_fee or self.DEFAULT_VOLUNTARY_BURN_FEE

        # Perform burn if burn_manager available
        burn_result = None
        if self.burn_manager:
            from observance_burn import BurnReason

            success, burn_result = self.burn_manager.perform_burn(
                burner=initiator,
                amount=burn_fee,
                reason=BurnReason.VOLUNTARY_SIGNAL,
                epitaph=f"Voluntary request to {recipient}: {request_type}",
            )
            if not success:
                return False, {"error": "Burn failed", "details": burn_result}

        request_id = self._generate_request_id(initiator, recipient, request_type)

        request_data = {
            "request_id": request_id,
            "initiator": initiator,
            "recipient": recipient,
            "request_type": request_type,
            "description": description,
            "burn_fee_paid": burn_fee,
            "burn_tx_hash": burn_result.get("tx_hash") if burn_result else None,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",  # pending, responded, ignored, withdrawn
            "response": None,
            "responded_at": None,
        }

        self.voluntary_requests[request_id] = request_data

        self._record_action(
            "voluntary_request_initiated",
            {
                "request_id": request_id,
                "initiator": initiator,
                "recipient": recipient,
                "burn_fee": burn_fee,
            },
        )

        return True, {
            "status": "request_sent",
            "request_id": request_id,
            "path": InitiationPath.VOLUNTARY_REQUEST.value,
            "burn_fee_paid": burn_fee,
            "burn_tx_hash": burn_result.get("tx_hash") if burn_result else None,
            "recipient_obligation": "NONE - may ignore at zero cost",
            "message": "Request sent. Recipient may respond or ignore with no penalty.",
        }

    def respond_to_voluntary_request(
        self, request_id: str, recipient: str, response: str, accept: bool
    ) -> tuple[bool, dict[str, Any]]:
        """
        Respond to a voluntary request (optional - ignoring is free).

        Args:
            request_id: The request to respond to
            recipient: The recipient responding
            response: Natural language response
            accept: Whether accepting the request

        Returns:
            Tuple of (success, result)
        """
        if request_id not in self.voluntary_requests:
            return False, {"error": "Request not found"}

        request = self.voluntary_requests[request_id]

        if request["recipient"] != recipient:
            return False, {"error": "Only the designated recipient can respond"}

        if request["status"] != "pending":
            return False, {"error": f"Request already handled (status: {request['status']})"}

        request["status"] = "responded"
        request["response"] = response
        request["accepted"] = accept
        request["responded_at"] = datetime.utcnow().isoformat()

        self._record_action(
            "voluntary_request_responded",
            {"request_id": request_id, "recipient": recipient, "accepted": accept},
        )

        return True, {
            "status": "responded",
            "request_id": request_id,
            "accepted": accept,
            "recipient_cost": 0,
            "message": "Response recorded. No cost to recipient.",
        }

    # ==================== GRIEFING LIMITS ====================

    def submit_counter_proposal(
        self, dispute_ref: str, party: str, proposal_content: str
    ) -> tuple[bool, dict[str, Any]]:
        """
        Submit a counter-proposal with exponential fee enforcement.

        Counter-proposals are capped at MAX_COUNTER_PROPOSALS per party.
        Fees increase exponentially: base_fee × 2ⁿ

        Args:
            dispute_ref: The dispute reference
            party: Party submitting the counter
            proposal_content: The counter-proposal content

        Returns:
            Tuple of (success, result with fee)
        """
        if dispute_ref not in self.counter_proposal_counts:
            self.counter_proposal_counts[dispute_ref] = {}

        current_count = self.counter_proposal_counts[dispute_ref].get(party, 0)

        if current_count >= self.MAX_COUNTER_PROPOSALS:
            return False, {
                "error": "Counter-proposal limit reached",
                "max_allowed": self.MAX_COUNTER_PROPOSALS,
                "submitted": current_count,
                "message": "You have exhausted your counter-proposals for this dispute.",
            }

        # Calculate exponential fee
        fee = self.BASE_COUNTER_FEE * (self.COUNTER_FEE_MULTIPLIER**current_count)

        # Perform burn if burn_manager available
        burn_result = None
        if self.burn_manager:
            from observance_burn import BurnReason

            success, burn_result = self.burn_manager.perform_burn(
                burner=party,
                amount=fee,
                reason=BurnReason.RATE_LIMIT_EXCESS,
                epitaph=f"Counter-proposal #{current_count + 1} for {dispute_ref}",
            )
            if not success:
                return False, {"error": "Counter-proposal fee burn failed", "details": burn_result}

        # Increment counter
        self.counter_proposal_counts[dispute_ref][party] = current_count + 1

        # Update profile
        profile = self._get_or_create_profile(party)
        profile.counter_proposals_made += 1
        self._recalculate_harassment_score(profile)

        self._record_action(
            "counter_proposal_submitted",
            {
                "dispute_ref": dispute_ref,
                "party": party,
                "counter_number": current_count + 1,
                "fee_burned": fee,
            },
        )

        remaining = self.MAX_COUNTER_PROPOSALS - current_count - 1
        next_fee = (
            self.BASE_COUNTER_FEE * (self.COUNTER_FEE_MULTIPLIER ** (current_count + 1))
            if remaining > 0
            else None
        )

        return True, {
            "status": "counter_proposal_accepted",
            "dispute_ref": dispute_ref,
            "counter_number": current_count + 1,
            "fee_burned": fee,
            "burn_tx_hash": burn_result.get("tx_hash") if burn_result else None,
            "remaining_counters": remaining,
            "next_counter_fee": next_fee,
            "message": f"Counter-proposal #{current_count + 1} accepted. Fee of {fee} burned.",
        }

    def get_counter_proposal_status(self, dispute_ref: str, party: str) -> dict[str, Any]:
        """
        Get counter-proposal status for a party in a dispute.

        Args:
            dispute_ref: The dispute reference
            party: The party to check

        Returns:
            Counter-proposal status
        """
        current_count = self.counter_proposal_counts.get(dispute_ref, {}).get(party, 0)
        remaining = self.MAX_COUNTER_PROPOSALS - current_count

        # Calculate current and next fee
        current_fee = (
            self.BASE_COUNTER_FEE * (self.COUNTER_FEE_MULTIPLIER**current_count)
            if remaining > 0
            else None
        )
        next_fee = (
            self.BASE_COUNTER_FEE * (self.COUNTER_FEE_MULTIPLIER ** (current_count + 1))
            if remaining > 1
            else None
        )

        # Calculate total possible cost of all counters
        total_possible = sum(
            self.BASE_COUNTER_FEE * (self.COUNTER_FEE_MULTIPLIER**i)
            for i in range(self.MAX_COUNTER_PROPOSALS)
        )

        return {
            "dispute_ref": dispute_ref,
            "party": party,
            "counters_used": current_count,
            "counters_remaining": remaining,
            "next_counter_fee": current_fee,
            "subsequent_fee": next_fee,
            "max_total_cost": total_possible,
            "limit_reached": remaining == 0,
        }

    # ==================== HARASSMENT SCORING ====================

    def get_harassment_score(self, address: str) -> dict[str, Any]:
        """
        Get harassment score and profile for an address.

        Args:
            address: The address to check

        Returns:
            Harassment profile and score
        """
        profile = self._get_or_create_profile(address)

        severity = "none"
        if profile.harassment_score >= self.HARASSMENT_THRESHOLD_SEVERE:
            severity = "severe"
        elif profile.harassment_score >= self.HARASSMENT_THRESHOLD_HIGH:
            severity = "high"
        elif profile.harassment_score >= self.HARASSMENT_THRESHOLD_MODERATE:
            severity = "moderate"

        # Calculate cost multiplier
        cost_multiplier = self._get_cost_multiplier(profile)

        return {
            "address": address,
            "harassment_score": round(profile.harassment_score, 2),
            "severity": severity,
            "cost_multiplier": cost_multiplier,
            "metrics": {
                "initiated_disputes": profile.initiated_disputes,
                "non_resolving_disputes": profile.non_resolving_disputes,
                "ignored_voluntary_requests": profile.ignored_voluntary_requests,
                "vetoes_used": profile.vetoes_used,
                "counter_proposals_made": profile.counter_proposals_made,
            },
            "active_cooldowns": len(profile.contract_cooldowns),
            "last_updated": profile.last_updated,
        }

    def record_veto(self, party: str, dispute_ref: str) -> None:
        """Record a veto action for harassment scoring."""
        profile = self._get_or_create_profile(party)
        profile.vetoes_used += 1
        self._recalculate_harassment_score(profile)

        self._record_action(
            "veto_recorded",
            {"party": party, "dispute_ref": dispute_ref, "new_score": profile.harassment_score},
        )

    def record_ignored_request(self, initiator: str, request_id: str) -> None:
        """Record when an initiator's request was ignored (for pattern tracking)."""
        profile = self._get_or_create_profile(initiator)
        profile.ignored_voluntary_requests += 1
        self._recalculate_harassment_score(profile)

    def _get_or_create_profile(self, address: str) -> HarassmentProfile:
        """Get or create harassment profile for address."""
        if address not in self.profiles:
            self.profiles[address] = HarassmentProfile(
                address=address, last_updated=datetime.utcnow().isoformat()
            )
        return self.profiles[address]

    def _recalculate_harassment_score(self, profile: HarassmentProfile) -> None:
        """Recalculate harassment score based on all metrics."""
        score = 0.0

        score += profile.non_resolving_disputes * self.SCORE_WEIGHT_NON_RESOLVING
        score += profile.ignored_voluntary_requests * self.SCORE_WEIGHT_IGNORED_VOLUNTARY
        score += profile.vetoes_used * self.SCORE_WEIGHT_VETO

        # Penalize excessive counter-proposals (above average)
        if profile.counter_proposals_made > 5:
            excess = profile.counter_proposals_made - 5
            score += excess * self.SCORE_WEIGHT_EXCESSIVE_COUNTER

        profile.harassment_score = score
        profile.last_updated = datetime.utcnow().isoformat()

    def _get_cost_multiplier(self, profile: HarassmentProfile) -> float:
        """Get cost multiplier based on harassment score."""
        if profile.harassment_score >= self.HARASSMENT_THRESHOLD_SEVERE:
            return 3.0
        elif profile.harassment_score >= self.HARASSMENT_THRESHOLD_HIGH:
            return 2.0
        elif profile.harassment_score >= self.HARASSMENT_THRESHOLD_MODERATE:
            return 1.5
        return 1.0

    def _calculate_adjusted_stake(
        self, base_stake: float, profile: HarassmentProfile, contract_ref: str
    ) -> float:
        """
        Calculate adjusted stake based on harassment history.

        Considers:
        - Overall harassment score → cost multiplier
        - Recent non-resolving disputes → escalating stake
        """
        # Base multiplier from harassment score
        multiplier = self._get_cost_multiplier(profile)

        # Count recent non-resolving disputes (within lookback window)
        # In production, this would query historical data
        recent_non_resolving = profile.non_resolving_disputes

        # Apply escalation for repeated behavior
        if recent_non_resolving > 0:
            escalation = self.ESCALATING_STAKE_MULTIPLIER ** min(recent_non_resolving, 5)
            multiplier *= escalation

        return base_stake * multiplier

    # ==================== COOLDOWN MANAGEMENT ====================

    def _check_cooldown(self, initiator: str, contract_ref: str) -> tuple[bool, str]:
        """Check if initiator is on cooldown for this contract."""
        profile = self._get_or_create_profile(initiator)

        # Check if any active cooldown applies
        for ref, cooldown_end in profile.contract_cooldowns.items():
            if ref in contract_ref or contract_ref in ref:
                end_time = datetime.fromisoformat(cooldown_end)
                if datetime.utcnow() < end_time:
                    remaining = end_time - datetime.utcnow()
                    return (
                        False,
                        f"Cooldown active. Cannot initiate dispute until {cooldown_end} ({remaining.days} days remaining)",
                    )

        return True, ""

    def clear_expired_cooldowns(self) -> int:
        """Clear all expired cooldowns. Returns count cleared."""
        cleared = 0
        now = datetime.utcnow()

        for profile in self.profiles.values():
            expired = [
                ref
                for ref, end in profile.contract_cooldowns.items()
                if datetime.fromisoformat(end) < now
            ]
            for ref in expired:
                del profile.contract_cooldowns[ref]
                cleared += 1

        return cleared

    # ==================== STAKE WINDOW TIMEOUT ====================

    def check_stake_timeouts(self) -> list[dict[str, Any]]:
        """
        Check for stake window timeouts and resolve to fallback.

        Returns:
            List of escrows resolved due to timeout
        """
        resolved = []
        now = datetime.utcnow()

        for escrow_id, escrow in self.escrows.items():
            if escrow.status != "pending_match":
                continue

            window_end = datetime.fromisoformat(escrow.stake_window_ends)
            if now > window_end:
                # Resolve to fallback
                escrow.status = "fallback"
                escrow.resolution = DisputeResolution.TIMEOUT.value

                # Update initiator profile
                profile = self._get_or_create_profile(escrow.initiator)
                profile.non_resolving_disputes += 1
                self._recalculate_harassment_score(profile)

                # Set cooldown
                cooldown_end = now + timedelta(days=self.DEFAULT_COOLDOWN_DAYS)
                profile.contract_cooldowns[escrow.dispute_ref] = cooldown_end.isoformat()

                resolved.append(
                    {
                        "escrow_id": escrow_id,
                        "dispute_ref": escrow.dispute_ref,
                        "initiator": escrow.initiator,
                        "stake_returned": escrow.stake_amount,
                        "resolution": DisputeResolution.TIMEOUT.value,
                        "cooldown_until": cooldown_end.isoformat(),
                    }
                )

                self._record_action(
                    "stake_timeout_fallback",
                    {"escrow_id": escrow_id, "initiator": escrow.initiator},
                )

        return resolved

    # ==================== RESOLUTION ====================

    def resolve_dispute(
        self, escrow_id: str, resolution: DisputeResolution, resolver: str, resolution_details: str
    ) -> tuple[bool, dict[str, Any]]:
        """
        Resolve a matched dispute.

        Args:
            escrow_id: The escrow to resolve
            resolution: How it was resolved
            resolver: Who resolved it
            resolution_details: Details of resolution

        Returns:
            Tuple of (success, result)
        """
        if escrow_id not in self.escrows:
            return False, {"error": "Escrow not found"}

        escrow = self.escrows[escrow_id]

        if escrow.status not in ["matched", "pending_match"]:
            return False, {"error": f"Cannot resolve, status is: {escrow.status}"}

        escrow.status = "resolved"
        escrow.resolution = resolution.value

        # Return stakes (simplified - in production would handle distribution)
        total_stake = escrow.stake_amount + escrow.counterparty_stake

        self._record_action(
            "dispute_resolved",
            {
                "escrow_id": escrow_id,
                "resolution": resolution.value,
                "resolver": resolver,
                "total_stake_released": total_stake,
            },
        )

        return True, {
            "status": "resolved",
            "escrow_id": escrow_id,
            "dispute_ref": escrow.dispute_ref,
            "resolution": resolution.value,
            "total_stake_released": total_stake,
            "resolved_by": resolver,
            "details": resolution_details,
        }

    # ==================== UTILITY METHODS ====================

    def _generate_escrow_id(self, initiator: str, counterparty: str, contract_ref: str) -> str:
        """Generate unique escrow ID."""
        data = {
            "initiator": initiator,
            "counterparty": counterparty,
            "contract_ref": contract_ref,
            "timestamp": datetime.utcnow().isoformat(),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"ESCROW-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _generate_request_id(self, initiator: str, recipient: str, request_type: str) -> str:
        """Generate unique request ID."""
        data = {
            "initiator": initiator,
            "recipient": recipient,
            "request_type": request_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"VREQ-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _record_action(self, action_type: str, details: dict[str, Any]) -> None:
        """Record an action for audit trail."""
        action = {
            "action_type": action_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details,
        }
        self.actions.append(action)

    def get_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit trail entries."""
        return sorted(self.actions[-limit:], key=lambda x: x["timestamp"], reverse=True)

    def get_statistics(self) -> dict[str, Any]:
        """Get anti-harassment system statistics."""
        active_escrows = sum(1 for e in self.escrows.values() if e.status == "pending_match")
        matched_escrows = sum(1 for e in self.escrows.values() if e.status == "matched")
        fallback_resolutions = sum(1 for e in self.escrows.values() if e.status == "fallback")

        pending_requests = sum(
            1 for r in self.voluntary_requests.values() if r["status"] == "pending"
        )

        flagged_addresses = sum(
            1
            for p in self.profiles.values()
            if p.harassment_score >= self.HARASSMENT_THRESHOLD_MODERATE
        )

        return {
            "escrows": {
                "total": len(self.escrows),
                "active_pending_match": active_escrows,
                "matched_in_progress": matched_escrows,
                "resolved_fallback": fallback_resolutions,
            },
            "voluntary_requests": {
                "total": len(self.voluntary_requests),
                "pending": pending_requests,
            },
            "harassment_profiles": {
                "total_tracked": len(self.profiles),
                "flagged_moderate_plus": flagged_addresses,
            },
            "counter_proposal_limits": {
                "max_per_party": self.MAX_COUNTER_PROPOSALS,
                "base_fee": self.BASE_COUNTER_FEE,
                "fee_multiplier": self.COUNTER_FEE_MULTIPLIER,
            },
            "cooldowns": {
                "default_days": self.DEFAULT_COOLDOWN_DAYS,
                "stake_window_hours": self.DEFAULT_STAKE_WINDOW_HOURS,
            },
        }
