"""
NatLangChain - Escalation Fork Protocol
Extends MP-01 with optional fork mechanism when mediation fails.
Fee pool splits 50/50 between mediator and resolution bounty pool.
"""

import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class ForkStatus(Enum):
    """Fork lifecycle states."""
    PENDING_BURN = "pending_burn"  # Awaiting Observance Burn
    ACTIVE = "active"              # Solver window open
    RESOLVED = "resolved"          # Both parties ratified
    TIMEOUT = "timeout"            # Solver window expired
    CANCELLED = "cancelled"        # Fork cancelled


class TriggerReason(Enum):
    """Valid escalation fork trigger reasons."""
    FAILED_RATIFICATION = "failed_ratification"
    REFUSAL_TO_MEDIATE = "refusal_to_mediate"
    MEDIATION_TIMEOUT = "timeout"
    MUTUAL_REQUEST = "mutual_request"


class EscalationForkManager:
    """
    Manages the Escalation Fork protocol for failed mediations.

    Core Principle: When negotiation hits a wall, the system doesn't
    stall—it opens the floor to anyone who can solve the deadlock.

    Fee pool splits:
    - 50% retained by original mediator
    - 50% goes to Resolution Bounty Pool for solvers
    """

    # Configuration
    DEFAULT_SOLVER_WINDOW_DAYS = 7
    DEFAULT_FEE_SPLIT = 0.50  # 50% to bounty pool
    DEFAULT_TIMEOUT_REFUND = 0.90  # 90% refunded on timeout
    DEFAULT_TIMEOUT_BURN = 0.10  # 10% burned on timeout

    # Effort weight configuration
    EFFORT_WEIGHT_WORDS = 0.30
    EFFORT_WEIGHT_ITERATIONS = 0.40
    EFFORT_WEIGHT_ALIGNMENT = 0.30

    # Minimum requirements
    MIN_PROPOSAL_WORDS = 500
    MIN_VETO_REASON_WORDS = 100
    MAX_VETOES_PER_PARTY = 3

    def __init__(self):
        """Initialize fork manager."""
        # In production, these would be persisted
        self.forks: Dict[str, Dict[str, Any]] = {}
        self.proposals: Dict[str, List[Dict[str, Any]]] = {}  # fork_id -> proposals
        self.ratifications: Dict[str, Dict[str, Dict]] = {}  # fork_id -> party -> ratification
        self.vetoes: Dict[str, Dict[str, int]] = {}  # fork_id -> party -> veto count

    def trigger_fork(
        self,
        dispute_id: str,
        trigger_reason: TriggerReason,
        triggering_party: str,
        original_mediator: str,
        original_pool: float,
        burn_tx_hash: str,
        evidence_of_failure: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger an Escalation Fork after Observance Burn is verified.

        Args:
            dispute_id: The dispute/mediation being escalated
            trigger_reason: Why the fork is being triggered
            triggering_party: Party triggering the escalation
            original_mediator: Original mediator node ID
            original_pool: Total fee pool amount
            burn_tx_hash: Transaction hash proving Observance Burn
            evidence_of_failure: Failed proposals, rejection reasons, etc.

        Returns:
            Fork metadata
        """
        fork_id = self._generate_fork_id(dispute_id, triggering_party)

        solver_window_ends = datetime.utcnow() + timedelta(days=self.DEFAULT_SOLVER_WINDOW_DAYS)

        mediator_retained = original_pool * self.DEFAULT_FEE_SPLIT
        bounty_pool = original_pool * self.DEFAULT_FEE_SPLIT

        fork_data = {
            "fork_id": fork_id,
            "dispute_id": dispute_id,
            "status": ForkStatus.ACTIVE.value,
            "trigger_reason": trigger_reason.value if isinstance(trigger_reason, TriggerReason) else trigger_reason,
            "triggering_party": triggering_party,
            "original_mediator": original_mediator,
            "original_pool": original_pool,
            "mediator_retained": mediator_retained,
            "bounty_pool": bounty_pool,
            "burn_tx_hash": burn_tx_hash,
            "observance_burn_verified": True,
            "evidence_of_failure": evidence_of_failure or {},
            "solver_window_ends": solver_window_ends.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "winning_proposal": None,
            "distribution": None
        }

        self.forks[fork_id] = fork_data
        self.proposals[fork_id] = []
        self.ratifications[fork_id] = {}
        self.vetoes[fork_id] = {}

        return fork_data

    def _generate_fork_id(self, dispute_id: str, triggering_party: str) -> str:
        """Generate unique fork ID."""
        data = {
            "dispute_id": dispute_id,
            "triggering_party": triggering_party,
            "timestamp": datetime.utcnow().isoformat()
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"FORK-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def submit_proposal(
        self,
        fork_id: str,
        solver: str,
        proposal_content: str,
        addresses_concerns: List[str],
        supporting_evidence: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a resolution proposal to an active fork.

        Args:
            fork_id: The fork to submit to
            solver: Solver submitting the proposal
            proposal_content: Full proposal text
            addresses_concerns: List of concerns addressed
            supporting_evidence: Optional evidence references

        Returns:
            Tuple of (success, proposal data or error)
        """
        if fork_id not in self.forks:
            return False, {"error": "Fork not found"}

        fork = self.forks[fork_id]

        if fork["status"] != ForkStatus.ACTIVE.value:
            return False, {"error": f"Fork is not active (status: {fork['status']})"}

        # Check solver window
        window_end = datetime.fromisoformat(fork["solver_window_ends"])
        if datetime.utcnow() > window_end:
            return False, {"error": "Solver window has expired"}

        # Validate minimum word count
        word_count = len(proposal_content.split())
        if word_count < self.MIN_PROPOSAL_WORDS:
            return False, {"error": f"Proposal must be at least {self.MIN_PROPOSAL_WORDS} words (got {word_count})"}

        # Count iterations for this solver
        existing_proposals = [p for p in self.proposals[fork_id] if p["solver"] == solver]
        iteration = len(existing_proposals) + 1

        proposal_id = f"PROP-{fork_id[-8:]}-{solver[:6].upper()}-{iteration:03d}"

        proposal_data = {
            "proposal_id": proposal_id,
            "fork_id": fork_id,
            "solver": solver,
            "content": proposal_content,
            "word_count": word_count,
            "addresses_concerns": addresses_concerns,
            "supporting_evidence": supporting_evidence or [],
            "iteration": iteration,
            "submitted_at": datetime.utcnow().isoformat(),
            "ratifications": {},
            "vetoed": False,
            "veto_reason": None
        }

        self.proposals[fork_id].append(proposal_data)

        return True, proposal_data

    def ratify_proposal(
        self,
        fork_id: str,
        proposal_id: str,
        ratifying_party: str,
        satisfaction_rating: int,
        comments: Optional[str] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Ratify a proposal (both parties must ratify for resolution).

        Args:
            fork_id: The fork
            proposal_id: The proposal to ratify
            ratifying_party: Party ratifying
            satisfaction_rating: 0-100 satisfaction score
            comments: Optional comments

        Returns:
            Tuple of (success, result data)
        """
        if fork_id not in self.forks:
            return False, {"error": "Fork not found"}

        fork = self.forks[fork_id]

        if fork["status"] != ForkStatus.ACTIVE.value:
            return False, {"error": f"Fork is not active (status: {fork['status']})"}

        # Find the proposal
        proposal = None
        for p in self.proposals[fork_id]:
            if p["proposal_id"] == proposal_id:
                proposal = p
                break

        if not proposal:
            return False, {"error": "Proposal not found"}

        if proposal.get("vetoed"):
            return False, {"error": "Proposal has been vetoed"}

        # Record ratification
        proposal["ratifications"][ratifying_party] = {
            "accepted": True,
            "satisfaction_rating": satisfaction_rating,
            "comments": comments,
            "ratified_at": datetime.utcnow().isoformat()
        }

        # Check if both parties have ratified
        # In a real implementation, we'd track the dispute parties
        if len(proposal["ratifications"]) >= 2:
            return self._resolve_fork(fork_id, proposal)

        return True, {
            "status": "ratification_recorded",
            "proposal_id": proposal_id,
            "ratifying_party": ratifying_party,
            "awaiting_ratification_from": "other party"
        }

    def _resolve_fork(
        self,
        fork_id: str,
        winning_proposal: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Resolve the fork after dual ratification."""
        fork = self.forks[fork_id]

        # Calculate effort-based distribution
        distribution = self._calculate_distribution(fork_id, winning_proposal)

        fork["status"] = ForkStatus.RESOLVED.value
        fork["resolved_at"] = datetime.utcnow().isoformat()
        fork["winning_proposal"] = winning_proposal["proposal_id"]
        fork["distribution"] = distribution

        return True, {
            "fork_id": fork_id,
            "status": "resolved",
            "winning_proposal": winning_proposal["proposal_id"],
            "solver": winning_proposal["solver"],
            "bounty_distributed": True,
            "distribution": distribution
        }

    def _calculate_distribution(
        self,
        fork_id: str,
        winning_proposal: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate effort-based bounty distribution.

        Formula: Solver's Share = (Solver Effort / Total Resolution Effort) * Bounty Pool

        Effort Metrics:
        - Word Count: 30%
        - Proposal Iterations: 40%
        - Alignment Score: 30%
        """
        fork = self.forks[fork_id]
        bounty_pool = fork["bounty_pool"]

        # Get all proposals for this fork to calculate total effort
        all_proposals = self.proposals.get(fork_id, [])

        if not all_proposals:
            return {winning_proposal["solver"]: bounty_pool}

        # Calculate effort scores for all contributing solvers
        solver_efforts = {}
        for proposal in all_proposals:
            if proposal.get("vetoed"):
                continue

            solver = proposal["solver"]

            # Word count score (normalized to 0-1, capped at 5000 words)
            word_score = min(proposal["word_count"] / 5000, 1.0) * self.EFFORT_WEIGHT_WORDS

            # Iteration score (normalized to 0-1, capped at 10 iterations)
            iteration_score = min(proposal["iteration"] / 10, 1.0) * self.EFFORT_WEIGHT_ITERATIONS

            # Alignment score from ratifications
            ratings = [r.get("satisfaction_rating", 50) for r in proposal.get("ratifications", {}).values()]
            avg_rating = sum(ratings) / len(ratings) if ratings else 50
            alignment_score = (avg_rating / 100) * self.EFFORT_WEIGHT_ALIGNMENT

            effort = word_score + iteration_score + alignment_score

            if solver in solver_efforts:
                solver_efforts[solver] += effort
            else:
                solver_efforts[solver] = effort

        # Calculate distribution
        total_effort = sum(solver_efforts.values())

        if total_effort == 0:
            return {winning_proposal["solver"]: bounty_pool}

        distribution = {}
        for solver, effort in solver_efforts.items():
            share = (effort / total_effort) * bounty_pool
            distribution[solver] = round(share, 2)

        return distribution

    def veto_proposal(
        self,
        fork_id: str,
        proposal_id: str,
        vetoing_party: str,
        veto_reason: str,
        evidence_refs: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Veto a proposal with documented reasoning.

        Args:
            fork_id: The fork
            proposal_id: Proposal to veto
            vetoing_party: Party vetoing
            veto_reason: Why (must be 100+ words)
            evidence_refs: Supporting evidence

        Returns:
            Tuple of (success, result)
        """
        if fork_id not in self.forks:
            return False, {"error": "Fork not found"}

        fork = self.forks[fork_id]

        if fork["status"] != ForkStatus.ACTIVE.value:
            return False, {"error": f"Fork is not active (status: {fork['status']})"}

        # Check veto limit
        if fork_id not in self.vetoes:
            self.vetoes[fork_id] = {}

        current_vetoes = self.vetoes[fork_id].get(vetoing_party, 0)
        if current_vetoes >= self.MAX_VETOES_PER_PARTY:
            return False, {"error": f"Maximum vetoes ({self.MAX_VETOES_PER_PARTY}) reached for this party"}

        # Validate veto reason word count
        word_count = len(veto_reason.split())
        if word_count < self.MIN_VETO_REASON_WORDS:
            return False, {"error": f"Veto reason must be at least {self.MIN_VETO_REASON_WORDS} words (got {word_count})"}

        # Find and veto the proposal
        for proposal in self.proposals[fork_id]:
            if proposal["proposal_id"] == proposal_id:
                proposal["vetoed"] = True
                proposal["veto_reason"] = veto_reason
                proposal["vetoed_by"] = vetoing_party
                proposal["vetoed_at"] = datetime.utcnow().isoformat()
                proposal["veto_evidence"] = evidence_refs or []

                self.vetoes[fork_id][vetoing_party] = current_vetoes + 1

                return True, {
                    "status": "vetoed",
                    "proposal_id": proposal_id,
                    "vetoing_party": vetoing_party,
                    "remaining_vetoes": self.MAX_VETOES_PER_PARTY - current_vetoes - 1
                }

        return False, {"error": "Proposal not found"}

    def check_timeout(self, fork_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if fork has timed out and process if so.

        Returns:
            Tuple of (is_timed_out, timeout_result if applicable)
        """
        if fork_id not in self.forks:
            return False, None

        fork = self.forks[fork_id]

        if fork["status"] != ForkStatus.ACTIVE.value:
            return False, None

        window_end = datetime.fromisoformat(fork["solver_window_ends"])

        if datetime.utcnow() <= window_end:
            return False, None

        # Process timeout
        bounty_pool = fork["bounty_pool"]
        refund_amount = bounty_pool * self.DEFAULT_TIMEOUT_REFUND
        burn_amount = bounty_pool * self.DEFAULT_TIMEOUT_BURN

        fork["status"] = ForkStatus.TIMEOUT.value
        fork["resolved_at"] = datetime.utcnow().isoformat()
        fork["distribution"] = {
            "party_a_refund": round(refund_amount / 2, 2),
            "party_b_refund": round(refund_amount / 2, 2),
            "observance_burn": round(burn_amount, 2)
        }

        return True, {
            "fork_id": fork_id,
            "status": "timeout",
            "bounty_pool": bounty_pool,
            "distribution": fork["distribution"],
            "timeout_reason": "No ratified proposal within solver window"
        }

    def get_fork_status(self, fork_id: str) -> Optional[Dict[str, Any]]:
        """Get current fork status with proposals and ratifications."""
        if fork_id not in self.forks:
            return None

        fork = self.forks[fork_id].copy()
        fork["proposals"] = self.proposals.get(fork_id, [])
        fork["total_proposals"] = len(fork["proposals"])
        fork["ratified_proposals"] = sum(
            1 for p in fork["proposals"]
            if len(p.get("ratifications", {})) >= 2
        )
        fork["vetoed_proposals"] = sum(
            1 for p in fork["proposals"]
            if p.get("vetoed")
        )

        # Check for timeout
        if fork["status"] == ForkStatus.ACTIVE.value:
            is_timeout, _ = self.check_timeout(fork_id)
            if is_timeout:
                fork = self.forks[fork_id].copy()

        return fork

    def get_fork_audit_trail(self, fork_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for a fork."""
        if fork_id not in self.forks:
            return []

        fork = self.forks[fork_id]
        trail = []

        # Fork creation
        trail.append({
            "audit_type": "fork_action",
            "fork_id": fork_id,
            "action": "fork_created",
            "actor": fork["triggering_party"],
            "timestamp": fork["created_at"],
            "details": {
                "trigger_reason": fork["trigger_reason"],
                "original_pool": fork["original_pool"],
                "bounty_pool": fork["bounty_pool"]
            }
        })

        # Proposals
        for proposal in self.proposals.get(fork_id, []):
            trail.append({
                "audit_type": "fork_action",
                "fork_id": fork_id,
                "action": "proposal_submitted",
                "actor": proposal["solver"],
                "timestamp": proposal["submitted_at"],
                "details": {
                    "proposal_id": proposal["proposal_id"],
                    "word_count": proposal["word_count"],
                    "iteration": proposal["iteration"]
                }
            })

            # Ratifications
            for party, ratification in proposal.get("ratifications", {}).items():
                trail.append({
                    "audit_type": "fork_action",
                    "fork_id": fork_id,
                    "action": "proposal_ratified",
                    "actor": party,
                    "timestamp": ratification["ratified_at"],
                    "details": {
                        "proposal_id": proposal["proposal_id"],
                        "satisfaction_rating": ratification["satisfaction_rating"]
                    }
                })

            # Veto
            if proposal.get("vetoed"):
                trail.append({
                    "audit_type": "fork_action",
                    "fork_id": fork_id,
                    "action": "proposal_vetoed",
                    "actor": proposal.get("vetoed_by"),
                    "timestamp": proposal.get("vetoed_at"),
                    "details": {
                        "proposal_id": proposal["proposal_id"]
                    }
                })

        # Resolution
        if fork.get("resolved_at"):
            trail.append({
                "audit_type": "fork_action",
                "fork_id": fork_id,
                "action": "fork_resolved" if fork["status"] == ForkStatus.RESOLVED.value else "fork_timeout",
                "actor": "system",
                "timestamp": fork["resolved_at"],
                "details": {
                    "status": fork["status"],
                    "distribution": fork.get("distribution")
                }
            })

        # Sort by timestamp
        trail.sort(key=lambda x: x["timestamp"])

        # Add hashes for integrity
        prev_hash = "0" * 64
        for entry in trail:
            entry_content = json.dumps({k: v for k, v in entry.items() if k != "action_hash"}, sort_keys=True)
            entry["previous_action_hash"] = prev_hash
            entry["action_hash"] = hashlib.sha256((prev_hash + entry_content).encode()).hexdigest()
            prev_hash = entry["action_hash"]

        return trail

    def list_active_forks(self) -> List[Dict[str, Any]]:
        """List all active forks."""
        return [
            self.get_fork_status(fork_id)
            for fork_id, fork in self.forks.items()
            if fork["status"] == ForkStatus.ACTIVE.value
        ]
