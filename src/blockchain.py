"""
NatLangChain - Natural Language Blockchain Implementation
Core blockchain data structures and logic
"""

import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Validation decision constants
VALIDATION_VALID = "VALID"
VALIDATION_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
VALIDATION_INVALID = "INVALID"
VALIDATION_ERROR = "ERROR"

# Allowed decisions for entry acceptance
ACCEPTABLE_DECISIONS = {VALIDATION_VALID}

# Default deduplication window in seconds (1 hour)
DEFAULT_DEDUP_WINDOW_SECONDS = 3600

# Rate limiting defaults — tuned for a single-node demo; production would
# need per-endpoint limits backed by Redis (see _deferred/src/rate_limiter.py)
# TODO: make rate limits configurable per-endpoint instead of globally
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window
DEFAULT_MAX_ENTRIES_PER_AUTHOR = 10  # Max entries per author per window
DEFAULT_MAX_GLOBAL_ENTRIES = 100  # Max total entries per window

# Timestamp validation defaults — 5 min drift handles NTP-synced nodes;
# 1 min future drift accommodates minor clock skew without allowing replay
DEFAULT_MAX_TIMESTAMP_DRIFT_SECONDS = 300
DEFAULT_MAX_FUTURE_DRIFT_SECONDS = 60

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

# Import intent classifier (LLM-based with keyword fallback)
try:
    from intent_classifier import IntentClassifier, TRANSFER_INTENT_KEYWORDS

    INTENT_CLASSIFIER_AVAILABLE = True
except ImportError:
    INTENT_CLASSIFIER_AVAILABLE = False
    TRANSFER_INTENT_KEYWORDS = {
        "transfer", "transfers", "transferring", "transferred",
        "sell", "sells", "selling", "sold",
        "give", "gives", "giving", "gave",
        "assign", "assigns", "assigning", "assigned",
        "convey", "conveys", "conveying", "conveyed",
        "grant", "grants", "granting", "granted",
    }

# Entry quality defaults (addresses chain bloat)
DEFAULT_MAX_ENTRY_SIZE = 10000  # ~2500 words, sufficient for detailed contracts
DEFAULT_MIN_ENTRY_SIZE = 20  # Minimum meaningful content
DEFAULT_QUALITY_STRICT_MODE = False  # If True, warnings become rejections

# Derivative tracking constants
# Types of derivation relationships
DERIVATIVE_TYPE_AMENDMENT = "amendment"  # Modifies terms of parent
DERIVATIVE_TYPE_EXTENSION = "extension"  # Adds to parent without modifying
DERIVATIVE_TYPE_RESPONSE = "response"  # Response to parent entry
DERIVATIVE_TYPE_REVISION = "revision"  # Supersedes parent entirely
DERIVATIVE_TYPE_REFERENCE = "reference"  # Simply references parent
DERIVATIVE_TYPE_FULFILLMENT = "fulfillment"  # Fulfills/completes parent intent

VALID_DERIVATIVE_TYPES = {
    DERIVATIVE_TYPE_AMENDMENT,
    DERIVATIVE_TYPE_EXTENSION,
    DERIVATIVE_TYPE_RESPONSE,
    DERIVATIVE_TYPE_REVISION,
    DERIVATIVE_TYPE_REFERENCE,
    DERIVATIVE_TYPE_FULFILLMENT,
}

# Import entry quality analyzer (for chain bloat prevention)
try:
    from src.entry_quality import (
        EntryQualityAnalyzer,
        QualityDecision,
    )

    ENTRY_QUALITY_AVAILABLE = True
except ImportError:
    ENTRY_QUALITY_AVAILABLE = False


class AssetRegistry:
    """
    Registry for tracking asset ownership and preventing double-spending.

    This layer ensures that:
    1. Assets can only be transferred by their current owner
    2. Assets cannot be transferred twice in the same pending queue
    3. Completed transfers update ownership records
    """

    def __init__(self):
        """Initialize the asset registry."""
        # Asset ownership: {asset_id: owner}
        self._ownership: dict[str, str] = {}
        # Pending transfers: {asset_id: {"from": owner, "to": recipient, "fingerprint": fp}}
        self._pending_transfers: dict[str, dict[str, str]] = {}
        # Transfer history for audit: [{asset_id, from, to, timestamp, fingerprint}]
        self._transfer_history: list[dict[str, Any]] = []

    def register_asset(self, asset_id: str, owner: str) -> dict[str, Any]:
        """
        Register a new asset with an owner.

        Args:
            asset_id: Unique identifier for the asset
            owner: The owner of the asset

        Returns:
            Dict with registration result
        """
        if asset_id in self._ownership:
            return {
                "success": False,
                "message": f"Asset '{asset_id}' already registered to {self._ownership[asset_id]}",
            }

        self._ownership[asset_id] = owner
        return {
            "success": True,
            "message": f"Asset '{asset_id}' registered to {owner}",
            "asset_id": asset_id,
            "owner": owner,
        }

    def get_owner(self, asset_id: str) -> str | None:
        """Get the current owner of an asset."""
        return self._ownership.get(asset_id)

    def is_registered(self, asset_id: str) -> bool:
        """Check if an asset is registered."""
        return asset_id in self._ownership

    def reserve_for_transfer(
        self, asset_id: str, from_owner: str, to_recipient: str, fingerprint: str
    ) -> dict[str, Any]:
        """
        Reserve an asset for pending transfer.

        This prevents double-transfer by marking the asset as "in transit".

        Args:
            asset_id: The asset being transferred
            from_owner: The current owner initiating transfer
            to_recipient: The intended recipient
            fingerprint: Entry fingerprint for tracking

        Returns:
            Dict with reservation result
        """
        # Check if asset is already pending transfer
        if asset_id in self._pending_transfers:
            existing = self._pending_transfers[asset_id]
            return {
                "success": False,
                "reason": "already_pending",
                "message": f"Asset '{asset_id}' already has pending transfer to {existing['to']}",
                "existing_transfer": existing,
            }

        # Check ownership - if asset is registered, only owner can transfer
        if asset_id in self._ownership:
            if self._ownership[asset_id] != from_owner:
                return {
                    "success": False,
                    "reason": "not_owner",
                    "message": f"Author '{from_owner}' is not the owner of asset '{asset_id}' (owner: {self._ownership[asset_id]})",
                }
        else:
            # Asset not registered - auto-register to the author claiming ownership
            self._ownership[asset_id] = from_owner

        # Reserve the asset
        self._pending_transfers[asset_id] = {
            "from": from_owner,
            "to": to_recipient,
            "fingerprint": fingerprint,
            "timestamp": time.time(),
        }

        return {
            "success": True,
            "message": f"Asset '{asset_id}' reserved for transfer from {from_owner} to {to_recipient}",
            "asset_id": asset_id,
        }

    def complete_transfer(self, asset_id: str, fingerprint: str) -> dict[str, Any]:
        """
        Complete a pending transfer after block is mined.

        Args:
            asset_id: The asset to transfer
            fingerprint: The entry fingerprint to verify

        Returns:
            Dict with completion result
        """
        if asset_id not in self._pending_transfers:
            return {"success": False, "message": f"No pending transfer for asset '{asset_id}'"}

        pending = self._pending_transfers[asset_id]

        # Verify fingerprint matches
        if pending["fingerprint"] != fingerprint:
            return {"success": False, "message": f"Fingerprint mismatch for asset '{asset_id}'"}

        # Complete the transfer
        old_owner = pending["from"]
        new_owner = pending["to"]
        self._ownership[asset_id] = new_owner

        # Record in history
        self._transfer_history.append(
            {
                "asset_id": asset_id,
                "from": old_owner,
                "to": new_owner,
                "timestamp": time.time(),
                "fingerprint": fingerprint,
            }
        )

        # Remove from pending
        del self._pending_transfers[asset_id]

        return {
            "success": True,
            "message": f"Transfer complete: '{asset_id}' now owned by {new_owner}",
            "asset_id": asset_id,
            "old_owner": old_owner,
            "new_owner": new_owner,
        }

    def cancel_transfer(self, asset_id: str) -> dict[str, Any]:
        """
        Cancel a pending transfer (e.g., entry rejected or expired).

        Args:
            asset_id: The asset to cancel transfer for

        Returns:
            Dict with cancellation result
        """
        if asset_id not in self._pending_transfers:
            return {"success": False, "message": f"No pending transfer for asset '{asset_id}'"}

        del self._pending_transfers[asset_id]
        return {"success": True, "message": f"Transfer cancelled for asset '{asset_id}'"}

    def has_pending_transfer(self, asset_id: str) -> bool:
        """Check if asset has a pending transfer."""
        return asset_id in self._pending_transfers

    def get_pending_transfer(self, asset_id: str) -> dict[str, str] | None:
        """Get pending transfer details for an asset."""
        return self._pending_transfers.get(asset_id)

    def get_assets_by_owner(self, owner: str) -> list[str]:
        """Get all assets owned by a specific owner."""
        return [
            asset_id for asset_id, asset_owner in self._ownership.items() if asset_owner == owner
        ]

    def get_transfer_history(self, asset_id: str | None = None) -> list[dict[str, Any]]:
        """Get transfer history, optionally filtered by asset."""
        if asset_id is None:
            return self._transfer_history.copy()
        return [t for t in self._transfer_history if t["asset_id"] == asset_id]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the registry."""
        return {
            "ownership": self._ownership.copy(),
            "pending_transfers": {k: v.copy() for k, v in self._pending_transfers.items()},
            "transfer_history": [t.copy() for t in self._transfer_history],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetRegistry":
        """Deserialize the registry."""
        registry = cls()
        registry._ownership = data.get("ownership", {})
        registry._pending_transfers = data.get("pending_transfers", {})
        registry._transfer_history = data.get("transfer_history", [])
        return registry


class DerivativeRegistry:
    """
    Registry for tracking entry derivation relationships.

    Enables intent evolution tracking by maintaining a directed graph of
    parent-child relationships between entries. This allows:
    1. Tracking how intents evolve over time (amendments, revisions)
    2. Finding all derivatives of a given entry
    3. Tracing the full lineage/ancestry of an entry
    4. Understanding the complete derivation tree
    """

    def __init__(self):
        """Initialize the derivative registry."""
        # Forward references: parent -> list of children
        # Key: "block_index:entry_index", Value: list of child refs
        self._derivatives: dict[str, list[dict[str, Any]]] = {}

        # Reverse references: child -> list of parents
        # Key: "block_index:entry_index", Value: list of parent refs
        self._parents: dict[str, list[dict[str, Any]]] = {}

        # Entry metadata cache for quick lookups
        self._entry_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _make_ref_key(block_index: int, entry_index: int) -> str:
        """Create a unique key for an entry reference."""
        return f"{block_index}:{entry_index}"

    @staticmethod
    def _parse_ref_key(key: str) -> tuple[int, int]:
        """Parse a reference key into block and entry indices."""
        parts = key.split(":")
        return int(parts[0]), int(parts[1])

    def register_derivative(
        self,
        child_block: int,
        child_entry: int,
        parent_refs: list[dict[str, Any]],
        derivative_type: str,
        child_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Register a derivative relationship between entries.

        Args:
            child_block: Block index of the derivative entry
            child_entry: Entry index of the derivative entry
            parent_refs: List of parent references, each containing:
                        - block_index: Parent block index
                        - entry_index: Parent entry index
                        - relationship: Optional specific relationship type
            derivative_type: Type of derivation (amendment, extension, etc.)
            child_metadata: Optional metadata about the child entry

        Returns:
            Dict with registration result
        """
        if derivative_type not in VALID_DERIVATIVE_TYPES:
            return {
                "success": False,
                "reason": "invalid_derivative_type",
                "message": f"Invalid derivative type: {derivative_type}",
                "valid_types": list(VALID_DERIVATIVE_TYPES),
            }

        child_key = self._make_ref_key(child_block, child_entry)

        # Store parent references for the child
        parent_entries = []
        for parent_ref in parent_refs:
            parent_block = parent_ref.get("block_index")
            parent_entry = parent_ref.get("entry_index")

            if parent_block is None or parent_entry is None:
                continue

            parent_key = self._make_ref_key(parent_block, parent_entry)
            relationship = parent_ref.get("relationship", derivative_type)

            parent_entry_data = {
                "block_index": parent_block,
                "entry_index": parent_entry,
                "relationship": relationship,
            }
            parent_entries.append(parent_entry_data)

            # Add to forward references (parent -> children)
            if parent_key not in self._derivatives:
                self._derivatives[parent_key] = []

            child_entry_data = {
                "block_index": child_block,
                "entry_index": child_entry,
                "derivative_type": derivative_type,
                "relationship": relationship,
                "registered_at": time.time(),
            }
            self._derivatives[parent_key].append(child_entry_data)

        # Store reverse references (child -> parents)
        self._parents[child_key] = parent_entries

        # Cache child metadata
        if child_metadata:
            self._entry_cache[child_key] = child_metadata

        return {
            "success": True,
            "message": f"Registered derivative at {child_key}",
            "child_ref": {"block_index": child_block, "entry_index": child_entry},
            "parent_count": len(parent_entries),
            "derivative_type": derivative_type,
        }

    def get_derivatives(
        self, block_index: int, entry_index: int, recursive: bool = False, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get all direct derivatives of an entry.

        Args:
            block_index: Block index of the parent entry
            entry_index: Entry index of the parent entry
            recursive: If True, get all descendants recursively
            max_depth: Maximum recursion depth (prevents infinite loops)

        Returns:
            List of derivative entry references
        """
        key = self._make_ref_key(block_index, entry_index)

        if not recursive:
            return self._derivatives.get(key, []).copy()

        # Recursive traversal with depth limiting
        visited = set()
        result = []

        def traverse(current_key: str, depth: int):
            if depth > max_depth or current_key in visited:
                return
            visited.add(current_key)

            children = self._derivatives.get(current_key, [])
            for child in children:
                child_with_depth = {**child, "depth": depth}
                result.append(child_with_depth)
                child_key = self._make_ref_key(child["block_index"], child["entry_index"])
                traverse(child_key, depth + 1)

        traverse(key, 1)
        return result

    def get_parents(self, block_index: int, entry_index: int) -> list[dict[str, Any]]:
        """
        Get the direct parent entries of a derivative.

        Args:
            block_index: Block index of the derivative entry
            entry_index: Entry index of the derivative entry

        Returns:
            List of parent entry references
        """
        key = self._make_ref_key(block_index, entry_index)
        return self._parents.get(key, []).copy()

    def get_lineage(
        self, block_index: int, entry_index: int, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get the full ancestry/lineage of an entry.

        Traces back through all parent relationships to find
        the original root entries.

        Args:
            block_index: Block index of the entry
            entry_index: Entry index of the entry
            max_depth: Maximum traversal depth

        Returns:
            List of ancestor entries with depth information
        """
        visited = set()
        result = []

        def traverse(current_key: str, depth: int):
            if depth > max_depth or current_key in visited:
                return
            visited.add(current_key)

            parents = self._parents.get(current_key, [])
            for parent in parents:
                parent_with_depth = {**parent, "depth": depth}
                result.append(parent_with_depth)
                parent_key = self._make_ref_key(parent["block_index"], parent["entry_index"])
                traverse(parent_key, depth + 1)

        key = self._make_ref_key(block_index, entry_index)
        traverse(key, 1)
        return result

    def get_roots(
        self, block_index: int, entry_index: int, max_depth: int = 10
    ) -> list[dict[str, Any]]:
        """
        Get the root entries (entries with no parents) in the lineage.

        Args:
            block_index: Block index of the entry
            entry_index: Entry index of the entry
            max_depth: Maximum traversal depth

        Returns:
            List of root entry references
        """
        lineage = self.get_lineage(block_index, entry_index, max_depth)

        if not lineage:
            # This entry itself is a root
            return [{"block_index": block_index, "entry_index": entry_index}]

        roots = []
        for ancestor in lineage:
            ancestor_key = self._make_ref_key(ancestor["block_index"], ancestor["entry_index"])
            if not self._parents.get(ancestor_key):
                roots.append(
                    {"block_index": ancestor["block_index"], "entry_index": ancestor["entry_index"]}
                )

        return roots if roots else [{"block_index": block_index, "entry_index": entry_index}]

    def get_derivation_tree(
        self, block_index: int, entry_index: int, max_depth: int = 10
    ) -> dict[str, Any]:
        """
        Get the complete derivation tree for an entry.

        Returns both ancestors and descendants in a tree structure.

        Args:
            block_index: Block index of the entry
            entry_index: Entry index of the entry
            max_depth: Maximum traversal depth in each direction

        Returns:
            Dict containing the full derivation tree
        """
        return {
            "entry": {"block_index": block_index, "entry_index": entry_index},
            "parents": self.get_parents(block_index, entry_index),
            "lineage": self.get_lineage(block_index, entry_index, max_depth),
            "roots": self.get_roots(block_index, entry_index, max_depth),
            "derivatives": self.get_derivatives(block_index, entry_index, recursive=False),
            "all_descendants": self.get_derivatives(
                block_index, entry_index, recursive=True, max_depth=max_depth
            ),
        }

    def has_derivatives(self, block_index: int, entry_index: int) -> bool:
        """Check if an entry has any derivatives."""
        key = self._make_ref_key(block_index, entry_index)
        return bool(self._derivatives.get(key))

    def is_derivative(self, block_index: int, entry_index: int) -> bool:
        """Check if an entry is a derivative of another entry."""
        key = self._make_ref_key(block_index, entry_index)
        return bool(self._parents.get(key))

    def to_dict(self) -> dict[str, Any]:
        """Serialize the registry."""
        return {
            "derivatives": {k: v.copy() for k, v in self._derivatives.items()},
            "parents": {k: v.copy() for k, v in self._parents.items()},
            "entry_cache": {k: v.copy() for k, v in self._entry_cache.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DerivativeRegistry":
        """Deserialize the registry."""
        registry = cls()
        registry._derivatives = data.get("derivatives", {})
        registry._parents = data.get("parents", {})
        registry._entry_cache = data.get("entry_cache", {})
        return registry


class EntryRateLimiter:
    """
    Rate limiter for blockchain entry submissions.

    Prevents Sybil/flooding attacks by tracking entry submissions
    per author and globally. This is different from the general-purpose
    RateLimiter in rate_limiter.py which handles API request limiting.
    """

    def __init__(
        self,
        window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        max_per_author: int = DEFAULT_MAX_ENTRIES_PER_AUTHOR,
        max_global: int = DEFAULT_MAX_GLOBAL_ENTRIES,
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
        self._author_submissions: dict[str, list[float]] = {}
        # Track global submissions: [timestamps]
        self._global_submissions: list[float] = []

    def check_rate_limit(self, author: str) -> dict[str, Any]:
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
                "retry_after": self._get_retry_after(self._global_submissions, current_time),
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
                "retry_after": self._get_retry_after(author_subs, current_time),
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
                ts for ts in self._author_submissions[author] if ts > cutoff
            ]
            # Remove empty author entries
            if not self._author_submissions[author]:
                del self._author_submissions[author]

        # Clean global submissions
        self._global_submissions = [ts for ts in self._global_submissions if ts > cutoff]

    def _get_retry_after(self, timestamps: list[float], current_time: float) -> float:
        """Calculate seconds until oldest entry expires from window."""
        if not timestamps:
            return 0
        oldest = min(timestamps)
        retry_after = (oldest + self.window_seconds) - current_time
        return max(0, retry_after)

    def get_stats(self) -> dict[str, Any]:
        """Get current rate limiter statistics."""
        self._cleanup_old_entries(time.time())
        return {
            "global_count": len(self._global_submissions),
            "global_limit": self.max_global,
            "author_counts": {
                author: len(subs) for author, subs in self._author_submissions.items()
            },
            "author_limit": self.max_per_author,
            "window_seconds": self.window_seconds,
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
        "soon",
        "later",
        "reasonable",
        "appropriate",
        "satisfactory",
        "acceptable",
        "approximately",
        "some",
        "various",
        "etc",
        "as needed",
        "when possible",
        "in due time",
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

    # High-impact action verbs categorized by semantic meaning
    # If content contains an action from one category, intent should match that category
    ACTION_CATEGORIES = {
        "restriction": {
            "banned",
            "ban",
            "banning",
            "blocked",
            "block",
            "blocking",
            "suspended",
            "suspend",
            "suspending",
            "terminated",
            "terminate",
            "revoked",
            "revoke",
            "revoking",
            "denied",
            "deny",
            "denying",
            "prohibited",
            "prohibit",
            "forbid",
            "forbidden",
            "expelled",
            "removed",
            "remove",
            "removing",
            "deleted",
            "delete",
            "deleting",
        },
        "modification": {
            "updated",
            "update",
            "updating",
            "edited",
            "edit",
            "editing",
            "changed",
            "change",
            "changing",
            "modified",
            "modify",
            "modifying",
            "revised",
            "revise",
            "revising",
            "amended",
            "amend",
            "amending",
        },
        "creation": {
            "created",
            "create",
            "creating",
            "added",
            "add",
            "adding",
            "registered",
            "register",
            "registering",
            "established",
            "establish",
            "initiated",
            "initiate",
            "initiating",
            "opened",
            "open",
            "opening",
        },
        "financial": {
            "paid",
            "pay",
            "paying",
            "transferred",
            "transfer",
            "transferring",
            "deposited",
            "deposit",
            "depositing",
            "withdrew",
            "withdraw",
            "refunded",
            "refund",
            "refunding",
            "charged",
            "charge",
            "charging",
        },
        "agreement": {
            "agreed",
            "agree",
            "agreeing",
            "accepted",
            "accept",
            "accepting",
            "approved",
            "approve",
            "approving",
            "confirmed",
            "confirm",
            "signed",
            "sign",
            "signing",
            "consented",
            "consent",
            "consenting",
        },
    }

    # Intent keywords that map to action categories
    INTENT_CATEGORY_KEYWORDS = {
        "restriction": {
            "ban",
            "block",
            "suspend",
            "terminate",
            "revoke",
            "deny",
            "prohibit",
            "remove",
            "delete",
            "moderation",
        },
        "modification": {"update", "edit", "change", "modify", "revise", "amend", "profile"},
        "creation": {"create", "add", "register", "establish", "initiate", "open", "new"},
        "financial": {
            "pay",
            "transfer",
            "deposit",
            "withdraw",
            "refund",
            "charge",
            "payment",
            "transaction",
        },
        "agreement": {"agree", "accept", "approve", "confirm", "sign", "consent", "contract"},
    }

    def _detect_action_mismatch(self, content: str, intent: str) -> dict[str, Any] | None:
        """
        Detect if high-impact actions in content don't match the stated intent.

        This catches cases like:
        - Intent: "User profile update" + Content: "User is banned" -> MISMATCH
        - Intent: "Payment record" + Content: "User is banned" -> MISMATCH

        Returns:
            None if no mismatch, or dict with mismatch details
        """
        content_lower = content.lower()
        intent_lower = intent.lower()

        # Find action categories present in content
        content_categories = set()
        content_actions = []
        for category, actions in self.ACTION_CATEGORIES.items():
            for action in actions:
                if action in content_lower.split():
                    content_categories.add(category)
                    content_actions.append((action, category))

        if not content_categories:
            return None  # No high-impact actions detected

        # Find action categories implied by intent
        intent_categories = set()
        for category, keywords in self.INTENT_CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in intent_lower:
                    intent_categories.add(category)

        # If content has high-impact actions but intent doesn't match any category
        # that's suspicious but not necessarily wrong
        if not intent_categories:
            # Intent is generic - check if content action is drastic
            drastic_categories = {"restriction", "financial"}
            if content_categories & drastic_categories:
                return {
                    "mismatch": True,
                    "content_actions": content_actions,
                    "content_categories": list(content_categories),
                    "intent_categories": [],
                    "reason": f"Content contains drastic action(s) {content_actions} but intent '{intent}' doesn't indicate this",
                }
            return None

        # Check if content actions align with intent categories
        if not (content_categories & intent_categories):
            return {
                "mismatch": True,
                "content_actions": content_actions,
                "content_categories": list(content_categories),
                "intent_categories": list(intent_categories),
                "reason": f"Content action category {list(content_categories)} doesn't match intent category {list(intent_categories)}",
            }

        return None

    def _build_validation_response(
        self,
        paraphrase: str,
        intent_match: bool,
        decision: str,
        reasoning: str,
        ambiguities: list[str] | None = None,
        adversarial_indicators: list[str] | None = None,
        action_mismatch: dict | None = None,
    ) -> dict[str, Any]:
        """Build a standardized validation response."""
        validation = {
            "paraphrase": paraphrase,
            "intent_match": intent_match,
            "ambiguities": ambiguities or [],
            "adversarial_indicators": adversarial_indicators or [],
            "decision": decision,
            "reasoning": reasoning,
        }
        if action_mismatch:
            validation["action_mismatch"] = action_mismatch
        return {"status": "success", "validation": validation}

    def _find_adversarial_patterns(self, content_lower: str) -> list[str]:
        """Find adversarial patterns in content."""
        return [p for p in self.ADVERSARIAL_PATTERNS if p in content_lower]

    def _find_ambiguous_terms(self, content_lower: str) -> list[str]:
        """Find ambiguous terms in content."""
        return [t for t in self.AMBIGUOUS_TERMS if t in content_lower]

    def _check_intent_match(self, content_lower: str, intent_lower: str) -> bool:
        """Check if intent keywords appear in content."""
        stop_words = {"the", "a", "an", "to", "for", "of", "and", "is", "in", "on", "at"}
        intent_keywords = set(intent_lower.split()) - stop_words
        content_keywords = set(content_lower.split()) - stop_words
        overlap = intent_keywords & content_keywords
        return len(overlap) > 0 or len(intent_keywords) == 0

    def validate_entry(self, content: str, intent: str, author: str) -> dict[str, Any]:
        """
        Perform mock validation with basic heuristic checks.

        Detects adversarial patterns, action mismatches, ambiguous terms,
        and intent-content mismatches.

        Returns:
            Validation result mimicking ProofOfUnderstanding format
        """
        content_lower = content.lower()
        intent_lower = intent.lower()

        # Check for adversarial patterns
        adversarial = self._find_adversarial_patterns(content_lower)
        if adversarial:
            return self._build_validation_response(
                paraphrase="[MOCK] Entry contains adversarial patterns",
                intent_match=False,
                decision=VALIDATION_INVALID,
                reasoning=f"Detected adversarial patterns: {adversarial}",
                adversarial_indicators=adversarial,
            )

        # Check for action category mismatch
        action_mismatch = self._detect_action_mismatch(content, intent)
        if action_mismatch:
            return self._build_validation_response(
                paraphrase="[MOCK] Entry action doesn't match stated intent",
                intent_match=False,
                decision=VALIDATION_INVALID,
                reasoning=action_mismatch["reason"],
                action_mismatch=action_mismatch,
            )

        # Check for ambiguous terms
        ambiguities = self._find_ambiguous_terms(content_lower)
        intent_match = self._check_intent_match(content_lower, intent_lower)

        if ambiguities:
            return self._build_validation_response(
                paraphrase=f"[MOCK] Entry about: {intent}",
                intent_match=intent_match,
                decision=VALIDATION_NEEDS_CLARIFICATION,
                reasoning=f"Contains ambiguous terms: {ambiguities}",
                ambiguities=ambiguities,
            )

        if not intent_match:
            return self._build_validation_response(
                paraphrase="[MOCK] Entry content does not match stated intent",
                intent_match=False,
                decision=VALIDATION_INVALID,
                reasoning="Intent does not match content keywords",
            )

        # All checks passed
        return self._build_validation_response(
            paraphrase=f"[MOCK] The author {author} states: {content[:100]}...",
            intent_match=True,
            decision=VALIDATION_VALID,
            reasoning="Entry passes basic validation checks",
        )


class NaturalLanguageEntry:
    """
    A natural language entry in the blockchain.
    The core innovation: prose as the primary substrate.

    Supports derivative tracking for intent evolution:
    - parent_refs: References to parent entries this derives from
    - derivative_type: Type of derivation relationship
    """

    def __init__(
        self,
        content: str,
        author: str,
        intent: str,
        metadata: dict[str, Any] | None = None,
        parent_refs: list[dict[str, Any]] | None = None,
        derivative_type: str | None = None,
    ):
        """
        Create a natural language entry.

        Args:
            content: The natural language prose describing the transaction/event
            author: Identifier of the entry creator
            intent: Brief summary of the entry's purpose
            metadata: Optional additional structured data
            parent_refs: Optional list of parent entry references for derivatives.
                        Each ref contains: block_index, entry_index, relationship (optional)
            derivative_type: Type of derivation if this is a derivative entry.
                           Valid types: amendment, extension, response, revision,
                           reference, fulfillment
        """
        self.content = content
        self.author = author
        self.intent = intent
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.validation_status = "pending"
        self.validation_paraphrases = []

        # Cryptographic identity fields (Audit 1.3)
        self.signature = None  # Base64-encoded Ed25519 signature
        self.public_key = None  # Base64-encoded signer public key

        # Derivative tracking fields
        self.parent_refs = parent_refs or []
        self.derivative_type = derivative_type

    def is_derivative(self) -> bool:
        """Check if this entry is a derivative of another entry."""
        return bool(self.parent_refs)

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        result = {
            "content": self.content,
            "author": self.author,
            "intent": self.intent,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "validation_status": self.validation_status,
            "validation_paraphrases": self.validation_paraphrases,
        }

        # Include cryptographic identity fields if present (Audit 1.3)
        if self.signature:
            result["signature"] = self.signature
        if self.public_key:
            result["public_key"] = self.public_key

        # Include derivative fields if present
        if self.parent_refs:
            result["parent_refs"] = self.parent_refs
        if self.derivative_type:
            result["derivative_type"] = self.derivative_type

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NaturalLanguageEntry":
        """Create entry from dictionary."""
        entry = cls(
            content=data["content"],
            author=data["author"],
            intent=data["intent"],
            metadata=data.get("metadata", {}),
            parent_refs=data.get("parent_refs", []),
            derivative_type=data.get("derivative_type"),
        )
        entry.timestamp = data.get("timestamp", entry.timestamp)
        entry.validation_status = data.get("validation_status", "pending")
        entry.validation_paraphrases = data.get("validation_paraphrases", [])
        # Restore cryptographic identity fields (Audit 1.3)
        entry.signature = data.get("signature")
        entry.public_key = data.get("public_key")
        return entry


class Block:
    """
    A block in the NatLangChain.
    Contains natural language entries and maintains chain integrity.
    """

    def __init__(
        self, index: int, entries: list[NaturalLanguageEntry], previous_hash: str, nonce: int = 0
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
        # sort_keys=True ensures deterministic serialization so the same
        # block content always produces the same hash regardless of dict ordering
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        # SHA-256 chosen for wide tooling support; not trying to be Bitcoin-hard
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        """Create block from dictionary."""
        entries = [NaturalLanguageEntry.from_dict(e) for e in data["entries"]]
        block = cls(
            index=data["index"],
            entries=entries,
            previous_hash=data["previous_hash"],
            nonce=data.get("nonce", 0),
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
        validator: Any | None = None,
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
        forbidden_metadata_fields: set | None = None,
        enable_asset_tracking: bool = True,
        asset_registry: AssetRegistry | None = None,
        enable_quality_checks: bool = True,
        max_entry_size: int = DEFAULT_MAX_ENTRY_SIZE,
        min_entry_size: int = DEFAULT_MIN_ENTRY_SIZE,
        quality_strict_mode: bool = DEFAULT_QUALITY_STRICT_MODE,
        enable_derivative_tracking: bool = True,
        derivative_registry: DerivativeRegistry | None = None,
        intent_classifier: Any | None = None,
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
            enable_asset_tracking: If True, track asset ownership and prevent double-transfers.
                                  Default is True to prevent double-spending attacks.
            asset_registry: Optional pre-configured AssetRegistry instance.
                           If None and enable_asset_tracking is True, a new registry is created.
            enable_quality_checks: If True, analyze entry quality before acceptance.
                                  Default is True to prevent chain bloat.
            max_entry_size: Maximum entry size in characters (default 10000).
            min_entry_size: Minimum entry size in characters (default 20).
            quality_strict_mode: If True, quality warnings become rejections.
            enable_derivative_tracking: If True, track entry derivation relationships.
                                       Default is True to enable intent evolution tracking.
            derivative_registry: Optional pre-configured DerivativeRegistry instance.
                                If None and enable_derivative_tracking is True, a new registry is created.
            intent_classifier: Optional IntentClassifier for LLM-based transfer detection.
                              If None, keyword-based fallback is used.
        """
        self.chain: list[Block] = []
        self.pending_entries: list[NaturalLanguageEntry] = []
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

        # Entry fingerprint registry for deduplication
        self._entry_fingerprints: dict[str, float] = {}

        # Initialize optional components
        self._rate_limiter = self._init_rate_limiter(
            enable_rate_limiting, rate_limit_window, max_entries_per_author, max_global_entries
        )
        self.enable_asset_tracking = enable_asset_tracking
        self._asset_registry = self._init_asset_registry(enable_asset_tracking, asset_registry)
        self.enable_quality_checks = enable_quality_checks
        self.max_entry_size = max_entry_size
        self.min_entry_size = min_entry_size
        self.quality_strict_mode = quality_strict_mode
        self._quality_analyzer = self._init_quality_analyzer(
            enable_quality_checks, max_entry_size, min_entry_size, quality_strict_mode
        )

        # Initialize derivative tracking
        self.enable_derivative_tracking = enable_derivative_tracking
        self._derivative_registry = self._init_derivative_registry(
            enable_derivative_tracking, derivative_registry
        )

        # Initialize intent classifier for transfer detection
        self._intent_classifier = intent_classifier

        # Lock to prevent concurrent mining race conditions
        self._mining_lock = threading.Lock()

        self.create_genesis_block()

    def _init_rate_limiter(
        self, enabled: bool, window_seconds: int, max_per_author: int, max_global: int
    ) -> EntryRateLimiter | None:
        """Initialize rate limiter for anti-flooding protection."""
        if not enabled:
            return None
        return EntryRateLimiter(
            window_seconds=window_seconds, max_per_author=max_per_author, max_global=max_global
        )

    def _init_asset_registry(
        self, enabled: bool, registry: AssetRegistry | None
    ) -> AssetRegistry | None:
        """Initialize asset registry for double-transfer prevention."""
        if registry:
            return registry
        return AssetRegistry() if enabled else None

    def _init_quality_analyzer(
        self, enabled: bool, max_size: int, min_size: int, strict_mode: bool
    ) -> Any | None:
        """Initialize quality analyzer for chain bloat prevention."""
        if not enabled or not ENTRY_QUALITY_AVAILABLE:
            return None
        return EntryQualityAnalyzer(max_size=max_size, min_size=min_size, strict_mode=strict_mode)

    def _init_derivative_registry(
        self, enabled: bool, registry: DerivativeRegistry | None
    ) -> DerivativeRegistry | None:
        """Initialize derivative registry for intent evolution tracking."""
        if registry:
            return registry
        return DerivativeRegistry() if enabled else None

    def create_genesis_block(self):
        """Create the first block in the chain."""
        genesis_entry = NaturalLanguageEntry(
            content="This is the genesis block of the NatLangChain, a distributed ledger "
            "paradigm where natural language prose is the primary substrate for "
            "immutable entries. This chain enables linguistic consensus, validation, "
            "and execution, preserving intent and enhancing auditability.",
            author="system",
            intent="Initialize the NatLangChain",
            metadata={"type": "genesis"},
        )
        genesis_entry.validation_status = "validated"

        genesis_block = Block(index=0, entries=[genesis_entry], previous_hash="0")
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]

    def add_entry(
        self, entry: NaturalLanguageEntry, skip_validation: bool = False
    ) -> dict[str, Any]:
        """
        Add a new natural language entry to pending entries.

        Runs a validation pipeline with the following checks (all configurable):
        - Rate limiting: Prevents Sybil/flooding attacks
        - Timestamp validation: Prevents backdating attacks
        - Metadata sanitization: Prevents injection attacks
        - Quality analysis: Prevents chain bloat
        - Deduplication: Prevents replay attacks
        - Asset tracking: Prevents double-transfer attacks
        - Entry validation: Ensures semantic validity via PoU

        Args:
            entry: The natural language entry to add
            skip_validation: If True, bypass PoU validation (testing only)

        Returns:
            Dict with entry information and validation result
        """
        # Run validation pipeline - early return on any rejection
        if rejection := self._get_rate_limit_rejection(entry):
            return rejection

        if rejection := self._get_timestamp_rejection(entry):
            return rejection

        metadata_rejection, metadata_warning = self._get_metadata_rejection(entry)
        if metadata_rejection:
            return metadata_rejection

        quality_rejection, quality_info = self._get_quality_rejection(entry)
        if quality_rejection:
            return quality_rejection

        if rejection := self._get_duplicate_rejection(entry):
            return rejection

        asset_rejection, asset_transfer_info = self._get_asset_transfer_rejection(entry)
        if asset_rejection:
            return asset_rejection

        if rejection := self._get_validation_rejection(entry, skip_validation):
            return rejection

        # All checks passed - finalize and return success
        return self._finalize_entry_addition(
            entry, skip_validation, metadata_warning, asset_transfer_info, quality_info
        )

    def _check_duplicate(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
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
                    "original_timestamp": original_time,
                }

            time_diff = current_time - original_time
            if time_diff <= self.dedup_window_seconds:
                return {
                    "is_duplicate": True,
                    "fingerprint": fingerprint,
                    "original_timestamp": original_time,
                    "time_since_original": time_diff,
                }

        # Also check mined blocks for duplicates
        for block in self.chain:
            for existing_entry in block.entries:
                existing_fp = compute_entry_fingerprint(
                    existing_entry.content, existing_entry.author, existing_entry.intent
                )
                if existing_fp == fingerprint:
                    return {
                        "is_duplicate": True,
                        "fingerprint": fingerprint,
                        "original_timestamp": block.timestamp,
                        "source": "mined_block",
                        "block_index": block.index,
                    }

        # Also check pending entries
        for pending_entry in self.pending_entries:
            pending_fp = compute_entry_fingerprint(
                pending_entry.content, pending_entry.author, pending_entry.intent
            )
            if pending_fp == fingerprint:
                return {"is_duplicate": True, "fingerprint": fingerprint, "source": "pending_queue"}

        return {"is_duplicate": False, "fingerprint": fingerprint}

    def _cleanup_expired_fingerprints(self):
        """Remove expired fingerprints from the registry."""
        if self.dedup_window_seconds == 0:
            return  # Permanent dedup, never expire

        current_time = time.time()
        expired = [
            fp
            for fp, ts in self._entry_fingerprints.items()
            if current_time - ts > self.dedup_window_seconds
        ]
        for fp in expired:
            del self._entry_fingerprints[fp]

    def _validate_timestamp(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
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
                "error": str(e),
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
                "max_allowed": self.max_timestamp_drift,
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
                "max_allowed": self.max_future_drift,
            }

        return {"is_valid": True, "drift_seconds": time_diff}

    def _sanitize_metadata(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
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
        for field in entry.metadata:
            # Check exact match
            if (
                field in self.forbidden_metadata_fields
                or field.lower() in {f.lower() for f in self.forbidden_metadata_fields}
                or field.startswith("__")
                or field.startswith("_system")
            ):
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
                "message": f"Entry rejected: forbidden metadata fields found: {found_forbidden}",
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
                "message": f"Warning: removed forbidden metadata fields: {found_forbidden}",
            }

        # Strip mode - silently removed
        return {"is_clean": True, "stripped_fields": found_forbidden, "rejected": False}

    def _detect_asset_transfer(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
        """
        Detect if an entry represents an asset transfer.

        Uses LLM classification when an IntentClassifier is available,
        otherwise falls back to keyword matching.

        Args:
            entry: The entry to analyze

        Returns:
            Dict with is_transfer flag and extracted details
        """
        # Use LLM-based classifier if available
        if self._intent_classifier is not None:
            try:
                classification = self._intent_classifier.classify_transfer_intent(
                    content=entry.content,
                    intent=entry.intent,
                    author=entry.author,
                    metadata=entry.metadata,
                )
                return {
                    "is_transfer": classification.get("is_transfer", False),
                    "asset_id": classification.get("asset_id"),
                    "from_owner": classification.get("from_owner", entry.author),
                    "to_recipient": classification.get("to_recipient"),
                }
            except (ValueError, KeyError):
                pass  # Fall through to keyword detection

        # Keyword fallback
        result = {
            "is_transfer": False,
            "asset_id": None,
            "from_owner": entry.author,
            "to_recipient": None,
        }

        asset_id = entry.metadata.get("asset_id") if entry.metadata else None
        recipient = None
        if entry.metadata:
            recipient = entry.metadata.get("recipient") or entry.metadata.get("to")

        intent_words = set(entry.intent.lower().split())
        content_words = set(entry.content.lower().split())
        has_transfer_intent = bool(intent_words & TRANSFER_INTENT_KEYWORDS)
        has_transfer_content = bool(content_words & TRANSFER_INTENT_KEYWORDS)

        if asset_id and (has_transfer_intent or has_transfer_content):
            result["is_transfer"] = True
            result["asset_id"] = asset_id
            result["to_recipient"] = recipient
        elif asset_id and recipient:
            result["is_transfer"] = True
            result["asset_id"] = asset_id
            result["to_recipient"] = recipient

        return result

    def _check_asset_transfer(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
        """
        Check if an asset transfer is allowed (no double-spending).

        Args:
            entry: The entry to check

        Returns:
            Dict with allowed flag and details
        """
        if not self.enable_asset_tracking or self._asset_registry is None:
            return {"allowed": True, "is_transfer": False}

        # Detect if this is a transfer
        transfer_info = self._detect_asset_transfer(entry)

        if not transfer_info["is_transfer"]:
            return {"allowed": True, "is_transfer": False}

        asset_id = transfer_info["asset_id"]
        from_owner = transfer_info["from_owner"]
        to_recipient = transfer_info["to_recipient"] or "unknown"

        # Compute fingerprint for this entry
        fingerprint = compute_entry_fingerprint(entry.content, entry.author, entry.intent)

        # Try to reserve the asset for transfer
        reserve_result = self._asset_registry.reserve_for_transfer(
            asset_id=asset_id,
            from_owner=from_owner,
            to_recipient=to_recipient,
            fingerprint=fingerprint,
        )

        if not reserve_result["success"]:
            return {
                "allowed": False,
                "is_transfer": True,
                "asset_id": asset_id,
                "reason": reserve_result.get("reason", "transfer_failed"),
                "message": reserve_result["message"],
                "existing_transfer": reserve_result.get("existing_transfer"),
            }

        return {
            "allowed": True,
            "is_transfer": True,
            "asset_id": asset_id,
            "from_owner": from_owner,
            "to_recipient": to_recipient,
            "fingerprint": fingerprint,
        }

    def _validate_entry(self, entry: NaturalLanguageEntry) -> dict[str, Any]:
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
                    "error": f"No validator configured and could not create one: {e}",
                }

        return self.validator.validate_entry(
            content=entry.content, intent=entry.intent, author=entry.author
        )

    # =========================================================================
    # Entry Validation Helpers (extracted from add_entry for clarity)
    # =========================================================================

    def _get_rate_limit_rejection(self, entry: NaturalLanguageEntry) -> dict[str, Any] | None:
        """Check rate limits and return rejection response if exceeded."""
        if self._rate_limiter is None:
            return None
        rate_check = self._rate_limiter.check_rate_limit(entry.author)
        if not rate_check["allowed"]:
            logger.info("Entry rejected: rate limit exceeded for author=%s reason=%s",
                       entry.author, rate_check["reason"])
            return {
                "status": "rejected",
                "message": rate_check["message"],
                "reason": "rate_limit",
                "rate_limit_type": rate_check["reason"],
                "retry_after": rate_check.get("retry_after", 0),
                "entry": entry.to_dict(),
            }
        return None

    def _get_timestamp_rejection(self, entry: NaturalLanguageEntry) -> dict[str, Any] | None:
        """Check timestamp validity and return rejection response if invalid."""
        if not self.enable_timestamp_validation:
            return None
        ts_check = self._validate_timestamp(entry)
        if not ts_check["is_valid"]:
            logger.info("Entry rejected: invalid timestamp author=%s reason=%s",
                       entry.author, ts_check["reason"])
            return {
                "status": "rejected",
                "message": ts_check["message"],
                "reason": "invalid_timestamp",
                "timestamp_issue": ts_check["reason"],
                "entry": entry.to_dict(),
            }
        return None

    def _get_metadata_rejection(
        self, entry: NaturalLanguageEntry
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Check metadata and return (rejection, warning) tuple."""
        if not self.enable_metadata_sanitization:
            return None, None
        sanitize_result = self._sanitize_metadata(entry)
        if sanitize_result["rejected"]:
            logger.info("Entry rejected: forbidden metadata author=%s fields=%s",
                       entry.author, sanitize_result.get("forbidden_fields", []))
            rejection = {
                "status": "rejected",
                "message": sanitize_result["message"],
                "reason": "forbidden_metadata",
                "forbidden_fields": sanitize_result.get("forbidden_fields", []),
                "entry": entry.to_dict(),
            }
            return rejection, None
        warning = None
        if sanitize_result.get("warning"):
            warning = {
                "stripped_fields": sanitize_result["stripped_fields"],
                "message": sanitize_result["message"],
            }
        return None, warning

    def _get_quality_rejection(
        self, entry: NaturalLanguageEntry
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Check quality and return (rejection, quality_info) tuple."""
        if self._quality_analyzer is None:
            return None, None

        quality_result = self._quality_analyzer.analyze(entry.content, entry.intent)
        quality_issues = [
            {
                "issue": i.issue.value,
                "severity": i.severity,
                "message": i.message,
                "suggestion": i.suggestion,
            }
            for i in quality_result.issues
        ]

        if quality_result.decision == QualityDecision.REJECT:
            return {
                "status": "rejected",
                "message": quality_result.summary,
                "reason": "quality_check_failed",
                "quality_score": quality_result.score,
                "quality_issues": quality_issues,
                "quality_metrics": quality_result.metrics,
                "entry": entry.to_dict(),
            }, None

        if quality_result.decision == QualityDecision.NEEDS_REVISION:
            return {
                "status": "needs_revision",
                "message": quality_result.summary,
                "reason": "quality_needs_improvement",
                "quality_score": quality_result.score,
                "quality_issues": quality_issues,
                "quality_metrics": quality_result.metrics,
                "entry": entry.to_dict(),
            }, None

        # Track quality info for successful entries
        quality_info = None
        if quality_result.has_suggestions:
            quality_info = {
                "score": quality_result.score,
                "suggestions": [
                    {"message": i.message, "suggestion": i.suggestion}
                    for i in quality_result.issues
                ],
                "metrics": quality_result.metrics,
            }
        return None, quality_info

    def _get_duplicate_rejection(self, entry: NaturalLanguageEntry) -> dict[str, Any] | None:
        """Check for duplicates and return rejection response if found."""
        if not self.enable_deduplication:
            return None
        duplicate_check = self._check_duplicate(entry)
        if duplicate_check["is_duplicate"]:
            logger.info("Entry rejected: duplicate detected author=%s fingerprint=%s",
                       entry.author, duplicate_check["fingerprint"][:16])
            return {
                "status": "rejected",
                "message": "Entry rejected: duplicate detected (possible replay attack)",
                "reason": "duplicate",
                "original_timestamp": duplicate_check["original_timestamp"],
                "fingerprint": duplicate_check["fingerprint"],
                "entry": entry.to_dict(),
            }
        return None

    def _get_asset_transfer_rejection(
        self, entry: NaturalLanguageEntry
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        """Check asset transfer and return (rejection, transfer_info) tuple."""
        if not self.enable_asset_tracking:
            return None, None
        asset_check = self._check_asset_transfer(entry)
        if not asset_check["allowed"]:
            logger.warning("Entry rejected: double transfer attempt author=%s asset=%s",
                          entry.author, asset_check.get("asset_id"))
            return {
                "status": "rejected",
                "message": asset_check["message"],
                "reason": "double_transfer",
                "asset_id": asset_check.get("asset_id"),
                "existing_transfer": asset_check.get("existing_transfer"),
                "entry": entry.to_dict(),
            }, None
        transfer_info = asset_check if asset_check.get("is_transfer") else None
        return None, transfer_info

    def _get_validation_rejection(
        self, entry: NaturalLanguageEntry, skip_validation: bool
    ) -> dict[str, Any] | None:
        """Run entry validation and return rejection response if failed."""
        if not self.require_validation or skip_validation:
            return None

        try:
            validation_result = self._validate_entry(entry)
        except (ValueError, RuntimeError) as e:
            logger.error("Validation pipeline error for author=%s: %s", entry.author, e)
            return {
                "status": "rejected",
                "message": "Validation pipeline error",
                "error": str(e),
                "entry": entry.to_dict(),
            }

        if validation_result["status"] == "error":
            logger.warning("Entry validation error author=%s: %s",
                          entry.author, validation_result.get("error"))
            return {
                "status": "rejected",
                "message": "Validation failed with error",
                "error": validation_result.get("error", "Unknown validation error"),
                "entry": entry.to_dict(),
            }

        decision = validation_result.get("validation", {}).get("decision", "ERROR")

        if decision not in self._acceptable_decisions:
            logger.info("Entry rejected: validation decision=%s author=%s",
                       decision, entry.author)
            return {
                "status": "rejected",
                "message": f"Entry rejected: validation decision was {decision}",
                "validation_decision": decision,
                "validation_details": validation_result.get("validation", {}),
                "entry": entry.to_dict(),
            }

        # Entry passed validation - update status and store paraphrase
        entry.validation_status = "validated"
        paraphrase = validation_result.get("validation", {}).get("paraphrase", "")
        if paraphrase:
            entry.validation_paraphrases.append(paraphrase)

        return None

    def _finalize_entry_addition(
        self,
        entry: NaturalLanguageEntry,
        skip_validation: bool,
        metadata_warning: dict | None,
        asset_transfer_info: dict | None,
        quality_info: dict | None,
    ) -> dict[str, Any]:
        """Finalize entry addition and build success response."""
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
            "entry": entry.to_dict(),
        }

        if metadata_warning:
            response["metadata_warning"] = metadata_warning
        if asset_transfer_info:
            response["asset_transfer"] = {
                "asset_id": asset_transfer_info["asset_id"],
                "from": asset_transfer_info["from_owner"],
                "to": asset_transfer_info["to_recipient"],
            }
        if quality_info:
            response["quality_suggestions"] = quality_info

        return response

    def mine_pending_entries(self, difficulty: int = 2) -> Block | None:
        """
        Mine pending entries into a new block.
        Implements a simple proof-of-work for demonstration.

        Args:
            difficulty: Number of leading zeros required in hash

        Returns:
            The newly mined block or None if no pending entries
        """
        with self._mining_lock:
            if not self.pending_entries:
                return None

            new_block = Block(
                index=len(self.chain),
                entries=self.pending_entries.copy(),
                previous_hash=self.get_latest_block().hash,
            )

            # Proof of work: iterate nonces until hash has `difficulty` leading zeros.
            # This is intentionally simple — the goal is demonstrating PoW mechanics,
            # not competing with production mining difficulty.
            # TODO: add timeout to prevent runaway mining at high difficulty
            target = "0" * difficulty
            while not new_block.hash.startswith(target):
                new_block.nonce += 1
                new_block.hash = new_block.calculate_hash()

            self.chain.append(new_block)

            # Complete any pending asset transfers for mined entries
            if self.enable_asset_tracking and self._asset_registry is not None:
                for entry in self.pending_entries:
                    transfer_info = self._detect_asset_transfer(entry)
                    if transfer_info["is_transfer"]:
                        fingerprint = compute_entry_fingerprint(
                            entry.content, entry.author, entry.intent
                        )
                        self._asset_registry.complete_transfer(
                            asset_id=transfer_info["asset_id"], fingerprint=fingerprint
                        )

            # Register derivative relationships for mined entries
            if self.enable_derivative_tracking and self._derivative_registry is not None:
                block_index = new_block.index
                for entry_index, entry in enumerate(self.pending_entries):
                    if entry.is_derivative() and entry.parent_refs:
                        self._derivative_registry.register_derivative(
                            child_block=block_index,
                            child_entry=entry_index,
                            parent_refs=entry.parent_refs,
                            derivative_type=entry.derivative_type or DERIVATIVE_TYPE_REFERENCE,
                            child_metadata={
                                "author": entry.author,
                                "intent": entry.intent,
                                "timestamp": entry.timestamp,
                            },
                        )

            self.pending_entries = []

            return new_block

    def validate_chain(self, verify_pow: bool = True, difficulty: int = 1) -> bool:
        """
        Validate the entire blockchain for integrity.

        Args:
            verify_pow: Whether to verify proof-of-work on mined blocks
            difficulty: Minimum difficulty (leading zeros) to verify. Defaults to 1,
                       the minimum meaningful PoW. Pass a higher value if your chain
                       was mined with a known higher difficulty.

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

            # Verify proof-of-work: mined blocks must meet difficulty target
            if verify_pow and current_block.entries:
                target = "0" * difficulty
                if not current_block.hash.startswith(target):
                    return False

        return True

    def get_entries_by_author(self, author: str) -> list[dict[str, Any]]:
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
                    entries.append(
                        {
                            "block_index": block.index,
                            "block_hash": block.hash,
                            "entry": entry.to_dict(),
                        }
                    )
        return entries

    def get_entries_by_intent(self, intent_keyword: str) -> list[dict[str, Any]]:
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
                    entries.append(
                        {
                            "block_index": block.index,
                            "block_hash": block.hash,
                            "entry": entry.to_dict(),
                        }
                    )
        return entries

    # =========================================================================
    # Derivative Tracking Methods
    # =========================================================================

    def get_derivatives(
        self,
        block_index: int,
        entry_index: int,
        recursive: bool = False,
        max_depth: int = 10,
        include_entries: bool = False,
    ) -> dict[str, Any]:
        """
        Get all derivatives of a specific entry.

        Args:
            block_index: Block containing the parent entry
            entry_index: Index of the parent entry within the block
            recursive: If True, get all descendants recursively
            max_depth: Maximum recursion depth
            include_entries: If True, include full entry data

        Returns:
            Dict with derivative information
        """
        if not self.enable_derivative_tracking or not self._derivative_registry:
            return {"error": "Derivative tracking not enabled", "derivatives": []}

        derivatives = self._derivative_registry.get_derivatives(
            block_index, entry_index, recursive=recursive, max_depth=max_depth
        )

        # Optionally include full entry data
        if include_entries:
            for deriv in derivatives:
                entry = self._get_entry_at(deriv["block_index"], deriv["entry_index"])
                if entry:
                    deriv["entry"] = entry.to_dict()

        return {
            "parent": {"block_index": block_index, "entry_index": entry_index},
            "derivative_count": len(derivatives),
            "recursive": recursive,
            "derivatives": derivatives,
        }

    def get_lineage(
        self, block_index: int, entry_index: int, max_depth: int = 10, include_entries: bool = False
    ) -> dict[str, Any]:
        """
        Get the full ancestry/lineage of an entry.

        Args:
            block_index: Block containing the entry
            entry_index: Index of the entry within the block
            max_depth: Maximum traversal depth
            include_entries: If True, include full entry data

        Returns:
            Dict with lineage information
        """
        if not self.enable_derivative_tracking or not self._derivative_registry:
            return {"error": "Derivative tracking not enabled", "lineage": []}

        lineage = self._derivative_registry.get_lineage(
            block_index, entry_index, max_depth=max_depth
        )
        roots = self._derivative_registry.get_roots(block_index, entry_index, max_depth=max_depth)

        # Optionally include full entry data
        if include_entries:
            for ancestor in lineage:
                entry = self._get_entry_at(ancestor["block_index"], ancestor["entry_index"])
                if entry:
                    ancestor["entry"] = entry.to_dict()
            for root in roots:
                entry = self._get_entry_at(root["block_index"], root["entry_index"])
                if entry:
                    root["entry"] = entry.to_dict()

        return {
            "entry": {"block_index": block_index, "entry_index": entry_index},
            "ancestor_count": len(lineage),
            "lineage": lineage,
            "roots": roots,
        }

    def get_derivation_tree(
        self, block_index: int, entry_index: int, max_depth: int = 10, include_entries: bool = False
    ) -> dict[str, Any]:
        """
        Get the complete derivation tree for an entry.

        Returns both ancestors and descendants in a tree structure.

        Args:
            block_index: Block containing the entry
            entry_index: Index of the entry within the block
            max_depth: Maximum traversal depth in each direction
            include_entries: If True, include full entry data

        Returns:
            Dict containing the full derivation tree
        """
        if not self.enable_derivative_tracking or not self._derivative_registry:
            return {"error": "Derivative tracking not enabled", "tree": {}}

        tree = self._derivative_registry.get_derivation_tree(
            block_index, entry_index, max_depth=max_depth
        )

        # Optionally include full entry data
        if include_entries:
            # Include entry data for the target
            entry = self._get_entry_at(block_index, entry_index)
            if entry:
                tree["entry"]["data"] = entry.to_dict()

            # Include entry data for parents
            for parent in tree.get("parents", []):
                parent_entry = self._get_entry_at(parent["block_index"], parent["entry_index"])
                if parent_entry:
                    parent["entry"] = parent_entry.to_dict()

            # Include entry data for lineage
            for ancestor in tree.get("lineage", []):
                ancestor_entry = self._get_entry_at(
                    ancestor["block_index"], ancestor["entry_index"]
                )
                if ancestor_entry:
                    ancestor["entry"] = ancestor_entry.to_dict()

            # Include entry data for derivatives
            for deriv in tree.get("derivatives", []):
                deriv_entry = self._get_entry_at(deriv["block_index"], deriv["entry_index"])
                if deriv_entry:
                    deriv["entry"] = deriv_entry.to_dict()

            # Include entry data for all descendants
            for desc in tree.get("all_descendants", []):
                desc_entry = self._get_entry_at(desc["block_index"], desc["entry_index"])
                if desc_entry:
                    desc["entry"] = desc_entry.to_dict()

        return tree

    def _get_entry_at(self, block_index: int, entry_index: int) -> NaturalLanguageEntry | None:
        """Get an entry at a specific block and entry index."""
        if block_index < 0 or block_index >= len(self.chain):
            return None
        block = self.chain[block_index]
        if entry_index < 0 or entry_index >= len(block.entries):
            return None
        return block.entries[entry_index]

    def is_derivative(self, block_index: int, entry_index: int) -> bool:
        """Check if an entry is a derivative of another entry."""
        if not self.enable_derivative_tracking or not self._derivative_registry:
            return False
        return self._derivative_registry.is_derivative(block_index, entry_index)

    def has_derivatives(self, block_index: int, entry_index: int) -> bool:
        """Check if an entry has any derivatives."""
        if not self.enable_derivative_tracking or not self._derivative_registry:
            return False
        return self._derivative_registry.has_derivatives(block_index, entry_index)

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
                    narrative.append("  Validation Paraphrases:")
                    for paraphrase in entry.validation_paraphrases:
                        narrative.append(f"    - {paraphrase}")
                narrative.append("")

        return "\n".join(narrative)

    def to_dict(self) -> dict[str, Any]:
        """Export the entire chain as dictionary."""
        result = {
            "chain": [block.to_dict() for block in self.chain],
            "pending_entries": [entry.to_dict() for entry in self.pending_entries],
        }

        # Include derivative registry if enabled
        if self.enable_derivative_tracking and self._derivative_registry:
            result["derivative_registry"] = self._derivative_registry.to_dict()

        # Include asset registry if enabled
        if self.enable_asset_tracking and self._asset_registry:
            result["asset_registry"] = self._asset_registry.to_dict()

        # Include entry fingerprints for deduplication persistence
        if self._entry_fingerprints:
            result["entry_fingerprints"] = self._entry_fingerprints

        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        require_validation: bool = False,
        validator: Any | None = None,
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
        forbidden_metadata_fields: set | None = None,
        enable_asset_tracking: bool = True,
        asset_registry: AssetRegistry | None = None,
        enable_derivative_tracking: bool = True,
        derivative_registry: DerivativeRegistry | None = None,
    ) -> "NatLangChain":
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
            enable_asset_tracking: Whether to track asset ownership.
            asset_registry: Optional pre-configured AssetRegistry instance.
            enable_derivative_tracking: Whether to track entry derivations.
            derivative_registry: Optional pre-configured DerivativeRegistry instance.
        """
        chain = cls.__new__(cls)
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        chain.pending_entries = [
            NaturalLanguageEntry.from_dict(e) for e in data.get("pending_entries", [])
        ]
        chain.require_validation = require_validation
        chain.validator = validator
        chain.allow_needs_clarification = False
        chain._acceptable_decisions = {VALIDATION_VALID}
        chain.enable_deduplication = enable_deduplication
        chain.dedup_window_seconds = dedup_window_seconds
        chain._entry_fingerprints = data.get("entry_fingerprints", {})
        chain.enable_rate_limiting = enable_rate_limiting
        chain._rate_limiter = (
            EntryRateLimiter(
                window_seconds=rate_limit_window,
                max_per_author=max_entries_per_author,
                max_global=max_global_entries,
            )
            if enable_rate_limiting
            else None
        )
        chain.enable_timestamp_validation = enable_timestamp_validation
        chain.max_timestamp_drift = max_timestamp_drift
        chain.max_future_drift = max_future_drift
        chain.enable_metadata_sanitization = enable_metadata_sanitization
        chain.metadata_sanitize_mode = metadata_sanitize_mode
        chain.forbidden_metadata_fields = forbidden_metadata_fields or FORBIDDEN_METADATA_FIELDS
        # Initialize quality checks (using defaults — these aren't serialized)
        chain.enable_quality_checks = True
        chain.max_entry_size = DEFAULT_MAX_ENTRY_SIZE
        chain.min_entry_size = DEFAULT_MIN_ENTRY_SIZE
        chain.quality_strict_mode = DEFAULT_QUALITY_STRICT_MODE
        chain._quality_analyzer = chain._init_quality_analyzer(
            True, DEFAULT_MAX_ENTRY_SIZE, DEFAULT_MIN_ENTRY_SIZE, DEFAULT_QUALITY_STRICT_MODE
        )

        chain.enable_asset_tracking = enable_asset_tracking
        if asset_registry:
            chain._asset_registry = asset_registry
        elif "asset_registry" in data and enable_asset_tracking:
            chain._asset_registry = AssetRegistry.from_dict(data["asset_registry"])
        else:
            chain._asset_registry = (
                AssetRegistry() if enable_asset_tracking else None
            )

        # Initialize derivative tracking
        chain.enable_derivative_tracking = enable_derivative_tracking
        if derivative_registry:
            chain._derivative_registry = derivative_registry
        elif "derivative_registry" in data and enable_derivative_tracking:
            chain._derivative_registry = DerivativeRegistry.from_dict(data["derivative_registry"])
        else:
            chain._derivative_registry = (
                DerivativeRegistry() if enable_derivative_tracking else None
            )

        # Intent classifier (not serialized — initialized separately)
        chain._intent_classifier = None

        return chain
