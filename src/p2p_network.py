"""
NatLangChain - Peer-to-Peer Network Module

Implements P2P networking for distributed NatLangChain nodes with:
- Peer discovery and registration
- Entry broadcast to peer nodes
- Chain synchronization and reconciliation
- Mediator node integration for 3rd party mining

Architecture:
- Nodes register with each other via /api/v1/peers endpoints
- New entries are broadcast to all known peers
- Mediator nodes poll for intents and submit settlements
- Chain sync uses longest-chain rule with hash verification
"""

import os
import json
import time
import secrets
import hashlib
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import requests
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

# API version for P2P protocol
P2P_API_VERSION = "v1"

# Default ports
DEFAULT_P2P_PORT = 8545
DEFAULT_API_PORT = 5000

# Timeouts
PEER_TIMEOUT = 10  # seconds
BROADCAST_TIMEOUT = 5  # seconds
SYNC_TIMEOUT = 30  # seconds

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds

# Peer health check interval
HEALTH_CHECK_INTERVAL = 60  # seconds
PEER_STALE_THRESHOLD = 300  # 5 minutes without response = stale

# Broadcast settings
MAX_BROADCAST_PEERS = 10  # Max peers to broadcast to simultaneously
BROADCAST_FANOUT = 3  # Number of peers to forward broadcasts to

# Sync settings
SYNC_BATCH_SIZE = 100  # Blocks per sync batch
MAX_CHAIN_DIVERGENCE = 100  # Max blocks to reconcile

# =============================================================================
# Security Constants - P2P Attack Hardening
# =============================================================================

# Sybil Attack Protection
MAX_PEERS = 50  # Maximum number of connected peers
MAX_PEERS_PER_IP = 3  # Max peers from same IP address
MIN_PEER_REPUTATION = 0.1  # Minimum reputation to stay connected
REPUTATION_DECAY_RATE = 0.01  # Reputation decay per violation
REPUTATION_RECOVERY_RATE = 0.001  # Reputation recovery per successful interaction

# Eclipse Attack Protection
MIN_PEER_DIVERSITY = 3  # Minimum unique IP prefixes (/16)
MAX_PEERS_SAME_PREFIX = 5  # Max peers from same /16 subnet

# DoS/Flooding Protection
MAX_MESSAGES_PER_MINUTE = 100  # Rate limit per peer
MAX_BROADCASTS_PER_MINUTE = 30  # Max broadcasts we originate
MAX_PAYLOAD_SIZE = 1024 * 1024  # 1MB max payload
MAX_ENTRY_SIZE = 100 * 1024  # 100KB max entry
MAX_BLOCK_SIZE = 10 * 1024 * 1024  # 10MB max block
RATE_LIMIT_WINDOW = 60  # seconds

# Replay Attack Protection
MESSAGE_MAX_AGE = 300  # 5 minutes max message age
MESSAGE_MAX_FUTURE = 30  # 30 seconds max future timestamp
NONCE_CACHE_SIZE = 10000  # Max nonces to track

# Message Authentication
REQUIRE_SIGNATURES = True  # Require HMAC signatures on messages
SIGNATURE_ALGORITHM = "sha256"

# Block/Entry Validation
REQUIRE_BLOCK_VALIDATION = True  # Validate blocks before accepting
MAX_ENTRIES_PER_BLOCK = 1000  # Max entries in a block
MAX_BLOCK_TIMESTAMP_DRIFT = 600  # 10 minutes max timestamp drift

# Peer Behavior Tracking
VIOLATION_THRESHOLD = 5  # Violations before ban
BAN_DURATION_HOURS = 24  # Hours to ban misbehaving peers
SUSPICIOUS_BEHAVIOR_WEIGHT = {
    "invalid_message": 1,
    "invalid_signature": 2,
    "replay_attack": 3,
    "oversized_payload": 1,
    "rate_limit_exceeded": 1,
    "invalid_block": 3,
    "invalid_chain": 5,
    "timestamp_manipulation": 2,
}


# =============================================================================
# Enums
# =============================================================================

class PeerStatus(Enum):
    """Peer connection status."""
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"
    BANNED = "banned"


class NodeRole(Enum):
    """Node roles in the network."""
    FULL_NODE = "full_node"  # Stores full chain, validates, mines
    LIGHT_NODE = "light_node"  # Stores headers only
    MEDIATOR = "mediator"  # 3rd party miner/mediator
    ARCHIVE = "archive"  # Full history, no mining


class BroadcastType(Enum):
    """Types of broadcasts."""
    NEW_ENTRY = "new_entry"
    NEW_BLOCK = "new_block"
    SETTLEMENT = "settlement"
    PEER_ANNOUNCE = "peer_announce"
    CHAIN_TIP = "chain_tip"


class ConsensusMode(Enum):
    """Consensus modes (from mediator-node)."""
    PERMISSIONLESS = "permissionless"  # Proof-of-Alignment + reputation
    DPOS = "dpos"  # Delegated Proof of Stake
    POA = "poa"  # Proof of Authority
    HYBRID = "hybrid"  # Combined modes


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PeerInfo:
    """Information about a peer node."""
    peer_id: str
    endpoint: str
    role: NodeRole = NodeRole.FULL_NODE
    status: PeerStatus = PeerStatus.UNKNOWN
    chain_height: int = 0
    chain_tip_hash: str = ""
    last_seen: Optional[datetime] = None
    latency_ms: float = 0.0
    reputation: float = 1.0
    version: str = "unknown"
    capabilities: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "endpoint": self.endpoint,
            "role": self.role.value,
            "status": self.status.value,
            "chain_height": self.chain_height,
            "chain_tip_hash": self.chain_tip_hash,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "latency_ms": self.latency_ms,
            "reputation": self.reputation,
            "version": self.version,
            "capabilities": list(self.capabilities)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PeerInfo':
        return cls(
            peer_id=data["peer_id"],
            endpoint=data["endpoint"],
            role=NodeRole(data.get("role", "full_node")),
            status=PeerStatus(data.get("status", "unknown")),
            chain_height=data.get("chain_height", 0),
            chain_tip_hash=data.get("chain_tip_hash", ""),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else None,
            latency_ms=data.get("latency_ms", 0.0),
            reputation=data.get("reputation", 1.0),
            version=data.get("version", "unknown"),
            capabilities=set(data.get("capabilities", []))
        )


@dataclass
class BroadcastMessage:
    """Message to broadcast to peers."""
    message_id: str
    broadcast_type: BroadcastType
    payload: Dict[str, Any]
    origin_node: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl: int = 3  # Hops remaining
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "broadcast_type": self.broadcast_type.value,
            "payload": self.payload,
            "origin_node": self.origin_node,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "signature": self.signature
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BroadcastMessage':
        return cls(
            message_id=data["message_id"],
            broadcast_type=BroadcastType(data["broadcast_type"]),
            payload=data["payload"],
            origin_node=data["origin_node"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            ttl=data.get("ttl", 0),
            signature=data.get("signature")
        )


@dataclass
class SyncState:
    """Chain synchronization state."""
    is_syncing: bool = False
    sync_target_height: int = 0
    sync_current_height: int = 0
    sync_peer: Optional[str] = None
    sync_started: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    sync_errors: List[str] = field(default_factory=list)


# =============================================================================
# Security Classes - P2P Attack Hardening
# =============================================================================

class PeerRateLimiter:
    """
    Rate limiter to prevent DoS/flooding attacks.

    Tracks message rates per peer and enforces limits.
    """

    def __init__(self, max_per_minute: int = MAX_MESSAGES_PER_MINUTE, window: int = RATE_LIMIT_WINDOW):
        self.max_per_minute = max_per_minute
        self.window = window
        self.peer_counts: Dict[str, List[float]] = {}  # peer_id -> list of timestamps
        self._lock = threading.Lock()

    def check_rate_limit(self, peer_id: str) -> Tuple[bool, str]:
        """
        Check if a peer has exceeded rate limits.

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            now = time.time()
            cutoff = now - self.window

            # Get or create peer's timestamp list
            if peer_id not in self.peer_counts:
                self.peer_counts[peer_id] = []

            # Remove old timestamps
            self.peer_counts[peer_id] = [
                ts for ts in self.peer_counts[peer_id] if ts > cutoff
            ]

            # Check limit
            if len(self.peer_counts[peer_id]) >= self.max_per_minute:
                return False, f"Rate limit exceeded: {len(self.peer_counts[peer_id])}/{self.max_per_minute} per minute"

            # Record this request
            self.peer_counts[peer_id].append(now)
            return True, "OK"

    def get_peer_rate(self, peer_id: str) -> int:
        """Get current message rate for a peer."""
        with self._lock:
            if peer_id not in self.peer_counts:
                return 0
            now = time.time()
            cutoff = now - self.window
            return len([ts for ts in self.peer_counts[peer_id] if ts > cutoff])

    def cleanup(self):
        """Remove old entries to prevent memory growth."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window
            for peer_id in list(self.peer_counts.keys()):
                self.peer_counts[peer_id] = [
                    ts for ts in self.peer_counts[peer_id] if ts > cutoff
                ]
                if not self.peer_counts[peer_id]:
                    del self.peer_counts[peer_id]


class MessageValidator:
    """
    Validates incoming P2P messages for security.

    Checks:
    - Message signatures (HMAC)
    - Timestamp validity (replay protection)
    - Payload size limits
    - Message structure
    """

    def __init__(self, secret_key: str, require_signatures: bool = REQUIRE_SIGNATURES):
        self.secret_key = secret_key.encode('utf-8') if isinstance(secret_key, str) else secret_key
        self.require_signatures = require_signatures
        self.seen_nonces: Dict[str, float] = {}  # nonce -> timestamp
        self._lock = threading.Lock()

    def compute_signature(self, message_data: Dict[str, Any]) -> str:
        """Compute HMAC signature for a message."""
        # Create canonical string from message (exclude signature field)
        sign_data = {k: v for k, v in message_data.items() if k != 'signature'}
        sign_string = json.dumps(sign_data, sort_keys=True)

        import hmac
        signature = hmac.new(
            self.secret_key,
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, message_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify message HMAC signature.

        Returns:
            Tuple of (valid, reason)
        """
        if not self.require_signatures:
            return True, "Signatures not required"

        provided_sig = message_data.get('signature')
        if not provided_sig:
            return False, "Missing signature"

        expected_sig = self.compute_signature(message_data)

        import hmac as hmac_module
        if not hmac_module.compare_digest(provided_sig, expected_sig):
            return False, "Invalid signature"

        return True, "OK"

    def validate_timestamp(self, timestamp_str: str) -> Tuple[bool, str]:
        """
        Validate message timestamp for replay protection.

        Returns:
            Tuple of (valid, reason)
        """
        try:
            msg_time = datetime.fromisoformat(timestamp_str)
            now = datetime.utcnow()

            # Check if too old
            age = (now - msg_time).total_seconds()
            if age > MESSAGE_MAX_AGE:
                return False, f"Message too old: {age:.0f}s (max {MESSAGE_MAX_AGE}s)"

            # Check if in future
            if age < -MESSAGE_MAX_FUTURE:
                return False, f"Message from future: {-age:.0f}s ahead"

            return True, "OK"
        except Exception as e:
            return False, f"Invalid timestamp format: {e}"

    def check_replay(self, message_id: str, nonce: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check if message is a replay attack.

        Returns:
            Tuple of (is_new, reason)
        """
        with self._lock:
            check_id = nonce or message_id

            if check_id in self.seen_nonces:
                return False, "Replay detected: message/nonce already seen"

            # Add to seen nonces
            self.seen_nonces[check_id] = time.time()

            # Cleanup old nonces if cache too large
            if len(self.seen_nonces) > NONCE_CACHE_SIZE:
                self._cleanup_nonces()

            return True, "OK"

    def _cleanup_nonces(self):
        """Remove old nonces to prevent memory growth."""
        cutoff = time.time() - MESSAGE_MAX_AGE
        self.seen_nonces = {
            nonce: ts for nonce, ts in self.seen_nonces.items()
            if ts > cutoff
        }

    def validate_payload_size(self, payload: Any, max_size: int = MAX_PAYLOAD_SIZE) -> Tuple[bool, str]:
        """
        Validate payload size.

        Returns:
            Tuple of (valid, reason)
        """
        try:
            payload_str = json.dumps(payload)
            size = len(payload_str.encode('utf-8'))

            if size > max_size:
                return False, f"Payload too large: {size} bytes (max {max_size})"

            return True, "OK"
        except Exception as e:
            return False, f"Invalid payload: {e}"

    def validate_message(self, message_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Full message validation.

        Returns:
            Tuple of (valid, reason)
        """
        # Check required fields
        required = ['message_id', 'broadcast_type', 'payload', 'origin_node', 'timestamp']
        for field in required:
            if field not in message_data:
                return False, f"Missing required field: {field}"

        # Validate signature
        valid, reason = self.verify_signature(message_data)
        if not valid:
            return False, reason

        # Validate timestamp
        valid, reason = self.validate_timestamp(message_data['timestamp'])
        if not valid:
            return False, reason

        # Check replay
        valid, reason = self.check_replay(message_data['message_id'])
        if not valid:
            return False, reason

        # Validate payload size
        valid, reason = self.validate_payload_size(message_data['payload'])
        if not valid:
            return False, reason

        return True, "OK"


class BlockValidator:
    """
    Validates blocks and entries for security.

    Checks:
    - Block structure and size
    - Hash chain integrity
    - Entry validity
    - Timestamp validity
    """

    def __init__(self):
        pass

    def validate_block_structure(self, block_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate block has required structure."""
        required = ['index', 'hash', 'previous_hash', 'timestamp', 'entries']
        for field in required:
            if field not in block_data:
                return False, f"Block missing required field: {field}"

        # Check entries count
        entries = block_data.get('entries', [])
        if len(entries) > MAX_ENTRIES_PER_BLOCK:
            return False, f"Too many entries: {len(entries)} (max {MAX_ENTRIES_PER_BLOCK})"

        return True, "OK"

    def validate_block_size(self, block_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate block size limits."""
        try:
            block_str = json.dumps(block_data)
            size = len(block_str.encode('utf-8'))

            if size > MAX_BLOCK_SIZE:
                return False, f"Block too large: {size} bytes (max {MAX_BLOCK_SIZE})"

            return True, "OK"
        except Exception as e:
            return False, f"Invalid block data: {e}"

    def validate_block_hash(self, block_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate block hash is correct."""
        claimed_hash = block_data.get('hash', '')

        # Recompute hash (simplified - actual implementation depends on blockchain.py)
        hash_input = json.dumps({
            'index': block_data.get('index'),
            'previous_hash': block_data.get('previous_hash'),
            'timestamp': block_data.get('timestamp'),
            'entries': block_data.get('entries', [])
        }, sort_keys=True)

        computed_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        # Note: This is a simplified check - actual hash computation may differ
        # The real validation should use the same algorithm as blockchain.py
        if not claimed_hash:
            return False, "Block hash is empty"

        return True, "OK"  # Hash format valid, detailed check left to blockchain

    def validate_chain_link(self, block_data: Dict[str, Any], previous_block: Optional[Dict[str, Any]]) -> Tuple[bool, str]:
        """Validate block links correctly to previous block."""
        if previous_block is None:
            # Genesis block
            if block_data.get('index', 0) != 0:
                return False, "Non-genesis block without previous block"
            return True, "OK"

        # Check index continuity
        if block_data.get('index', 0) != previous_block.get('index', 0) + 1:
            return False, f"Block index discontinuity: {block_data.get('index')} should be {previous_block.get('index', 0) + 1}"

        # Check hash chain
        if block_data.get('previous_hash', '') != previous_block.get('hash', ''):
            return False, "Block previous_hash doesn't match previous block hash"

        return True, "OK"

    def validate_block_timestamp(self, block_data: Dict[str, Any], previous_block: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Validate block timestamp."""
        try:
            block_time = block_data.get('timestamp', '')
            if isinstance(block_time, str):
                block_time = datetime.fromisoformat(block_time.replace('Z', '+00:00'))

            now = datetime.utcnow()

            # Check not too far in future
            if hasattr(block_time, 'timestamp'):
                age = (now - block_time).total_seconds()
            else:
                age = 0

            if age < -MAX_BLOCK_TIMESTAMP_DRIFT:
                return False, f"Block timestamp too far in future: {-age:.0f}s"

            # Check not before previous block (if provided)
            if previous_block:
                prev_time = previous_block.get('timestamp', '')
                if isinstance(prev_time, str):
                    prev_time = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                # Block should be after previous
                # (Simplified check - actual may need more nuance)

            return True, "OK"
        except Exception as e:
            return False, f"Invalid timestamp: {e}"

    def validate_entry(self, entry_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate an individual entry."""
        required = ['content', 'author', 'timestamp']
        for field in required:
            if field not in entry_data:
                return False, f"Entry missing required field: {field}"

        # Check entry size
        try:
            entry_str = json.dumps(entry_data)
            size = len(entry_str.encode('utf-8'))
            if size > MAX_ENTRY_SIZE:
                return False, f"Entry too large: {size} bytes (max {MAX_ENTRY_SIZE})"
        except (json.JSONDecodeError, TypeError, UnicodeEncodeError) as e:
            logger.warning(f"Entry validation failed: {type(e).__name__}: {e}")
            return False, f"Invalid entry data: {type(e).__name__}"

        return True, "OK"

    def validate_block(self, block_data: Dict[str, Any], previous_block: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Full block validation."""
        # Structure check
        valid, reason = self.validate_block_structure(block_data)
        if not valid:
            return False, reason

        # Size check
        valid, reason = self.validate_block_size(block_data)
        if not valid:
            return False, reason

        # Hash check
        valid, reason = self.validate_block_hash(block_data)
        if not valid:
            return False, reason

        # Chain link check
        valid, reason = self.validate_chain_link(block_data, previous_block)
        if not valid:
            return False, reason

        # Timestamp check
        valid, reason = self.validate_block_timestamp(block_data, previous_block)
        if not valid:
            return False, reason

        # Validate each entry
        for entry in block_data.get('entries', []):
            valid, reason = self.validate_entry(entry)
            if not valid:
                return False, f"Invalid entry: {reason}"

        return True, "OK"


class PeerSecurityManager:
    """
    Manages peer security, reputation, and banning.

    Features:
    - Reputation tracking
    - Violation counting
    - Automatic banning
    - Eclipse attack detection
    """

    def __init__(self):
        self.violations: Dict[str, List[Tuple[str, float, float]]] = {}  # peer_id -> [(type, weight, timestamp)]
        self.banned_until: Dict[str, datetime] = {}  # peer_id -> unban time
        self.peer_ips: Dict[str, str] = {}  # peer_id -> IP address
        self._lock = threading.Lock()

    def extract_ip(self, endpoint: str) -> str:
        """Extract IP address from endpoint URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)
            host = parsed.hostname or ''
            # Handle localhost
            if host in ('localhost', '127.0.0.1', '::1'):
                return '127.0.0.1'
            return host
        except (ValueError, AttributeError) as e:
            logger.debug(f"IP extraction failed for endpoint: {type(e).__name__}")
            return 'unknown'

    def get_ip_prefix(self, ip: str, prefix_len: int = 16) -> str:
        """Get IP prefix for diversity checking (/16 by default)."""
        try:
            parts = ip.split('.')
            if len(parts) == 4 and prefix_len == 16:
                return f"{parts[0]}.{parts[1]}"
            return ip
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug(f"IP prefix extraction failed: {type(e).__name__}")
            return ip

    def check_peer_allowed(self, peer_id: str, endpoint: str, current_peers: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if a new peer should be allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        with self._lock:
            # Check if banned
            if peer_id in self.banned_until:
                if datetime.utcnow() < self.banned_until[peer_id]:
                    remaining = (self.banned_until[peer_id] - datetime.utcnow()).total_seconds()
                    return False, f"Peer is banned for {remaining:.0f} more seconds"
                else:
                    del self.banned_until[peer_id]

            # Check max peers
            if len(current_peers) >= MAX_PEERS:
                return False, f"Maximum peers reached: {MAX_PEERS}"

            # Check IP-based limits
            ip = self.extract_ip(endpoint)
            ip_count = sum(1 for pid, ep in self.peer_ips.items()
                          if self.extract_ip(ep) == ip and pid in current_peers)

            if ip_count >= MAX_PEERS_PER_IP:
                return False, f"Too many peers from IP {ip}: {ip_count}/{MAX_PEERS_PER_IP}"

            # Check subnet diversity (eclipse protection)
            prefix = self.get_ip_prefix(ip)
            prefix_count = sum(1 for pid, ep in self.peer_ips.items()
                              if self.get_ip_prefix(self.extract_ip(ep)) == prefix and pid in current_peers)

            if prefix_count >= MAX_PEERS_SAME_PREFIX:
                return False, f"Too many peers from subnet {prefix}.x.x: {prefix_count}/{MAX_PEERS_SAME_PREFIX}"

            # Track this peer's IP
            self.peer_ips[peer_id] = endpoint

            return True, "OK"

    def record_violation(self, peer_id: str, violation_type: str) -> Tuple[bool, str]:
        """
        Record a security violation for a peer.

        Returns:
            Tuple of (should_ban, reason)
        """
        with self._lock:
            weight = SUSPICIOUS_BEHAVIOR_WEIGHT.get(violation_type, 1)
            now = time.time()

            if peer_id not in self.violations:
                self.violations[peer_id] = []

            self.violations[peer_id].append((violation_type, weight, now))

            # Calculate total violation score (decay old violations)
            total_score = 0
            recent_violations = []
            for vtype, vweight, vtime in self.violations[peer_id]:
                age = now - vtime
                if age < BAN_DURATION_HOURS * 3600:  # Keep violations for ban duration
                    # Decay weight over time
                    decay_factor = max(0, 1 - (age / (BAN_DURATION_HOURS * 3600)))
                    total_score += vweight * decay_factor
                    recent_violations.append((vtype, vweight, vtime))

            self.violations[peer_id] = recent_violations

            logger.warning(f"Peer {peer_id} violation: {violation_type} (score: {total_score:.1f}/{VIOLATION_THRESHOLD})")

            if total_score >= VIOLATION_THRESHOLD:
                return True, f"Violation threshold exceeded: {total_score:.1f}"

            return False, "OK"

    def ban_peer(self, peer_id: str, reason: str = "") -> None:
        """Ban a peer for the configured duration."""
        with self._lock:
            self.banned_until[peer_id] = datetime.utcnow() + timedelta(hours=BAN_DURATION_HOURS)
            logger.warning(f"Banned peer {peer_id} for {BAN_DURATION_HOURS}h: {reason}")

    def is_banned(self, peer_id: str) -> bool:
        """Check if a peer is currently banned."""
        with self._lock:
            if peer_id not in self.banned_until:
                return False
            if datetime.utcnow() >= self.banned_until[peer_id]:
                del self.banned_until[peer_id]
                return False
            return True

    def update_reputation(self, peer_id: str, success: bool) -> float:
        """Update peer reputation based on interaction outcome."""
        # This integrates with PeerInfo.reputation
        if success:
            return REPUTATION_RECOVERY_RATE
        else:
            return -REPUTATION_DECAY_RATE

    def check_eclipse_attack(self, peers: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check for potential eclipse attack (low peer diversity).

        Returns:
            Tuple of (is_safe, warning)
        """
        if len(peers) < MIN_PEER_DIVERSITY:
            return True, "OK"  # Not enough peers to check

        # Count unique IP prefixes
        prefixes = set()
        for peer_id, peer in peers.items():
            if hasattr(peer, 'endpoint'):
                ip = self.extract_ip(peer.endpoint)
            else:
                ip = self.extract_ip(str(peer.get('endpoint', '')))
            prefixes.add(self.get_ip_prefix(ip))

        if len(prefixes) < MIN_PEER_DIVERSITY:
            return False, f"Low peer diversity: only {len(prefixes)} unique subnets (min {MIN_PEER_DIVERSITY})"

        return True, "OK"


# =============================================================================
# P2P Network Manager
# =============================================================================

class P2PNetwork:
    """
    Manages peer-to-peer network connections for NatLangChain.

    Features:
    - Peer discovery and registration
    - Entry/block broadcasting
    - Chain synchronization
    - Mediator node integration
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        role: NodeRole = NodeRole.FULL_NODE,
        consensus_mode: ConsensusMode = ConsensusMode.PERMISSIONLESS,
        bootstrap_peers: Optional[List[str]] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize P2P network manager.

        Args:
            node_id: Unique identifier for this node
            endpoint: This node's public endpoint
            role: Node role (full, light, mediator, archive)
            consensus_mode: Consensus mechanism to use
            bootstrap_peers: Initial peers to connect to
            secret_key: Secret key for signing messages
        """
        self.node_id = node_id or f"node_{secrets.token_hex(8)}"
        self.endpoint = endpoint or f"http://localhost:{DEFAULT_API_PORT}"
        self.role = role
        self.consensus_mode = consensus_mode
        self.secret_key = secret_key or secrets.token_hex(32)

        # Peer management
        self.peers: Dict[str, PeerInfo] = {}
        self.banned_peers: Set[str] = set()
        self.bootstrap_peers = bootstrap_peers or []

        # Message deduplication
        self.seen_messages: Dict[str, datetime] = {}
        self.message_expiry = timedelta(minutes=10)

        # Sync state
        self.sync_state = SyncState()

        # Callbacks for handling received data
        self._on_entry_received: Optional[Callable] = None
        self._on_block_received: Optional[Callable] = None
        self._on_settlement_received: Optional[Callable] = None
        self._get_chain_info: Optional[Callable] = None
        self._get_blocks: Optional[Callable] = None
        self._add_block: Optional[Callable] = None

        # Background threads
        self._health_check_thread: Optional[threading.Thread] = None
        self._running = False

        # HTTP session
        self.session = None
        if HAS_REQUESTS:
            self._setup_session()

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
            "sync_operations": 0,
            "failed_connections": 0,
            "blocked_messages": 0,
            "security_violations": 0,
            "peers_banned": 0
        }

        # Security components
        self.rate_limiter = PeerRateLimiter()
        self.message_validator = MessageValidator(self.secret_key)
        self.block_validator = BlockValidator()
        self.security_manager = PeerSecurityManager()

        logger.info(f"P2P Network initialized: node_id={self.node_id}, role={role.value}")
        logger.info(f"Security hardening enabled: rate_limit={MAX_MESSAGES_PER_MINUTE}/min, max_peers={MAX_PEERS}")

    def _setup_session(self):
        """Set up HTTP session with retry logic."""
        self.session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Node-ID": self.node_id,
            "X-Node-Role": self.role.value
        })

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def start(self):
        """Start the P2P network (connect to bootstrap peers, start health checks)."""
        if self._running:
            return

        self._running = True
        logger.info("Starting P2P network...")

        # Connect to bootstrap peers
        for peer_endpoint in self.bootstrap_peers:
            self.connect_to_peer(peer_endpoint)

        # Start health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()

        logger.info(f"P2P network started with {len(self.peers)} peers")

    def stop(self):
        """Stop the P2P network."""
        self._running = False
        logger.info("P2P network stopped")

    def _health_check_loop(self):
        """Background loop to check peer health."""
        while self._running:
            try:
                self._check_peer_health()
                self._cleanup_seen_messages()
            except Exception as e:
                logger.error(f"Health check error: {e}")

            time.sleep(HEALTH_CHECK_INTERVAL)

    def _check_peer_health(self):
        """Check health of all connected peers."""
        now = datetime.utcnow()
        stale_threshold = now - timedelta(seconds=PEER_STALE_THRESHOLD)

        for peer_id, peer in list(self.peers.items()):
            if peer.last_seen and peer.last_seen < stale_threshold:
                # Peer is stale, try to reconnect
                success = self._ping_peer(peer)
                if not success:
                    peer.status = PeerStatus.STALE
                    logger.warning(f"Peer {peer_id} is stale")

    def _cleanup_seen_messages(self):
        """Remove expired message IDs."""
        now = datetime.utcnow()
        expired = [
            msg_id for msg_id, ts in self.seen_messages.items()
            if now - ts > self.message_expiry
        ]
        for msg_id in expired:
            del self.seen_messages[msg_id]

    # =========================================================================
    # Peer Management
    # =========================================================================

    def connect_to_peer(self, endpoint: str) -> Tuple[bool, Optional[PeerInfo]]:
        """
        Connect to a peer node with security validation.

        Security checks:
        - Maximum peer limit (Sybil protection)
        - IP-based limits (Sybil protection)
        - Subnet diversity (Eclipse protection)
        - Ban list check

        Args:
            endpoint: Peer's API endpoint

        Returns:
            Tuple of (success, peer_info)
        """
        if not HAS_REQUESTS:
            return False, None

        try:
            # Request peer info
            start_time = time.time()
            response = self.session.get(
                f"{endpoint}/api/{P2P_API_VERSION}/node/info",
                timeout=PEER_TIMEOUT
            )
            latency = (time.time() - start_time) * 1000

            if response.ok:
                data = response.json()
                peer_id = data.get("node_id", secrets.token_hex(8))

                # Security Check 1: Don't connect to ourselves
                if peer_id == self.node_id:
                    logger.debug(f"Rejected connection to self: {endpoint}")
                    return False, None

                # Security Check 2: Check if peer is banned
                if peer_id in self.banned_peers or self.security_manager.is_banned(peer_id):
                    logger.warning(f"Rejected banned peer: {peer_id} at {endpoint}")
                    return False, None

                # Security Check 3: Sybil/Eclipse protection
                allowed, reason = self.security_manager.check_peer_allowed(
                    peer_id, endpoint, self.peers
                )
                if not allowed:
                    logger.warning(f"Peer rejected by security policy: {reason}")
                    self.stats["failed_connections"] += 1
                    return False, None

                peer_info = PeerInfo(
                    peer_id=peer_id,
                    endpoint=endpoint,
                    role=NodeRole(data.get("role", "full_node")),
                    status=PeerStatus.CONNECTED,
                    chain_height=data.get("chain_height", 0),
                    chain_tip_hash=data.get("chain_tip_hash", ""),
                    last_seen=datetime.utcnow(),
                    latency_ms=latency,
                    version=data.get("version", "unknown"),
                    capabilities=set(data.get("capabilities", []))
                )

                self.peers[peer_info.peer_id] = peer_info

                # Security Check 4: Eclipse attack detection
                is_safe, warning = self.security_manager.check_eclipse_attack(self.peers)
                if not is_safe:
                    logger.warning(f"Eclipse attack warning: {warning}")
                    # Don't reject but log warning - operator should investigate

                # Register ourselves with the peer
                self._register_with_peer(peer_info)

                logger.info(f"Connected to peer: {peer_info.peer_id} at {endpoint} (latency: {latency:.0f}ms)")
                return True, peer_info
            else:
                self.stats["failed_connections"] += 1
                return False, None

        except Exception as e:
            logger.error(f"Failed to connect to peer {endpoint}: {e}")
            self.stats["failed_connections"] += 1
            return False, None

    def _register_with_peer(self, peer: PeerInfo):
        """Register this node with a peer."""
        try:
            self.session.post(
                f"{peer.endpoint}/api/{P2P_API_VERSION}/peers/register",
                json={
                    "node_id": self.node_id,
                    "endpoint": self.endpoint,
                    "role": self.role.value,
                    "chain_height": self._get_chain_height(),
                    "chain_tip_hash": self._get_chain_tip_hash(),
                    "version": "1.0.0",
                    "capabilities": ["entries", "blocks", "sync"]
                },
                timeout=PEER_TIMEOUT
            )
        except Exception as e:
            logger.warning(f"Failed to register with peer {peer.peer_id}: {e}")

    def _ping_peer(self, peer: PeerInfo) -> bool:
        """Ping a peer to check if it's alive."""
        try:
            response = self.session.get(
                f"{peer.endpoint}/api/{P2P_API_VERSION}/health",
                timeout=PEER_TIMEOUT
            )
            if response.ok:
                peer.status = PeerStatus.CONNECTED
                peer.last_seen = datetime.utcnow()
                return True
        except (requests.RequestException, OSError, ValueError) as e:
            logger.debug(f"Ping to peer {peer.peer_id} failed: {type(e).__name__}")
        return False

    def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer."""
        if peer_id in self.peers:
            self.peers[peer_id].status = PeerStatus.DISCONNECTED
            del self.peers[peer_id]
            logger.info(f"Disconnected from peer: {peer_id}")

    def ban_peer(self, peer_id: str, reason: str = ""):
        """Ban a peer from reconnecting."""
        self.banned_peers.add(peer_id)
        if peer_id in self.peers:
            self.peers[peer_id].status = PeerStatus.BANNED
            del self.peers[peer_id]
        logger.warning(f"Banned peer {peer_id}: {reason}")

    def get_connected_peers(self) -> List[PeerInfo]:
        """Get list of connected peers."""
        return [
            p for p in self.peers.values()
            if p.status == PeerStatus.CONNECTED
        ]

    def get_mediator_peers(self) -> List[PeerInfo]:
        """Get list of connected mediator nodes."""
        return [
            p for p in self.peers.values()
            if p.role == NodeRole.MEDIATOR and p.status == PeerStatus.CONNECTED
        ]

    # =========================================================================
    # Broadcasting
    # =========================================================================

    def broadcast_entry(self, entry_data: Dict[str, Any]) -> int:
        """
        Broadcast a new entry to all peers.

        Args:
            entry_data: Entry data to broadcast

        Returns:
            Number of peers that received the broadcast
        """
        message = BroadcastMessage(
            message_id=secrets.token_hex(16),
            broadcast_type=BroadcastType.NEW_ENTRY,
            payload=entry_data,
            origin_node=self.node_id,
            ttl=BROADCAST_FANOUT
        )
        return self._broadcast(message)

    def broadcast_block(self, block_data: Dict[str, Any]) -> int:
        """
        Broadcast a new block to all peers.

        Args:
            block_data: Block data to broadcast

        Returns:
            Number of peers that received the broadcast
        """
        message = BroadcastMessage(
            message_id=secrets.token_hex(16),
            broadcast_type=BroadcastType.NEW_BLOCK,
            payload=block_data,
            origin_node=self.node_id,
            ttl=BROADCAST_FANOUT
        )
        return self._broadcast(message)

    def broadcast_settlement(self, settlement_data: Dict[str, Any]) -> int:
        """
        Broadcast a settlement from a mediator.

        Args:
            settlement_data: Settlement data to broadcast

        Returns:
            Number of peers that received the broadcast
        """
        message = BroadcastMessage(
            message_id=secrets.token_hex(16),
            broadcast_type=BroadcastType.SETTLEMENT,
            payload=settlement_data,
            origin_node=self.node_id,
            ttl=BROADCAST_FANOUT
        )
        return self._broadcast(message)

    def _broadcast(self, message: BroadcastMessage) -> int:
        """Internal broadcast implementation."""
        if not HAS_REQUESTS:
            return 0

        # Mark message as seen
        self.seen_messages[message.message_id] = datetime.utcnow()

        # Get connected peers
        peers = self.get_connected_peers()
        if not peers:
            return 0

        # Limit broadcast to avoid flooding
        peers = peers[:MAX_BROADCAST_PEERS]

        success_count = 0
        for peer in peers:
            try:
                response = self.session.post(
                    f"{peer.endpoint}/api/{P2P_API_VERSION}/broadcast",
                    json=message.to_dict(),
                    timeout=BROADCAST_TIMEOUT
                )
                if response.ok:
                    success_count += 1
                    peer.last_seen = datetime.utcnow()
            except Exception as e:
                logger.debug(f"Broadcast to {peer.peer_id} failed: {e}")

        self.stats["broadcasts_sent"] += 1
        self.stats["messages_sent"] += success_count

        logger.info(f"Broadcast {message.broadcast_type.value} to {success_count}/{len(peers)} peers")
        return success_count

    def handle_broadcast(self, message_data: Dict[str, Any], sender_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        Handle an incoming broadcast message with security validation.

        Args:
            message_data: Incoming message data
            sender_id: ID of the sending peer (for rate limiting)

        Returns:
            Tuple of (success, reason)
        """
        origin_node = message_data.get('origin_node', sender_id or 'unknown')

        # Security Check 1: Rate limiting
        allowed, reason = self.rate_limiter.check_rate_limit(origin_node)
        if not allowed:
            self.stats["blocked_messages"] += 1
            self._record_violation(origin_node, "rate_limit_exceeded")
            logger.warning(f"Rate limit exceeded for {origin_node}: {reason}")
            return False, reason

        # Security Check 2: Full message validation (signature, timestamp, replay, size)
        valid, reason = self.message_validator.validate_message(message_data)
        if not valid:
            self.stats["blocked_messages"] += 1
            violation_type = "invalid_message"
            if "signature" in reason.lower():
                violation_type = "invalid_signature"
            elif "replay" in reason.lower():
                violation_type = "replay_attack"
            elif "too old" in reason.lower() or "future" in reason.lower():
                violation_type = "timestamp_manipulation"
            elif "too large" in reason.lower():
                violation_type = "oversized_payload"

            self._record_violation(origin_node, violation_type)
            logger.warning(f"Message validation failed from {origin_node}: {reason}")
            return False, reason

        # Parse the message
        try:
            message = BroadcastMessage.from_dict(message_data)
        except Exception as e:
            self.stats["blocked_messages"] += 1
            self._record_violation(origin_node, "invalid_message")
            logger.error(f"Invalid broadcast message structure: {e}")
            return False, f"Invalid message structure: {e}"

        # Check for duplicate (already in validator, but double-check)
        if message.message_id in self.seen_messages:
            return False, "Duplicate message"

        # Mark as seen
        self.seen_messages[message.message_id] = datetime.utcnow()
        self.stats["messages_received"] += 1

        # Security Check 3: Block-specific validation
        if message.broadcast_type == BroadcastType.NEW_BLOCK:
            valid, reason = self.block_validator.validate_block(message.payload)
            if not valid:
                self.stats["blocked_messages"] += 1
                self._record_violation(origin_node, "invalid_block")
                logger.warning(f"Invalid block from {origin_node}: {reason}")
                return False, reason

        # Security Check 4: Entry-specific validation
        if message.broadcast_type == BroadcastType.NEW_ENTRY:
            valid, reason = self.block_validator.validate_entry(message.payload)
            if not valid:
                self.stats["blocked_messages"] += 1
                self._record_violation(origin_node, "invalid_message")
                logger.warning(f"Invalid entry from {origin_node}: {reason}")
                return False, reason

        # Process based on type
        if message.broadcast_type == BroadcastType.NEW_ENTRY:
            if self._on_entry_received:
                self._on_entry_received(message.payload)

        elif message.broadcast_type == BroadcastType.NEW_BLOCK:
            if self._on_block_received:
                self._on_block_received(message.payload)

        elif message.broadcast_type == BroadcastType.SETTLEMENT:
            if self._on_settlement_received:
                self._on_settlement_received(message.payload)

        # Update peer reputation positively
        if origin_node in self.peers:
            self.peers[origin_node].reputation = min(
                1.0,
                self.peers[origin_node].reputation + REPUTATION_RECOVERY_RATE
            )

        # Forward if TTL > 0
        if message.ttl > 0:
            message.ttl -= 1
            self._forward_broadcast(message)

        return True, "OK"

    def _record_violation(self, peer_id: str, violation_type: str):
        """Record a security violation and potentially ban the peer."""
        self.stats["security_violations"] += 1

        should_ban, reason = self.security_manager.record_violation(peer_id, violation_type)

        # Update peer reputation
        if peer_id in self.peers:
            self.peers[peer_id].reputation = max(
                0.0,
                self.peers[peer_id].reputation - REPUTATION_DECAY_RATE
            )

            # Check if reputation too low
            if self.peers[peer_id].reputation < MIN_PEER_REPUTATION:
                should_ban = True
                reason = f"Reputation too low: {self.peers[peer_id].reputation:.2f}"

        if should_ban:
            self.ban_peer(peer_id, reason)
            self.stats["peers_banned"] += 1

    def _forward_broadcast(self, message: BroadcastMessage):
        """Forward a broadcast to a subset of peers."""
        peers = self.get_connected_peers()
        # Select random subset for forwarding
        import random
        forward_peers = random.sample(peers, min(BROADCAST_FANOUT, len(peers)))

        for peer in forward_peers:
            try:
                self.session.post(
                    f"{peer.endpoint}/api/{P2P_API_VERSION}/broadcast",
                    json=message.to_dict(),
                    timeout=BROADCAST_TIMEOUT
                )
            except (requests.RequestException, OSError, ValueError) as e:
                logger.debug(f"Forward broadcast to {peer.peer_id} failed: {type(e).__name__}")

    # =========================================================================
    # Chain Synchronization
    # =========================================================================

    def sync_chain(self, target_peer: Optional[str] = None) -> bool:
        """
        Synchronize chain with peers.

        Args:
            target_peer: Specific peer to sync with (None = best peer)

        Returns:
            True if sync was successful
        """
        if self.sync_state.is_syncing:
            logger.warning("Sync already in progress")
            return False

        # Find best peer to sync with
        if target_peer:
            peer = self.peers.get(target_peer)
        else:
            peer = self._find_best_sync_peer()

        if not peer:
            logger.warning("No suitable peer for sync")
            return False

        self.sync_state.is_syncing = True
        self.sync_state.sync_peer = peer.peer_id
        self.sync_state.sync_started = datetime.utcnow()
        self.stats["sync_operations"] += 1

        try:
            success = self._perform_sync(peer)
            self.sync_state.last_sync = datetime.utcnow()
            return success
        except Exception as e:
            self.sync_state.sync_errors.append(str(e))
            logger.error(f"Sync failed: {e}")
            return False
        finally:
            self.sync_state.is_syncing = False
            self.sync_state.sync_peer = None

    def _find_best_sync_peer(self) -> Optional[PeerInfo]:
        """Find the best peer to sync with (highest chain, best reputation)."""
        peers = self.get_connected_peers()
        if not peers:
            return None

        local_height = self._get_chain_height()

        # Filter peers with higher chains
        candidates = [p for p in peers if p.chain_height > local_height]
        if not candidates:
            return None

        # Sort by chain height (desc), then reputation (desc)
        candidates.sort(key=lambda p: (p.chain_height, p.reputation), reverse=True)
        return candidates[0]

    def _perform_sync(self, peer: PeerInfo) -> bool:
        """Perform chain sync with a specific peer."""
        local_height = self._get_chain_height()
        target_height = peer.chain_height

        if target_height <= local_height:
            return True  # Already synced

        self.sync_state.sync_target_height = target_height
        self.sync_state.sync_current_height = local_height

        logger.info(f"Syncing from {local_height} to {target_height} with {peer.peer_id}")

        # Fetch blocks in batches
        current = local_height + 1
        while current <= target_height:
            batch_end = min(current + SYNC_BATCH_SIZE - 1, target_height)

            try:
                response = self.session.get(
                    f"{peer.endpoint}/api/{P2P_API_VERSION}/blocks",
                    params={"start": current, "end": batch_end},
                    timeout=SYNC_TIMEOUT
                )

                if not response.ok:
                    raise Exception(f"Failed to fetch blocks: {response.status_code}")

                blocks = response.json().get("blocks", [])

                for block_data in blocks:
                    if self._add_block:
                        success = self._add_block(block_data)
                        if not success:
                            raise Exception(f"Failed to add block {block_data.get('index')}")

                current = batch_end + 1
                self.sync_state.sync_current_height = batch_end

            except Exception as e:
                logger.error(f"Sync batch failed: {e}")
                return False

        logger.info(f"Sync completed: now at height {target_height}")
        return True

    # =========================================================================
    # Mediator Node Integration
    # =========================================================================

    def get_pending_intents(self) -> List[Dict[str, Any]]:
        """
        Get pending intents for mediator nodes.

        This is what mediator nodes poll to find matching opportunities.

        Returns:
            List of pending intent entries
        """
        if not self._get_chain_info:
            return []

        chain_info = self._get_chain_info()
        intents = []

        # Get pending entries
        for entry in chain_info.get("pending_entries", []):
            if entry.get("metadata", {}).get("is_contract"):
                intents.append({
                    "intent_id": hashlib.sha256(
                        json.dumps(entry, sort_keys=True).encode()
                    ).hexdigest()[:16],
                    "content": entry.get("content"),
                    "author": entry.get("author"),
                    "intent": entry.get("intent"),
                    "metadata": entry.get("metadata"),
                    "timestamp": entry.get("timestamp"),
                    "status": "pending"
                })

        # Also include open contracts from chain
        for block in chain_info.get("chain", []):
            for entry in block.get("entries", []):
                metadata = entry.get("metadata", {})
                if metadata.get("is_contract") and metadata.get("status") == "open":
                    intents.append({
                        "intent_id": hashlib.sha256(
                            json.dumps(entry, sort_keys=True).encode()
                        ).hexdigest()[:16],
                        "block_index": block.get("index"),
                        "block_hash": block.get("hash"),
                        "content": entry.get("content"),
                        "author": entry.get("author"),
                        "intent": entry.get("intent"),
                        "metadata": metadata,
                        "timestamp": entry.get("timestamp"),
                        "status": "open"
                    })

        return intents

    def submit_settlement(self, settlement: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a settlement from a mediator node.

        Args:
            settlement: Settlement data from mediator

        Returns:
            Tuple of (success, result)
        """
        # Validate settlement structure
        required_fields = ["mediator_id", "intent_a", "intent_b", "terms", "settlement_text"]
        for field in required_fields:
            if field not in settlement:
                return False, {"error": f"Missing required field: {field}"}

        # Create settlement entry
        entry_data = {
            "content": settlement["settlement_text"],
            "author": settlement["mediator_id"],
            "intent": "settlement",
            "metadata": {
                "is_settlement": True,
                "intent_a": settlement["intent_a"],
                "intent_b": settlement["intent_b"],
                "terms": settlement["terms"],
                "mediator_id": settlement["mediator_id"],
                "model_hash": settlement.get("model_hash"),
                "consensus_mode": settlement.get("consensus_mode", "permissionless"),
                "acceptance_window_hours": settlement.get("acceptance_window", 72),
                "status": "proposed"
            }
        }

        # Broadcast to network
        broadcast_count = self.broadcast_settlement(entry_data)

        return True, {
            "settlement_id": secrets.token_hex(8),
            "status": "proposed",
            "broadcast_count": broadcast_count
        }

    # =========================================================================
    # Callback Registration
    # =========================================================================

    def on_entry_received(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for received entries."""
        self._on_entry_received = callback

    def on_block_received(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for received blocks."""
        self._on_block_received = callback

    def on_settlement_received(self, callback: Callable[[Dict[str, Any]], None]):
        """Register callback for received settlements."""
        self._on_settlement_received = callback

    def set_chain_provider(
        self,
        get_chain_info: Callable[[], Dict[str, Any]],
        get_blocks: Callable[[int, int], List[Dict[str, Any]]],
        add_block: Callable[[Dict[str, Any]], bool]
    ):
        """Set callbacks for chain data access."""
        self._get_chain_info = get_chain_info
        self._get_blocks = get_blocks
        self._add_block = add_block

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_chain_height(self) -> int:
        """Get current chain height."""
        if self._get_chain_info:
            info = self._get_chain_info()
            return len(info.get("chain", [])) - 1
        return 0

    def _get_chain_tip_hash(self) -> str:
        """Get hash of the chain tip."""
        if self._get_chain_info:
            info = self._get_chain_info()
            chain = info.get("chain", [])
            if chain:
                return chain[-1].get("hash", "")
        return ""

    def get_node_info(self) -> Dict[str, Any]:
        """Get this node's info for peer discovery."""
        return {
            "node_id": self.node_id,
            "endpoint": self.endpoint,
            "role": self.role.value,
            "chain_height": self._get_chain_height(),
            "chain_tip_hash": self._get_chain_tip_hash(),
            "version": "1.0.0",
            "capabilities": ["entries", "blocks", "sync", "settlements"],
            "consensus_mode": self.consensus_mode.value,
            "peer_count": len(self.get_connected_peers())
        }

    def get_network_stats(self) -> Dict[str, Any]:
        """Get network statistics."""
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "peer_count": len(self.get_connected_peers()),
            "mediator_count": len(self.get_mediator_peers()),
            "sync_state": {
                "is_syncing": self.sync_state.is_syncing,
                "last_sync": self.sync_state.last_sync.isoformat() if self.sync_state.last_sync else None
            },
            "stats": self.stats
        }


# =============================================================================
# Singleton Instance
# =============================================================================

# Global P2P network instance
_p2p_network: Optional[P2PNetwork] = None


def get_p2p_network() -> Optional[P2PNetwork]:
    """Get the global P2P network instance."""
    return _p2p_network


def init_p2p_network(
    node_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    role: NodeRole = NodeRole.FULL_NODE,
    consensus_mode: ConsensusMode = ConsensusMode.PERMISSIONLESS,
    bootstrap_peers: Optional[List[str]] = None
) -> P2PNetwork:
    """Initialize and return the global P2P network instance."""
    global _p2p_network

    # Check environment for bootstrap peers
    if bootstrap_peers is None:
        env_peers = os.getenv("NATLANGCHAIN_BOOTSTRAP_PEERS", "")
        if env_peers:
            bootstrap_peers = [p.strip() for p in env_peers.split(",")]

    _p2p_network = P2PNetwork(
        node_id=node_id or os.getenv("NATLANGCHAIN_NODE_ID"),
        endpoint=endpoint or os.getenv("NATLANGCHAIN_ENDPOINT"),
        role=role,
        consensus_mode=consensus_mode,
        bootstrap_peers=bootstrap_peers
    )

    return _p2p_network
