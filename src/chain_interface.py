"""
NatLangChain - Secure Chain Interface for Mediator-Node Communication
Implements HTTPS/TLS with HMAC authentication for mediator-node integration.

Core principle: All external communication must be authenticated,
encrypted, and auditable.
"""

import contextlib
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import requests for HTTP client
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None


# =============================================================================
# Constants
# =============================================================================

# Default chain endpoint (configurable via environment variable)
DEFAULT_CHAIN_ENDPOINT = os.getenv("NATLANGCHAIN_CHAIN_ENDPOINT", "http://localhost:8545")

# API version
API_VERSION = "v1"

# Timeouts (seconds)
DEFAULT_TIMEOUT = 30
CONNECT_TIMEOUT = 10

# Retry configuration
MAX_RETRIES = 4
RETRY_BACKOFF_FACTOR = 2  # Exponential: 2s, 4s, 8s, 16s

# HMAC configuration
HMAC_ALGORITHM = "sha256"
HMAC_HEADER = "X-NLC-Signature"
TIMESTAMP_HEADER = "X-NLC-Timestamp"
NONCE_HEADER = "X-NLC-Nonce"

# Timestamp window (seconds) for replay attack prevention
TIMESTAMP_WINDOW = 300  # 5 minutes


# =============================================================================
# Enums
# =============================================================================


class IntentStatus(Enum):
    """Status of an intent on the chain."""

    PENDING = "pending"
    MATCHED = "matched"
    SETTLED = "settled"
    CHALLENGED = "challenged"
    REJECTED = "rejected"


class SubmissionType(Enum):
    """Types of submissions that can be made to the chain.

    Note: This is different from SubmissionType in sunset_clauses.py which
    defines document types with different sunset/archival policies.
    """

    SETTLEMENT = "settlement"
    ACCEPT = "accept"
    PAYOUT = "payout"
    CHALLENGE = "challenge"
    REPUTATION_UPDATE = "reputation_update"


class SettlementStatus(Enum):
    """Status of a settlement."""

    PROPOSED = "proposed"
    PARTY_A_ACCEPTED = "party_a_accepted"
    PARTY_B_ACCEPTED = "party_b_accepted"
    BOTH_ACCEPTED = "both_accepted"
    CHALLENGED = "challenged"
    FINALIZED = "finalized"
    REJECTED = "rejected"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ChainIntent:
    """An intent fetched from the chain."""

    hash: str
    author: str
    prose: str
    desires: list[str]
    constraints: list[str]
    offered_fee: float
    timestamp: int
    status: IntentStatus
    branch: str
    nonce: str | None = None
    signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hash": self.hash,
            "author": self.author,
            "prose": self.prose,
            "desires": self.desires,
            "constraints": self.constraints,
            "offeredFee": self.offered_fee,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "branch": self.branch,
            "nonce": self.nonce,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChainIntent":
        """Create from dictionary."""
        return cls(
            hash=data.get("hash", ""),
            author=data.get("author", ""),
            prose=data.get("prose", ""),
            desires=data.get("desires", []),
            constraints=data.get("constraints", []),
            offered_fee=float(data.get("offeredFee", 0)),
            timestamp=int(data.get("timestamp", 0)),
            status=IntentStatus(data.get("status", "pending")),
            branch=data.get("branch", ""),
            nonce=data.get("nonce"),
            signature=data.get("signature"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ChainSettlement:
    """A settlement on the chain."""

    id: str
    intent_hash_a: str
    intent_hash_b: str
    mediator_id: str
    terms: dict[str, Any]
    fee: float
    status: SettlementStatus
    party_a_accepted: bool = False
    party_b_accepted: bool = False
    challenges: list[dict[str, Any]] = field(default_factory=list)
    created_at: str | None = None
    finalized_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "intentHashA": self.intent_hash_a,
            "intentHashB": self.intent_hash_b,
            "mediatorId": self.mediator_id,
            "terms": self.terms,
            "fee": self.fee,
            "status": self.status.value,
            "partyAAccepted": self.party_a_accepted,
            "partyBAccepted": self.party_b_accepted,
            "challenges": self.challenges,
            "createdAt": self.created_at,
            "finalizedAt": self.finalized_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChainSettlement":
        """Create from dictionary."""
        status_str = data.get("status", "proposed")
        try:
            status = SettlementStatus(status_str)
        except ValueError:
            status = SettlementStatus.PROPOSED

        return cls(
            id=data.get("id", ""),
            intent_hash_a=data.get("intentHashA", data.get("intent_hash_a", "")),
            intent_hash_b=data.get("intentHashB", data.get("intent_hash_b", "")),
            mediator_id=data.get("mediatorId", data.get("mediator_id", "")),
            terms=data.get("terms", {}),
            fee=float(data.get("fee", 0)),
            status=status,
            party_a_accepted=data.get("partyAAccepted", False),
            party_b_accepted=data.get("partyBAccepted", False),
            challenges=data.get("challenges", []),
            created_at=data.get("createdAt"),
            finalized_at=data.get("finalizedAt"),
        )


@dataclass
class ChainReputation:
    """Mediator reputation from the chain."""

    mediator_id: str
    successful_closures: int = 0
    failed_challenges: int = 0
    upheld_challenges_against: int = 0
    forfeited_fees: int = 0
    weight: float = 1.0
    last_updated: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mediatorId": self.mediator_id,
            "successfulClosures": self.successful_closures,
            "failedChallenges": self.failed_challenges,
            "upheldChallengesAgainst": self.upheld_challenges_against,
            "forfeitedFees": self.forfeited_fees,
            "weight": self.weight,
            "lastUpdated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChainReputation":
        """Create from dictionary."""
        return cls(
            mediator_id=data.get("mediatorId", data.get("mediator_id", "")),
            successful_closures=int(data.get("successfulClosures", 0)),
            failed_challenges=int(data.get("failedChallenges", 0)),
            upheld_challenges_against=int(data.get("upheldChallengesAgainst", 0)),
            forfeited_fees=int(data.get("forfeitedFees", 0)),
            weight=float(data.get("weight", 1.0)),
            last_updated=data.get("lastUpdated"),
        )


@dataclass
class ChainDelegation:
    """A delegation to a mediator."""

    delegator_id: str
    mediator_id: str
    amount: float
    timestamp: int
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "delegatorId": self.delegator_id,
            "mediatorId": self.mediator_id,
            "amount": self.amount,
            "timestamp": self.timestamp,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChainDelegation":
        """Create from dictionary."""
        return cls(
            delegator_id=data.get("delegatorId", data.get("delegator_id", "")),
            mediator_id=data.get("mediatorId", data.get("mediator_id", "")),
            amount=float(data.get("amount", 0)),
            timestamp=int(data.get("timestamp", 0)),
            status=data.get("status", "active"),
        )


@dataclass
class ChainHealth:
    """Chain health status."""

    status: str
    chain_id: str
    consensus_mode: str
    intent_count: int
    settlement_count: int
    uptime: float


# =============================================================================
# HMAC Authentication
# =============================================================================


class HMACAuthenticator:
    """
    HMAC-based request authentication.

    Provides:
    - Request signing with HMAC-SHA256
    - Timestamp validation for replay prevention
    - Nonce tracking for uniqueness
    """

    def __init__(self, secret_key: str):
        """
        Initialize authenticator.

        Args:
            secret_key: Shared secret for HMAC signing
        """
        self.secret_key = secret_key.encode("utf-8")
        self._used_nonces: dict[str, int] = {}  # nonce -> timestamp
        self._nonce_cleanup_interval = 3600  # Clean up nonces older than 1 hour

    def _compute_signature(
        self, method: str, path: str, timestamp: int, nonce: str, body: str | None = None
    ) -> str:
        """
        Compute HMAC signature for a request.

        Args:
            method: HTTP method
            path: Request path
            timestamp: Request timestamp
            nonce: Request nonce
            body: Request body (JSON string)

        Returns:
            HMAC signature string
        """
        sign_string = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body or ''}"
        return hmac.new(self.secret_key, sign_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def sign_request(
        self, method: str, path: str, body: str | None = None, timestamp: int | None = None
    ) -> dict[str, str]:
        """
        Sign a request and return authentication headers.

        Args:
            method: HTTP method
            path: Request path
            body: Request body (JSON string)
            timestamp: Optional timestamp (uses current time if not provided)

        Returns:
            Dictionary of authentication headers
        """
        if timestamp is None:
            timestamp = int(time.time())

        nonce = secrets.token_hex(16)
        signature = self._compute_signature(method, path, timestamp, nonce, body)

        return {HMAC_HEADER: signature, TIMESTAMP_HEADER: str(timestamp), NONCE_HEADER: nonce}

    def verify_request(
        self, method: str, path: str, body: str | None, signature: str, timestamp: str, nonce: str
    ) -> tuple[bool, str]:
        """
        Verify a request's authentication.

        Args:
            method: HTTP method
            path: Request path
            body: Request body
            signature: HMAC signature from header
            timestamp: Timestamp from header
            nonce: Nonce from header

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate timestamp
        try:
            ts = int(timestamp)
        except ValueError:
            return False, "Invalid timestamp format"

        current_time = int(time.time())
        if abs(current_time - ts) > TIMESTAMP_WINDOW:
            return False, "Timestamp outside acceptable window"

        # Check nonce uniqueness
        self._cleanup_old_nonces()
        if nonce in self._used_nonces:
            return False, "Nonce already used (replay attack detected)"

        # Store nonce
        self._used_nonces[nonce] = ts

        # Verify signature using the provided nonce (not a new one)
        expected_signature = self._compute_signature(method, path, ts, nonce, body)
        if not hmac.compare_digest(signature, expected_signature):
            return False, "Invalid signature"

        return True, "OK"

    def _cleanup_old_nonces(self):
        """Remove old nonces to prevent memory growth."""
        current_time = int(time.time())
        cutoff = current_time - self._nonce_cleanup_interval

        self._used_nonces = {nonce: ts for nonce, ts in self._used_nonces.items() if ts > cutoff}


# =============================================================================
# Chain Interface
# =============================================================================


class ChainInterface:
    """
    Secure interface for communicating with the NatLangChain mediator-node.

    Features:
    - HTTPS with TLS certificate verification
    - HMAC request authentication
    - Automatic retry with exponential backoff
    - Request/response logging for audit
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_CHAIN_ENDPOINT,
        secret_key: str | None = None,
        verify_ssl: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        mediator_id: str | None = None,
    ):
        """
        Initialize chain interface.

        Args:
            endpoint: Chain API endpoint URL
            secret_key: Shared secret for HMAC authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
            mediator_id: This mediator's identifier
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_base = f"{self.endpoint}/api/{API_VERSION}"
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.mediator_id = mediator_id or f"mediator_{secrets.token_hex(8)}"

        # Set up authentication
        self.authenticator = None
        if secret_key:
            self.authenticator = HMACAuthenticator(secret_key)

        # Set up HTTP session with retry
        self.session = None
        if HAS_REQUESTS:
            self._setup_session()

        # Audit log
        self.audit_log: list[dict[str, Any]] = []

        # Event callbacks
        self._callbacks: dict[str, list[Callable]] = {}

    def _setup_session(self):
        """Set up requests session with retry logic."""
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": f"NatLangChain-Python/{API_VERSION}",
            }
        )

    def _make_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        """
        Make an authenticated HTTP request.

        Args:
            method: HTTP method
            path: API path (without base URL)
            body: Request body (will be JSON-encoded)
            params: Query parameters

        Returns:
            Tuple of (success, response_data or error)
        """
        if not HAS_REQUESTS:
            return False, {"error": "requests library not installed"}

        url = f"{self.api_base}{path}"
        body_str = json.dumps(body) if body else None

        # Build headers
        headers = {}
        if self.authenticator:
            auth_headers = self.authenticator.sign_request(method, path, body_str)
            headers.update(auth_headers)

        # Log request
        request_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "path": path,
            "params": params,
            "body_hash": hashlib.sha256(body_str.encode()).hexdigest() if body_str else None,
        }

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=body,
                params=params,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, self.timeout),
                verify=self.verify_ssl,
            )

            # Log response
            request_log["status_code"] = response.status_code
            request_log["success"] = response.ok
            self.audit_log.append(request_log)

            if response.ok:
                try:
                    data = response.json()
                    return True, data
                except json.JSONDecodeError:
                    return True, {"raw": response.text}
            else:
                error_data = {
                    "error": f"HTTP {response.status_code}",
                    "status_code": response.status_code,
                    "message": response.text,
                }
                with contextlib.suppress(Exception):
                    error_data.update(response.json())
                return False, error_data

        except requests.exceptions.Timeout:
            request_log["error"] = "timeout"
            self.audit_log.append(request_log)
            return False, {"error": "Request timed out"}
        except requests.exceptions.SSLError as e:
            request_log["error"] = f"ssl_error: {e!s}"
            self.audit_log.append(request_log)
            return False, {"error": f"SSL error: {e!s}"}
        except requests.exceptions.ConnectionError as e:
            request_log["error"] = f"connection_error: {e!s}"
            self.audit_log.append(request_log)
            return False, {"error": f"Connection error: {e!s}"}
        except Exception as e:
            request_log["error"] = str(e)
            self.audit_log.append(request_log)
            return False, {"error": str(e)}

    # =========================================================================
    # Intent Operations
    # =========================================================================

    def get_intents(
        self, status: IntentStatus | None = None, since: int | None = None, limit: int | None = None
    ) -> tuple[bool, list[ChainIntent]]:
        """
        Fetch intents from the chain.

        Args:
            status: Filter by status
            since: Fetch intents since this timestamp
            limit: Maximum number of intents to return

        Returns:
            Tuple of (success, list of intents or error)
        """
        params = {}
        if status:
            params["status"] = status.value
        if since:
            params["since"] = since
        if limit:
            params["limit"] = limit

        success, result = self._make_request("GET", "/intents", params=params)

        if success:
            intents_data = result.get("intents", [])
            intents = [ChainIntent.from_dict(i) for i in intents_data]
            self._emit("intents_fetched", {"count": len(intents)})
            return True, intents

        return False, result

    def get_pending_intents(self) -> tuple[bool, list[ChainIntent]]:
        """Get all pending intents."""
        return self.get_intents(status=IntentStatus.PENDING)

    # =========================================================================
    # Entry Submission
    # =========================================================================

    def submit_entry(
        self,
        entry_type: SubmissionType,
        author: str,
        content: dict[str, Any],
        metadata: dict[str, Any],
        signature: str | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        """
        Submit an entry to the chain.

        Args:
            entry_type: Type of entry
            author: Entry author
            content: Entry content
            metadata: Entry metadata
            signature: Optional cryptographic signature

        Returns:
            Tuple of (success, result)
        """
        body = {
            "type": entry_type.value,
            "author": author,
            "content": content,
            "metadata": metadata,
            "signature": signature,
        }

        success, result = self._make_request("POST", "/entries", body=body)

        if success:
            self._emit(
                "entry_submitted", {"type": entry_type.value, "entry_id": result.get("entryId")}
            )

        return success, result

    def propose_settlement(
        self, intent_hash_a: str, intent_hash_b: str, terms: dict[str, Any], fee: float
    ) -> tuple[bool, dict[str, Any]]:
        """
        Propose a settlement between two intents.

        Args:
            intent_hash_a: First intent hash
            intent_hash_b: Second intent hash
            terms: Settlement terms
            fee: Mediator fee

        Returns:
            Tuple of (success, result)
        """
        settlement_id = f"settlement_{secrets.token_hex(8)}"

        metadata = {
            "id": settlement_id,
            "intentHashA": intent_hash_a,
            "intentHashB": intent_hash_b,
            "mediatorId": self.mediator_id,
            "terms": terms,
            "fee": fee,
        }

        return self.submit_entry(
            entry_type=SubmissionType.SETTLEMENT,
            author=self.mediator_id,
            content={"settlement": metadata},
            metadata=metadata,
        )

    def accept_settlement(
        self, settlement_id: str, party: str, party_identifier: str
    ) -> tuple[bool, dict[str, Any]]:
        """
        Submit acceptance of a settlement.

        Args:
            settlement_id: Settlement to accept
            party: Party role (A or B)
            party_identifier: Party's identifier

        Returns:
            Tuple of (success, result)
        """
        metadata = {"settlementId": settlement_id, "party": party, "partyId": party_identifier}

        return self.submit_entry(
            entry_type=SubmissionType.ACCEPT,
            author=party_identifier,
            content={"acceptance": metadata},
            metadata=metadata,
        )

    def claim_payout(self, settlement_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Claim payout for a finalized settlement.

        Args:
            settlement_id: Settlement to claim payout for

        Returns:
            Tuple of (success, result)
        """
        metadata = {
            "settlementId": settlement_id,
            "mediatorId": self.mediator_id,
            "claimedAt": datetime.utcnow().isoformat(),
        }

        return self.submit_entry(
            entry_type=SubmissionType.PAYOUT,
            author=self.mediator_id,
            content={"payout": metadata},
            metadata=metadata,
        )

    # =========================================================================
    # Settlement Operations
    # =========================================================================

    def get_settlement_status(self, settlement_id: str) -> tuple[bool, ChainSettlement | None]:
        """
        Get the status of a settlement.

        Args:
            settlement_id: Settlement ID

        Returns:
            Tuple of (success, settlement or error)
        """
        success, result = self._make_request("GET", f"/settlements/{settlement_id}/status")

        if success:
            settlement = ChainSettlement.from_dict(result)
            return True, settlement

        return False, result

    def is_settlement_accepted(self, settlement_id: str) -> tuple[bool, bool]:
        """
        Check if both parties have accepted a settlement.

        Args:
            settlement_id: Settlement ID

        Returns:
            Tuple of (success, both_accepted)
        """
        success, settlement = self.get_settlement_status(settlement_id)

        if success and isinstance(settlement, ChainSettlement):
            both_accepted = settlement.party_a_accepted and settlement.party_b_accepted
            return True, both_accepted

        return False, False

    # =========================================================================
    # Reputation Operations
    # =========================================================================

    def get_reputation(self, mediator_id: str | None = None) -> tuple[bool, ChainReputation | None]:
        """
        Get reputation for a mediator.

        Args:
            mediator_id: Mediator ID (defaults to self)

        Returns:
            Tuple of (success, reputation or error)
        """
        mid = mediator_id or self.mediator_id

        success, result = self._make_request("GET", f"/reputation/{mid}")

        if success:
            reputation = ChainReputation.from_dict(result)
            return True, reputation

        return False, result

    def update_reputation(
        self, mediator_id: str, reputation: ChainReputation
    ) -> tuple[bool, dict[str, Any]]:
        """
        Update reputation for a mediator.

        Args:
            mediator_id: Mediator to update
            reputation: New reputation data

        Returns:
            Tuple of (success, result)
        """
        body = {"mediatorId": mediator_id, "reputation": reputation.to_dict()}

        return self._make_request("POST", "/reputation", body=body)

    # =========================================================================
    # Delegation Operations
    # =========================================================================

    def get_delegations(self, mediator_id: str | None = None) -> tuple[bool, list[ChainDelegation]]:
        """
        Get delegations for a mediator.

        Args:
            mediator_id: Mediator ID (defaults to self)

        Returns:
            Tuple of (success, delegations or error)
        """
        mid = mediator_id or self.mediator_id

        success, result = self._make_request("GET", f"/delegations/{mid}")

        if success:
            delegations_data = result.get("delegations", [])
            delegations = [ChainDelegation.from_dict(d) for d in delegations_data]
            return True, delegations

        return False, result

    # =========================================================================
    # Staking Operations
    # =========================================================================

    def bond_stake(self, amount: float) -> tuple[bool, dict[str, Any]]:
        """
        Bond stake for this mediator.

        Args:
            amount: Amount to stake

        Returns:
            Tuple of (success, result)
        """
        body = {"mediatorId": self.mediator_id, "amount": amount}

        success, result = self._make_request("POST", "/stake/bond", body=body)

        if success:
            self._emit("stake_bonded", {"amount": amount})

        return success, result

    def unbond_stake(self) -> tuple[bool, dict[str, Any]]:
        """
        Request to unbond stake.

        Returns:
            Tuple of (success, result)
        """
        body = {"mediatorId": self.mediator_id}

        success, result = self._make_request("POST", "/stake/unbond", body=body)

        if success:
            self._emit("stake_unbonding", {})

        return success, result

    # =========================================================================
    # Governance Operations
    # =========================================================================

    def get_authorities(self) -> tuple[bool, list[str]]:
        """
        Get the current authority set.

        Returns:
            Tuple of (success, authorities or error)
        """
        success, result = self._make_request("GET", "/consensus/authorities")

        if success:
            return True, result.get("authorities", [])

        return False, result

    def submit_governance_proposal(
        self, title: str, description: str, proposal_type: str, parameters: dict[str, Any]
    ) -> tuple[bool, dict[str, Any]]:
        """
        Submit a governance proposal.

        Args:
            title: Proposal title
            description: Proposal description
            proposal_type: Type of proposal
            parameters: Proposal parameters

        Returns:
            Tuple of (success, result)
        """
        body = {
            "title": title,
            "description": description,
            "type": proposal_type,
            "parameters": parameters,
            "proposer": self.mediator_id,
        }

        return self._make_request("POST", "/governance/proposals", body=body)

    # =========================================================================
    # Health Check
    # =========================================================================

    def health_check(self) -> tuple[bool, ChainHealth | None]:
        """
        Check chain health.

        Returns:
            Tuple of (success, health or error)
        """
        # Health endpoint is at root, not API base
        url = f"{self.endpoint}/health"

        try:
            if HAS_REQUESTS:
                response = self.session.get(
                    url, timeout=(CONNECT_TIMEOUT, self.timeout), verify=self.verify_ssl
                )

                if response.ok:
                    data = response.json()
                    health = ChainHealth(
                        status=data.get("status", "unknown"),
                        chain_id=data.get("chainId", ""),
                        consensus_mode=data.get("consensusMode", ""),
                        intent_count=data.get("intents", 0),
                        settlement_count=data.get("settlements", 0),
                        uptime=data.get("uptime", 0),
                    )
                    return True, health
                else:
                    return False, {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}

        return False, {"error": "requests library not installed"}

    # =========================================================================
    # Event System
    # =========================================================================

    def on(self, event: str, callback: Callable):
        """
        Register an event callback.

        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable):
        """
        Unregister an event callback.

        Args:
            event: Event name
            callback: Callback to remove
        """
        if event in self._callbacks:
            self._callbacks[event] = [cb for cb in self._callbacks[event] if cb != callback]

    def _emit(self, event: str, data: dict[str, Any]):
        """Emit an event to registered callbacks."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.warning(f"Event callback error: {e}")

    # =========================================================================
    # Audit
    # =========================================================================

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]

    def clear_audit_log(self):
        """Clear the audit log."""
        self.audit_log = []


# =============================================================================
# Mock Chain Interface for Testing
# =============================================================================


class MockChainInterface(ChainInterface):
    """
    Mock chain interface for testing without a real mediator-node.

    Simulates chain behavior locally for unit tests.
    """

    def __init__(
        self, mediator_id: str | None = None, initial_intents: list[ChainIntent] | None = None
    ):
        """
        Initialize mock interface.

        Args:
            mediator_id: Mediator identifier
            initial_intents: Optional initial intents
        """
        super().__init__(endpoint="http://mock:8545", mediator_id=mediator_id, verify_ssl=False)

        # Mock data stores
        self._intents: dict[str, ChainIntent] = {}
        self._settlements: dict[str, ChainSettlement] = {}
        self._reputations: dict[str, ChainReputation] = {}
        self._delegations: dict[str, list[ChainDelegation]] = {}
        self._entries: list[dict[str, Any]] = []
        self._stake: dict[str, float] = {}

        # Initialize with provided intents
        if initial_intents:
            for intent in initial_intents:
                self._intents[intent.hash] = intent

    def _make_request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[bool, Any]:
        """Override to use mock data instead of HTTP."""
        # Log the request
        self.audit_log.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "method": method,
                "path": path,
                "params": params,
                "mock": True,
            }
        )

        # Route to mock handlers
        if path == "/intents" and method == "GET":
            return self._mock_get_intents(params or {})
        elif path == "/entries" and method == "POST":
            return self._mock_submit_entry(body or {})
        elif path.startswith("/settlements/") and path.endswith("/status"):
            settlement_id = path.split("/")[2]
            return self._mock_get_settlement(settlement_id)
        elif path.startswith("/reputation/"):
            mediator_id = path.split("/")[2]
            if method == "GET":
                return self._mock_get_reputation(mediator_id)
        elif path == "/reputation" and method == "POST":
            return self._mock_update_reputation(body or {})
        elif path.startswith("/delegations/"):
            mediator_id = path.split("/")[2]
            return self._mock_get_delegations(mediator_id)
        elif path == "/stake/bond" and method == "POST":
            return self._mock_bond_stake(body or {})
        elif path == "/stake/unbond" and method == "POST":
            return self._mock_unbond_stake(body or {})
        elif path == "/consensus/authorities":
            return True, {"authorities": ["authority_1", "authority_2"]}
        elif path == "/governance/proposals" and method == "POST":
            return True, {"proposalId": f"proposal_{secrets.token_hex(4)}"}

        return False, {"error": f"Unknown path: {path}"}

    def _mock_get_intents(self, params: dict[str, Any]) -> tuple[bool, Any]:
        """Mock get intents."""
        intents = list(self._intents.values())

        # Apply filters
        if "status" in params:
            status = params["status"]
            intents = [i for i in intents if i.status.value == status]

        if "since" in params:
            since = int(params["since"])
            intents = [i for i in intents if i.timestamp >= since]

        if "limit" in params:
            limit = int(params["limit"])
            intents = intents[:limit]

        return True, {"intents": [i.to_dict() for i in intents]}

    def _mock_submit_entry(self, body: dict[str, Any]) -> tuple[bool, Any]:
        """Mock submit entry."""
        entry_id = f"entry_{secrets.token_hex(8)}"

        # Store entry
        self._entries.append({"id": entry_id, **body})

        # Handle settlement type
        if body.get("type") == "settlement":
            metadata = body.get("metadata", {})
            settlement = ChainSettlement(
                id=metadata.get("id", entry_id),
                intent_hash_a=metadata.get("intentHashA", ""),
                intent_hash_b=metadata.get("intentHashB", ""),
                mediator_id=metadata.get("mediatorId", ""),
                terms=metadata.get("terms", {}),
                fee=metadata.get("fee", 0),
                status=SettlementStatus.PROPOSED,
                created_at=datetime.utcnow().isoformat(),
            )
            self._settlements[settlement.id] = settlement

        # Handle accept type
        elif body.get("type") == "accept":
            metadata = body.get("metadata", {})
            settlement_id = metadata.get("settlementId")
            party = metadata.get("party")

            if settlement_id in self._settlements:
                settlement = self._settlements[settlement_id]
                if party == "A":
                    settlement.party_a_accepted = True
                elif party == "B":
                    settlement.party_b_accepted = True

                # Update status
                if settlement.party_a_accepted and settlement.party_b_accepted:
                    settlement.status = SettlementStatus.BOTH_ACCEPTED

        return True, {"entryId": entry_id, "hash": entry_id}

    def _mock_get_settlement(self, settlement_id: str) -> tuple[bool, Any]:
        """Mock get settlement status."""
        if settlement_id in self._settlements:
            return True, self._settlements[settlement_id].to_dict()
        return False, {"error": "Settlement not found"}

    def _mock_get_reputation(self, mediator_id: str) -> tuple[bool, Any]:
        """Mock get reputation."""
        if mediator_id in self._reputations:
            return True, self._reputations[mediator_id].to_dict()

        # Return default reputation
        default_rep = ChainReputation(
            mediator_id=mediator_id, weight=1.0, last_updated=int(time.time())
        )
        return True, default_rep.to_dict()

    def _mock_update_reputation(self, body: dict[str, Any]) -> tuple[bool, Any]:
        """Mock update reputation."""
        mediator_id = body.get("mediatorId")
        rep_data = body.get("reputation", {})

        self._reputations[mediator_id] = ChainReputation.from_dict(rep_data)
        return True, {"success": True}

    def _mock_get_delegations(self, mediator_id: str) -> tuple[bool, Any]:
        """Mock get delegations."""
        delegations = self._delegations.get(mediator_id, [])
        return True, {"delegations": [d.to_dict() for d in delegations]}

    def _mock_bond_stake(self, body: dict[str, Any]) -> tuple[bool, Any]:
        """Mock bond stake."""
        mediator_id = body.get("mediatorId")
        amount = body.get("amount", 0)

        self._stake[mediator_id] = self._stake.get(mediator_id, 0) + amount
        return True, {"success": True}

    def _mock_unbond_stake(self, body: dict[str, Any]) -> tuple[bool, Any]:
        """Mock unbond stake."""
        return True, {"success": True}

    # =========================================================================
    # Test Helpers
    # =========================================================================

    def add_test_intent(self, intent: ChainIntent):
        """Add an intent for testing."""
        self._intents[intent.hash] = intent

    def set_test_settlement_accepted(
        self, settlement_id: str, party_a: bool = False, party_b: bool = False
    ):
        """Set settlement acceptance for testing."""
        if settlement_id in self._settlements:
            settlement = self._settlements[settlement_id]
            if party_a:
                settlement.party_a_accepted = True
            if party_b:
                settlement.party_b_accepted = True

            if settlement.party_a_accepted and settlement.party_b_accepted:
                settlement.status = SettlementStatus.BOTH_ACCEPTED

    def add_test_delegation(self, delegation: ChainDelegation):
        """Add a delegation for testing."""
        if delegation.mediator_id not in self._delegations:
            self._delegations[delegation.mediator_id] = []
        self._delegations[delegation.mediator_id].append(delegation)

    def get_submitted_entries(self) -> list[dict[str, Any]]:
        """Get all submitted entries for verification."""
        return self._entries.copy()


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_interface: ChainInterface | None = None


def get_chain_interface() -> ChainInterface:
    """Get the default chain interface singleton."""
    global _default_interface
    if _default_interface is None:
        _default_interface = ChainInterface()
    return _default_interface


def configure_chain_interface(
    endpoint: str = DEFAULT_CHAIN_ENDPOINT,
    secret_key: str | None = None,
    mediator_id: str | None = None,
) -> ChainInterface:
    """
    Configure and return the default chain interface.

    Args:
        endpoint: Chain API endpoint
        secret_key: HMAC secret key
        mediator_id: Mediator identifier

    Returns:
        Configured chain interface
    """
    global _default_interface
    _default_interface = ChainInterface(
        endpoint=endpoint, secret_key=secret_key, mediator_id=mediator_id
    )
    return _default_interface


def reset_chain_interface():
    """Reset the default chain interface (useful for testing)."""
    global _default_interface
    _default_interface = None
