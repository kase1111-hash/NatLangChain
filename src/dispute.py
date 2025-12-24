"""
NatLangChain - Dispute Protocol (MP-03)
Handles dispute declaration, evidence freezing, escalation, and resolution
Per the Refusal Doctrine: disputes are signals, not failures

Integrates NCIP-005: Semantic Locking & Cooling Periods
Integrates NCIP-010: Mediator Reputation, Bonding & Slashing
"""

import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import os

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# Import NCIP-005 semantic locking
try:
    from semantic_locking import (
        SemanticLockManager,
        SemanticLock,
        DisputeLevel,
        DisputeTrigger,
        LockAction,
        EscalationStage,
        ResolutionOutcome,
        CoolingPeriodStatus,
        get_ncip_005_config,
        get_cooling_period_hours,
        is_action_allowed_during_cooling,
        is_action_forbidden_during_lock
    )
    NCIP_005_AVAILABLE = True
except ImportError:
    NCIP_005_AVAILABLE = False

# Import NCIP-010 mediator reputation
try:
    from mediator_reputation import (
        MediatorReputationManager,
        MediatorProfile,
        MediatorStatus,
        SlashingOffense,
        CooldownReason,
        ProposalStatus,
        get_reputation_manager,
        get_ncip_010_config,
        MINIMUM_BOND,
        DEFAULT_BOND,
        CTS_WEIGHTS
    )
    NCIP_010_AVAILABLE = True
except ImportError:
    NCIP_010_AVAILABLE = False


class DisputeManager:
    """
    Manages dispute lifecycle per MP-03 protocol.

    Key principles:
    - Disputes are signals, not failures
    - Evidence freezing upon dispute initiation
    - No automated resolution; human judgment required
    - Explicit escalation declarations
    """

    # Dispute types
    TYPE_DECLARATION = "dispute_declaration"
    TYPE_EVIDENCE = "dispute_evidence"
    TYPE_ESCALATION = "dispute_escalation"
    TYPE_RESOLUTION = "dispute_resolution"
    TYPE_CLARIFICATION = "dispute_clarification"

    # Dispute statuses
    STATUS_OPEN = "open"
    STATUS_CLARIFYING = "clarifying"
    STATUS_ESCALATED = "escalated"
    STATUS_RESOLVED = "resolved"
    STATUS_WITHDRAWN = "withdrawn"

    # Escalation paths
    ESCALATION_MEDIATOR = "mediator_node"
    ESCALATION_ARBITRATOR = "external_arbitrator"
    ESCALATION_COURT = "legal_court"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize dispute manager.

        Args:
            api_key: Anthropic API key for LLM-assisted analysis
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if (self.api_key and Anthropic) else None
        self.model = "claude-3-5-sonnet-20241022"

        # Track frozen evidence (in production, this would be persisted)
        self.frozen_entries: Dict[str, Dict] = {}

    def create_dispute(
        self,
        claimant: str,
        respondent: str,
        contested_refs: List[Dict[str, Any]],
        description: str,
        escalation_path: str = ESCALATION_MEDIATOR,
        supporting_evidence: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new dispute declaration.

        Args:
            claimant: Identifier of party filing dispute
            respondent: Identifier of party being disputed against
            contested_refs: List of block/entry references being contested
            description: Natural language description of the dispute
            escalation_path: Preferred escalation path
            supporting_evidence: Optional list of evidence hashes

        Returns:
            Dispute metadata for entry creation
        """
        dispute_id = self._generate_dispute_id(claimant, contested_refs)

        dispute_data = {
            "is_dispute": True,
            "dispute_type": self.TYPE_DECLARATION,
            "dispute_id": dispute_id,
            "claimant": claimant,
            "respondent": respondent,
            "contested_refs": contested_refs,
            "description": description,
            "escalation_path": escalation_path,
            "status": self.STATUS_OPEN,
            "evidence_frozen": True,
            "frozen_at": datetime.utcnow().isoformat(),
            "supporting_evidence": supporting_evidence or [],
            "resolution": None,
            "created_at": datetime.utcnow().isoformat()
        }

        # Freeze contested entries
        for ref in contested_refs:
            self._freeze_entry(ref, dispute_id)

        return dispute_data

    def _generate_dispute_id(
        self,
        claimant: str,
        contested_refs: List[Dict]
    ) -> str:
        """Generate unique dispute ID."""
        data = {
            "claimant": claimant,
            "contested_refs": contested_refs,
            "timestamp": datetime.utcnow().isoformat()
        }
        hash_input = json.dumps(data, sort_keys=True)
        return f"DISPUTE-{hashlib.sha256(hash_input.encode()).hexdigest()[:12].upper()}"

    def _freeze_entry(self, ref: Dict[str, Any], dispute_id: str) -> None:
        """
        Mark an entry as frozen due to dispute.

        Args:
            ref: Block/entry reference
            dispute_id: Associated dispute ID
        """
        ref_key = f"{ref.get('block', 0)}:{ref.get('entry', 0)}"
        self.frozen_entries[ref_key] = {
            "dispute_id": dispute_id,
            "frozen_at": datetime.utcnow().isoformat(),
            "ref": ref
        }

    def is_entry_frozen(self, block_index: int, entry_index: int) -> Tuple[bool, Optional[str]]:
        """
        Check if an entry is frozen due to dispute.

        Args:
            block_index: Block index
            entry_index: Entry index

        Returns:
            Tuple of (is_frozen, dispute_id if frozen)
        """
        ref_key = f"{block_index}:{entry_index}"
        if ref_key in self.frozen_entries:
            return True, self.frozen_entries[ref_key].get("dispute_id")
        return False, None

    def add_evidence(
        self,
        dispute_id: str,
        author: str,
        evidence_content: str,
        evidence_type: str = "document",
        evidence_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add evidence to an existing dispute.

        Args:
            dispute_id: The dispute to add evidence to
            author: Who is submitting the evidence
            evidence_content: Description/content of evidence
            evidence_type: Type of evidence (document, testimony, receipt, etc.)
            evidence_hash: Hash of external evidence file

        Returns:
            Evidence entry metadata
        """
        if not evidence_hash:
            evidence_hash = hashlib.sha256(evidence_content.encode()).hexdigest()

        return {
            "is_dispute": True,
            "dispute_type": self.TYPE_EVIDENCE,
            "dispute_id": dispute_id,
            "evidence_author": author,
            "evidence_type": evidence_type,
            "evidence_hash": evidence_hash,
            "submitted_at": datetime.utcnow().isoformat()
        }

    def request_clarification(
        self,
        dispute_id: str,
        author: str,
        clarification_request: str,
        directed_to: str
    ) -> Dict[str, Any]:
        """
        Request clarification from a party.

        Args:
            dispute_id: The dispute requiring clarification
            author: Who is requesting clarification
            clarification_request: What needs to be clarified
            directed_to: Who should respond

        Returns:
            Clarification request metadata
        """
        return {
            "is_dispute": True,
            "dispute_type": self.TYPE_CLARIFICATION,
            "dispute_id": dispute_id,
            "requested_by": author,
            "directed_to": directed_to,
            "status": self.STATUS_CLARIFYING,
            "clarification_request": clarification_request,
            "requested_at": datetime.utcnow().isoformat()
        }

    def escalate_dispute(
        self,
        dispute_id: str,
        escalating_party: str,
        escalation_path: str,
        escalation_reason: str,
        escalation_authority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Escalate a dispute to higher authority.

        Args:
            dispute_id: The dispute to escalate
            escalating_party: Who is escalating
            escalation_path: Where to escalate (mediator, arbitrator, court)
            escalation_reason: Why escalation is needed
            escalation_authority: Specific authority if known

        Returns:
            Escalation entry metadata
        """
        return {
            "is_dispute": True,
            "dispute_type": self.TYPE_ESCALATION,
            "dispute_id": dispute_id,
            "escalating_party": escalating_party,
            "escalation_path": escalation_path,
            "escalation_reason": escalation_reason,
            "escalation_authority": escalation_authority,
            "status": self.STATUS_ESCALATED,
            "escalated_at": datetime.utcnow().isoformat()
        }

    def record_resolution(
        self,
        dispute_id: str,
        resolution_authority: str,
        resolution_type: str,
        resolution_content: str,
        findings: Optional[Dict[str, Any]] = None,
        remedies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Record the resolution of a dispute.

        Note: Per Refusal Doctrine, this only RECORDS resolution.
        Actual resolution is a human act.

        Args:
            dispute_id: The dispute being resolved
            resolution_authority: Who authorized the resolution
            resolution_type: Type of resolution (settled, arbitrated, adjudicated, withdrawn)
            resolution_content: Natural language resolution description
            findings: Structured findings
            remedies: List of remedies/actions required

        Returns:
            Resolution entry metadata
        """
        # Unfreeze entries when resolved
        entries_to_unfreeze = [
            key for key, val in self.frozen_entries.items()
            if val.get("dispute_id") == dispute_id
        ]
        for key in entries_to_unfreeze:
            del self.frozen_entries[key]

        return {
            "is_dispute": True,
            "dispute_type": self.TYPE_RESOLUTION,
            "dispute_id": dispute_id,
            "resolution_authority": resolution_authority,
            "resolution_type": resolution_type,
            "findings": findings or {},
            "remedies": remedies or [],
            "entries_unfrozen": len(entries_to_unfreeze),
            "status": self.STATUS_RESOLVED,
            "resolved_at": datetime.utcnow().isoformat()
        }

    def generate_dispute_package(
        self,
        dispute_id: str,
        blockchain,
        include_frozen_entries: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a complete dispute package for external arbitration.

        This package contains all information needed for an external
        authority to review and resolve the dispute.

        Args:
            dispute_id: The dispute to package
            blockchain: The NatLangChain instance
            include_frozen_entries: Whether to include full frozen entry content

        Returns:
            Complete dispute package
        """
        package = {
            "package_id": f"PKG-{dispute_id}",
            "generated_at": datetime.utcnow().isoformat(),
            "dispute_id": dispute_id,
            "dispute_entries": [],
            "contested_entries": [],
            "evidence_entries": [],
            "escalation_history": [],
            "frozen_entries": [],
            "chain_verification": {
                "chain_valid": blockchain.validate_chain(),
                "total_blocks": len(blockchain.chain)
            }
        }

        # Collect all dispute-related entries
        for block in blockchain.chain:
            for entry_idx, entry in enumerate(block.entries):
                metadata = entry.metadata or {}

                if metadata.get("dispute_id") == dispute_id:
                    entry_data = {
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "entry_index": entry_idx,
                        "entry": entry.to_dict()
                    }

                    dispute_type = metadata.get("dispute_type")
                    if dispute_type == self.TYPE_DECLARATION:
                        package["dispute_entries"].append(entry_data)
                        # Get contested refs
                        contested_refs = metadata.get("contested_refs", [])
                        package["contested_refs"] = contested_refs
                    elif dispute_type == self.TYPE_EVIDENCE:
                        package["evidence_entries"].append(entry_data)
                    elif dispute_type == self.TYPE_ESCALATION:
                        package["escalation_history"].append(entry_data)

        # Include frozen entries if requested
        if include_frozen_entries:
            for ref_key, freeze_data in self.frozen_entries.items():
                if freeze_data.get("dispute_id") == dispute_id:
                    ref = freeze_data.get("ref", {})
                    block_idx = ref.get("block", 0)
                    entry_idx = ref.get("entry", 0)

                    if block_idx < len(blockchain.chain):
                        block = blockchain.chain[block_idx]
                        if entry_idx < len(block.entries):
                            entry = block.entries[entry_idx]
                            package["frozen_entries"].append({
                                "block_index": block_idx,
                                "entry_index": entry_idx,
                                "block_hash": block.hash,
                                "frozen_at": freeze_data.get("frozen_at"),
                                "entry": entry.to_dict()
                            })

        # Generate package hash for integrity
        package_content = json.dumps(package, sort_keys=True)
        package["integrity_hash"] = hashlib.sha256(package_content.encode()).hexdigest()

        return package

    def analyze_dispute(self, dispute_description: str, contested_content: str) -> Optional[Dict[str, Any]]:
        """
        Use LLM to analyze a dispute and identify key issues.

        Note: This is for ANALYSIS only. Per Refusal Doctrine,
        LLMs do not resolve disputes.

        Args:
            dispute_description: The dispute description
            contested_content: Content being contested

        Returns:
            Analysis of the dispute or None if LLM not available
        """
        if not self.client:
            return None

        try:
            prompt = f"""Analyze this dispute and identify key issues.
DO NOT resolve or judge - only analyze and structure.

DISPUTE DESCRIPTION:
{dispute_description}

CONTESTED CONTENT:
{contested_content}

Provide analysis in JSON format:
{{
    "key_issues": ["list of main issues in dispute"],
    "ambiguities_identified": ["any unclear terms or conditions"],
    "missing_information": ["information needed for resolution"],
    "parties_claims_summary": {{
        "claimant": "summary of claimant's position",
        "respondent": "summary of likely respondent position"
    }},
    "suggested_clarifications": ["questions that should be clarified"],
    "complexity_assessment": "simple/moderate/complex",
    "recommended_escalation_path": "mediator_node/external_arbitrator/legal_court"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            return json.loads(response_text)

        except Exception as e:
            print(f"Dispute analysis failed: {e}")
            return None

    def validate_dispute_clarity(self, description: str) -> Tuple[bool, str]:
        """
        Validate that dispute description is clear enough to proceed.

        Args:
            description: Dispute description

        Returns:
            Tuple of (is_valid, reason)
        """
        # Basic checks without LLM
        if len(description.strip()) < 50:
            return False, "Dispute description too brief. Please provide more detail."

        required_elements = ["contested", "dispute", "claim", "issue", "disagree", "violation", "breach"]
        description_lower = description.lower()

        has_dispute_language = any(elem in description_lower for elem in required_elements)
        if not has_dispute_language:
            return False, "Dispute description should clearly identify what is being contested."

        if not self.client:
            return True, "Basic validation passed"

        # LLM validation for clarity
        try:
            prompt = f"""Evaluate if this dispute description is clear enough to proceed:

{description}

Check for:
1. Clear identification of the issue
2. Reference to what is being contested
3. Basis for the dispute
4. What outcome is sought

Return JSON:
{{
    "is_clear": true/false,
    "missing_elements": ["list of missing elements"],
    "recommendation": "PROCEED/NEEDS_CLARIFICATION/TOO_VAGUE",
    "guidance": "brief guidance for improvement if needed"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            if result.get("recommendation") == "TOO_VAGUE":
                return False, f"Dispute too vague: {result.get('guidance', 'Please provide more detail.')}"

            if result.get("recommendation") == "NEEDS_CLARIFICATION":
                missing = result.get("missing_elements", [])
                return False, f"Please clarify: {', '.join(missing)}"

            return True, "Dispute description is clear and actionable"

        except Exception as e:
            print(f"Dispute clarity validation failed: {e}")
            return True, "Basic validation passed (LLM validation unavailable)"

    def format_dispute_entry(
        self,
        dispute_type: str,
        content: str,
        dispute_id: Optional[str] = None
    ) -> str:
        """
        Format a dispute entry with proper tags.

        Args:
            dispute_type: Type of dispute entry
            content: Natural language content
            dispute_id: Dispute ID if referencing existing dispute

        Returns:
            Formatted dispute entry string
        """
        parts = [f"[DISPUTE: {dispute_type.upper()}]"]

        if dispute_id:
            parts.append(f"[REF: {dispute_id}]")

        parts.append(content)

        return " ".join(parts)

    def get_dispute_status(self, dispute_id: str, blockchain) -> Optional[Dict[str, Any]]:
        """
        Get current status of a dispute.

        Args:
            dispute_id: The dispute ID
            blockchain: The NatLangChain instance

        Returns:
            Current dispute status or None if not found
        """
        status = {
            "dispute_id": dispute_id,
            "status": None,
            "declaration": None,
            "evidence_count": 0,
            "escalation_count": 0,
            "is_resolved": False,
            "frozen_entries_count": 0
        }

        found = False

        for block in blockchain.chain:
            for entry in block.entries:
                metadata = entry.metadata or {}

                if metadata.get("dispute_id") != dispute_id:
                    continue

                found = True
                dispute_type = metadata.get("dispute_type")

                if dispute_type == self.TYPE_DECLARATION:
                    status["declaration"] = {
                        "claimant": metadata.get("claimant"),
                        "respondent": metadata.get("respondent"),
                        "contested_refs": metadata.get("contested_refs"),
                        "created_at": metadata.get("created_at")
                    }
                    status["status"] = metadata.get("status", self.STATUS_OPEN)

                elif dispute_type == self.TYPE_EVIDENCE:
                    status["evidence_count"] += 1

                elif dispute_type == self.TYPE_ESCALATION:
                    status["escalation_count"] += 1
                    status["status"] = self.STATUS_ESCALATED

                elif dispute_type == self.TYPE_RESOLUTION:
                    status["status"] = self.STATUS_RESOLVED
                    status["is_resolved"] = True
                    status["resolution"] = {
                        "resolution_type": metadata.get("resolution_type"),
                        "resolution_authority": metadata.get("resolution_authority"),
                        "resolved_at": metadata.get("resolved_at")
                    }

        if not found:
            return None

        # Count frozen entries
        for freeze_data in self.frozen_entries.values():
            if freeze_data.get("dispute_id") == dispute_id:
                status["frozen_entries_count"] += 1

        return status

    # =========================================================================
    # NCIP-005: Semantic Locking & Cooling Periods
    # =========================================================================

    def create_dispute_ncip_005(
        self,
        contract_id: str,
        claimant: str,
        respondent: str,
        trigger: str,
        claimed_divergence: str,
        registry_version: str,
        prose_content: str,
        anchor_language: str = "en",
        verified_pou_hashes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a dispute with NCIP-005 semantic locking.

        This method:
        1. Activates a semantic lock
        2. Starts the cooling period (24h D3 / 72h D4)
        3. Halts execution
        4. Freezes semantic state

        Args:
            contract_id: The prose contract being disputed
            claimant: Party filing the dispute
            respondent: Party being disputed against
            trigger: Dispute trigger (drift_level_d3, drift_level_d4, pou_failure, etc.)
            claimed_divergence: Description of semantic divergence
            registry_version: Current registry version
            prose_content: Contract prose content
            anchor_language: Anchor language
            verified_pou_hashes: Optional verified PoU hashes

        Returns:
            Dispute and lock information
        """
        if not NCIP_005_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-005 semantic locking not available",
                "ncip_005_enabled": False
            }

        # Get or create lock manager
        if not hasattr(self, '_lock_manager'):
            self._lock_manager = SemanticLockManager(validator_id="dispute_manager")

        # Map trigger string to enum
        trigger_map = {
            "drift_level_d3": DisputeTrigger.DRIFT_D3,
            "drift_level_d4": DisputeTrigger.DRIFT_D4,
            "pou_failure": DisputeTrigger.POU_FAILURE,
            "pou_contradiction": DisputeTrigger.POU_CONTRADICTION,
            "conflicting_ratifications": DisputeTrigger.CONFLICTING_RATIFICATIONS,
            "multilingual_misalignment": DisputeTrigger.MULTILINGUAL_MISALIGNMENT,
            "material_breach": DisputeTrigger.MATERIAL_BREACH
        }

        dispute_trigger = trigger_map.get(trigger)
        if not dispute_trigger:
            return {
                "status": "error",
                "message": f"Unknown trigger: {trigger}. Valid triggers: {list(trigger_map.keys())}"
            }

        try:
            # Initiate dispute with semantic lock
            lock, dispute_entry = self._lock_manager.initiate_dispute(
                contract_id=contract_id,
                trigger=dispute_trigger,
                claimed_divergence=claimed_divergence,
                initiator_id=claimant,
                registry_version=registry_version,
                prose_content=prose_content,
                anchor_language=anchor_language,
                verified_pou_hashes=verified_pou_hashes
            )

            # Create traditional dispute data
            dispute_data = self.create_dispute(
                claimant=claimant,
                respondent=respondent,
                contested_refs=[{"contract_id": contract_id}],
                description=claimed_divergence,
                escalation_path=self.ESCALATION_MEDIATOR
            )

            # Add NCIP-005 lock info
            dispute_data["ncip_005"] = {
                "enabled": True,
                "lock_id": lock.lock_id,
                "lock_time": lock.lock_time,
                "dispute_level": lock.dispute_level.value,
                "cooling_ends_at": lock.cooling_ends_at,
                "current_stage": lock.current_stage.value,
                "execution_halted": lock.execution_halted,
                "locked_state": {
                    "registry_version": lock.locked_state.registry_version,
                    "anchor_language": lock.locked_state.anchor_language,
                    "prose_hash": lock.locked_state.prose_content_hash[:16] + "..."
                }
            }

            return dispute_data

        except ValueError as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def check_action_allowed(
        self,
        contract_id: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Check if an action is allowed given any active semantic lock.

        Per NCIP-005 Section 5.2 and 6.3.

        Args:
            contract_id: The contract ID
            action: The action to check (clarification, escalation, enforcement, etc.)

        Returns:
            Dict with allowed status and reason
        """
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return {
                "allowed": True,
                "reason": "No NCIP-005 lock manager active"
            }

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        if not lock:
            return {
                "allowed": True,
                "reason": "No active lock for this contract"
            }

        # Map action string to enum
        action_map = {
            "clarification": LockAction.CLARIFICATION,
            "settlement_proposal": LockAction.SETTLEMENT_PROPOSAL,
            "mediator_assignment": LockAction.MEDIATOR_ASSIGNMENT,
            "evidence_submission": LockAction.EVIDENCE_SUBMISSION,
            "escalation": LockAction.ESCALATION,
            "enforcement": LockAction.ENFORCEMENT,
            "semantic_change": LockAction.SEMANTIC_CHANGE,
            "contract_amendment": LockAction.CONTRACT_AMENDMENT,
            "re_translation": LockAction.RE_TRANSLATION,
            "registry_upgrade": LockAction.REGISTRY_UPGRADE,
            "pou_regeneration": LockAction.POU_REGENERATION
        }

        lock_action = action_map.get(action)
        if not lock_action:
            return {
                "allowed": True,
                "reason": f"Unknown action: {action}"
            }

        return self._lock_manager.get_validator_response(lock.lock_id, lock_action)

    def get_cooling_status(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the cooling period status for a contract.

        Args:
            contract_id: The contract ID

        Returns:
            Cooling period status or None
        """
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return None

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        if not lock:
            return None

        status = self._lock_manager.get_cooling_status(lock.lock_id)
        if not status:
            return None

        return {
            "dispute_level": status.dispute_level.value,
            "started_at": status.started_at,
            "ends_at": status.ends_at,
            "duration_hours": status.duration_hours,
            "is_active": status.is_active,
            "time_remaining_seconds": status.time_remaining_seconds,
            "time_remaining_hours": status.time_remaining_seconds / 3600
        }

    def advance_escalation(
        self,
        contract_id: str,
        actor_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Advance to the next escalation stage per NCIP-005 Section 7.

        Escalation path:
        COOLING -> MUTUAL_SETTLEMENT -> MEDIATOR_REVIEW -> ADJUDICATION -> BINDING_RESOLUTION

        Args:
            contract_id: The contract ID
            actor_id: Who is advancing the escalation
            reason: Optional reason for advancement

        Returns:
            Result of advancement attempt
        """
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return {
                "success": False,
                "message": "NCIP-005 not available"
            }

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        if not lock:
            return {
                "success": False,
                "message": "No active lock for this contract"
            }

        success, message, new_stage = self._lock_manager.advance_stage(
            lock.lock_id, actor_id, reason
        )

        return {
            "success": success,
            "message": message,
            "new_stage": new_stage.value if new_stage else None,
            "lock_id": lock.lock_id
        }

    def resolve_dispute_ncip_005(
        self,
        contract_id: str,
        outcome: str,
        resolution_authority: str,
        resolution_details: str,
        findings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolve a dispute and release the semantic lock per NCIP-005.

        Args:
            contract_id: The contract ID
            outcome: Resolution outcome (dismissed, clarified, amended, terminated, compensated)
            resolution_authority: Who authorized the resolution
            resolution_details: Description of resolution
            findings: Optional structured findings

        Returns:
            Resolution result
        """
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return {
                "success": False,
                "message": "NCIP-005 not available"
            }

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        if not lock:
            return {
                "success": False,
                "message": "No active lock for this contract"
            }

        # Map outcome string to enum
        outcome_map = {
            "dismissed": ResolutionOutcome.DISMISSED,
            "clarified": ResolutionOutcome.CLARIFIED,
            "amended": ResolutionOutcome.AMENDED,
            "terminated": ResolutionOutcome.TERMINATED,
            "compensated": ResolutionOutcome.COMPENSATED
        }

        resolution_outcome = outcome_map.get(outcome)
        if not resolution_outcome:
            return {
                "success": False,
                "message": f"Unknown outcome: {outcome}. Valid: {list(outcome_map.keys())}"
            }

        success, message = self._lock_manager.resolve_dispute(
            lock.lock_id,
            resolution_outcome,
            resolution_authority,
            resolution_details,
            findings
        )

        return {
            "success": success,
            "message": message,
            "outcome": outcome,
            "lock_id": lock.lock_id
        }

    def get_lock_summary(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the semantic lock for a contract."""
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return None

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        if not lock:
            return None

        return self._lock_manager.get_lock_summary(lock.lock_id)

    def is_execution_halted(self, contract_id: str) -> bool:
        """Check if execution is halted for a contract due to dispute."""
        if not NCIP_005_AVAILABLE or not hasattr(self, '_lock_manager'):
            return False

        lock = self._lock_manager.get_lock_by_contract(contract_id)
        return lock is not None and lock.is_active and lock.execution_halted

    # =========================================================================
    # NCIP-010: Mediator Reputation, Bonding & Slashing
    # =========================================================================

    def register_mediator(
        self,
        mediator_id: str,
        stake_amount: float = DEFAULT_BOND,
        supported_domains: Optional[List[str]] = None,
        models_used: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Register a mediator with required bond per NCIP-010.

        Per NCIP-010 Section 3.1:
        - All mediator nodes MUST register a persistent mediator ID
        - Post a reputation bond (stake)
        - Declare supported domains (optional)

        Args:
            mediator_id: Unique identifier for the mediator
            stake_amount: Bond amount in NLC tokens (default 50,000)
            supported_domains: Optional list of supported domains
            models_used: Optional list of AI models used

        Returns:
            Registration result
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available",
                "ncip_010_enabled": False
            }

        try:
            manager = get_reputation_manager()
            profile = manager.register_mediator(
                mediator_id=mediator_id,
                stake_amount=stake_amount,
                supported_domains=supported_domains,
                models_used=models_used
            )

            return {
                "status": "registered",
                "mediator_id": mediator_id,
                "bond_amount": profile.bond.amount,
                "composite_trust_score": profile.composite_trust_score,
                "ncip_010_enabled": True
            }

        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "ncip_010_enabled": True
            }

    def get_mediator_reputation(self, mediator_id: str) -> Dict[str, Any]:
        """
        Get a mediator's reputation summary per NCIP-010.

        Args:
            mediator_id: The mediator to query

        Returns:
            Reputation summary including CTS and all dimension scores
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available"
            }

        manager = get_reputation_manager()
        return manager.get_mediator_summary(mediator_id)

    def record_mediation_outcome(
        self,
        mediator_id: str,
        accepted: bool,
        semantic_drift_score: Optional[float] = None,
        latency_seconds: Optional[float] = None,
        coercion_detected: bool = False
    ) -> Dict[str, Any]:
        """
        Record a mediation proposal outcome per NCIP-010.

        Updates the mediator's reputation scores:
        - Acceptance Rate (AR)
        - Semantic Accuracy (SA)
        - Latency Discipline (LD)
        - Coercion Signal (CS)

        Args:
            mediator_id: The mediator who made the proposal
            accepted: Whether the proposal was accepted by both parties
            semantic_drift_score: Validator-measured drift (0=perfect, 1=bad)
            latency_seconds: Response time in seconds
            coercion_detected: Whether coercion tactics were detected

        Returns:
            Updated reputation summary
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available"
            }

        manager = get_reputation_manager()
        return manager.record_proposal_outcome(
            mediator_id=mediator_id,
            accepted=accepted,
            semantic_drift_score=semantic_drift_score,
            latency_seconds=latency_seconds,
            coercion_detected=coercion_detected
        )

    def slash_mediator(
        self,
        mediator_id: str,
        offense: str,
        severity: float = 0.5,
        evidence: Optional[Dict[str, Any]] = None,
        affected_party_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Slash a mediator's bond for an offense per NCIP-010 Section 6.

        Slashing is automatic, deterministic, and non-discretionary.

        Offense types:
        - semantic_manipulation: Drift ≥ D4 (10-30% bond)
        - repeated_invalid_proposals: 3× rejected (5-15%)
        - coercive_framing: Validator flag + evidence (15%)
        - appeal_reversal: Successful NCIP-008 appeal (5-20%)
        - collusion_signals: Statistical correlation (progressive)

        Args:
            mediator_id: The mediator to slash
            offense: Type of offense
            severity: Severity factor 0-1 (affects penalty percentage)
            evidence: Evidence of the offense
            affected_party_id: If there's a victim to compensate

        Returns:
            Slashing result
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available"
            }

        # Map offense string to enum
        offense_map = {
            "semantic_manipulation": SlashingOffense.SEMANTIC_MANIPULATION,
            "repeated_invalid_proposals": SlashingOffense.REPEATED_INVALID_PROPOSALS,
            "coercive_framing": SlashingOffense.COERCIVE_FRAMING,
            "appeal_reversal": SlashingOffense.APPEAL_REVERSAL,
            "collusion_signals": SlashingOffense.COLLUSION_SIGNALS
        }

        slash_offense = offense_map.get(offense.lower())
        if not slash_offense:
            return {
                "status": "error",
                "message": f"Unknown offense: {offense}. Valid: {list(offense_map.keys())}"
            }

        manager = get_reputation_manager()
        event = manager.slash(
            mediator_id=mediator_id,
            offense=slash_offense,
            severity=severity,
            evidence=evidence,
            affected_party_id=affected_party_id
        )

        if event is None:
            return {
                "status": "error",
                "message": f"Mediator {mediator_id} not found"
            }

        return {
            "status": "slashed",
            "event_id": event.event_id,
            "mediator_id": mediator_id,
            "offense": offense,
            "amount_slashed": event.amount_slashed,
            "percentage": event.percentage,
            "treasury_portion": event.treasury_portion,
            "affected_party_portion": event.affected_party_portion
        }

    def rank_mediator_proposals(
        self,
        mediator_ids: List[str],
        include_cts: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank mediator proposals by Composite Trust Score per NCIP-010 Section 8.

        Per NCIP-010:
        - Multiple mediators may propose simultaneously
        - Parties see proposals ranked by CTS
        - Includes diversity weighting and diminishing returns on volume

        Args:
            mediator_ids: List of mediators with proposals
            include_cts: Whether to include CTS in results

        Returns:
            Ranked list of mediators with scores
        """
        if not NCIP_010_AVAILABLE:
            return []

        manager = get_reputation_manager()
        return manager.get_proposal_ranking(mediator_ids, include_cts)

    def sample_mediators_by_trust(
        self,
        mediator_ids: List[str],
        sample_size: int = 3
    ) -> List[str]:
        """
        Sample mediators proportional to trust for validator attention.

        Per NCIP-010 Section 8.1: Validators sample proposals proportional to trust.

        Args:
            mediator_ids: List of mediator IDs to sample from
            sample_size: Number of mediators to sample

        Returns:
            List of sampled mediator IDs
        """
        if not NCIP_010_AVAILABLE:
            return mediator_ids[:sample_size]

        manager = get_reputation_manager()
        return manager.sample_proposals_by_trust(mediator_ids, sample_size)

    def get_treasury_balance(self) -> Dict[str, Any]:
        """
        Get the treasury balance from mediator slashing.

        Per NCIP-010 Section 9: Slashed funds contribute to
        defensive dispute subsidies, escalation bounty pools,
        and harassment-mitigation reserves.

        Returns:
            Treasury balance information
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available"
            }

        manager = get_reputation_manager()
        return {
            "status": "ok",
            "balance": manager.get_treasury_balance(),
            "token": "NLC"
        }

    def allocate_defensive_subsidy(
        self,
        amount: float,
        purpose: str
    ) -> Dict[str, Any]:
        """
        Allocate treasury funds for defensive purposes per NCIP-010 Section 9.

        Purposes:
        - defensive_dispute: Subsidize defensive dispute costs
        - escalation_bounty: Fund escalation bounty pools
        - harassment_mitigation: Harassment-mitigation reserves

        Args:
            amount: Amount to allocate
            purpose: Purpose of allocation

        Returns:
            Allocation result
        """
        if not NCIP_010_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-010 mediator reputation not available"
            }

        manager = get_reputation_manager()
        return manager.allocate_defensive_subsidy(amount, purpose)

    def is_ncip_010_enabled(self) -> bool:
        """Check if NCIP-010 mediator reputation is available."""
        return NCIP_010_AVAILABLE

    def get_ncip_010_status(self) -> Dict[str, Any]:
        """Get NCIP-010 implementation status and configuration."""
        if not NCIP_010_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-010 module not available"
            }

        manager = get_reputation_manager()
        return {
            "enabled": True,
            "config": get_ncip_010_config(),
            "registered_mediators": len(manager.mediators),
            "treasury_balance": manager.get_treasury_balance()
        }
