"""
Tests for NAT traversal (STUN/TURN) functionality.
"""

import os
import socket
import struct
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


from nat_traversal import (
    STUN_ATTR_XOR_MAPPED_ADDRESS,
    STUN_BINDING_REQUEST,
    STUN_BINDING_RESPONSE,
    # Protocol constants
    STUN_MAGIC_COOKIE,
    CandidateGatherer,
    CandidateType,
    ICECandidate,
    NATConnectionState,
    NATDetector,
    NATInfo,
    NATTraversalManager,
    # Enums
    NATType,
    # Classes
    STUNClient,
    # Data classes
    STUNServer,
    TURNAllocation,
    TURNClient,
    TURNServer,
    create_nat_manager_from_env,
    # Helper functions
    load_nat_config_from_env,
)


class TestSTUNServer:
    """Tests for STUNServer data class."""

    def test_from_uri_basic(self):
        """Test parsing basic host:port URI."""
        server = STUNServer.from_uri("stun.example.com:3478")
        assert server.host == "stun.example.com"
        assert server.port == 3478

    def test_from_uri_with_stun_prefix(self):
        """Test parsing stun: prefixed URI."""
        server = STUNServer.from_uri("stun:stun.l.google.com:19302")
        assert server.host == "stun.l.google.com"
        assert server.port == 19302

    def test_from_uri_default_port(self):
        """Test default port assignment."""
        server = STUNServer.from_uri("stun.example.com")
        assert server.host == "stun.example.com"
        assert server.port == 3478


class TestTURNServer:
    """Tests for TURNServer data class."""

    def test_from_uri_basic(self):
        """Test parsing basic TURN URI."""
        server = TURNServer.from_uri("turn:turn.example.com:3478", username="user", password="pass")
        assert server.host == "turn.example.com"
        assert server.port == 3478
        assert server.username == "user"
        assert server.password == "pass"
        assert server.transport == "udp"

    def test_from_uri_with_transport(self):
        """Test parsing TURN URI with transport parameter."""
        server = TURNServer.from_uri("turn:relay.example.com:443?transport=tcp")
        assert server.host == "relay.example.com"
        assert server.port == 443
        assert server.transport == "tcp"

    def test_from_uri_turns_tls(self):
        """Test parsing TURNS (TLS) URI."""
        server = TURNServer.from_uri("turns:secure.example.com:5349")
        assert server.host == "secure.example.com"
        assert server.port == 5349
        assert server.transport == "tls"


class TestICECandidate:
    """Tests for ICECandidate data class."""

    def test_to_sdp(self):
        """Test SDP formatting of ICE candidate."""
        candidate = ICECandidate(
            foundation="host0",
            component=1,
            transport="udp",
            priority=126 * (2**24) + 65535 * (2**8) + 255,
            address="192.168.1.100",
            port=5000,
            candidate_type=CandidateType.HOST,
        )

        sdp = candidate.to_sdp()
        assert "candidate:host0" in sdp
        assert "192.168.1.100" in sdp
        assert "5000" in sdp
        assert "typ host" in sdp

    def test_to_sdp_with_related(self):
        """Test SDP formatting with related address."""
        candidate = ICECandidate(
            foundation="srflx0",
            component=1,
            transport="udp",
            priority=100 * (2**24) + 65535 * (2**8) + 255,
            address="203.0.113.50",
            port=50000,
            candidate_type=CandidateType.SERVER_REFLEXIVE,
            related_address="192.168.1.100",
            related_port=5000,
        )

        sdp = candidate.to_sdp()
        assert "typ srflx" in sdp
        assert "raddr 192.168.1.100" in sdp
        assert "rport 5000" in sdp

    def test_to_dict(self):
        """Test dictionary conversion."""
        candidate = ICECandidate(
            foundation="relay0",
            component=1,
            transport="udp",
            priority=1000,
            address="10.0.0.1",
            port=3478,
            candidate_type=CandidateType.RELAY,
        )

        data = candidate.to_dict()
        assert data["foundation"] == "relay0"
        assert data["address"] == "10.0.0.1"
        assert data["type"] == "relay"


class TestNATInfo:
    """Tests for NATInfo data class."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        info = NATInfo(
            nat_type=NATType.FULL_CONE,
            external_ip="203.0.113.50",
            external_port=50000,
            internal_ip="192.168.1.100",
            stun_server_used="stun.example.com:3478",
        )

        data = info.to_dict()
        assert data["nat_type"] == "full_cone"
        assert data["external_ip"] == "203.0.113.50"
        assert data["external_port"] == 50000


class TestTURNAllocation:
    """Tests for TURNAllocation data class."""

    def test_is_expired(self):
        """Test expiration check."""
        # Not expired
        allocation = TURNAllocation(
            relay_address="10.0.0.1",
            relay_port=49152,
            server=TURNServer(host="turn.example.com", port=3478),
            expires_at=datetime.utcnow() + timedelta(seconds=300),
        )
        assert not allocation.is_expired()

        # Expired
        allocation.expires_at = datetime.utcnow() - timedelta(seconds=10)
        assert allocation.is_expired()

    def test_needs_refresh(self):
        """Test refresh check."""
        allocation = TURNAllocation(
            relay_address="10.0.0.1",
            relay_port=49152,
            server=TURNServer(host="turn.example.com", port=3478),
            expires_at=datetime.utcnow() + timedelta(seconds=600),
        )
        # Plenty of time left
        assert not allocation.needs_refresh()

        # Less than refresh interval (300s)
        allocation.expires_at = datetime.utcnow() + timedelta(seconds=200)
        assert allocation.needs_refresh()


class TestSTUNClient:
    """Tests for STUN client implementation."""

    def test_create_transaction_id(self):
        """Test transaction ID generation."""
        client = STUNClient()
        tid = client._create_transaction_id()

        assert len(tid) == 12
        assert isinstance(tid, bytes)

    def test_build_binding_request(self):
        """Test STUN binding request construction."""
        client = STUNClient()
        request = client._build_binding_request()

        # Verify header structure
        assert len(request) == 20  # 20-byte header, no attributes

        # Parse header
        msg_type, msg_len, magic = struct.unpack(">HHI", request[:8])
        assert msg_type == STUN_BINDING_REQUEST
        assert msg_len == 0
        assert magic == STUN_MAGIC_COOKIE

    def test_parse_binding_response_valid(self):
        """Test parsing valid STUN binding response."""
        client = STUNClient()
        client._transaction_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c"

        # Build a mock response with XOR-MAPPED-ADDRESS
        # Header: type=0x0101, len=12, magic=0x2112A442
        header = struct.pack(">HHI", STUN_BINDING_RESPONSE, 12, STUN_MAGIC_COOKIE)

        # XOR-MAPPED-ADDRESS attribute
        # Type=0x0020, Length=8
        # Family=0x01 (IPv4), XOR'd port, XOR'd address
        test_ip = "203.0.113.50"
        test_port = 50000
        xor_port = test_port ^ (STUN_MAGIC_COOKIE >> 16)
        ip_bytes = socket.inet_aton(test_ip)
        ip_int = struct.unpack(">I", ip_bytes)[0]
        xor_ip = ip_int ^ STUN_MAGIC_COOKIE

        attr = struct.pack(">HH", STUN_ATTR_XOR_MAPPED_ADDRESS, 8)
        attr += struct.pack(">BBH", 0, 0x01, xor_port)
        attr += struct.pack(">I", xor_ip)

        response = header + client._transaction_id + attr

        result = client._parse_binding_response(response)
        assert result is not None
        assert result[0] == test_ip
        assert result[1] == test_port

    def test_parse_binding_response_wrong_transaction(self):
        """Test rejection of response with wrong transaction ID."""
        client = STUNClient()
        client._transaction_id = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c"

        # Build response with different transaction ID
        header = struct.pack(">HHI", STUN_BINDING_RESPONSE, 0, STUN_MAGIC_COOKIE)
        wrong_tid = b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff"

        response = header + wrong_tid

        result = client._parse_binding_response(response)
        assert result is None

    @patch("socket.socket")
    def test_get_mapped_address_timeout(self, mock_socket_class):
        """Test handling of STUN request timeout."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.recvfrom.side_effect = TimeoutError()

        client = STUNClient(servers=["stun.example.com:3478"])
        result = client.get_mapped_address(timeout=0.1)

        assert result is None


class TestNATDetector:
    """Tests for NAT type detection."""

    @patch.object(STUNClient, "get_mapped_address")
    def test_detect_nat_type_blocked(self, mock_get_mapped):
        """Test detection of blocked UDP."""
        mock_get_mapped.return_value = None

        detector = NATDetector()
        info = detector.detect_nat_type()

        assert info.nat_type == NATType.BLOCKED

    @patch.object(STUNClient, "get_mapped_address")
    @patch.object(NATDetector, "_get_local_ip")
    def test_detect_nat_type_open(self, mock_local_ip, mock_get_mapped):
        """Test detection of open/no NAT."""
        mock_local_ip.return_value = "203.0.113.50"
        mock_get_mapped.return_value = ("203.0.113.50", 5000)

        detector = NATDetector()
        info = detector.detect_nat_type()

        assert info.nat_type == NATType.OPEN
        assert info.external_ip == "203.0.113.50"

    @patch.object(STUNClient, "get_mapped_address")
    @patch.object(NATDetector, "_get_local_ip")
    def test_detect_nat_type_behind_nat(self, mock_local_ip, mock_get_mapped):
        """Test detection of NAT (different internal/external IP)."""
        mock_local_ip.return_value = "192.168.1.100"
        mock_get_mapped.return_value = ("203.0.113.50", 50000)

        detector = NATDetector(stun_servers=["server1:3478"])
        info = detector.detect_nat_type()

        assert info.nat_type != NATType.OPEN
        assert info.external_ip == "203.0.113.50"
        assert info.internal_ip == "192.168.1.100"

    def test_cache_expiry(self):
        """Test that cached NAT info is used within expiry."""
        detector = NATDetector()

        # Manually set cached info
        cached_info = NATInfo(nat_type=NATType.FULL_CONE, external_ip="1.2.3.4", external_port=5000)
        detector._cached_info = cached_info
        detector._cache_expiry = datetime.utcnow() + timedelta(minutes=10)

        # Should return cached info without querying
        info = detector.detect_nat_type(force_refresh=False)
        assert info.external_ip == "1.2.3.4"


class TestCandidateGatherer:
    """Tests for ICE candidate gathering."""

    def test_calculate_priority(self):
        """Test ICE priority calculation."""
        gatherer = CandidateGatherer()

        # Host should have highest priority
        host_priority = gatherer._calculate_priority(CandidateType.HOST)
        srflx_priority = gatherer._calculate_priority(CandidateType.SERVER_REFLEXIVE)
        relay_priority = gatherer._calculate_priority(CandidateType.RELAY)

        assert host_priority > srflx_priority
        assert srflx_priority > relay_priority

    @patch.object(CandidateGatherer, "_get_local_addresses")
    @patch.object(STUNClient, "get_mapped_address")
    def test_gather_host_candidates(self, mock_stun, mock_local):
        """Test gathering of host candidates."""
        mock_local.return_value = [("192.168.1.100", 0)]
        mock_stun.return_value = None  # No STUN response

        gatherer = CandidateGatherer()
        candidates = gatherer.gather_candidates(gather_relay=False)

        assert len(candidates) >= 1
        host_candidates = [c for c in candidates if c.candidate_type == CandidateType.HOST]
        assert len(host_candidates) >= 1
        assert host_candidates[0].address == "192.168.1.100"

    @patch.object(CandidateGatherer, "_get_local_addresses")
    @patch.object(STUNClient, "get_mapped_address")
    def test_gather_srflx_candidates(self, mock_stun, mock_local):
        """Test gathering of server-reflexive candidates."""
        mock_local.return_value = [("192.168.1.100", 0)]
        mock_stun.return_value = ("203.0.113.50", 50000)

        gatherer = CandidateGatherer()
        candidates = gatherer.gather_candidates(gather_relay=False)

        srflx_candidates = [
            c for c in candidates if c.candidate_type == CandidateType.SERVER_REFLEXIVE
        ]
        assert len(srflx_candidates) == 1
        assert srflx_candidates[0].address == "203.0.113.50"

    def test_candidates_sorted_by_priority(self):
        """Test that candidates are sorted by priority (highest first)."""
        gatherer = CandidateGatherer()
        gatherer._candidates = [
            ICECandidate("r0", 1, "udp", 100, "10.0.0.1", 3478, CandidateType.RELAY),
            ICECandidate("h0", 1, "udp", 1000, "192.168.1.1", 5000, CandidateType.HOST),
            ICECandidate("s0", 1, "udp", 500, "203.0.113.1", 50000, CandidateType.SERVER_REFLEXIVE),
        ]

        gatherer._candidates.sort(key=lambda c: c.priority, reverse=True)
        candidates = gatherer.get_candidates()

        assert candidates[0].candidate_type == CandidateType.HOST
        assert candidates[1].candidate_type == CandidateType.SERVER_REFLEXIVE
        assert candidates[2].candidate_type == CandidateType.RELAY


class TestNATTraversalManager:
    """Tests for high-level NAT traversal manager."""

    def test_can_traverse_open_nat(self):
        """Test traversal compatibility with open NAT."""
        manager = NATTraversalManager(enable_relay=False)
        manager._nat_info = NATInfo(nat_type=NATType.OPEN, external_ip="1.2.3.4")

        # Open NAT can connect to anything
        assert manager.can_traverse(NATType.OPEN)
        assert manager.can_traverse(NATType.FULL_CONE)
        assert manager.can_traverse(NATType.SYMMETRIC)

    def test_can_traverse_symmetric_to_symmetric(self):
        """Test that symmetric-to-symmetric requires relay."""
        manager = NATTraversalManager(enable_relay=True)
        manager._nat_info = NATInfo(nat_type=NATType.SYMMETRIC, external_ip="1.2.3.4")

        # Symmetric-to-symmetric typically fails
        assert not manager.can_traverse(NATType.SYMMETRIC)
        assert manager.needs_relay(NATType.SYMMETRIC)

    def test_can_traverse_cone_types(self):
        """Test traversal between cone NAT types."""
        manager = NATTraversalManager()
        manager._nat_info = NATInfo(nat_type=NATType.RESTRICTED_CONE, external_ip="1.2.3.4")

        # Cone types can usually work together
        assert manager.can_traverse(NATType.FULL_CONE)
        assert manager.can_traverse(NATType.PORT_RESTRICTED_CONE)

    def test_get_connection_info(self):
        """Test connection info export."""
        manager = NATTraversalManager()
        manager._nat_info = NATInfo(
            nat_type=NATType.FULL_CONE, external_ip="203.0.113.50", external_port=50000
        )
        manager._candidates = [
            ICECandidate("h0", 1, "udp", 1000, "192.168.1.100", 5000, CandidateType.HOST)
        ]
        manager._state = NATConnectionState.CHECKING

        info = manager.get_connection_info()

        assert info["nat_type"] == "full_cone"
        assert info["external_address"]["ip"] == "203.0.113.50"
        assert len(info["candidates"]) == 1
        assert info["state"] == "checking"

    def test_get_best_candidate(self):
        """Test getting highest priority candidate."""
        manager = NATTraversalManager()
        # Candidates should be sorted by priority (highest first)
        manager._candidates = [
            ICECandidate("h0", 1, "udp", 1000, "192.168.1.1", 5000, CandidateType.HOST),
            ICECandidate("r0", 1, "udp", 100, "10.0.0.1", 3478, CandidateType.RELAY),
        ]

        best = manager.get_best_candidate()
        assert best.candidate_type == CandidateType.HOST

    def test_get_relay_address(self):
        """Test getting relay address."""
        manager = NATTraversalManager()
        manager._candidates = [
            ICECandidate("h0", 1, "udp", 1000, "192.168.1.1", 5000, CandidateType.HOST),
            ICECandidate("r0", 1, "udp", 100, "10.0.0.1", 3478, CandidateType.RELAY),
        ]

        relay = manager.get_relay_address()
        assert relay == ("10.0.0.1", 3478)

    def test_no_relay_when_not_present(self):
        """Test relay address returns None when no relay candidate."""
        manager = NATTraversalManager()
        manager._candidates = [
            ICECandidate("h0", 1, "udp", 1000, "192.168.1.1", 5000, CandidateType.HOST),
        ]

        relay = manager.get_relay_address()
        assert relay is None


class TestConfigLoading:
    """Tests for environment configuration loading."""

    def test_load_default_stun_servers(self):
        """Test default STUN servers are loaded."""
        # Clear any existing env vars
        for key in ["NATLANGCHAIN_NAT_ENABLED", "NATLANGCHAIN_STUN_SERVERS"]:
            os.environ.pop(key, None)

        config = load_nat_config_from_env()

        assert config["enabled"]  # Default is true
        assert len(config["stun_servers"]) > 0
        assert "stun.l.google.com" in config["stun_servers"][0]

    def test_load_custom_stun_servers(self):
        """Test loading custom STUN servers from env."""
        os.environ["NATLANGCHAIN_STUN_SERVERS"] = "stun1.example.com:3478,stun2.example.com:19302"

        try:
            config = load_nat_config_from_env()
            assert len(config["stun_servers"]) == 2
            assert "stun1.example.com:3478" in config["stun_servers"]
        finally:
            os.environ.pop("NATLANGCHAIN_STUN_SERVERS", None)

    def test_load_turn_servers(self):
        """Test loading TURN servers from env."""
        os.environ["NATLANGCHAIN_TURN_SERVERS"] = "turn:relay.example.com:3478"
        os.environ["NATLANGCHAIN_TURN_USERNAME"] = "testuser"
        os.environ["NATLANGCHAIN_TURN_PASSWORD"] = "testpass"

        try:
            config = load_nat_config_from_env()
            assert len(config["turn_servers"]) == 1
            assert config["turn_servers"][0].host == "relay.example.com"
            assert config["turn_servers"][0].username == "testuser"
        finally:
            os.environ.pop("NATLANGCHAIN_TURN_SERVERS", None)
            os.environ.pop("NATLANGCHAIN_TURN_USERNAME", None)
            os.environ.pop("NATLANGCHAIN_TURN_PASSWORD", None)

    def test_nat_disabled(self):
        """Test NAT traversal can be disabled."""
        os.environ["NATLANGCHAIN_NAT_ENABLED"] = "false"

        try:
            config = load_nat_config_from_env()
            assert not config["enabled"]
        finally:
            os.environ.pop("NATLANGCHAIN_NAT_ENABLED", None)

    def test_create_manager_when_disabled(self):
        """Test manager creation returns None when disabled."""
        os.environ["NATLANGCHAIN_NAT_ENABLED"] = "false"

        try:
            manager = create_nat_manager_from_env()
            assert manager is None
        finally:
            os.environ.pop("NATLANGCHAIN_NAT_ENABLED", None)


class TestP2PIntegration:
    """Tests for P2P network integration with NAT traversal."""

    def test_p2p_network_with_nat_disabled(self):
        """Test P2P network initialization with NAT disabled."""
        from p2p_network import P2PNetwork

        network = P2PNetwork(enable_nat_traversal=False)

        assert network.nat_manager is None
        assert not network._nat_initialized

    def test_p2p_network_node_info_includes_nat(self):
        """Test that node info includes NAT traversal data when enabled."""
        from p2p_network import P2PNetwork

        network = P2PNetwork(enable_nat_traversal=False)
        info = network.get_node_info()

        # Without NAT, should not have nat_info
        assert "nat_traversal" not in info.get("capabilities", [])

    def test_p2p_network_stats_include_nat(self):
        """Test that network stats include NAT metrics."""
        from p2p_network import P2PNetwork

        network = P2PNetwork(enable_nat_traversal=False)
        stats = network.get_network_stats()

        assert "nat_traversal" in stats
        assert stats["nat_traversal"]["enabled"] is False

    def test_p2p_get_nat_info_when_disabled(self):
        """Test get_nat_info returns None when NAT is disabled."""
        from p2p_network import P2PNetwork

        network = P2PNetwork(enable_nat_traversal=False)

        assert network.get_nat_info() is None
        assert network.get_ice_candidates() == []


class TestNATTypeEnum:
    """Tests for NAT type enumeration."""

    def test_nat_type_values(self):
        """Test NAT type enum values."""
        assert NATType.UNKNOWN.value == "unknown"
        assert NATType.OPEN.value == "open"
        assert NATType.FULL_CONE.value == "full_cone"
        assert NATType.RESTRICTED_CONE.value == "restricted_cone"
        assert NATType.PORT_RESTRICTED_CONE.value == "port_restricted_cone"
        assert NATType.SYMMETRIC.value == "symmetric"
        assert NATType.BLOCKED.value == "blocked"


class TestCandidateTypeEnum:
    """Tests for ICE candidate type enumeration."""

    def test_candidate_type_values(self):
        """Test candidate type enum values match ICE spec."""
        assert CandidateType.HOST.value == "host"
        assert CandidateType.SERVER_REFLEXIVE.value == "srflx"
        assert CandidateType.PEER_REFLEXIVE.value == "prflx"
        assert CandidateType.RELAY.value == "relay"
