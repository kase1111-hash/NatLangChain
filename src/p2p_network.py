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
            "failed_connections": 0
        }

        logger.info(f"P2P Network initialized: node_id={self.node_id}, role={role.value}")

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
        Connect to a peer node.

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
                peer_info = PeerInfo(
                    peer_id=data.get("node_id", secrets.token_hex(8)),
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

                # Don't connect to ourselves
                if peer_info.peer_id == self.node_id:
                    return False, None

                # Don't connect to banned peers
                if peer_info.peer_id in self.banned_peers:
                    return False, None

                self.peers[peer_info.peer_id] = peer_info

                # Register ourselves with the peer
                self._register_with_peer(peer_info)

                logger.info(f"Connected to peer: {peer_info.peer_id} at {endpoint}")
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
        except:
            pass
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

    def handle_broadcast(self, message_data: Dict[str, Any]) -> bool:
        """
        Handle an incoming broadcast message.

        Args:
            message_data: Incoming message data

        Returns:
            True if message was processed
        """
        try:
            message = BroadcastMessage.from_dict(message_data)
        except Exception as e:
            logger.error(f"Invalid broadcast message: {e}")
            return False

        # Check for duplicate
        if message.message_id in self.seen_messages:
            return False

        # Mark as seen
        self.seen_messages[message.message_id] = datetime.utcnow()
        self.stats["messages_received"] += 1

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

        # Forward if TTL > 0
        if message.ttl > 0:
            message.ttl -= 1
            self._forward_broadcast(message)

        return True

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
            except:
                pass

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
