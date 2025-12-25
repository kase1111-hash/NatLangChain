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

# Rate limiting defaults
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
DEFAULT_MAX_ENTRIES_PER_AUTHOR = 10  # Max entries per author per window
DEFAULT_MAX_GLOBAL_ENTRIES = 100  # Max total entries per window

# Timestamp validation defaults
DEFAULT_MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 minutes max drift from current time
DEFAULT_MAX_FUTURE_DRIFT_SECONDS = 60  # 1 minute max future drift (clock skew tolerance)

# Metadata sanitization constants
# These fields are reserved for system use and should not be set by users
FORBIDDEN_METADATA_FIELDS = {
    # Validation-related fields (could spoof validation status)
    "validation_status",
    "validated",
    "verified",
    "verified_by",
    "validator",
    "validation_result",
    "trust_score",
    "trust_level",
    # System-reserved fields
    "__override__",
    "__bypass__",
    "__admin__",
    "__system__",
    "skip_validation",
    "bypass_validation",
    "force_accept",
    # Internal tracking fields
    "block_index",
    "block_hash",
    "entry_hash",
    "chain_id",
}

# Metadata sanitization modes
SANITIZE_MODE_STRIP = "strip"  # Remove forbidden fields silently
SANITIZE_MODE_REJECT = "reject"  # Reject entries with forbidden fields
SANITIZE_MODE_WARN = "warn"  # Strip fields but include warning in response

DEFAULT_SANITIZE_MODE = SANITIZE_MODE_STRIP


class RateLimiter:
    """
    Rate limiter to prevent Sybil/flooding attacks.
    Tracks entry submissions per author and globally.
    """

    def __init__(
        self,
        window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        max_per_author: int = DEFAULT_MAX_ENTRIES_PER_AUTHOR,
        max_global: int = DEFAULT_MAX_GLOBAL_ENTRIES
    ):
        """
        Initialize rate limiter.

        Args:
            window_seconds: Time window for rate limiting (default 60s)
            max_per_author: Max entries per author within window (default 10)
            max_global: Max total entries within window (default 100)
        """
        self.window_seconds = window_seconds
        self.max_per_author = max_per_author
        self.max_global = max_global

        # Track submissions: {author: [timestamps]}
        self._author_submissions: Dict[str, List[float]] = {}
        # Track global submissions: [timestamps]
        self._global_submissions: List[float] = []

    def check_rate_limit(self, author: str) -> Dict[str, Any]:
        """
        Check if an author can submit a new entry.

        Args:
            author: The author attempting to submit

        Returns:
            Dict with allowed flag and details
        """
        current_time = time.time()
        self._cleanup_old_entries(current_time)

        # Check global limit
        if len(self._global_submissions) >= self.max_global:
            return {
                "allowed": False,
                "reason": "global_limit",
                "message": f"Global rate limit exceeded ({self.max_global} entries per {self.window_seconds}s)",
                "current_count": len(self._global_submissions),
                "limit": self.max_global,
                "retry_after": self._get_retry_after(self._global_submissions, current_time)
            }

        # Check per-author limit
        author_subs = self._author_submissions.get(author, [])
        if len(author_subs) >= self.max_per_author:
            return {
                "allowed": False,
                "reason": "author_limit",
                "message": f"Author rate limit exceeded ({self.max_per_author} entries per {self.window_seconds}s)",
                "author": author,
                "current_count": len(author_subs),
                "limit": self.max_per_author,
                "retry_after": self._get_retry_after(author_subs, current_time)
            }

        return {"allowed": True}

    def record_submission(self, author: str):
        """Record a successful submission."""
        current_time = time.time()

        # Record for author
        if author not in self._author_submissions:
            self._author_submissions[author] = []
        self._author_submissions[author].append(current_time)

        # Record globally
        self._global_submissions.append(current_time)

    def _cleanup_old_entries(self, current_time: float):
        """Remove entries outside the rate limit window."""
        cutoff = current_time - self.window_seconds

        # Clean author submissions
        for author in list(self._author_submissions.keys()):
            self._author_submissions[author] = [
                ts for ts in self._author_submissions[author]
                if ts > cutoff
            ]
            # Remove empty author entries
            if not self._author_submissions[author]:
                del self._author_submissions[author]

        # Clean global submissions
        self._global_submissions = [
            ts for ts in self._global_submissions
            if ts > cutoff
        ]

    def _get_retry_after(self, timestamps: List[float], current_time: float) -> float:
        """Calculate seconds until oldest entry expires from window."""
        if not timestamps:
            return 0
        oldest = min(timestamps)
        retry_after = (oldest + self.window_seconds) - current_time
        return max(0, retry_after)

    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        self._cleanup_old_entries(time.time())
        return {
            "global_count": len(self._global_submissions),
            "global_limit": self.max_global,
            "author_counts": {
                author: len(subs)
                for author, subs in self._author_submissions.items()
            },
            "author_limit": self.max_per_author,
            "window_seconds": self.window_seconds
        }


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
        dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS,
        enable_rate_limiting: bool = True,
        rate_limit_window: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        max_entries_per_author: int = DEFAULT_MAX_ENTRIES_PER_AUTHOR,
        max_global_entries: int = DEFAULT_MAX_GLOBAL_ENTRIES,
        enable_timestamp_validation: bool = True,
        max_timestamp_drift: int = DEFAULT_MAX_TIMESTAMP_DRIFT_SECONDS,
        max_future_drift: int = DEFAULT_MAX_FUTURE_DRIFT_SECONDS,
        enable_metadata_sanitization: bool = True,
        metadata_sanitize_mode: str = DEFAULT_SANITIZE_MODE,
        forbidden_metadata_fields: Optional[set] = None
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
            enable_rate_limiting: If True, enforce rate limits on entry submissions.
                                 Default is True to prevent Sybil/flooding attacks.
            rate_limit_window: Time window for rate limiting in seconds (default 60).
            max_entries_per_author: Max entries per author within window (default 10).
            max_global_entries: Max total entries within window (default 100).
            enable_timestamp_validation: If True, validate entry timestamps against system time.
                                        Default is True to prevent timestamp manipulation.
            max_timestamp_drift: Max seconds an entry timestamp can be in the past (default 300).
            max_future_drift: Max seconds an entry timestamp can be in the future (default 60).
            enable_metadata_sanitization: If True, sanitize entry metadata to prevent injection.
                                         Default is True to prevent metadata spoofing attacks.
            metadata_sanitize_mode: How to handle forbidden metadata fields.
                                   "strip" - silently remove forbidden fields
                                   "reject" - reject entries with forbidden fields
                                   "warn" - strip fields but include warning
            forbidden_metadata_fields: Optional custom set of forbidden field names.
                                      Defaults to FORBIDDEN_METADATA_FIELDS.
        """
        self.chain: List[Block] = []
        self.pending_entries: List[NaturalLanguageEntry] = []
        self.require_validation = require_validation
        self.validator = validator
        self.allow_needs_clarification = allow_needs_clarification
        self.enable_deduplication = enable_deduplication
        self.dedup_window_seconds = dedup_window_seconds
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_timestamp_validation = enable_timestamp_validation
        self.max_timestamp_drift = max_timestamp_drift
        self.max_future_drift = max_future_drift
        self.enable_metadata_sanitization = enable_metadata_sanitization
        self.metadata_sanitize_mode = metadata_sanitize_mode
        self.forbidden_metadata_fields = forbidden_metadata_fields or FORBIDDEN_METADATA_FIELDS

        # Track acceptable decisions based on settings
        self._acceptable_decisions = {VALIDATION_VALID}
        if allow_needs_clarification:
            self._acceptable_decisions.add(VALIDATION_NEEDS_CLARIFICATION)

        # Entry fingerprint registry for deduplication: {fingerprint: timestamp}
        self._entry_fingerprints: Dict[str, float] = {}

        # Rate limiter for anti-flooding
        self._rate_limiter = RateLimiter(
            window_seconds=rate_limit_window,
            max_per_author=max_entries_per_author,
            max_global=max_global_entries
        ) if enable_rate_limiting else None

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

        If enable_rate_limiting is True (default), rate limits are enforced per
        author and globally to prevent Sybil/flooding attacks.

        If enable_timestamp_validation is True (default), entry timestamps are
        validated against current system time to prevent backdating attacks.

        If enable_metadata_sanitization is True (default), entry metadata is
        sanitized to prevent injection of system-reserved fields like validation
        status or bypass flags.

        Args:
            entry: The natural language entry to add
            skip_validation: If True, bypass validation (requires require_validation=False
                           on chain initialization). This is for testing only.

        Returns:
            Dict with entry information and validation result
        """
        # Check rate limits (anti-flooding protection)
        if self._rate_limiter is not None:
            rate_check = self._rate_limiter.check_rate_limit(entry.author)
            if not rate_check["allowed"]:
                return {
                    "status": "rejected",
                    "message": rate_check["message"],
                    "reason": "rate_limit",
                    "rate_limit_type": rate_check["reason"],
                    "retry_after": rate_check.get("retry_after", 0),
                    "entry": entry.to_dict()
                }

        # Validate entry timestamp (anti-backdating protection)
        if self.enable_timestamp_validation:
            ts_check = self._validate_timestamp(entry)
            if not ts_check["is_valid"]:
                return {
                    "status": "rejected",
                    "message": ts_check["message"],
                    "reason": "invalid_timestamp",
                    "timestamp_issue": ts_check["reason"],
                    "entry": entry.to_dict()
                }

        # Sanitize metadata (anti-injection protection)
        metadata_warning = None
        if self.enable_metadata_sanitization:
            sanitize_result = self._sanitize_metadata(entry)
            if sanitize_result["rejected"]:
                return {
                    "status": "rejected",
                    "message": sanitize_result["message"],
                    "reason": "forbidden_metadata",
                    "forbidden_fields": sanitize_result.get("forbidden_fields", []),
                    "entry": entry.to_dict()
                }
            # Track warning for later inclusion in response
            if sanitize_result.get("warning"):
                metadata_warning = {
                    "stripped_fields": sanitize_result["stripped_fields"],
                    "message": sanitize_result["message"]
                }

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

        # Record submission for rate limiting
        if self._rate_limiter is not None:
            self._rate_limiter.record_submission(entry.author)

        self.pending_entries.append(entry)
        response = {
            "status": "pending",
            "message": "Entry added to pending queue",
            "validated": self.require_validation and not skip_validation,
            "entry": entry.to_dict()
        }
        # Include metadata warning if fields were stripped
        if metadata_warning:
            response["metadata_warning"] = metadata_warning
        return response

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

    def _validate_timestamp(self, entry: NaturalLanguageEntry) -> Dict[str, Any]:
        """
        Validate an entry's timestamp against the current system time.

        Prevents timestamp manipulation attacks where bad actors backdate
        entries to claim they were created earlier than they actually were.

        Args:
            entry: The entry to validate

        Returns:
            Dict with is_valid flag and details
        """
        current_time = datetime.utcnow()

        # Parse the entry timestamp
        try:
            entry_time = datetime.fromisoformat(entry.timestamp)
        except (ValueError, TypeError) as e:
            return {
                "is_valid": False,
                "reason": "invalid_format",
                "message": f"Invalid timestamp format: {entry.timestamp}",
                "error": str(e)
            }

        # Calculate time difference in seconds
        time_diff = (current_time - entry_time).total_seconds()

        # Check if timestamp is too far in the past (backdating attempt)
        if time_diff > self.max_timestamp_drift:
            return {
                "is_valid": False,
                "reason": "too_old",
                "message": f"Timestamp too old: {entry.timestamp} (max drift: {self.max_timestamp_drift}s)",
                "entry_time": entry.timestamp,
                "current_time": current_time.isoformat(),
                "drift_seconds": time_diff,
                "max_allowed": self.max_timestamp_drift
            }

        # Check if timestamp is too far in the future (clock skew or manipulation)
        if time_diff < -self.max_future_drift:
            return {
                "is_valid": False,
                "reason": "too_future",
                "message": f"Timestamp too far in future: {entry.timestamp} (max future drift: {self.max_future_drift}s)",
                "entry_time": entry.timestamp,
                "current_time": current_time.isoformat(),
                "drift_seconds": abs(time_diff),
                "max_allowed": self.max_future_drift
            }

        return {
            "is_valid": True,
            "drift_seconds": time_diff
        }

    def _sanitize_metadata(self, entry: NaturalLanguageEntry) -> Dict[str, Any]:
        """
        Sanitize entry metadata to prevent injection attacks.

        Checks for forbidden fields in metadata that could be used to spoof
        validation status, bypass security checks, or inject malicious data.

        Args:
            entry: The entry whose metadata to sanitize

        Returns:
            Dict with sanitization result:
            - is_clean: True if no forbidden fields found (or stripped)
            - stripped_fields: List of fields that were removed (if any)
            - rejected: True if entry should be rejected (reject mode)
            - message: Human-readable status message
        """
        if not entry.metadata:
            return {"is_clean": True, "stripped_fields": [], "rejected": False}

        # Find forbidden fields in metadata
        found_forbidden = []
        for field in entry.metadata.keys():
            # Check exact match
            if field in self.forbidden_metadata_fields:
                found_forbidden.append(field)
            # Check case-insensitive match for bypass attempts
            elif field.lower() in {f.lower() for f in self.forbidden_metadata_fields}:
                found_forbidden.append(field)
            # Check for suspicious patterns
            elif field.startswith("__") or field.startswith("_system"):
                found_forbidden.append(field)

        if not found_forbidden:
            return {"is_clean": True, "stripped_fields": [], "rejected": False}

        # Handle based on sanitize mode
        if self.metadata_sanitize_mode == SANITIZE_MODE_REJECT:
            return {
                "is_clean": False,
                "stripped_fields": [],
                "rejected": True,
                "forbidden_fields": found_forbidden,
                "message": f"Entry rejected: forbidden metadata fields found: {found_forbidden}"
            }

        # Strip mode or Warn mode - remove the forbidden fields
        for field in found_forbidden:
            del entry.metadata[field]

        if self.metadata_sanitize_mode == SANITIZE_MODE_WARN:
            return {
                "is_clean": True,
                "stripped_fields": found_forbidden,
                "rejected": False,
                "warning": True,
                "message": f"Warning: removed forbidden metadata fields: {found_forbidden}"
            }

        # Strip mode - silently removed
        return {
            "is_clean": True,
            "stripped_fields": found_forbidden,
            "rejected": False
        }

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
        dedup_window_seconds: int = DEFAULT_DEDUP_WINDOW_SECONDS,
        enable_rate_limiting: bool = True,
        rate_limit_window: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        max_entries_per_author: int = DEFAULT_MAX_ENTRIES_PER_AUTHOR,
        max_global_entries: int = DEFAULT_MAX_GLOBAL_ENTRIES,
        enable_timestamp_validation: bool = True,
        max_timestamp_drift: int = DEFAULT_MAX_TIMESTAMP_DRIFT_SECONDS,
        max_future_drift: int = DEFAULT_MAX_FUTURE_DRIFT_SECONDS,
        enable_metadata_sanitization: bool = True,
        metadata_sanitize_mode: str = DEFAULT_SANITIZE_MODE,
        forbidden_metadata_fields: Optional[set] = None
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
            enable_rate_limiting: Whether to enable rate limiting for new entries.
            rate_limit_window: Time window for rate limiting in seconds.
            max_entries_per_author: Max entries per author within window.
            max_global_entries: Max total entries within window.
            enable_timestamp_validation: Whether to validate entry timestamps.
            max_timestamp_drift: Max seconds an entry can be in the past.
            max_future_drift: Max seconds an entry can be in the future.
            enable_metadata_sanitization: Whether to sanitize entry metadata.
            metadata_sanitize_mode: Mode for handling forbidden fields.
            forbidden_metadata_fields: Custom set of forbidden field names.
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
        chain.enable_rate_limiting = enable_rate_limiting
        chain._rate_limiter = RateLimiter(
            window_seconds=rate_limit_window,
            max_per_author=max_entries_per_author,
            max_global=max_global_entries
        ) if enable_rate_limiting else None
        chain.enable_timestamp_validation = enable_timestamp_validation
        chain.max_timestamp_drift = max_timestamp_drift
        chain.max_future_drift = max_future_drift
        chain.enable_metadata_sanitization = enable_metadata_sanitization
        chain.metadata_sanitize_mode = metadata_sanitize_mode
        chain.forbidden_metadata_fields = forbidden_metadata_fields or FORBIDDEN_METADATA_FIELDS
        return chain
