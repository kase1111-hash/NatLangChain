"""
NatLangChain - Treasury System
Fully on-chain, algorithmic fund for protocol sustainability and defender subsidies.

Purpose:
- Holds protocol funds from burns, counter-fees, and escalated stakes
- Subsidizes defensive stakes for low-resource participants in disputes
- Maintains no discretionary control by nodes or humans

Core Properties:
- Fully autonomous (no human discretion)
- Transparent (all actions emitted as events)
- Anti-Sybil protected (single subsidy per dispute, caps, reputation checks)
- Closed-loop economy (inflows from protocol fees, outflows to defenders)
"""

import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field


class InflowType(Enum):
    """Types of treasury inflows."""
    TIMEOUT_BURN = "timeout_burn"              # Burns from unresolved disputes
    COUNTER_FEE = "counter_fee"                 # Counter-proposal fees
    ESCALATED_STAKE = "escalated_stake"         # Stakes from frivolous initiations
    VOLUNTARY_BURN = "voluntary_burn"           # Voluntary protocol burns
    PROTOCOL_FEE = "protocol_fee"               # General protocol fees
    DONATION = "donation"                       # Direct donations


class SubsidyStatus(Enum):
    """Status of a subsidy request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    DISBURSED = "disbursed"
    EXPIRED = "expired"


class DenialReason(Enum):
    """Reasons for subsidy denial."""
    INSUFFICIENT_BALANCE = "insufficient_balance"
    ALREADY_SUBSIDIZED = "already_subsidized"
    HARASSMENT_SCORE_TOO_HIGH = "harassment_score_too_high"
    CAP_EXCEEDED = "cap_exceeded"
    NOT_DISPUTE_TARGET = "not_dispute_target"
    DISPUTE_NOT_FOUND = "dispute_not_found"
    INVALID_REQUEST = "invalid_request"


@dataclass
class Inflow:
    """Record of a treasury inflow."""
    inflow_id: str
    inflow_type: str
    amount: float
    source: str  # Address or dispute ID
    timestamp: str
    tx_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SubsidyRequest:
    """Request for defensive stake subsidy."""
    request_id: str
    dispute_id: str
    requester: str
    stake_required: float
    subsidy_requested: float
    subsidy_approved: float
    status: str
    created_at: str
    processed_at: Optional[str] = None
    denial_reason: Optional[str] = None
    disbursement_tx: Optional[str] = None


class NatLangChainTreasury:
    """
    Autonomous treasury for NatLangChain protocol.

    Key Design Principles:
    - No discretionary control by nodes or humans
    - All actions transparent and verifiable
    - Anti-Sybil protections prevent gaming
    - Sustainable through closed-loop economics
    """

    # Configuration - Subsidy Limits
    DEFAULT_MAX_SUBSIDY_PERCENT = 0.80  # Max 80% of stake subsidized
    DEFAULT_MAX_PER_DISPUTE = 500.0      # Max subsidy per dispute
    DEFAULT_MAX_PER_PARTICIPANT = 1000.0  # Max subsidy per participant (rolling window)
    ROLLING_WINDOW_DAYS = 30              # Rolling window for per-participant cap

    # Configuration - Eligibility
    MAX_HARASSMENT_SCORE_FOR_SUBSIDY = 25.0  # Must be below this to qualify
    MIN_TREASURY_BALANCE_RATIO = 0.10        # Keep at least 10% reserve

    # Configuration - Subsidy Tiers
    SUBSIDY_TIERS = [
        {"max_score": 0.0, "subsidy_percent": 1.0},    # Perfect record: 100%
        {"max_score": 10.0, "subsidy_percent": 0.80},  # Low score: 80%
        {"max_score": 20.0, "subsidy_percent": 0.60},  # Moderate score: 60%
        {"max_score": 25.0, "subsidy_percent": 0.50},  # At threshold: 50%
    ]

    def __init__(self, anti_harassment_manager=None, initial_balance: float = 0.0):
        """
        Initialize treasury.

        Args:
            anti_harassment_manager: Optional AntiHarassmentManager for score lookups
            initial_balance: Initial treasury balance
        """
        self.anti_harassment_manager = anti_harassment_manager
        self.balance = initial_balance
        self.total_inflows = 0.0
        self.total_outflows = 0.0

        # State tracking
        self.inflows: List[Inflow] = []
        self.subsidy_requests: Dict[str, SubsidyRequest] = {}
        self.dispute_subsidized: Dict[str, str] = {}  # dispute_id -> request_id
        self.participant_subsidies: Dict[str, List[Dict]] = {}  # address -> [{amount, timestamp}]

        # Audit trail
        self.events: List[Dict[str, Any]] = []

    # ==================== PHASE 12A: TREASURY CONTRACT ====================

    def deposit(
        self,
        amount: float,
        inflow_type: InflowType,
        source: str,
        tx_hash: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Deposit funds into treasury.

        Args:
            amount: Amount to deposit
            inflow_type: Type of inflow
            source: Source address or dispute ID
            tx_hash: Optional transaction hash
            metadata: Optional additional metadata

        Returns:
            Tuple of (success, result)
        """
        if amount <= 0:
            return False, {"error": "Deposit amount must be positive"}

        inflow_id = self._generate_inflow_id(amount, inflow_type, source)

        inflow = Inflow(
            inflow_id=inflow_id,
            inflow_type=inflow_type.value,
            amount=amount,
            source=source,
            timestamp=datetime.utcnow().isoformat(),
            tx_hash=tx_hash,
            metadata=metadata or {}
        )

        self.inflows.append(inflow)
        self.balance += amount
        self.total_inflows += amount

        self._emit_event("Deposit", {
            "inflow_id": inflow_id,
            "inflow_type": inflow_type.value,
            "amount": amount,
            "source": source,
            "new_balance": self.balance
        })

        return True, {
            "status": "deposited",
            "inflow_id": inflow_id,
            "amount": amount,
            "inflow_type": inflow_type.value,
            "new_balance": self.balance
        }

    def deposit_timeout_burn(
        self,
        dispute_id: str,
        amount: float,
        initiator: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Deposit from a dispute timeout burn."""
        return self.deposit(
            amount=amount,
            inflow_type=InflowType.TIMEOUT_BURN,
            source=dispute_id,
            metadata={"initiator": initiator, "reason": "dispute_timeout"}
        )

    def deposit_counter_fee(
        self,
        dispute_id: str,
        amount: float,
        party: str,
        counter_number: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Deposit from counter-proposal fee burn."""
        return self.deposit(
            amount=amount,
            inflow_type=InflowType.COUNTER_FEE,
            source=dispute_id,
            metadata={
                "party": party,
                "counter_number": counter_number
            }
        )

    def deposit_escalated_stake(
        self,
        dispute_id: str,
        amount: float,
        party: str,
        escalation_multiplier: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Deposit from escalated stake (frivolous initiation penalty)."""
        return self.deposit(
            amount=amount,
            inflow_type=InflowType.ESCALATED_STAKE,
            source=dispute_id,
            metadata={
                "party": party,
                "escalation_multiplier": escalation_multiplier
            }
        )

    def get_balance(self) -> Dict[str, Any]:
        """Get current treasury balance and statistics."""
        available = self.balance * (1 - self.MIN_TREASURY_BALANCE_RATIO)

        return {
            "total_balance": self.balance,
            "available_for_subsidies": available,
            "reserve_ratio": self.MIN_TREASURY_BALANCE_RATIO,
            "reserve_amount": self.balance * self.MIN_TREASURY_BALANCE_RATIO,
            "total_inflows": self.total_inflows,
            "total_outflows": self.total_outflows,
            "net_position": self.total_inflows - self.total_outflows
        }

    def get_inflow_history(
        self,
        limit: int = 50,
        inflow_type: Optional[InflowType] = None
    ) -> Dict[str, Any]:
        """Get inflow history with optional filtering."""
        filtered = self.inflows

        if inflow_type:
            filtered = [i for i in filtered if i.inflow_type == inflow_type.value]

        # Sort by timestamp descending
        sorted_inflows = sorted(
            filtered,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]

        return {
            "count": len(sorted_inflows),
            "total_filtered": len(filtered),
            "inflows": [
                {
                    "inflow_id": i.inflow_id,
                    "inflow_type": i.inflow_type,
                    "amount": i.amount,
                    "source": i.source,
                    "timestamp": i.timestamp,
                    "tx_hash": i.tx_hash
                }
                for i in sorted_inflows
            ]
        }

    # ==================== PHASE 12B: SUBSIDY SYSTEM ====================

    def request_subsidy(
        self,
        dispute_id: str,
        requester: str,
        stake_required: float,
        is_dispute_target: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Request a defensive stake subsidy.

        Eligibility requirements:
        1. Must be target of dispute (not initiator)
        2. Must opt-in (calling this function)
        3. Must have good on-chain dispute history (low harassment score)
        4. Dispute must not already be subsidized
        5. Participant must not exceed per-participant cap

        Args:
            dispute_id: The dispute requiring stake
            requester: Address requesting subsidy
            stake_required: Total stake required to participate
            is_dispute_target: Whether requester is the dispute target

        Returns:
            Tuple of (success, result with subsidy details or denial reason)
        """
        request_id = self._generate_request_id(dispute_id, requester)

        # Check 1: Must be dispute target
        if not is_dispute_target:
            return self._deny_subsidy(
                request_id, dispute_id, requester, stake_required,
                DenialReason.NOT_DISPUTE_TARGET
            )

        # Check 2: Dispute not already subsidized
        if dispute_id in self.dispute_subsidized:
            return self._deny_subsidy(
                request_id, dispute_id, requester, stake_required,
                DenialReason.ALREADY_SUBSIDIZED
            )

        # Check 3: Get harassment score and check eligibility
        harassment_score = self._get_harassment_score(requester)
        if harassment_score > self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY:
            return self._deny_subsidy(
                request_id, dispute_id, requester, stake_required,
                DenialReason.HARASSMENT_SCORE_TOO_HIGH,
                {"harassment_score": harassment_score, "max_allowed": self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY}
            )

        # Check 4: Per-participant cap
        participant_used = self._get_participant_usage(requester)
        if participant_used >= self.DEFAULT_MAX_PER_PARTICIPANT:
            return self._deny_subsidy(
                request_id, dispute_id, requester, stake_required,
                DenialReason.CAP_EXCEEDED,
                {"used": participant_used, "cap": self.DEFAULT_MAX_PER_PARTICIPANT}
            )

        # Calculate subsidy amount based on tier
        subsidy_percent = self._get_subsidy_percent(harassment_score)
        max_subsidy = min(
            stake_required * self.DEFAULT_MAX_SUBSIDY_PERCENT,
            self.DEFAULT_MAX_PER_DISPUTE,
            self.DEFAULT_MAX_PER_PARTICIPANT - participant_used
        )

        subsidy_amount = min(stake_required * subsidy_percent, max_subsidy)

        # Check 5: Treasury balance
        available = self.balance * (1 - self.MIN_TREASURY_BALANCE_RATIO)
        if subsidy_amount > available:
            # Partial subsidy if possible
            if available > 0:
                subsidy_amount = available
            else:
                return self._deny_subsidy(
                    request_id, dispute_id, requester, stake_required,
                    DenialReason.INSUFFICIENT_BALANCE,
                    {"available": available, "requested": subsidy_amount}
                )

        # Approve subsidy
        request = SubsidyRequest(
            request_id=request_id,
            dispute_id=dispute_id,
            requester=requester,
            stake_required=stake_required,
            subsidy_requested=stake_required * subsidy_percent,
            subsidy_approved=subsidy_amount,
            status=SubsidyStatus.APPROVED.value,
            created_at=datetime.utcnow().isoformat(),
            processed_at=datetime.utcnow().isoformat()
        )

        self.subsidy_requests[request_id] = request
        self.dispute_subsidized[dispute_id] = request_id

        self._emit_event("SubsidyApproved", {
            "request_id": request_id,
            "dispute_id": dispute_id,
            "requester": requester,
            "subsidy_approved": subsidy_amount,
            "subsidy_percent": subsidy_percent,
            "harassment_score": harassment_score
        })

        return True, {
            "status": "approved",
            "request_id": request_id,
            "dispute_id": dispute_id,
            "stake_required": stake_required,
            "subsidy_approved": subsidy_amount,
            "requester_pays": stake_required - subsidy_amount,
            "subsidy_percent": round(subsidy_percent * 100, 1),
            "harassment_score": harassment_score,
            "message": f"Subsidy of {subsidy_amount} approved. You pay {stake_required - subsidy_amount}."
        }

    def disburse_subsidy(
        self,
        request_id: str,
        escrow_address: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Disburse an approved subsidy to the stake escrow.

        Args:
            request_id: The approved subsidy request ID
            escrow_address: Address of the stake escrow contract

        Returns:
            Tuple of (success, result)
        """
        if request_id not in self.subsidy_requests:
            return False, {"error": "Subsidy request not found"}

        request = self.subsidy_requests[request_id]

        if request.status != SubsidyStatus.APPROVED.value:
            return False, {"error": f"Subsidy not in approved state (status: {request.status})"}

        amount = request.subsidy_approved

        # Verify balance still sufficient
        if amount > self.balance:
            request.status = SubsidyStatus.DENIED.value
            request.denial_reason = DenialReason.INSUFFICIENT_BALANCE.value
            return False, {"error": "Insufficient treasury balance for disbursement"}

        # Disburse
        self.balance -= amount
        self.total_outflows += amount

        # Record participant usage
        self._record_participant_usage(request.requester, amount)

        # Generate tx hash (in production, this would be actual tx)
        tx_hash = self._generate_tx_hash(request_id, amount, escrow_address)

        request.status = SubsidyStatus.DISBURSED.value
        request.disbursement_tx = tx_hash

        self._emit_event("SubsidyDisbursed", {
            "request_id": request_id,
            "dispute_id": request.dispute_id,
            "requester": request.requester,
            "amount": amount,
            "escrow_address": escrow_address,
            "tx_hash": tx_hash,
            "new_balance": self.balance
        })

        return True, {
            "status": "disbursed",
            "request_id": request_id,
            "amount": amount,
            "escrow_address": escrow_address,
            "tx_hash": tx_hash,
            "new_treasury_balance": self.balance
        }

    def _deny_subsidy(
        self,
        request_id: str,
        dispute_id: str,
        requester: str,
        stake_required: float,
        reason: DenialReason,
        details: Optional[Dict] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Record a denied subsidy request."""
        request = SubsidyRequest(
            request_id=request_id,
            dispute_id=dispute_id,
            requester=requester,
            stake_required=stake_required,
            subsidy_requested=stake_required,
            subsidy_approved=0.0,
            status=SubsidyStatus.DENIED.value,
            created_at=datetime.utcnow().isoformat(),
            processed_at=datetime.utcnow().isoformat(),
            denial_reason=reason.value
        )

        self.subsidy_requests[request_id] = request

        self._emit_event("SubsidyDenied", {
            "request_id": request_id,
            "dispute_id": dispute_id,
            "requester": requester,
            "reason": reason.value,
            "details": details
        })

        return False, {
            "status": "denied",
            "request_id": request_id,
            "reason": reason.value,
            "details": details or {},
            "message": self._get_denial_message(reason)
        }

    def _get_denial_message(self, reason: DenialReason) -> str:
        """Get human-readable denial message."""
        messages = {
            DenialReason.INSUFFICIENT_BALANCE: "Treasury balance insufficient for subsidy.",
            DenialReason.ALREADY_SUBSIDIZED: "This dispute has already received a subsidy.",
            DenialReason.HARASSMENT_SCORE_TOO_HIGH: "Harassment score exceeds eligibility threshold.",
            DenialReason.CAP_EXCEEDED: "Per-participant subsidy cap exceeded for this period.",
            DenialReason.NOT_DISPUTE_TARGET: "Only dispute targets (not initiators) can request subsidies.",
            DenialReason.DISPUTE_NOT_FOUND: "Referenced dispute not found.",
            DenialReason.INVALID_REQUEST: "Invalid subsidy request."
        }
        return messages.get(reason, "Subsidy request denied.")

    def get_subsidy_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a subsidy request."""
        if request_id not in self.subsidy_requests:
            return None

        request = self.subsidy_requests[request_id]
        return {
            "request_id": request.request_id,
            "dispute_id": request.dispute_id,
            "requester": request.requester,
            "stake_required": request.stake_required,
            "subsidy_requested": request.subsidy_requested,
            "subsidy_approved": request.subsidy_approved,
            "status": request.status,
            "created_at": request.created_at,
            "processed_at": request.processed_at,
            "denial_reason": request.denial_reason,
            "disbursement_tx": request.disbursement_tx
        }

    # ==================== PHASE 12C: ANTI-SYBIL PROTECTIONS ====================

    def _get_harassment_score(self, address: str) -> float:
        """Get harassment score for address."""
        if self.anti_harassment_manager:
            profile = self.anti_harassment_manager.get_harassment_score(address)
            return profile.get("harassment_score", 0.0)
        return 0.0

    def _get_subsidy_percent(self, harassment_score: float) -> float:
        """Get subsidy percentage based on harassment score tier."""
        for tier in self.SUBSIDY_TIERS:
            if harassment_score <= tier["max_score"]:
                return tier["subsidy_percent"]
        return 0.0  # Above all tiers

    def _get_participant_usage(self, address: str) -> float:
        """Get total subsidy usage for participant in rolling window."""
        if address not in self.participant_subsidies:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=self.ROLLING_WINDOW_DAYS)
        cutoff_str = cutoff.isoformat()

        total = sum(
            entry["amount"]
            for entry in self.participant_subsidies[address]
            if entry["timestamp"] > cutoff_str
        )

        return total

    def _record_participant_usage(self, address: str, amount: float) -> None:
        """Record subsidy usage for participant."""
        if address not in self.participant_subsidies:
            self.participant_subsidies[address] = []

        self.participant_subsidies[address].append({
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat()
        })

    def cleanup_expired_usage(self) -> int:
        """Clean up expired usage records. Returns count of records removed."""
        cutoff = datetime.utcnow() - timedelta(days=self.ROLLING_WINDOW_DAYS)
        cutoff_str = cutoff.isoformat()

        removed = 0
        for address in self.participant_subsidies:
            before_count = len(self.participant_subsidies[address])
            self.participant_subsidies[address] = [
                entry for entry in self.participant_subsidies[address]
                if entry["timestamp"] > cutoff_str
            ]
            removed += before_count - len(self.participant_subsidies[address])

        return removed

    def is_dispute_subsidized(self, dispute_id: str) -> Tuple[bool, Optional[str]]:
        """Check if a dispute has been subsidized."""
        if dispute_id in self.dispute_subsidized:
            return True, self.dispute_subsidized[dispute_id]
        return False, None

    def get_participant_subsidy_status(self, address: str) -> Dict[str, Any]:
        """Get subsidy status for a participant."""
        used = self._get_participant_usage(address)
        remaining = max(0, self.DEFAULT_MAX_PER_PARTICIPANT - used)
        harassment_score = self._get_harassment_score(address)

        eligible = harassment_score <= self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY
        subsidy_percent = self._get_subsidy_percent(harassment_score) if eligible else 0.0

        return {
            "address": address,
            "harassment_score": harassment_score,
            "eligible": eligible,
            "subsidy_percent": round(subsidy_percent * 100, 1),
            "used_this_period": used,
            "remaining_cap": remaining,
            "period_days": self.ROLLING_WINDOW_DAYS,
            "max_per_participant": self.DEFAULT_MAX_PER_PARTICIPANT,
            "subsidies_received": len(self.participant_subsidies.get(address, []))
        }

    # ==================== STATISTICS & REPORTING ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive treasury statistics."""
        # Inflow breakdown
        inflow_by_type = {}
        for i in self.inflows:
            if i.inflow_type not in inflow_by_type:
                inflow_by_type[i.inflow_type] = {"count": 0, "total": 0.0}
            inflow_by_type[i.inflow_type]["count"] += 1
            inflow_by_type[i.inflow_type]["total"] += i.amount

        # Subsidy breakdown
        subsidies_approved = sum(
            1 for r in self.subsidy_requests.values()
            if r.status in [SubsidyStatus.APPROVED.value, SubsidyStatus.DISBURSED.value]
        )
        subsidies_denied = sum(
            1 for r in self.subsidy_requests.values()
            if r.status == SubsidyStatus.DENIED.value
        )
        subsidies_disbursed = sum(
            1 for r in self.subsidy_requests.values()
            if r.status == SubsidyStatus.DISBURSED.value
        )
        total_disbursed = sum(
            r.subsidy_approved for r in self.subsidy_requests.values()
            if r.status == SubsidyStatus.DISBURSED.value
        )

        # Denial reasons breakdown
        denial_reasons = {}
        for r in self.subsidy_requests.values():
            if r.denial_reason:
                if r.denial_reason not in denial_reasons:
                    denial_reasons[r.denial_reason] = 0
                denial_reasons[r.denial_reason] += 1

        return {
            "balance": {
                "current": self.balance,
                "available_for_subsidies": self.balance * (1 - self.MIN_TREASURY_BALANCE_RATIO),
                "reserve": self.balance * self.MIN_TREASURY_BALANCE_RATIO,
                "total_inflows": self.total_inflows,
                "total_outflows": self.total_outflows
            },
            "inflows": {
                "total_count": len(self.inflows),
                "by_type": inflow_by_type
            },
            "subsidies": {
                "total_requests": len(self.subsidy_requests),
                "approved": subsidies_approved,
                "denied": subsidies_denied,
                "disbursed": subsidies_disbursed,
                "total_amount_disbursed": total_disbursed,
                "denial_reasons": denial_reasons
            },
            "disputes_subsidized": len(self.dispute_subsidized),
            "unique_beneficiaries": len(self.participant_subsidies),
            "configuration": {
                "max_subsidy_percent": self.DEFAULT_MAX_SUBSIDY_PERCENT * 100,
                "max_per_dispute": self.DEFAULT_MAX_PER_DISPUTE,
                "max_per_participant": self.DEFAULT_MAX_PER_PARTICIPANT,
                "rolling_window_days": self.ROLLING_WINDOW_DAYS,
                "max_harassment_score": self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY,
                "reserve_ratio": self.MIN_TREASURY_BALANCE_RATIO * 100
            }
        }

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit trail events."""
        return sorted(
            self.events[-limit:],
            key=lambda x: x["timestamp"],
            reverse=True
        )

    # ==================== UTILITY METHODS ====================

    def _generate_inflow_id(
        self,
        amount: float,
        inflow_type: InflowType,
        source: str
    ) -> str:
        """Generate unique inflow ID."""
        data = {
            "amount": str(amount),
            "type": inflow_type.value,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"INFLOW-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _generate_request_id(self, dispute_id: str, requester: str) -> str:
        """Generate unique subsidy request ID."""
        data = {
            "dispute_id": dispute_id,
            "requester": requester,
            "timestamp": datetime.utcnow().isoformat()
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"SUBSIDY-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _generate_tx_hash(
        self,
        request_id: str,
        amount: float,
        destination: str
    ) -> str:
        """Generate transaction hash for disbursement."""
        data = {
            "request_id": request_id,
            "amount": str(amount),
            "destination": destination,
            "timestamp": datetime.utcnow().isoformat()
        }
        hash_input = json.dumps(data, sort_keys=True)
        return "0x" + hashlib.sha256(hash_input.encode()).hexdigest()

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event for audit trail."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        self.events.append(event)

    # ==================== INTEGRATION HELPERS ====================

    def set_anti_harassment_manager(self, manager) -> None:
        """Set the anti-harassment manager for score lookups."""
        self.anti_harassment_manager = manager

    def simulate_subsidy(
        self,
        requester: str,
        stake_required: float
    ) -> Dict[str, Any]:
        """
        Simulate a subsidy request without creating a record.
        Useful for UI to show potential subsidy before committing.

        Args:
            requester: Address requesting subsidy
            stake_required: Total stake required

        Returns:
            Simulation result with potential subsidy details
        """
        harassment_score = self._get_harassment_score(requester)

        if harassment_score > self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY:
            return {
                "eligible": False,
                "reason": "harassment_score_too_high",
                "harassment_score": harassment_score,
                "max_allowed": self.MAX_HARASSMENT_SCORE_FOR_SUBSIDY
            }

        participant_used = self._get_participant_usage(requester)
        if participant_used >= self.DEFAULT_MAX_PER_PARTICIPANT:
            return {
                "eligible": False,
                "reason": "cap_exceeded",
                "used": participant_used,
                "cap": self.DEFAULT_MAX_PER_PARTICIPANT
            }

        subsidy_percent = self._get_subsidy_percent(harassment_score)
        max_subsidy = min(
            stake_required * self.DEFAULT_MAX_SUBSIDY_PERCENT,
            self.DEFAULT_MAX_PER_DISPUTE,
            self.DEFAULT_MAX_PER_PARTICIPANT - participant_used
        )

        available = self.balance * (1 - self.MIN_TREASURY_BALANCE_RATIO)
        potential_subsidy = min(stake_required * subsidy_percent, max_subsidy, available)

        return {
            "eligible": True,
            "harassment_score": harassment_score,
            "subsidy_percent": round(subsidy_percent * 100, 1),
            "stake_required": stake_required,
            "potential_subsidy": potential_subsidy,
            "you_would_pay": stake_required - potential_subsidy,
            "treasury_available": available,
            "remaining_cap": self.DEFAULT_MAX_PER_PARTICIPANT - participant_used
        }
