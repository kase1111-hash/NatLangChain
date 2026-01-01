"""
NatLangChain - Optimized Gossip Protocol

Implements efficient epidemic gossip dissemination replacing basic flooding:
- Plumtree: Hybrid push/pull with eager and lazy peer sets
- Bloom filters: Space-efficient duplicate detection
- Adaptive fanout: Dynamic adjustment based on network conditions
- IHAVE/IWANT: Lazy push to reduce redundant transmissions
- Priority queues: Critical messages (blocks) get priority delivery
- Protocol-aware routing: Route messages based on type and content

Based on:
- Plumtree: Epidemic Broadcast Trees (Leitão et al., 2007)
- HyParView: Hybrid Partial View Membership (Leitão et al., 2007)
- Adaptive Gossip (Kermarrec et al., 2003)
"""

import hashlib
import heapq
import logging
import math
import os
import random
import secrets
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Gossip Protocol Parameters
GOSSIP_FANOUT = 4  # Number of peers to gossip to (sqrt(N) recommended)
GOSSIP_FACTOR = 2  # ln(N) + c factor for reliability
LAZY_PUSH_DELAY_MS = 100  # Delay before sending IHAVE
EAGER_PUSH_TIMEOUT_MS = 500  # Time to wait for message before requesting

# Plumtree Parameters
MAX_EAGER_PEERS = 4  # Maximum peers in eager push set
MAX_LAZY_PEERS = 10  # Maximum peers in lazy push set
GRAFT_TIMEOUT_MS = 1000  # Timeout before grafting a lazy peer
PRUNE_THRESHOLD = 3  # Duplicate messages before pruning peer

# Bloom Filter Parameters
BLOOM_SIZE_BITS = 65536  # 8KB bloom filter
BLOOM_HASH_COUNT = 7  # Number of hash functions
BLOOM_ROTATION_INTERVAL = 300  # Rotate filter every 5 minutes

# Message Priority
PRIORITY_CRITICAL = 0  # Blocks, emergencies
PRIORITY_HIGH = 1  # Settlements, consensus
PRIORITY_NORMAL = 2  # Entries, regular messages
PRIORITY_LOW = 3  # Peer announcements, heartbeats

# Adaptive Parameters
MIN_FANOUT = 2
MAX_FANOUT = 8
FANOUT_ADJUSTMENT_INTERVAL = 60  # seconds
TARGET_DELIVERY_RATIO = 0.95  # Target 95% delivery rate

# Cache Settings
MESSAGE_CACHE_SIZE = 1000  # Recent messages to cache for IWANT
MESSAGE_CACHE_TTL = 300  # 5 minutes TTL
IHAVE_BATCH_SIZE = 50  # Max message IDs per IHAVE


# =============================================================================
# Enums
# =============================================================================

class GossipMessageType(Enum):
    """Types of gossip protocol messages."""
    GOSSIP = "gossip"  # Full message push
    IHAVE = "ihave"  # Lazy push notification
    IWANT = "iwant"  # Request for message
    GRAFT = "graft"  # Request to become eager peer
    PRUNE = "prune"  # Request to become lazy peer


class MessagePriority(IntEnum):
    """Message priority levels."""
    CRITICAL = PRIORITY_CRITICAL
    HIGH = PRIORITY_HIGH
    NORMAL = PRIORITY_NORMAL
    LOW = PRIORITY_LOW


class PeerType(Enum):
    """Peer classification in Plumtree."""
    EAGER = "eager"  # Receives full messages immediately
    LAZY = "lazy"  # Receives IHAVE notifications
    UNKNOWN = "unknown"  # New peer, not classified


# =============================================================================
# Bloom Filter Implementation
# =============================================================================

class BloomFilter:
    """
    Space-efficient probabilistic set for duplicate detection.

    Uses multiple hash functions to achieve low false positive rates
    with minimal memory overhead.
    """

    def __init__(self, size_bits: int = BLOOM_SIZE_BITS, hash_count: int = BLOOM_HASH_COUNT):
        """
        Initialize bloom filter.

        Args:
            size_bits: Size of bit array
            hash_count: Number of hash functions
        """
        self.size = size_bits
        self.hash_count = hash_count
        self.bit_array = bytearray(size_bits // 8)
        self.count = 0
        self._lock = threading.Lock()

    def _get_hash_values(self, item: str) -> list[int]:
        """Generate hash values for an item using double hashing."""
        # Use SHA-256 for base hashes
        h = hashlib.sha256(item.encode()).digest()
        h1 = int.from_bytes(h[:8], 'big')
        h2 = int.from_bytes(h[8:16], 'big')

        # Generate k hash values using double hashing
        return [(h1 + i * h2) % self.size for i in range(self.hash_count)]

    def add(self, item: str) -> None:
        """Add an item to the filter."""
        with self._lock:
            for idx in self._get_hash_values(item):
                byte_idx = idx // 8
                bit_idx = idx % 8
                self.bit_array[byte_idx] |= (1 << bit_idx)
            self.count += 1

    def contains(self, item: str) -> bool:
        """Check if an item might be in the filter."""
        with self._lock:
            for idx in self._get_hash_values(item):
                byte_idx = idx // 8
                bit_idx = idx % 8
                if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                    return False
            return True

    def add_and_check(self, item: str) -> bool:
        """
        Atomically add item and return whether it was already present.

        Returns:
            True if item was already in filter (probable duplicate)
        """
        with self._lock:
            indices = self._get_hash_values(item)
            was_present = True

            for idx in indices:
                byte_idx = idx // 8
                bit_idx = idx % 8
                if not (self.bit_array[byte_idx] & (1 << bit_idx)):
                    was_present = False
                self.bit_array[byte_idx] |= (1 << bit_idx)

            if not was_present:
                self.count += 1
            return was_present

    def clear(self) -> None:
        """Clear the filter."""
        with self._lock:
            self.bit_array = bytearray(self.size // 8)
            self.count = 0

    def estimated_false_positive_rate(self) -> float:
        """Estimate current false positive rate."""
        if self.count == 0:
            return 0.0
        # FPR ≈ (1 - e^(-kn/m))^k
        exponent = -self.hash_count * self.count / self.size
        return (1 - math.exp(exponent)) ** self.hash_count

    def merge(self, other: 'BloomFilter') -> None:
        """Merge another bloom filter into this one (OR operation)."""
        if self.size != other.size:
            raise ValueError("Cannot merge filters of different sizes")
        with self._lock:
            for i in range(len(self.bit_array)):
                self.bit_array[i] |= other.bit_array[i]


class RotatingBloomFilter:
    """
    Bloom filter with automatic rotation to prevent saturation.

    Maintains current and previous filters, rotating periodically.
    """

    def __init__(
        self,
        size_bits: int = BLOOM_SIZE_BITS,
        hash_count: int = BLOOM_HASH_COUNT,
        rotation_interval: int = BLOOM_ROTATION_INTERVAL
    ):
        self.size_bits = size_bits
        self.hash_count = hash_count
        self.rotation_interval = rotation_interval

        self.current = BloomFilter(size_bits, hash_count)
        self.previous = BloomFilter(size_bits, hash_count)
        self.last_rotation = time.time()
        self._lock = threading.Lock()

    def _maybe_rotate(self) -> None:
        """Rotate filters if interval has passed."""
        now = time.time()
        if now - self.last_rotation >= self.rotation_interval:
            with self._lock:
                if now - self.last_rotation >= self.rotation_interval:
                    self.previous = self.current
                    self.current = BloomFilter(self.size_bits, self.hash_count)
                    self.last_rotation = now
                    logger.debug("Rotated bloom filter")

    def add(self, item: str) -> None:
        """Add item to current filter."""
        self._maybe_rotate()
        self.current.add(item)

    def contains(self, item: str) -> bool:
        """Check if item is in current or previous filter."""
        self._maybe_rotate()
        return self.current.contains(item) or self.previous.contains(item)

    def add_and_check(self, item: str) -> bool:
        """Add to current and check both filters."""
        self._maybe_rotate()
        was_in_previous = self.previous.contains(item)
        was_in_current = self.current.add_and_check(item)
        return was_in_previous or was_in_current


# =============================================================================
# Message Cache
# =============================================================================

@dataclass
class CachedMessage:
    """Cached message for IWANT requests."""
    message_id: str
    message_data: dict[str, Any]
    priority: MessagePriority
    received_at: float
    size_bytes: int
    origin_peer: str


class MessageCache:
    """
    LRU cache for recent messages to serve IWANT requests.

    Maintains messages in memory for a configurable TTL to enable
    lazy push/pull mechanisms.
    """

    def __init__(self, max_size: int = MESSAGE_CACHE_SIZE, ttl: int = MESSAGE_CACHE_TTL):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: dict[str, CachedMessage] = {}
        self._lock = threading.Lock()

    def put(self, message_id: str, message_data: dict[str, Any],
            priority: MessagePriority, origin_peer: str) -> None:
        """Add a message to the cache."""
        with self._lock:
            # Evict if at capacity
            if len(self.cache) >= self.max_size:
                self._evict_oldest()

            size = len(str(message_data))
            self.cache[message_id] = CachedMessage(
                message_id=message_id,
                message_data=message_data,
                priority=priority,
                received_at=time.time(),
                size_bytes=size,
                origin_peer=origin_peer
            )

    def get(self, message_id: str) -> dict[str, Any] | None:
        """Get a message from cache if present and not expired."""
        with self._lock:
            if message_id not in self.cache:
                return None

            cached = self.cache[message_id]
            if time.time() - cached.received_at > self.ttl:
                del self.cache[message_id]
                return None

            return cached.message_data

    def contains(self, message_id: str) -> bool:
        """Check if message is in cache (and not expired)."""
        return self.get(message_id) is not None

    def get_message_ids(self) -> list[str]:
        """Get list of cached message IDs."""
        with self._lock:
            now = time.time()
            return [
                mid for mid, cached in self.cache.items()
                if now - cached.received_at <= self.ttl
            ]

    def _evict_oldest(self) -> None:
        """Evict oldest messages until under capacity."""
        if not self.cache:
            return

        # Sort by received_at and remove oldest
        sorted_items = sorted(self.cache.items(), key=lambda x: x[1].received_at)
        for mid, _ in sorted_items[:len(self.cache) - self.max_size + 1]:
            del self.cache[mid]

    def cleanup_expired(self) -> int:
        """Remove expired entries, returns count removed."""
        with self._lock:
            now = time.time()
            expired = [
                mid for mid, cached in self.cache.items()
                if now - cached.received_at > self.ttl
            ]
            for mid in expired:
                del self.cache[mid]
            return len(expired)


# =============================================================================
# Priority Queue for Messages
# =============================================================================

@dataclass(order=True)
class PrioritizedMessage:
    """Message wrapper for priority queue ordering."""
    priority: int
    timestamp: float
    message_id: str = field(compare=False)
    message_data: dict[str, Any] = field(compare=False)
    target_peer: str = field(compare=False)


class MessageQueue:
    """
    Priority queue for outgoing messages.

    Ensures critical messages (blocks) are sent before regular messages.
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: list[PrioritizedMessage] = []
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)

    def put(
        self,
        message_id: str,
        message_data: dict[str, Any],
        target_peer: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """Add a message to the queue."""
        with self._lock:
            if len(self._queue) >= self.max_size:
                return False

            item = PrioritizedMessage(
                priority=priority.value,
                timestamp=time.time(),
                message_id=message_id,
                message_data=message_data,
                target_peer=target_peer
            )
            heapq.heappush(self._queue, item)
            self._not_empty.notify()
            return True

    def get(self, timeout: float | None = None) -> PrioritizedMessage | None:
        """Get highest priority message from queue."""
        with self._not_empty:
            if not self._queue:
                self._not_empty.wait(timeout)

            if self._queue:
                return heapq.heappop(self._queue)
            return None

    def get_nowait(self) -> PrioritizedMessage | None:
        """Get message without blocking."""
        with self._lock:
            if self._queue:
                return heapq.heappop(self._queue)
            return None

    def size(self) -> int:
        """Get queue size."""
        with self._lock:
            return len(self._queue)

    def clear(self) -> None:
        """Clear the queue."""
        with self._lock:
            self._queue.clear()


# =============================================================================
# Peer Management for Gossip
# =============================================================================

@dataclass
class GossipPeerState:
    """State tracking for a peer in gossip protocol."""
    peer_id: str
    peer_type: PeerType = PeerType.UNKNOWN
    duplicate_count: int = 0  # Consecutive duplicates received
    missing_count: int = 0  # Messages we had to request
    last_gossip: float = 0.0
    last_ihave: float = 0.0
    pending_ihaves: set[str] = field(default_factory=set)  # Message IDs awaiting
    delivery_success: int = 0
    delivery_failure: int = 0

    def delivery_rate(self) -> float:
        """Calculate message delivery success rate."""
        total = self.delivery_success + self.delivery_failure
        if total == 0:
            return 1.0
        return self.delivery_success / total


class PlumtreePeerManager:
    """
    Manages eager and lazy peer sets for Plumtree protocol.

    Dynamically adjusts peer classification based on message patterns
    to optimize bandwidth while maintaining reliability.
    """

    def __init__(self, node_id: str, max_eager: int = MAX_EAGER_PEERS, max_lazy: int = MAX_LAZY_PEERS):
        self.node_id = node_id
        self.max_eager = max_eager
        self.max_lazy = max_lazy

        self.peers: dict[str, GossipPeerState] = {}
        self.eager_peers: set[str] = set()
        self.lazy_peers: set[str] = set()
        self._lock = threading.Lock()

    def add_peer(self, peer_id: str) -> None:
        """Add a new peer, initially as eager if space available."""
        with self._lock:
            if peer_id in self.peers:
                return

            self.peers[peer_id] = GossipPeerState(peer_id=peer_id)

            # New peers start as eager if we have room
            if len(self.eager_peers) < self.max_eager:
                self.peers[peer_id].peer_type = PeerType.EAGER
                self.eager_peers.add(peer_id)
            else:
                self.peers[peer_id].peer_type = PeerType.LAZY
                self.lazy_peers.add(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer from all sets."""
        with self._lock:
            self.eager_peers.discard(peer_id)
            self.lazy_peers.discard(peer_id)
            self.peers.pop(peer_id, None)

    def get_eager_peers(self) -> list[str]:
        """Get list of eager peers."""
        with self._lock:
            return list(self.eager_peers)

    def get_lazy_peers(self) -> list[str]:
        """Get list of lazy peers."""
        with self._lock:
            return list(self.lazy_peers)

    def graft(self, peer_id: str) -> bool:
        """
        Move a peer from lazy to eager set.

        Called when we need to receive messages from this peer eagerly
        (e.g., after requesting via IWANT).
        """
        with self._lock:
            if peer_id not in self.peers:
                return False

            if peer_id in self.eager_peers:
                return True  # Already eager

            # If at capacity, demote worst eager peer
            if len(self.eager_peers) >= self.max_eager:
                worst = self._find_worst_eager_peer()
                if worst:
                    self._demote_to_lazy(worst)

            self.lazy_peers.discard(peer_id)
            self.eager_peers.add(peer_id)
            self.peers[peer_id].peer_type = PeerType.EAGER
            self.peers[peer_id].missing_count = 0

            logger.debug(f"Grafted peer {peer_id} to eager set")
            return True

    def prune(self, peer_id: str) -> bool:
        """
        Move a peer from eager to lazy set.

        Called when we receive too many duplicates from this peer.
        """
        with self._lock:
            if peer_id not in self.peers:
                return False

            if peer_id in self.lazy_peers:
                return True  # Already lazy

            self.eager_peers.discard(peer_id)
            self.lazy_peers.add(peer_id)
            self.peers[peer_id].peer_type = PeerType.LAZY
            self.peers[peer_id].duplicate_count = 0

            logger.debug(f"Pruned peer {peer_id} to lazy set")
            return True

    def record_duplicate(self, peer_id: str) -> bool:
        """
        Record that we received a duplicate from this peer.

        Returns True if peer should be pruned.
        """
        with self._lock:
            if peer_id not in self.peers:
                return False

            self.peers[peer_id].duplicate_count += 1

            # Prune if exceeds threshold
            if (peer_id in self.eager_peers and
                self.peers[peer_id].duplicate_count >= PRUNE_THRESHOLD):
                return True
            return False

    def record_missing(self, peer_id: str) -> bool:
        """
        Record that we had to request a message from this peer.

        Returns True if peer should be grafted.
        """
        with self._lock:
            if peer_id not in self.peers:
                return False

            self.peers[peer_id].missing_count += 1

            # Graft if we're frequently missing messages
            if (peer_id in self.lazy_peers and
                self.peers[peer_id].missing_count >= 2):
                return True
            return False

    def record_delivery(self, peer_id: str, success: bool) -> None:
        """Record message delivery success/failure."""
        with self._lock:
            if peer_id in self.peers:
                if success:
                    self.peers[peer_id].delivery_success += 1
                else:
                    self.peers[peer_id].delivery_failure += 1

    def add_pending_ihave(self, peer_id: str, message_id: str) -> None:
        """Track a pending IHAVE for a peer."""
        with self._lock:
            if peer_id in self.peers:
                self.peers[peer_id].pending_ihaves.add(message_id)

    def resolve_pending_ihave(self, peer_id: str, message_id: str) -> None:
        """Remove a resolved IHAVE."""
        with self._lock:
            if peer_id in self.peers:
                self.peers[peer_id].pending_ihaves.discard(message_id)

    def get_pending_ihaves(self, peer_id: str) -> set[str]:
        """Get pending IHAVEs for a peer."""
        with self._lock:
            if peer_id in self.peers:
                return set(self.peers[peer_id].pending_ihaves)
            return set()

    def _find_worst_eager_peer(self) -> str | None:
        """Find the eager peer with worst delivery rate."""
        worst_peer = None
        worst_rate = 1.1

        for peer_id in self.eager_peers:
            if peer_id in self.peers:
                rate = self.peers[peer_id].delivery_rate()
                if rate < worst_rate:
                    worst_rate = rate
                    worst_peer = peer_id

        return worst_peer

    def _demote_to_lazy(self, peer_id: str) -> None:
        """Demote a peer to lazy set (internal, assumes lock held)."""
        self.eager_peers.discard(peer_id)
        if len(self.lazy_peers) < self.max_lazy:
            self.lazy_peers.add(peer_id)
            if peer_id in self.peers:
                self.peers[peer_id].peer_type = PeerType.LAZY

    def optimize_peer_sets(self) -> None:
        """Periodically optimize peer set composition."""
        with self._lock:
            # Ensure we have minimum eager peers
            if len(self.eager_peers) < self.max_eager // 2:
                # Promote best lazy peers
                lazy_by_rate = sorted(
                    [(pid, self.peers[pid].delivery_rate())
                     for pid in self.lazy_peers if pid in self.peers],
                    key=lambda x: x[1],
                    reverse=True
                )

                for peer_id, _ in lazy_by_rate[:self.max_eager - len(self.eager_peers)]:
                    self.lazy_peers.discard(peer_id)
                    self.eager_peers.add(peer_id)
                    self.peers[peer_id].peer_type = PeerType.EAGER


# =============================================================================
# Adaptive Fanout Controller
# =============================================================================

class AdaptiveFanout:
    """
    Dynamically adjusts gossip fanout based on network conditions.

    Targets a specific delivery ratio while minimizing bandwidth.
    """

    def __init__(
        self,
        initial_fanout: int = GOSSIP_FANOUT,
        min_fanout: int = MIN_FANOUT,
        max_fanout: int = MAX_FANOUT,
        target_ratio: float = TARGET_DELIVERY_RATIO
    ):
        self.fanout = initial_fanout
        self.min_fanout = min_fanout
        self.max_fanout = max_fanout
        self.target_ratio = target_ratio

        self.messages_sent = 0
        self.messages_delivered = 0
        self.last_adjustment = time.time()
        self._lock = threading.Lock()

    def record_send(self) -> None:
        """Record a message was sent."""
        with self._lock:
            self.messages_sent += 1

    def record_delivery(self, delivered: bool) -> None:
        """Record delivery outcome."""
        with self._lock:
            if delivered:
                self.messages_delivered += 1

    def get_fanout(self) -> int:
        """Get current fanout value."""
        with self._lock:
            return self.fanout

    def get_fanout_for_priority(self, priority: MessagePriority) -> int:
        """Get fanout adjusted for message priority."""
        with self._lock:
            base = self.fanout

            if priority == MessagePriority.CRITICAL:
                # Critical messages use maximum fanout
                return self.max_fanout
            elif priority == MessagePriority.HIGH:
                # High priority gets extra fanout
                return min(base + 2, self.max_fanout)
            elif priority == MessagePriority.LOW:
                # Low priority can use reduced fanout
                return max(base - 1, self.min_fanout)

            return base

    def adjust(self) -> None:
        """Adjust fanout based on recent delivery ratio."""
        with self._lock:
            now = time.time()
            if now - self.last_adjustment < FANOUT_ADJUSTMENT_INTERVAL:
                return

            if self.messages_sent == 0:
                return

            ratio = self.messages_delivered / self.messages_sent

            if ratio < self.target_ratio - 0.05:
                # Delivery too low, increase fanout
                self.fanout = min(self.fanout + 1, self.max_fanout)
                logger.info(f"Increased gossip fanout to {self.fanout} (delivery: {ratio:.2%})")
            elif ratio > self.target_ratio + 0.05 and self.fanout > self.min_fanout:
                # Delivery high, can reduce fanout
                self.fanout = max(self.fanout - 1, self.min_fanout)
                logger.info(f"Decreased gossip fanout to {self.fanout} (delivery: {ratio:.2%})")

            # Reset counters
            self.messages_sent = 0
            self.messages_delivered = 0
            self.last_adjustment = now

    def calculate_optimal_fanout(self, network_size: int) -> int:
        """Calculate optimal fanout for network size."""
        if network_size <= 1:
            return self.min_fanout

        # Optimal fanout ≈ ln(N) + c for epidemic gossip
        optimal = int(math.log(network_size) + GOSSIP_FACTOR)
        return max(self.min_fanout, min(optimal, self.max_fanout))


# =============================================================================
# Main Gossip Protocol Manager
# =============================================================================

class GossipProtocol:
    """
    Optimized epidemic gossip protocol implementation.

    Combines Plumtree (eager/lazy push), bloom filters for deduplication,
    and adaptive fanout for efficient message dissemination.
    """

    def __init__(
        self,
        node_id: str,
        send_callback: Callable[[str, dict[str, Any]], bool],
        on_message_callback: Callable[[dict[str, Any]], None] | None = None
    ):
        """
        Initialize gossip protocol.

        Args:
            node_id: This node's identifier
            send_callback: Function to send message to peer (peer_id, message) -> success
            on_message_callback: Function called when new message received
        """
        self.node_id = node_id
        self._send = send_callback
        self._on_message = on_message_callback

        # Duplicate detection
        self.seen_filter = RotatingBloomFilter()

        # Message cache for IWANT
        self.message_cache = MessageCache()

        # Peer management
        self.peer_manager = PlumtreePeerManager(node_id)

        # Adaptive fanout
        self.fanout_controller = AdaptiveFanout()

        # Outgoing message queue
        self.message_queue = MessageQueue()

        # IHAVE batching
        self.pending_ihaves: dict[str, list[str]] = defaultdict(list)  # peer_id -> [message_ids]
        self._ihave_lock = threading.Lock()

        # Statistics
        self.stats = {
            "messages_gossiped": 0,
            "messages_received": 0,
            "duplicates_filtered": 0,
            "ihaves_sent": 0,
            "ihaves_received": 0,
            "iwants_sent": 0,
            "iwants_received": 0,
            "grafts": 0,
            "prunes": 0,
            "eager_pushes": 0,
            "lazy_pushes": 0
        }

        # Background thread for IHAVE batching
        self._running = False
        self._ihave_thread: threading.Thread | None = None
        self._cleanup_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start background threads."""
        self._running = True

        self._ihave_thread = threading.Thread(target=self._ihave_batch_loop, daemon=True)
        self._ihave_thread.start()

        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

        logger.info("Gossip protocol started")

    def stop(self) -> None:
        """Stop background threads."""
        self._running = False
        logger.info("Gossip protocol stopped")

    # =========================================================================
    # Peer Management
    # =========================================================================

    def add_peer(self, peer_id: str) -> None:
        """Add a peer to the gossip network."""
        self.peer_manager.add_peer(peer_id)

    def remove_peer(self, peer_id: str) -> None:
        """Remove a peer from the gossip network."""
        self.peer_manager.remove_peer(peer_id)

    # =========================================================================
    # Message Dissemination
    # =========================================================================

    def gossip(
        self,
        message_id: str,
        message_data: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        exclude_peers: set[str] | None = None
    ) -> int:
        """
        Gossip a message to the network using Plumtree protocol.

        Args:
            message_id: Unique message identifier
            message_data: Message payload
            priority: Message priority level
            exclude_peers: Peers to exclude (already received)

        Returns:
            Number of peers message was sent to
        """
        exclude = exclude_peers or set()
        exclude.add(self.node_id)

        # Mark as seen
        self.seen_filter.add(message_id)

        # Cache for IWANT requests
        self.message_cache.put(message_id, message_data, priority, self.node_id)

        # Get fanout for this priority
        fanout = self.fanout_controller.get_fanout_for_priority(priority)

        sent_count = 0

        # Eager push to eager peers
        eager_peers = self.peer_manager.get_eager_peers()
        for peer_id in eager_peers:
            if peer_id not in exclude:
                if self._send_gossip(peer_id, message_id, message_data):
                    sent_count += 1
                    self.stats["eager_pushes"] += 1
                    self.peer_manager.record_delivery(peer_id, True)
                else:
                    self.peer_manager.record_delivery(peer_id, False)

        # Lazy push to lazy peers (send IHAVE)
        lazy_peers = self.peer_manager.get_lazy_peers()
        for peer_id in lazy_peers:
            if peer_id not in exclude:
                self._queue_ihave(peer_id, message_id)
                self.stats["lazy_pushes"] += 1

        # Additional random gossip if we haven't reached fanout
        if sent_count < fanout:
            all_peers = set(eager_peers + lazy_peers) - exclude
            additional = list(all_peers - set(eager_peers))
            random.shuffle(additional)

            for peer_id in additional[:fanout - sent_count]:
                if self._send_gossip(peer_id, message_id, message_data):
                    sent_count += 1

        self.stats["messages_gossiped"] += 1
        self.fanout_controller.record_send()

        logger.debug(f"Gossiped message {message_id[:8]} to {sent_count} peers (priority: {priority.name})")
        return sent_count

    def _send_gossip(self, peer_id: str, message_id: str, message_data: dict[str, Any]) -> bool:
        """Send a GOSSIP message to a peer."""
        gossip_msg = {
            "type": GossipMessageType.GOSSIP.value,
            "message_id": message_id,
            "origin": self.node_id,
            "payload": message_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        return self._send(peer_id, gossip_msg)

    def _queue_ihave(self, peer_id: str, message_id: str) -> None:
        """Queue an IHAVE for batched sending."""
        with self._ihave_lock:
            self.pending_ihaves[peer_id].append(message_id)
            self.peer_manager.add_pending_ihave(peer_id, message_id)

    def _send_ihave_batch(self, peer_id: str, message_ids: list[str]) -> bool:
        """Send batched IHAVE message."""
        if not message_ids:
            return True

        ihave_msg = {
            "type": GossipMessageType.IHAVE.value,
            "message_ids": message_ids[:IHAVE_BATCH_SIZE],
            "origin": self.node_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        success = self._send(peer_id, ihave_msg)
        if success:
            self.stats["ihaves_sent"] += 1
        return success

    def _send_iwant(self, peer_id: str, message_ids: list[str]) -> bool:
        """Send IWANT request for messages."""
        iwant_msg = {
            "type": GossipMessageType.IWANT.value,
            "message_ids": message_ids,
            "origin": self.node_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        success = self._send(peer_id, iwant_msg)
        if success:
            self.stats["iwants_sent"] += 1
        return success

    def _send_graft(self, peer_id: str) -> bool:
        """Send GRAFT request to become eager peer."""
        graft_msg = {
            "type": GossipMessageType.GRAFT.value,
            "origin": self.node_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        success = self._send(peer_id, graft_msg)
        if success:
            self.stats["grafts"] += 1
        return success

    def _send_prune(self, peer_id: str) -> bool:
        """Send PRUNE request to become lazy peer."""
        prune_msg = {
            "type": GossipMessageType.PRUNE.value,
            "origin": self.node_id,
            "timestamp": datetime.utcnow().isoformat()
        }

        success = self._send(peer_id, prune_msg)
        if success:
            self.stats["prunes"] += 1
        return success

    # =========================================================================
    # Message Reception
    # =========================================================================

    def handle_message(self, sender_id: str, message: dict[str, Any]) -> bool:
        """
        Handle an incoming gossip protocol message.

        Args:
            sender_id: ID of the peer that sent the message
            message: The gossip protocol message

        Returns:
            True if message was handled successfully
        """
        msg_type = message.get("type")

        try:
            if msg_type == GossipMessageType.GOSSIP.value:
                return self._handle_gossip(sender_id, message)
            elif msg_type == GossipMessageType.IHAVE.value:
                return self._handle_ihave(sender_id, message)
            elif msg_type == GossipMessageType.IWANT.value:
                return self._handle_iwant(sender_id, message)
            elif msg_type == GossipMessageType.GRAFT.value:
                return self._handle_graft(sender_id, message)
            elif msg_type == GossipMessageType.PRUNE.value:
                return self._handle_prune(sender_id, message)
            else:
                logger.warning(f"Unknown gossip message type: {msg_type}")
                return False
        except Exception as e:
            logger.error(f"Error handling gossip message: {e}")
            return False

    def _handle_gossip(self, sender_id: str, message: dict[str, Any]) -> bool:
        """Handle incoming GOSSIP message."""
        message_id = message.get("message_id")
        payload = message.get("payload")
        origin = message.get("origin")

        if not message_id or not payload:
            return False

        # Check if duplicate
        if self.seen_filter.add_and_check(message_id):
            self.stats["duplicates_filtered"] += 1

            # Record duplicate and maybe prune peer
            if self.peer_manager.record_duplicate(sender_id):
                self.peer_manager.prune(sender_id)
                self._send_prune(sender_id)

            return False

        self.stats["messages_received"] += 1
        self.fanout_controller.record_delivery(True)

        # Cache the message
        priority = self._get_message_priority(payload)
        self.message_cache.put(message_id, payload, priority, origin or sender_id)

        # Resolve any pending IHAVE
        self.peer_manager.resolve_pending_ihave(sender_id, message_id)

        # Notify application
        if self._on_message:
            self._on_message(payload)

        # Continue gossiping (exclude sender and origin)
        exclude = {sender_id}
        if origin:
            exclude.add(origin)

        self.gossip(message_id, payload, priority, exclude)

        return True

    def _handle_ihave(self, sender_id: str, message: dict[str, Any]) -> bool:
        """Handle incoming IHAVE message."""
        message_ids = message.get("message_ids", [])
        self.stats["ihaves_received"] += 1

        # Check which messages we don't have
        needed = []
        for msg_id in message_ids:
            if not self.seen_filter.contains(msg_id) and not self.message_cache.contains(msg_id):
                needed.append(msg_id)

        if needed:
            # Request the messages we need
            self._send_iwant(sender_id, needed)

            # Track that we're missing messages from this peer
            if self.peer_manager.record_missing(sender_id):
                # Graft this peer for more eager messages
                self.peer_manager.graft(sender_id)
                self._send_graft(sender_id)

        return True

    def _handle_iwant(self, sender_id: str, message: dict[str, Any]) -> bool:
        """Handle incoming IWANT message."""
        message_ids = message.get("message_ids", [])
        self.stats["iwants_received"] += 1

        # Send requested messages from cache
        for msg_id in message_ids:
            cached = self.message_cache.get(msg_id)
            if cached:
                self._send_gossip(sender_id, msg_id, cached)

        return True

    def _handle_graft(self, sender_id: str, message: dict[str, Any]) -> bool:
        """Handle incoming GRAFT message."""
        # Add peer to eager set
        self.peer_manager.graft(sender_id)
        return True

    def _handle_prune(self, sender_id: str, message: dict[str, Any]) -> bool:
        """Handle incoming PRUNE message."""
        # Move peer to lazy set
        self.peer_manager.prune(sender_id)
        return True

    def _get_message_priority(self, payload: dict[str, Any]) -> MessagePriority:
        """Determine message priority from payload."""
        broadcast_type = payload.get("broadcast_type", "")

        if broadcast_type == "new_block":
            return MessagePriority.CRITICAL
        elif broadcast_type == "settlement":
            return MessagePriority.HIGH
        elif broadcast_type == "new_entry":
            return MessagePriority.NORMAL
        else:
            return MessagePriority.LOW

    # =========================================================================
    # Background Tasks
    # =========================================================================

    def _ihave_batch_loop(self) -> None:
        """Background loop to send batched IHAVE messages."""
        while self._running:
            try:
                time.sleep(LAZY_PUSH_DELAY_MS / 1000)

                with self._ihave_lock:
                    for peer_id, message_ids in list(self.pending_ihaves.items()):
                        if message_ids:
                            self._send_ihave_batch(peer_id, message_ids)
                            self.pending_ihaves[peer_id] = []
            except Exception as e:
                logger.error(f"IHAVE batch error: {e}")

    def _cleanup_loop(self) -> None:
        """Background loop for maintenance tasks."""
        while self._running:
            try:
                time.sleep(60)  # Run every minute

                # Cleanup expired cache entries
                self.message_cache.cleanup_expired()

                # Adjust fanout based on delivery metrics
                self.fanout_controller.adjust()

                # Optimize peer sets
                self.peer_manager.optimize_peer_sets()

            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    # =========================================================================
    # Statistics & Monitoring
    # =========================================================================

    def get_stats(self) -> dict[str, Any]:
        """Get gossip protocol statistics."""
        return {
            **self.stats,
            "current_fanout": self.fanout_controller.get_fanout(),
            "eager_peers": len(self.peer_manager.get_eager_peers()),
            "lazy_peers": len(self.peer_manager.get_lazy_peers()),
            "cached_messages": len(self.message_cache.get_message_ids()),
            "bloom_fpr": self.seen_filter.current.estimated_false_positive_rate()
        }


# =============================================================================
# Helper Functions
# =============================================================================

def get_message_priority(broadcast_type: str) -> MessagePriority:
    """Get priority for a broadcast type."""
    priority_map = {
        "new_block": MessagePriority.CRITICAL,
        "settlement": MessagePriority.HIGH,
        "new_entry": MessagePriority.NORMAL,
        "peer_announce": MessagePriority.LOW,
        "chain_tip": MessagePriority.LOW
    }
    return priority_map.get(broadcast_type, MessagePriority.NORMAL)


def calculate_optimal_fanout(network_size: int) -> int:
    """Calculate optimal fanout for network size."""
    if network_size <= 1:
        return MIN_FANOUT
    # ln(N) + c for reliable epidemic spread
    return max(MIN_FANOUT, min(int(math.log(network_size) + GOSSIP_FACTOR), MAX_FANOUT))
