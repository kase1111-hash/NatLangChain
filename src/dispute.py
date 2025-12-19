"""
NatLangChain - Dispute Protocol (MP-03)
Handles dispute declaration, evidence freezing, escalation, and resolution
Per the Refusal Doctrine: disputes are signals, not failures
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
