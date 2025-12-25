"""
NatLangChain - Natural Language Blockchain Implementation
Core blockchain data structures and logic
"""

import hashlib
import json
import time
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime


# Validation decision constants
VALIDATION_VALID = "VALID"
VALIDATION_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
VALIDATION_INVALID = "INVALID"
VALIDATION_ERROR = "ERROR"

# Allowed decisions for entry acceptance
ACCEPTABLE_DECISIONS = {VALIDATION_VALID}

# Default deduplication window in seconds (1 hour)
DEFAULT_DEDUP_WINDOW_SECONDS = 3600


def compute_entry_fingerprint(content: str, author: str, intent: str) -> str:
    """
    Compute a unique fingerprint for an entry based on content, author, and intent.
    Used for replay attack prevention.

    Args:
        content: The entry content
        author: The entry author
        intent: The entry intent

    Returns:
        SHA256 hash of the combined data
    """
    fingerprint_data = f"{author}:{intent}:{content}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


class MockValidator:
    """
    A mock validator for testing that performs basic checks without LLM calls.
    Use this for unit tests to avoid API dependencies.
    """

    # Common ambiguous terms that should trigger NEEDS_CLARIFICATION
    AMBIGUOUS_TERMS = [
        "soon", "later", "reasonable", "appropriate", "satisfactory",
        "acceptable", "approximately", "some", "various", "etc",
        "as needed", "when possible", "in due time"
    ]

    # Adversarial patterns that should trigger INVALID
    ADVERSARIAL_PATTERNS = [
        "waives all rights",
        "null and void",
        "sole arbiter",
        "irrevocable",
        "perpetual",
        "supersedes all",
        "hidden",
        "buried in",
        "appendix z",
        "non-refundable",
        "minimum order",
    ]

    def validate_entry(
        self,
        content: str,
        intent: str,
        author: str
    ) -> Dict[str, Any]:
        """
        Perform mock validation with basic heuristic checks.

        Detects:
        - Ambiguous language
        - Intent-content mismatch (basic keyword check)
        - Adversarial patterns

        Returns:
            Validation result mimicking ProofOfUnderstanding format
        """
        content_lower = content.lower()
        intent_lower = intent.lower()

        # Check for adversarial patterns
        adversarial_found = []
        for pattern in self.ADVERSARIAL_PATTERNS:
            if pattern in content_lower:
                adversarial_found.append(pattern)

        if adversarial_found:
            return {
                "status": "success",
                "validation": {
                    "paraphrase": f"[MOCK] Entry contains adversarial patterns",
                    "intent_match": False,
                    "ambiguities": [],
                    "adversarial_indicators": adversarial_found,
                    "decision": VALIDATION_INVALID,
                    "reasoning": f"Detected adversarial patterns: {adversarial_found}"
                }
            }

        # Check for ambiguous terms
        ambiguities_found = []
        for term in self.AMBIGUOUS_TERMS:
            if term in content_lower:
                ambiguities_found.append(term)

        # Check for basic intent mismatch
        # Extract key words from intent and check if they appear in content
        intent_words = set(intent_lower.split())
        content_words = set(content_lower.split())

        # Remove common stop words
        stop_words = {"the", "a", "an", "to", "for", "of", "and", "is", "in", "on", "at"}
        intent_keywords = intent_words - stop_words
        content_keywords = content_words - stop_words

        # Check if at least some intent keywords appear in content
        overlap = intent_keywords & content_keywords
        intent_match = len(overlap) > 0 or len(intent_keywords) == 0

        if ambiguities_found:
            return {
                "status": "success",
                "validation": {
                    "paraphrase": f"[MOCK] Entry about: {intent}",
                    "intent_match": intent_match,
                    "ambiguities": ambiguities_found,
                    "adversarial_indicators": [],
                    "decision": VALIDATION_NEEDS_CLARIFICATION,
                    "reasoning": f"Contains ambiguous terms: {ambiguities_found}"
                }
            }

        if not intent_match:
            return {
                "status": "success",
                "validation": {
                    "paraphrase": f"[MOCK] Entry content does not match stated intent",
                    "intent_match": False,
                    "ambiguities": [],
                    "adversarial_indicators": [],
                    "decision": VALIDATION_INVALID,
                    "reasoning": "Intent does not match content keywords"
                }
            }

        # All checks passed
        return {
            "status": "success",
            "validation": {
                "paraphrase": f"[MOCK] The author {author} states: {content[:100]}...",
                "intent_match": True,
                "ambiguities": [],
                "adversarial_indicators": [],
                "decision": VALIDATION_VALID,
                "reasoning": "Entry passes basic validation checks"
            }
        }


class NaturalLanguageEntry:
    """
    A natural language entry in the blockchain.
    The core innovation: prose as the primary substrate.
    """

    def __init__(
        self,
        content: str,
        author: str,
        intent: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create a natural language entry.

        Args:
            content: The natural language prose describing the transaction/event
            author: Identifier of the entry creator
            intent: Brief summary of the entry's purpose
            metadata: Optional additional structured data
        """
        self.content = content
        self.author = author
        self.intent = intent
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.validation_status = "pending"
        self.validation_paraphrases = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "content": self.content,
            "author": self.author,
            "intent": self.intent,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "validation_status": self.validation_status,
            "validation_paraphrases": self.validation_paraphrases
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NaturalLanguageEntry':
        """Create entry from dictionary."""
        entry = cls(
            content=data["content"],
            author=data["author"],
            intent=data["intent"],
            metadata=data.get("metadata", {})
        )
        entry.timestamp = data.get("timestamp", entry.timestamp)
        entry.validation_status = data.get("validation_status", "pending")
        entry.validation_paraphrases = data.get("validation_paraphrases", [])
        return entry


class Block:
    """
    A block in the NatLangChain.
    Contains natural language entries and maintains chain integrity.
    """

    def __init__(
        self,
        index: int,
        entries: List[NaturalLanguageEntry],
        previous_hash: str,
        nonce: int = 0
    ):
        """
        Create a new block.

        Args:
            index: Block position in chain
            entries: List of natural language entries
            previous_hash: Hash of the previous block
            nonce: Proof of work nonce
        """
        self.index = index
        self.timestamp = time.time()
        self.entries = entries
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        Calculate the cryptographic hash of this block.
        Combines traditional cryptographic security with linguistic content.
        """
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary."""
        entries = [NaturalLanguageEntry.from_dict(e) for e in data["entries"]]
        block = cls(
            index=data["index"],
            entries=entries,
            previous_hash=data["previous_hash"],
            nonce=data.get("nonce", 0)
        )
        block.timestamp = data["timestamp"]
        block.hash = data.get("hash", block.calculate_hash())
        return block


class NatLangChain:
    """
    The NatLangChain blockchain.
    A distributed ledger where natural language prose is the primary substrate.
    """

    def __init__(
        self,
        require_validation: bool = True,
        validator: Optional[Any] = None,
        allow_needs_clarification: bool = False,
        enable_deduplication: bool = True,
        dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS
    ):
        """
        Initialize the blockchain with genesis block.

        Args:
            require_validation: If True, entries must pass PoU validation before acceptance.
                              Default is True for security. Set to False only for testing.
            validator: Optional ProofOfUnderstanding validator instance.
                      If None and require_validation is True, a default validator will be created.
            allow_needs_clarification: If True, entries with NEEDS_CLARIFICATION can be added.
                                      Default is False (only VALID entries accepted).
            enable_deduplication: If True, prevent duplicate entries within the dedup window.
                                 Default is True to prevent replay attacks.
            dedup_window_seconds: Time window for deduplication in seconds.
                                 Default is 3600 (1 hour). Set to 0 for permanent dedup.
        """
        self.chain: List[Block] = []
        self.pending_entries: List[NaturalLanguageEntry] = []
        self.require_validation = require_validation
        self.validator = validator
        self.allow_needs_clarification = allow_needs_clarification
        self.enable_deduplication = enable_deduplication
        self.dedup_window_seconds = dedup_window_seconds

        # Track acceptable decisions based on settings
        self._acceptable_decisions = {VALIDATION_VALID}
        if allow_needs_clarification:
            self._acceptable_decisions.add(VALIDATION_NEEDS_CLARIFICATION)

        # Entry fingerprint registry for deduplication: {fingerprint: timestamp}
        self._entry_fingerprints: Dict[str, float] = {}

        self.create_genesis_block()

    def create_genesis_block(self):
        """Create the first block in the chain."""
        genesis_entry = NaturalLanguageEntry(
            content="This is the genesis block of the NatLangChain, a distributed ledger "
                   "paradigm where natural language prose is the primary substrate for "
                   "immutable entries. This chain enables linguistic consensus, validation, "
                   "and execution, preserving intent and enhancing auditability.",
            author="system",
            intent="Initialize the NatLangChain",
            metadata={"type": "genesis"}
        )
        genesis_entry.validation_status = "validated"

        genesis_block = Block(
            index=0,
            entries=[genesis_entry],
            previous_hash="0"
        )
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]

    def add_entry(
        self,
        entry: NaturalLanguageEntry,
        skip_validation: bool = False
    ) -> Dict[str, Any]:
        """
        Add a new natural language entry to pending entries.

        If require_validation is True (default), the entry must pass PoU validation
        before being added to the pending queue. This prevents bad actors from
        submitting ambiguous, mismatched, or adversarial entries.

        If enable_deduplication is True (default), duplicate entries within the
        dedup window will be rejected. This prevents replay attacks.

        Args:
            entry: The natural language entry to add
            skip_validation: If True, bypass validation (requires require_validation=False
                           on chain initialization). This is for testing only.

        Returns:
            Dict with entry information and validation result
        """
        # Check for duplicate entries (replay attack prevention)
        if self.enable_deduplication:
            duplicate_check = self._check_duplicate(entry)
            if duplicate_check["is_duplicate"]:
                return {
                    "status": "rejected",
                    "message": "Entry rejected: duplicate detected (possible replay attack)",
                    "reason": "duplicate",
                    "original_timestamp": duplicate_check["original_timestamp"],
                    "fingerprint": duplicate_check["fingerprint"],
                    "entry": entry.to_dict()
                }

        # Check if validation should be enforced
        if self.require_validation and not skip_validation:
            validation_result = self._validate_entry(entry)

            if validation_result["status"] == "error":
                return {
                    "status": "rejected",
                    "message": "Validation failed with error",
                    "error": validation_result.get("error", "Unknown validation error"),
                    "entry": entry.to_dict()
                }

            decision = validation_result.get("validation", {}).get("decision", "ERROR")

            if decision not in self._acceptable_decisions:
                return {
                    "status": "rejected",
                    "message": f"Entry rejected: validation decision was {decision}",
                    "validation_decision": decision,
                    "validation_details": validation_result.get("validation", {}),
                    "entry": entry.to_dict()
                }

            # Entry passed validation - update status and store paraphrase
            entry.validation_status = "validated"
            paraphrase = validation_result.get("validation", {}).get("paraphrase", "")
            if paraphrase:
                entry.validation_paraphrases.append(paraphrase)

        # Register entry fingerprint for deduplication
        if self.enable_deduplication:
            fingerprint = compute_entry_fingerprint(entry.content, entry.author, entry.intent)
            self._entry_fingerprints[fingerprint] = time.time()
            self._cleanup_expired_fingerprints()

        self.pending_entries.append(entry)
        return {
            "status": "pending",
            "message": "Entry added to pending queue",
            "validated": self.require_validation and not skip_validation,
            "entry": entry.to_dict()
        }

    def _check_duplicate(self, entry: NaturalLanguageEntry) -> Dict[str, Any]:
        """
        Check if an entry is a duplicate of a previously seen entry.

        Args:
            entry: The entry to check

        Returns:
            Dict with is_duplicate flag and details
        """
        fingerprint = compute_entry_fingerprint(entry.content, entry.author, entry.intent)
        current_time = time.time()

        if fingerprint in self._entry_fingerprints:
            original_time = self._entry_fingerprints[fingerprint]

            # Check if within dedup window (0 means permanent dedup)
            if self.dedup_window_seconds == 0:
                return {
                    "is_duplicate": True,
                    "fingerprint": fingerprint,
                    "original_timestamp": original_time
                }

            time_diff = current_time - original_time
            if time_diff <= self.dedup_window_seconds:
                return {
                    "is_duplicate": True,
                    "fingerprint": fingerprint,
                    "original_timestamp": original_time,
                    "time_since_original": time_diff
                }

        # Also check mined blocks for duplicates
        for block in self.chain:
            for existing_entry in block.entries:
                existing_fp = compute_entry_fingerprint(
                    existing_entry.content,
                    existing_entry.author,
                    existing_entry.intent
                )
                if existing_fp == fingerprint:
                    return {
                        "is_duplicate": True,
                        "fingerprint": fingerprint,
                        "original_timestamp": block.timestamp,
                        "source": "mined_block",
                        "block_index": block.index
                    }

        # Also check pending entries
        for pending_entry in self.pending_entries:
            pending_fp = compute_entry_fingerprint(
                pending_entry.content,
                pending_entry.author,
                pending_entry.intent
            )
            if pending_fp == fingerprint:
                return {
                    "is_duplicate": True,
                    "fingerprint": fingerprint,
                    "source": "pending_queue"
                }

        return {"is_duplicate": False, "fingerprint": fingerprint}

    def _cleanup_expired_fingerprints(self):
        """Remove expired fingerprints from the registry."""
        if self.dedup_window_seconds == 0:
            return  # Permanent dedup, never expire

        current_time = time.time()
        expired = [
            fp for fp, ts in self._entry_fingerprints.items()
            if current_time - ts > self.dedup_window_seconds
        ]
        for fp in expired:
            del self._entry_fingerprints[fp]

    def _validate_entry(self, entry: NaturalLanguageEntry) -> Dict[str, Any]:
        """
        Validate an entry using the configured validator.

        Args:
            entry: The entry to validate

        Returns:
            Validation result dictionary
        """
        if self.validator is None:
            # Try to create a validator if not provided
            try:
                from validator import ProofOfUnderstanding
                self.validator = ProofOfUnderstanding()
            except (ImportError, ValueError) as e:
                return {
                    "status": "error",
                    "error": f"No validator configured and could not create one: {e}"
                }

        return self.validator.validate_entry(
            content=entry.content,
            intent=entry.intent,
            author=entry.author
        )

    def mine_pending_entries(self, difficulty: int = 2) -> Optional[Block]:
        """
        Mine pending entries into a new block.
        Implements a simple proof-of-work for demonstration.

        Args:
            difficulty: Number of leading zeros required in hash

        Returns:
            The newly mined block or None if no pending entries
        """
        if not self.pending_entries:
            return None

        new_block = Block(
            index=len(self.chain),
            entries=self.pending_entries.copy(),
            previous_hash=self.get_latest_block().hash
        )

        # Simple proof of work
        target = "0" * difficulty
        while not new_block.hash.startswith(target):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()

        self.chain.append(new_block)
        self.pending_entries = []

        return new_block

    def validate_chain(self) -> bool:
        """
        Validate the entire blockchain for integrity.

        Returns:
            True if chain is valid, False otherwise
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check hash integrity
            if current_block.hash != current_block.calculate_hash():
                return False

            # Check chain linkage
            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def get_entries_by_author(self, author: str) -> List[Dict[str, Any]]:
        """
        Retrieve all entries by a specific author.

        Args:
            author: The author identifier

        Returns:
            List of entry dictionaries
        """
        entries = []
        for block in self.chain:
            for entry in block.entries:
                if entry.author == author:
                    entries.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "entry": entry.to_dict()
                    })
        return entries

    def get_entries_by_intent(self, intent_keyword: str) -> List[Dict[str, Any]]:
        """
        Search for entries by intent keyword.

        Args:
            intent_keyword: Keyword to search for in intent

        Returns:
            List of matching entry dictionaries
        """
        entries = []
        for block in self.chain:
            for entry in block.entries:
                if intent_keyword.lower() in entry.intent.lower():
                    entries.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "entry": entry.to_dict()
                    })
        return entries

    def get_full_narrative(self) -> str:
        """
        Get the full narrative of the blockchain as readable text.
        This is the key innovation: the entire ledger as human-readable prose.

        Returns:
            The complete narrative history
        """
        narrative = []
        narrative.append("=== NatLangChain Narrative History ===\n")

        for block in self.chain:
            narrative.append(f"\n--- Block {block.index} ---")
            narrative.append(f"Hash: {block.hash}")
            narrative.append(f"Timestamp: {datetime.fromtimestamp(block.timestamp).isoformat()}")
            narrative.append(f"Previous Hash: {block.previous_hash}\n")

            for i, entry in enumerate(block.entries, 1):
                narrative.append(f"Entry {i}:")
                narrative.append(f"  Author: {entry.author}")
                narrative.append(f"  Intent: {entry.intent}")
                narrative.append(f"  Time: {entry.timestamp}")
                narrative.append(f"  Status: {entry.validation_status}")
                narrative.append(f"  Content:\n    {entry.content}")
                if entry.validation_paraphrases:
                    narrative.append(f"  Validation Paraphrases:")
                    for paraphrase in entry.validation_paraphrases:
                        narrative.append(f"    - {paraphrase}")
                narrative.append("")

        return "\n".join(narrative)

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire chain as dictionary."""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_entries": [entry.to_dict() for entry in self.pending_entries]
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        require_validation: bool = False,
        validator: Optional[Any] = None,
        enable_deduplication: bool = True,
        dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS
    ) -> 'NatLangChain':
        """
        Import chain from dictionary.

        Args:
            data: Serialized chain data
            require_validation: Whether to require validation for new entries.
                              Defaults to False for imports (entries already validated).
            validator: Optional validator instance
            enable_deduplication: Whether to enable deduplication for new entries.
            dedup_window_seconds: Time window for deduplication.
        """
        chain = cls.__new__(cls)
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        chain.pending_entries = [
            NaturalLanguageEntry.from_dict(e)
            for e in data.get("pending_entries", [])
        ]
        chain.require_validation = require_validation
        chain.validator = validator
        chain.allow_needs_clarification = False
        chain._acceptable_decisions = {VALIDATION_VALID}
        chain.enable_deduplication = enable_deduplication
        chain.dedup_window_seconds = dedup_window_seconds
        chain._entry_fingerprints = {}
        return chain
