"""
Tests for NatLangChain P2P Network module.

Tests:
- P2PNetwork initialization
- PeerInfo dataclass
- BroadcastMessage dataclass
- PeerRateLimiter
- MessageValidator
- BlockValidator
- PeerSecurityManager
- Connection and peer management
- Broadcasting
- Chain synchronization
- Security hardening
"""

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from p2p_network import (
    BlockValidator,
    BroadcastMessage,
    BroadcastType,
    ConsensusMode,
    MessageValidator,
    NodeRole,
    P2PNetwork,
    PeerInfo,
    PeerRateLimiter,
    PeerSecurityManager,
    PeerStatus,
    SyncState,
    MAX_MESSAGES_PER_MINUTE,
    MAX_PEERS,
    MAX_PEERS_PER_IP,
)


class TestPeerStatus:
    """Tests for PeerStatus enum."""

    def test_peer_status_values(self):
        """Test all peer statuses exist."""
        assert PeerStatus.UNKNOWN.value == "unknown"
        assert PeerStatus.CONNECTING.value == "connecting"
        assert PeerStatus.CONNECTED.value == "connected"
        assert PeerStatus.DISCONNECTED.value == "disconnected"
        assert PeerStatus.STALE.value == "stale"
        assert PeerStatus.BANNED.value == "banned"


class TestNodeRole:
    """Tests for NodeRole enum."""

    def test_node_role_values(self):
        """Test all node roles exist."""
        assert NodeRole.FULL_NODE.value == "full_node"
        assert NodeRole.LIGHT_NODE.value == "light_node"
        assert NodeRole.MEDIATOR.value == "mediator"
        assert NodeRole.ARCHIVE.value == "archive"


class TestBroadcastType:
    """Tests for BroadcastType enum."""

    def test_broadcast_type_values(self):
        """Test all broadcast types exist."""
        assert BroadcastType.NEW_ENTRY.value == "new_entry"
        assert BroadcastType.NEW_BLOCK.value == "new_block"
        assert BroadcastType.SETTLEMENT.value == "settlement"
        assert BroadcastType.PEER_ANNOUNCE.value == "peer_announce"
        assert BroadcastType.CHAIN_TIP.value == "chain_tip"


class TestPeerInfo:
    """Tests for PeerInfo dataclass."""

    def test_create_peer_info(self):
        """Test creating PeerInfo instance."""
        info = PeerInfo(
            peer_id="peer-123",
            endpoint="http://localhost:5000",
            role=NodeRole.FULL_NODE,
            status=PeerStatus.CONNECTED,
        )
        assert info.peer_id == "peer-123"
        assert info.endpoint == "http://localhost:5000"
        assert info.role == NodeRole.FULL_NODE
        assert info.status == PeerStatus.CONNECTED

    def test_peer_info_defaults(self):
        """Test PeerInfo default values."""
        info = PeerInfo(peer_id="peer", endpoint="http://localhost")
        assert info.role == NodeRole.FULL_NODE
        assert info.status == PeerStatus.UNKNOWN
        assert info.chain_height == 0
        assert info.reputation == 1.0

    def test_peer_info_to_dict(self):
        """Test serialization to dictionary."""
        info = PeerInfo(
            peer_id="peer-123",
            endpoint="http://localhost:5000",
            role=NodeRole.MEDIATOR,
            status=PeerStatus.CONNECTED,
            chain_height=100,
        )
        data = info.to_dict()
        assert data["peer_id"] == "peer-123"
        assert data["role"] == "mediator"
        assert data["status"] == "connected"
        assert data["chain_height"] == 100

    def test_peer_info_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "peer_id": "peer-456",
            "endpoint": "http://example.com:5000",
            "role": "full_node",
            "status": "connected",
            "chain_height": 50,
            "chain_tip_hash": "abc123",
            "last_seen": None,
            "latency_ms": 25.5,
            "reputation": 0.9,
            "version": "1.0.0",
            "capabilities": ["entries", "blocks"],
        }
        info = PeerInfo.from_dict(data)
        assert info.peer_id == "peer-456"
        assert info.role == NodeRole.FULL_NODE
        assert info.status == PeerStatus.CONNECTED
        assert info.latency_ms == 25.5


class TestBroadcastMessage:
    """Tests for BroadcastMessage dataclass."""

    def test_create_broadcast_message(self):
        """Test creating BroadcastMessage instance."""
        msg = BroadcastMessage(
            message_id="msg-123",
            broadcast_type=BroadcastType.NEW_ENTRY,
            payload={"content": "test"},
            origin_node="node-1",
        )
        assert msg.message_id == "msg-123"
        assert msg.broadcast_type == BroadcastType.NEW_ENTRY
        assert msg.payload == {"content": "test"}
        assert msg.ttl == 3

    def test_broadcast_message_to_dict(self):
        """Test serialization to dictionary."""
        msg = BroadcastMessage(
            message_id="msg-456",
            broadcast_type=BroadcastType.NEW_BLOCK,
            payload={"index": 1},
            origin_node="node-2",
            ttl=2,
        )
        data = msg.to_dict()
        assert data["message_id"] == "msg-456"
        assert data["broadcast_type"] == "new_block"
        assert data["ttl"] == 2

    def test_broadcast_message_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "message_id": "msg-789",
            "broadcast_type": "settlement",
            "payload": {"terms": {}},
            "origin_node": "node-3",
            "timestamp": datetime.utcnow().isoformat(),
            "ttl": 1,
            "signature": None,
        }
        msg = BroadcastMessage.from_dict(data)
        assert msg.message_id == "msg-789"
        assert msg.broadcast_type == BroadcastType.SETTLEMENT


class TestPeerRateLimiter:
    """Tests for PeerRateLimiter class."""

    def test_rate_limiter_allows_initial_request(self):
        """Test rate limiter allows first request."""
        limiter = PeerRateLimiter(max_per_minute=10)
        allowed, reason = limiter.check_rate_limit("peer-1")
        assert allowed is True

    def test_rate_limiter_enforces_limit(self):
        """Test rate limiter enforces limit."""
        limiter = PeerRateLimiter(max_per_minute=5, window=60)

        # Make 5 requests (should be allowed)
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit("peer-1")
            assert allowed is True

        # 6th request should be blocked
        allowed, reason = limiter.check_rate_limit("peer-1")
        assert allowed is False
        assert "exceeded" in reason.lower()

    def test_rate_limiter_separate_peers(self):
        """Test rate limiter tracks peers separately."""
        limiter = PeerRateLimiter(max_per_minute=5)

        # Fill up peer-1's limit
        for _ in range(5):
            limiter.check_rate_limit("peer-1")

        # peer-2 should still be allowed
        allowed, _ = limiter.check_rate_limit("peer-2")
        assert allowed is True

    def test_get_peer_rate(self):
        """Test getting current rate for a peer."""
        limiter = PeerRateLimiter()
        limiter.check_rate_limit("peer-1")
        limiter.check_rate_limit("peer-1")
        limiter.check_rate_limit("peer-1")

        rate = limiter.get_peer_rate("peer-1")
        assert rate == 3

    def test_cleanup_removes_old_entries(self):
        """Test cleanup removes old entries."""
        limiter = PeerRateLimiter()
        limiter.peer_counts["old-peer"] = [time.time() - 120]  # 2 minutes old
        limiter.cleanup()
        assert "old-peer" not in limiter.peer_counts


class TestMessageValidator:
    """Tests for MessageValidator class."""

    def test_compute_signature(self):
        """Test HMAC signature computation."""
        validator = MessageValidator(secret_key="test-secret")
        data = {"message_id": "123", "payload": "test"}
        sig = validator.compute_signature(data)
        assert len(sig) == 64  # SHA-256 hex

    def test_compute_signature_consistent(self):
        """Test signature is consistent for same data."""
        validator = MessageValidator(secret_key="test-secret")
        data = {"message_id": "123"}
        sig1 = validator.compute_signature(data)
        sig2 = validator.compute_signature(data)
        assert sig1 == sig2

    def test_verify_signature_valid(self):
        """Test signature verification with valid signature."""
        validator = MessageValidator(secret_key="test-secret")
        data = {"message_id": "123", "payload": "test"}
        data["signature"] = validator.compute_signature(data)
        valid, reason = validator.verify_signature(data)
        assert valid is True

    def test_verify_signature_invalid(self):
        """Test signature verification with invalid signature."""
        validator = MessageValidator(secret_key="test-secret", require_signatures=True)
        data = {"message_id": "123", "signature": "invalid-signature"}
        valid, reason = validator.verify_signature(data)
        assert valid is False

    def test_verify_signature_missing(self):
        """Test signature verification with missing signature."""
        validator = MessageValidator(secret_key="test-secret", require_signatures=True)
        data = {"message_id": "123"}
        valid, reason = validator.verify_signature(data)
        assert valid is False
        assert "missing" in reason.lower()

    def test_validate_timestamp_valid(self):
        """Test timestamp validation with valid timestamp."""
        validator = MessageValidator(secret_key="test")
        valid, _ = validator.validate_timestamp(datetime.utcnow().isoformat())
        assert valid is True

    def test_validate_timestamp_too_old(self):
        """Test timestamp validation with old timestamp."""
        validator = MessageValidator(secret_key="test")
        old_time = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
        valid, reason = validator.validate_timestamp(old_time)
        assert valid is False
        assert "too old" in reason.lower()

    def test_validate_timestamp_future(self):
        """Test timestamp validation with future timestamp."""
        validator = MessageValidator(secret_key="test")
        future_time = (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        valid, reason = validator.validate_timestamp(future_time)
        assert valid is False
        assert "future" in reason.lower()

    def test_check_replay_first_message(self):
        """Test replay check allows first message."""
        validator = MessageValidator(secret_key="test")
        is_new, _ = validator.check_replay("msg-123")
        assert is_new is True

    def test_check_replay_duplicate(self):
        """Test replay check detects duplicate."""
        validator = MessageValidator(secret_key="test")
        validator.check_replay("msg-123")
        is_new, reason = validator.check_replay("msg-123")
        assert is_new is False
        assert "replay" in reason.lower()

    def test_validate_payload_size_valid(self):
        """Test payload size validation with valid size."""
        validator = MessageValidator(secret_key="test")
        valid, _ = validator.validate_payload_size({"small": "payload"})
        assert valid is True

    def test_validate_payload_size_too_large(self):
        """Test payload size validation with large payload."""
        validator = MessageValidator(secret_key="test")
        large_payload = {"data": "x" * (1024 * 1024 + 1)}  # > 1MB
        valid, reason = validator.validate_payload_size(large_payload)
        assert valid is False
        assert "too large" in reason.lower()


class TestBlockValidator:
    """Tests for BlockValidator class."""

    def test_validate_block_structure_valid(self):
        """Test block structure validation with valid block."""
        validator = BlockValidator()
        block = {
            "index": 0,
            "hash": "abc123",
            "previous_hash": "000",
            "timestamp": 1234567890,
            "entries": [],
        }
        valid, _ = validator.validate_block_structure(block)
        assert valid is True

    def test_validate_block_structure_missing_field(self):
        """Test block structure validation with missing field."""
        validator = BlockValidator()
        block = {"index": 0, "hash": "abc123"}  # Missing fields
        valid, reason = validator.validate_block_structure(block)
        assert valid is False
        assert "missing" in reason.lower()

    def test_validate_block_size_valid(self):
        """Test block size validation with valid block."""
        validator = BlockValidator()
        block = {"index": 0, "entries": []}
        valid, _ = validator.validate_block_size(block)
        assert valid is True

    def test_validate_block_size_too_large(self):
        """Test block size validation with large block."""
        validator = BlockValidator()
        block = {"data": "x" * (10 * 1024 * 1024 + 1)}  # > 10MB
        valid, reason = validator.validate_block_size(block)
        assert valid is False
        assert "too large" in reason.lower()

    def test_validate_entry_valid(self):
        """Test entry validation with valid entry."""
        validator = BlockValidator()
        entry = {"content": "test", "author": "user", "timestamp": 123}
        valid, _ = validator.validate_entry(entry)
        assert valid is True

    def test_validate_entry_missing_field(self):
        """Test entry validation with missing field."""
        validator = BlockValidator()
        entry = {"content": "test"}  # Missing author and timestamp
        valid, reason = validator.validate_entry(entry)
        assert valid is False
        assert "missing" in reason.lower()

    def test_validate_chain_link_genesis(self):
        """Test chain link validation for genesis block."""
        validator = BlockValidator()
        block = {"index": 0, "previous_hash": "0"}
        valid, _ = validator.validate_chain_link(block, None)
        assert valid is True

    def test_validate_chain_link_valid(self):
        """Test chain link validation with valid link."""
        validator = BlockValidator()
        prev_block = {"index": 0, "hash": "abc123"}
        block = {"index": 1, "previous_hash": "abc123"}
        valid, _ = validator.validate_chain_link(block, prev_block)
        assert valid is True

    def test_validate_chain_link_invalid_hash(self):
        """Test chain link validation with hash mismatch."""
        validator = BlockValidator()
        prev_block = {"index": 0, "hash": "abc123"}
        block = {"index": 1, "previous_hash": "wrong-hash"}
        valid, reason = validator.validate_chain_link(block, prev_block)
        assert valid is False
        assert "doesn't match" in reason.lower()


class TestPeerSecurityManager:
    """Tests for PeerSecurityManager class."""

    def test_extract_ip_from_endpoint(self):
        """Test IP extraction from endpoint URL."""
        manager = PeerSecurityManager()
        ip = manager.extract_ip("http://192.168.1.1:5000")
        assert ip == "192.168.1.1"

    def test_extract_ip_localhost(self):
        """Test IP extraction for localhost."""
        manager = PeerSecurityManager()
        ip = manager.extract_ip("http://localhost:5000")
        assert ip == "127.0.0.1"

    def test_get_ip_prefix(self):
        """Test IP prefix extraction."""
        manager = PeerSecurityManager()
        prefix = manager.get_ip_prefix("192.168.1.100")
        assert prefix == "192.168"

    def test_check_peer_allowed_initial(self):
        """Test peer is allowed when no limits reached."""
        manager = PeerSecurityManager()
        allowed, _ = manager.check_peer_allowed(
            "peer-1", "http://192.168.1.1:5000", {}
        )
        assert allowed is True

    def test_check_peer_allowed_max_peers(self):
        """Test peer rejected when max peers reached."""
        manager = PeerSecurityManager()
        peers = {f"peer-{i}": {} for i in range(MAX_PEERS)}
        allowed, reason = manager.check_peer_allowed(
            "new-peer", "http://10.0.0.1:5000", peers
        )
        assert allowed is False
        assert "maximum" in reason.lower()

    def test_record_violation(self):
        """Test recording security violation."""
        manager = PeerSecurityManager()
        should_ban, _ = manager.record_violation("peer-1", "invalid_message")
        # Single violation shouldn't trigger ban
        assert should_ban is False

    def test_record_violation_triggers_ban(self):
        """Test multiple violations trigger ban."""
        manager = PeerSecurityManager()
        # Record many serious violations
        for _ in range(10):
            manager.record_violation("peer-1", "invalid_chain")  # Weight: 5

        should_ban, _ = manager.record_violation("peer-1", "invalid_chain")
        assert should_ban is True

    def test_ban_peer(self):
        """Test banning a peer."""
        manager = PeerSecurityManager()
        manager.ban_peer("peer-1", "test reason")
        assert manager.is_banned("peer-1") is True

    def test_is_banned_expired(self):
        """Test ban expiration."""
        manager = PeerSecurityManager()
        manager.banned_until["peer-1"] = datetime.utcnow() - timedelta(hours=1)
        assert manager.is_banned("peer-1") is False

    def test_check_eclipse_attack_safe(self):
        """Test eclipse attack detection with diverse peers."""
        manager = PeerSecurityManager()
        peers = {}
        for i in range(5):
            peer_info = MagicMock()
            peer_info.endpoint = f"http://192.{i}.1.1:5000"
            peers[f"peer-{i}"] = peer_info

        is_safe, _ = manager.check_eclipse_attack(peers)
        assert is_safe is True


class TestP2PNetwork:
    """Tests for P2PNetwork class."""

    def test_init_defaults(self):
        """Test P2PNetwork initialization with defaults."""
        with patch("p2p_network.requests", None):
            network = P2PNetwork()
            assert network.node_id is not None
            assert network.role == NodeRole.FULL_NODE
            assert network.consensus_mode == ConsensusMode.PERMISSIONLESS

    def test_init_custom_values(self):
        """Test P2PNetwork initialization with custom values."""
        network = P2PNetwork(
            node_id="custom-node",
            endpoint="http://example.com:5000",
            role=NodeRole.MEDIATOR,
            consensus_mode=ConsensusMode.DPOS,
        )
        assert network.node_id == "custom-node"
        assert network.endpoint == "http://example.com:5000"
        assert network.role == NodeRole.MEDIATOR

    def test_get_connected_peers_empty(self):
        """Test getting connected peers when none exist."""
        network = P2PNetwork()
        peers = network.get_connected_peers()
        assert peers == []

    def test_get_connected_peers_filters_status(self):
        """Test connected peers filters by status."""
        network = P2PNetwork()
        network.peers["peer-1"] = PeerInfo(
            peer_id="peer-1",
            endpoint="http://localhost",
            status=PeerStatus.CONNECTED,
        )
        network.peers["peer-2"] = PeerInfo(
            peer_id="peer-2",
            endpoint="http://localhost",
            status=PeerStatus.DISCONNECTED,
        )

        connected = network.get_connected_peers()
        assert len(connected) == 1
        assert connected[0].peer_id == "peer-1"

    def test_get_mediator_peers(self):
        """Test getting mediator peers."""
        network = P2PNetwork()
        network.peers["peer-1"] = PeerInfo(
            peer_id="peer-1",
            endpoint="http://localhost",
            role=NodeRole.MEDIATOR,
            status=PeerStatus.CONNECTED,
        )
        network.peers["peer-2"] = PeerInfo(
            peer_id="peer-2",
            endpoint="http://localhost",
            role=NodeRole.FULL_NODE,
            status=PeerStatus.CONNECTED,
        )

        mediators = network.get_mediator_peers()
        assert len(mediators) == 1
        assert mediators[0].peer_id == "peer-1"

    def test_disconnect_peer(self):
        """Test disconnecting a peer."""
        network = P2PNetwork()
        network.peers["peer-1"] = PeerInfo(
            peer_id="peer-1",
            endpoint="http://localhost",
            status=PeerStatus.CONNECTED,
        )

        network.disconnect_peer("peer-1")
        assert "peer-1" not in network.peers

    def test_ban_peer(self):
        """Test banning a peer."""
        network = P2PNetwork()
        network.peers["peer-1"] = PeerInfo(
            peer_id="peer-1",
            endpoint="http://localhost",
            status=PeerStatus.CONNECTED,
        )

        network.ban_peer("peer-1", "test reason")
        assert "peer-1" not in network.peers
        assert "peer-1" in network.banned_peers

    def test_get_node_info(self):
        """Test getting node info."""
        network = P2PNetwork(node_id="test-node")
        info = network.get_node_info()

        assert info["node_id"] == "test-node"
        assert "endpoint" in info
        assert "role" in info
        assert "capabilities" in info

    def test_get_network_stats(self):
        """Test getting network statistics."""
        network = P2PNetwork()
        stats = network.get_network_stats()

        assert "node_id" in stats
        assert "peer_count" in stats
        assert "stats" in stats
        assert "sync_state" in stats


class TestSyncState:
    """Tests for SyncState dataclass."""

    def test_sync_state_defaults(self):
        """Test SyncState default values."""
        state = SyncState()
        assert state.is_syncing is False
        assert state.sync_target_height == 0
        assert state.sync_current_height == 0
        assert state.sync_peer is None

    def test_sync_state_with_values(self):
        """Test SyncState with values."""
        state = SyncState(
            is_syncing=True,
            sync_target_height=100,
            sync_current_height=50,
            sync_peer="peer-1",
        )
        assert state.is_syncing is True
        assert state.sync_target_height == 100


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_handle_broadcast_invalid_message(self):
        """Test handling broadcast with invalid message structure."""
        network = P2PNetwork()
        success, reason = network.handle_broadcast({}, "peer-1")
        assert success is False

    def test_rate_limiter_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = PeerRateLimiter(max_per_minute=1000)
        errors = []

        def make_requests():
            try:
                for _ in range(100):
                    limiter.check_rate_limit("peer-1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=make_requests) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_message_validator_thread_safety(self):
        """Test message validator is thread-safe."""
        validator = MessageValidator(secret_key="test")
        errors = []

        def check_replays():
            try:
                for i in range(100):
                    validator.check_replay(f"msg-{threading.current_thread().name}-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=check_replays, name=f"t-{i}") for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_p2p_network_start_stop(self):
        """Test P2P network start and stop."""
        network = P2PNetwork()

        # Start should work
        network.start()
        assert network._running is True

        # Stop should work
        network.stop()
        assert network._running is False
