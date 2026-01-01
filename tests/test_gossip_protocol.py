"""
Tests for optimized gossip protocol implementation.
"""

import os
import sys
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from gossip_protocol import (
    # Enums
    GossipMessageType,
    MessagePriority,
    PeerType,
    # Bloom Filter
    BloomFilter,
    RotatingBloomFilter,
    # Message Cache
    MessageCache,
    CachedMessage,
    # Message Queue
    MessageQueue,
    PrioritizedMessage,
    # Peer Management
    GossipPeerState,
    PlumtreePeerManager,
    # Adaptive Fanout
    AdaptiveFanout,
    # Main Protocol
    GossipProtocol,
    # Constants
    GOSSIP_FANOUT,
    MAX_EAGER_PEERS,
    MAX_LAZY_PEERS,
    PRUNE_THRESHOLD,
    # Helper functions
    get_message_priority,
    calculate_optimal_fanout,
)


class TestBloomFilter:
    """Tests for Bloom filter implementation."""

    def test_add_and_contains(self):
        """Test basic add and contains operations."""
        bf = BloomFilter(size_bits=1024, hash_count=3)

        bf.add("test_item_1")
        bf.add("test_item_2")

        assert bf.contains("test_item_1")
        assert bf.contains("test_item_2")
        assert not bf.contains("never_added")

    def test_add_and_check(self):
        """Test atomic add and check operation."""
        bf = BloomFilter()

        # First add returns False (wasn't present)
        was_present = bf.add_and_check("new_item")
        assert not was_present

        # Second add returns True (was present)
        was_present = bf.add_and_check("new_item")
        assert was_present

    def test_clear(self):
        """Test filter clearing."""
        bf = BloomFilter()
        bf.add("item")
        assert bf.contains("item")

        bf.clear()
        assert not bf.contains("item")
        assert bf.count == 0

    def test_false_positive_rate(self):
        """Test that FPR estimation works."""
        bf = BloomFilter(size_bits=1024, hash_count=5)

        # Empty filter should have 0 FPR
        assert bf.estimated_false_positive_rate() == 0.0

        # Add items and check FPR increases
        for i in range(100):
            bf.add(f"item_{i}")

        fpr = bf.estimated_false_positive_rate()
        assert fpr > 0.0
        assert fpr < 1.0

    def test_merge(self):
        """Test merging two bloom filters."""
        bf1 = BloomFilter(size_bits=1024, hash_count=3)
        bf2 = BloomFilter(size_bits=1024, hash_count=3)

        bf1.add("item_a")
        bf2.add("item_b")

        bf1.merge(bf2)

        assert bf1.contains("item_a")
        assert bf1.contains("item_b")

    def test_thread_safety(self):
        """Test thread-safe operations."""
        bf = BloomFilter()
        items_added = []

        def add_items(prefix, count):
            for i in range(count):
                item = f"{prefix}_{i}"
                bf.add(item)
                items_added.append(item)

        threads = [
            threading.Thread(target=add_items, args=(f"thread_{t}", 100))
            for t in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All items should be present
        for item in items_added:
            assert bf.contains(item)


class TestRotatingBloomFilter:
    """Tests for rotating bloom filter."""

    def test_rotation(self):
        """Test filter rotation."""
        rbf = RotatingBloomFilter(rotation_interval=1)  # 1 second

        rbf.add("item_before")
        assert rbf.contains("item_before")

        # Wait for rotation
        time.sleep(1.5)

        # Item should still be in previous filter
        rbf.add("item_after")
        assert rbf.contains("item_before")
        assert rbf.contains("item_after")

    def test_add_and_check(self):
        """Test atomic add and check with rotation."""
        rbf = RotatingBloomFilter(rotation_interval=300)

        was_present = rbf.add_and_check("new_item")
        assert not was_present

        was_present = rbf.add_and_check("new_item")
        assert was_present


class TestMessageCache:
    """Tests for message cache."""

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = MessageCache(max_size=100, ttl=300)

        cache.put("msg1", {"content": "test"}, MessagePriority.NORMAL, "origin1")

        result = cache.get("msg1")
        assert result is not None
        assert result["content"] == "test"

    def test_missing_key(self):
        """Test get for missing key."""
        cache = MessageCache()
        assert cache.get("nonexistent") is None

    def test_expiration(self):
        """Test message expiration."""
        cache = MessageCache(ttl=1)  # 1 second TTL

        cache.put("msg1", {"content": "test"}, MessagePriority.NORMAL, "origin1")

        assert cache.get("msg1") is not None

        time.sleep(1.5)

        assert cache.get("msg1") is None

    def test_max_size_eviction(self):
        """Test eviction when cache is full."""
        cache = MessageCache(max_size=3, ttl=300)

        cache.put("msg1", {"content": "1"}, MessagePriority.NORMAL, "origin")
        time.sleep(0.1)
        cache.put("msg2", {"content": "2"}, MessagePriority.NORMAL, "origin")
        time.sleep(0.1)
        cache.put("msg3", {"content": "3"}, MessagePriority.NORMAL, "origin")
        time.sleep(0.1)
        cache.put("msg4", {"content": "4"}, MessagePriority.NORMAL, "origin")

        # Oldest should be evicted
        assert cache.get("msg1") is None
        assert cache.get("msg4") is not None

    def test_get_message_ids(self):
        """Test getting list of cached message IDs."""
        cache = MessageCache(ttl=300)

        cache.put("msg1", {}, MessagePriority.NORMAL, "origin")
        cache.put("msg2", {}, MessagePriority.NORMAL, "origin")

        ids = cache.get_message_ids()
        assert "msg1" in ids
        assert "msg2" in ids


class TestMessageQueue:
    """Tests for priority message queue."""

    def test_priority_ordering(self):
        """Test that messages are dequeued in priority order."""
        queue = MessageQueue()

        queue.put("low", {}, "peer1", MessagePriority.LOW)
        queue.put("critical", {}, "peer2", MessagePriority.CRITICAL)
        queue.put("normal", {}, "peer3", MessagePriority.NORMAL)

        # Should get critical first
        msg = queue.get_nowait()
        assert msg.message_id == "critical"

        msg = queue.get_nowait()
        assert msg.message_id == "normal"

        msg = queue.get_nowait()
        assert msg.message_id == "low"

    def test_same_priority_fifo(self):
        """Test FIFO ordering for same priority."""
        queue = MessageQueue()

        queue.put("first", {}, "peer1", MessagePriority.NORMAL)
        time.sleep(0.01)
        queue.put("second", {}, "peer2", MessagePriority.NORMAL)

        msg1 = queue.get_nowait()
        msg2 = queue.get_nowait()

        assert msg1.message_id == "first"
        assert msg2.message_id == "second"

    def test_max_size(self):
        """Test max size enforcement."""
        queue = MessageQueue(max_size=2)

        assert queue.put("msg1", {}, "peer1")
        assert queue.put("msg2", {}, "peer2")
        assert not queue.put("msg3", {}, "peer3")  # Should fail


class TestPlumtreePeerManager:
    """Tests for Plumtree peer management."""

    def test_add_peer_eager(self):
        """Test new peers are added as eager when space available."""
        manager = PlumtreePeerManager("node1", max_eager=2, max_lazy=5)

        manager.add_peer("peer1")
        manager.add_peer("peer2")

        assert "peer1" in manager.get_eager_peers()
        assert "peer2" in manager.get_eager_peers()

    def test_add_peer_lazy_when_eager_full(self):
        """Test new peers go to lazy when eager is full."""
        manager = PlumtreePeerManager("node1", max_eager=1, max_lazy=5)

        manager.add_peer("peer1")
        manager.add_peer("peer2")

        assert "peer1" in manager.get_eager_peers()
        assert "peer2" in manager.get_lazy_peers()

    def test_graft(self):
        """Test grafting lazy peer to eager."""
        manager = PlumtreePeerManager("node1", max_eager=2, max_lazy=5)

        manager.add_peer("peer1")
        manager.peers["peer1"].peer_type = PeerType.LAZY
        manager.eager_peers.discard("peer1")
        manager.lazy_peers.add("peer1")

        assert manager.graft("peer1")
        assert "peer1" in manager.get_eager_peers()
        assert "peer1" not in manager.get_lazy_peers()

    def test_prune(self):
        """Test pruning eager peer to lazy."""
        manager = PlumtreePeerManager("node1", max_eager=2, max_lazy=5)

        manager.add_peer("peer1")
        assert "peer1" in manager.get_eager_peers()

        assert manager.prune("peer1")
        assert "peer1" not in manager.get_eager_peers()
        assert "peer1" in manager.get_lazy_peers()

    def test_record_duplicate(self):
        """Test duplicate recording triggers prune."""
        manager = PlumtreePeerManager("node1")
        manager.add_peer("peer1")

        # Record duplicates up to threshold
        for _ in range(PRUNE_THRESHOLD - 1):
            should_prune = manager.record_duplicate("peer1")
            assert not should_prune

        # Next duplicate should trigger prune
        should_prune = manager.record_duplicate("peer1")
        assert should_prune

    def test_record_missing(self):
        """Test missing recording triggers graft."""
        manager = PlumtreePeerManager("node1", max_eager=1)
        manager.add_peer("peer1")
        manager.add_peer("peer2")  # Goes to lazy

        # Record missing messages
        manager.record_missing("peer2")
        should_graft = manager.record_missing("peer2")
        assert should_graft

    def test_remove_peer(self):
        """Test removing a peer."""
        manager = PlumtreePeerManager("node1")
        manager.add_peer("peer1")

        manager.remove_peer("peer1")

        assert "peer1" not in manager.get_eager_peers()
        assert "peer1" not in manager.get_lazy_peers()
        assert "peer1" not in manager.peers


class TestAdaptiveFanout:
    """Tests for adaptive fanout controller."""

    def test_initial_fanout(self):
        """Test initial fanout value."""
        fanout = AdaptiveFanout(initial_fanout=4)
        assert fanout.get_fanout() == 4

    def test_fanout_for_priority(self):
        """Test fanout adjustment for priority."""
        fanout = AdaptiveFanout(initial_fanout=4, min_fanout=2, max_fanout=8)

        # Critical should get max
        assert fanout.get_fanout_for_priority(MessagePriority.CRITICAL) == 8

        # High should get base + 2
        assert fanout.get_fanout_for_priority(MessagePriority.HIGH) == 6

        # Normal should get base
        assert fanout.get_fanout_for_priority(MessagePriority.NORMAL) == 4

        # Low should get base - 1
        assert fanout.get_fanout_for_priority(MessagePriority.LOW) == 3

    def test_calculate_optimal_fanout(self):
        """Test optimal fanout calculation."""
        fanout = AdaptiveFanout()

        # Small network
        assert fanout.calculate_optimal_fanout(1) == 2  # min

        # Medium network (50 nodes)
        optimal = fanout.calculate_optimal_fanout(50)
        assert optimal >= 2
        assert optimal <= 8

        # Large network (1000 nodes)
        optimal = fanout.calculate_optimal_fanout(1000)
        assert optimal >= 4  # ln(1000) ≈ 6.9

    def test_record_and_adjust(self):
        """Test delivery recording and adjustment."""
        fanout = AdaptiveFanout(initial_fanout=4)

        # Record some deliveries
        for _ in range(10):
            fanout.record_send()
            fanout.record_delivery(True)

        # Fanout shouldn't change with good delivery
        fanout.adjust()


class TestGossipProtocol:
    """Tests for main gossip protocol."""

    def test_initialization(self):
        """Test protocol initialization."""
        send_mock = MagicMock(return_value=True)
        protocol = GossipProtocol("node1", send_mock)

        assert protocol.node_id == "node1"
        assert protocol._running is False  # Not started yet

    def test_add_remove_peer(self):
        """Test peer management."""
        protocol = GossipProtocol("node1", MagicMock())

        protocol.add_peer("peer1")
        assert "peer1" in protocol.peer_manager.peers

        protocol.remove_peer("peer1")
        assert "peer1" not in protocol.peer_manager.peers

    def test_gossip_message(self):
        """Test gossiping a message."""
        send_mock = MagicMock(return_value=True)
        protocol = GossipProtocol("node1", send_mock)
        protocol.add_peer("peer1")
        protocol.add_peer("peer2")

        count = protocol.gossip("msg1", {"content": "test"}, MessagePriority.NORMAL)

        assert count > 0
        assert protocol.stats["messages_gossiped"] == 1

    def test_duplicate_detection(self):
        """Test duplicate message detection."""
        protocol = GossipProtocol("node1", MagicMock())

        # First gossip
        protocol.gossip("msg1", {"content": "test"})

        # Message should be in seen filter
        assert protocol.seen_filter.contains("msg1")

    def test_handle_gossip_message(self):
        """Test handling incoming gossip message."""
        on_message_mock = MagicMock()
        protocol = GossipProtocol("node1", MagicMock(), on_message_mock)
        protocol.add_peer("sender1")

        message = {
            "type": GossipMessageType.GOSSIP.value,
            "message_id": "msg1",
            "origin": "sender1",
            "payload": {"content": "test"},
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert protocol.stats["messages_received"] == 1

    def test_handle_duplicate_gossip(self):
        """Test handling duplicate gossip message."""
        protocol = GossipProtocol("node1", MagicMock())
        protocol.add_peer("sender1")

        # First message - should succeed
        message = {
            "type": GossipMessageType.GOSSIP.value,
            "message_id": "msg1",
            "origin": "sender1",
            "payload": {"content": "test"},
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert protocol.stats["messages_received"] == 1

        # Same message again - should be filtered
        success = protocol.handle_message("sender1", message)
        assert not success
        assert protocol.stats["duplicates_filtered"] == 1

    def test_handle_ihave(self):
        """Test handling IHAVE message."""
        send_mock = MagicMock(return_value=True)
        protocol = GossipProtocol("node1", send_mock)
        protocol.add_peer("sender1")

        message = {
            "type": GossipMessageType.IHAVE.value,
            "message_ids": ["msg1", "msg2"],
            "origin": "sender1",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert protocol.stats["ihaves_received"] == 1

    def test_handle_iwant(self):
        """Test handling IWANT message."""
        send_mock = MagicMock(return_value=True)
        protocol = GossipProtocol("node1", send_mock)
        protocol.add_peer("sender1")

        # Cache a message
        protocol.message_cache.put("msg1", {"content": "cached"}, MessagePriority.NORMAL, "node1")

        message = {
            "type": GossipMessageType.IWANT.value,
            "message_ids": ["msg1"],
            "origin": "sender1",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert protocol.stats["iwants_received"] == 1

    def test_handle_graft(self):
        """Test handling GRAFT message."""
        protocol = GossipProtocol("node1", MagicMock())
        protocol.add_peer("sender1")
        protocol.peer_manager.prune("sender1")

        message = {
            "type": GossipMessageType.GRAFT.value,
            "origin": "sender1",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert "sender1" in protocol.peer_manager.get_eager_peers()

    def test_handle_prune(self):
        """Test handling PRUNE message."""
        protocol = GossipProtocol("node1", MagicMock())
        protocol.add_peer("sender1")

        message = {
            "type": GossipMessageType.PRUNE.value,
            "origin": "sender1",
            "timestamp": datetime.utcnow().isoformat()
        }

        success = protocol.handle_message("sender1", message)
        assert success
        assert "sender1" in protocol.peer_manager.get_lazy_peers()

    def test_get_stats(self):
        """Test getting statistics."""
        protocol = GossipProtocol("node1", MagicMock())

        stats = protocol.get_stats()

        assert "messages_gossiped" in stats
        assert "messages_received" in stats
        assert "current_fanout" in stats
        assert "eager_peers" in stats
        assert "lazy_peers" in stats


class TestMessagePriority:
    """Tests for message priority."""

    def test_priority_ordering(self):
        """Test priority values are ordered correctly."""
        assert MessagePriority.CRITICAL < MessagePriority.HIGH
        assert MessagePriority.HIGH < MessagePriority.NORMAL
        assert MessagePriority.NORMAL < MessagePriority.LOW


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_message_priority(self):
        """Test priority detection from broadcast type."""
        assert get_message_priority("new_block") == MessagePriority.CRITICAL
        assert get_message_priority("settlement") == MessagePriority.HIGH
        assert get_message_priority("new_entry") == MessagePriority.NORMAL
        assert get_message_priority("peer_announce") == MessagePriority.LOW
        assert get_message_priority("unknown") == MessagePriority.NORMAL

    def test_calculate_optimal_fanout(self):
        """Test optimal fanout calculation."""
        # Very small network
        assert calculate_optimal_fanout(1) >= 2

        # Medium network
        fanout = calculate_optimal_fanout(100)
        assert 2 <= fanout <= 8

        # Large network
        fanout = calculate_optimal_fanout(10000)
        assert fanout >= 4


class TestP2PIntegration:
    """Tests for P2P network integration."""

    def test_p2p_gossip_initialization(self):
        """Test P2P network initializes gossip protocol."""
        from p2p_network import P2PNetwork, HAS_GOSSIP_PROTOCOL

        network = P2PNetwork()

        if HAS_GOSSIP_PROTOCOL:
            assert network.gossip_protocol is not None
            assert network._gossip_enabled
        else:
            # Gossip protocol not available, should be None
            assert network.gossip_protocol is None

    def test_p2p_network_stats_include_gossip(self):
        """Test network stats include gossip metrics."""
        from p2p_network import P2PNetwork, HAS_GOSSIP_PROTOCOL

        network = P2PNetwork()
        stats = network.get_network_stats()

        assert "gossip_protocol" in stats

        if HAS_GOSSIP_PROTOCOL:
            assert stats["gossip_protocol"]["enabled"]
            assert stats["gossip_protocol"]["protocol"] == "plumtree"
        else:
            assert not stats["gossip_protocol"]["enabled"]
            assert stats["gossip_protocol"]["protocol"] == "basic_flooding"

    def test_p2p_gossip_stats_method(self):
        """Test dedicated gossip stats method."""
        from p2p_network import P2PNetwork, HAS_GOSSIP_PROTOCOL

        network = P2PNetwork()
        stats = network.get_gossip_stats()

        if HAS_GOSSIP_PROTOCOL:
            assert stats is not None
            assert "messages_gossiped" in stats
        else:
            # No gossip protocol, should return None
            assert stats is None
