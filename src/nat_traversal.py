"""
NatLangChain - NAT Traversal Module

Implements STUN/TURN-based NAT traversal for P2P connectivity:
- NAT type detection (Full Cone, Restricted Cone, Port Restricted, Symmetric)
- STUN client for public IP/port discovery
- TURN relay connection management
- ICE-like candidate gathering and prioritization
- Smart connection fallback strategies

RFC References:
- RFC 5389: STUN (Session Traversal Utilities for NAT)
- RFC 5766: TURN (Traversal Using Relays around NAT)
- RFC 8445: ICE (Interactive Connectivity Establishment)
"""

import hashlib
import hmac
import logging
import os
import secrets
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# STUN Message Types (RFC 5389)
STUN_BINDING_REQUEST = 0x0001
STUN_BINDING_RESPONSE = 0x0101
STUN_BINDING_ERROR = 0x0111

# STUN Attributes (RFC 5389)
STUN_ATTR_MAPPED_ADDRESS = 0x0001
STUN_ATTR_XOR_MAPPED_ADDRESS = 0x0020
STUN_ATTR_ERROR_CODE = 0x0009
STUN_ATTR_SOFTWARE = 0x8022
STUN_ATTR_FINGERPRINT = 0x8028
STUN_ATTR_MESSAGE_INTEGRITY = 0x0008

# TURN Message Types (RFC 5766)
TURN_ALLOCATE_REQUEST = 0x0003
TURN_ALLOCATE_RESPONSE = 0x0103
TURN_ALLOCATE_ERROR = 0x0113
TURN_REFRESH_REQUEST = 0x0004
TURN_REFRESH_RESPONSE = 0x0104
TURN_SEND_INDICATION = 0x0016
TURN_DATA_INDICATION = 0x0017
TURN_CREATE_PERMISSION_REQUEST = 0x0008
TURN_CREATE_PERMISSION_RESPONSE = 0x0108
TURN_CHANNEL_BIND_REQUEST = 0x0009
TURN_CHANNEL_BIND_RESPONSE = 0x0109

# TURN Attributes (RFC 5766)
TURN_ATTR_CHANNEL_NUMBER = 0x000C
TURN_ATTR_LIFETIME = 0x000D
TURN_ATTR_XOR_PEER_ADDRESS = 0x0012
TURN_ATTR_DATA = 0x0013
TURN_ATTR_XOR_RELAYED_ADDRESS = 0x0016
TURN_ATTR_REQUESTED_TRANSPORT = 0x0019
TURN_ATTR_REALM = 0x0014
TURN_ATTR_NONCE = 0x0015
TURN_ATTR_USERNAME = 0x0006

# STUN Magic Cookie (RFC 5389)
STUN_MAGIC_COOKIE = 0x2112A442

# Timeouts
STUN_TIMEOUT = 3.0  # seconds
STUN_RETRY_COUNT = 3
TURN_ALLOCATION_LIFETIME = 600  # seconds (default 10 minutes)
TURN_REFRESH_INTERVAL = 300  # seconds (refresh at 5 minutes)

# Default STUN servers
DEFAULT_STUN_SERVERS = [
    "stun.l.google.com:19302",
    "stun1.l.google.com:19302",
    "stun2.l.google.com:19302",
    "stun.stunprotocol.org:3478",
]

# ICE Candidate priorities (RFC 8445)
ICE_PRIORITY_HOST = 126
ICE_PRIORITY_SERVER_REFLEXIVE = 100
ICE_PRIORITY_PEER_REFLEXIVE = 110
ICE_PRIORITY_RELAY = 0


# =============================================================================
# Enums
# =============================================================================

class NATType(Enum):
    """NAT type classification based on RFC 3489."""
    UNKNOWN = "unknown"
    OPEN = "open"  # No NAT, public IP
    FULL_CONE = "full_cone"  # Endpoint-Independent Mapping, EIF
    RESTRICTED_CONE = "restricted_cone"  # EIM, Address-Dependent Filtering
    PORT_RESTRICTED_CONE = "port_restricted_cone"  # EIM, Address+Port-Dependent Filtering
    SYMMETRIC = "symmetric"  # Address+Port-Dependent Mapping
    BLOCKED = "blocked"  # UDP blocked


class CandidateType(Enum):
    """ICE candidate types (RFC 8445)."""
    HOST = "host"  # Local network interface
    SERVER_REFLEXIVE = "srflx"  # STUN-derived public address
    PEER_REFLEXIVE = "prflx"  # Discovered from peer
    RELAY = "relay"  # TURN relay address


class NATConnectionState(Enum):
    """Connection state for NAT traversal (ICE negotiation).

    Note: This is different from ConnectionState in mobile_deployment.py
    which tracks device connectivity (online/offline/syncing).
    """
    NEW = "new"
    CHECKING = "checking"
    CONNECTED = "connected"
    COMPLETED = "completed"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class STUNServer:
    """STUN server configuration."""
    host: str
    port: int = 3478
    transport: str = "udp"

    @classmethod
    def from_uri(cls, uri: str) -> "STUNServer":
        """Parse STUN URI (stun:host:port or host:port)."""
        if uri.startswith("stun:"):
            uri = uri[5:]
        if uri.startswith("//"):
            uri = uri[2:]

        parts = uri.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 3478

        return cls(host=host, port=port)


@dataclass
class TURNServer:
    """TURN server configuration."""
    host: str
    port: int = 3478
    username: str = ""
    password: str = ""
    transport: str = "udp"  # udp, tcp, tls
    realm: str = ""

    @classmethod
    def from_uri(cls, uri: str, username: str = "", password: str = "") -> "TURNServer":
        """Parse TURN URI (turn:host:port?transport=tcp)."""
        transport = "udp"
        if "?transport=" in uri:
            uri, params = uri.split("?", 1)
            for param in params.split("&"):
                if param.startswith("transport="):
                    transport = param.split("=")[1]

        if uri.startswith("turn:"):
            uri = uri[5:]
        elif uri.startswith("turns:"):
            uri = uri[6:]
            transport = "tls"
        if uri.startswith("//"):
            uri = uri[2:]

        parts = uri.split(":")
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 3478

        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            transport=transport
        )


@dataclass
class ICECandidate:
    """ICE candidate for connectivity checking."""
    foundation: str
    component: int
    transport: str
    priority: int
    address: str
    port: int
    candidate_type: CandidateType
    related_address: str | None = None
    related_port: int | None = None

    def to_sdp(self) -> str:
        """Convert to SDP attribute format."""
        sdp = (
            f"candidate:{self.foundation} {self.component} {self.transport} "
            f"{self.priority} {self.address} {self.port} typ {self.candidate_type.value}"
        )
        if self.related_address and self.related_port:
            sdp += f" raddr {self.related_address} rport {self.related_port}"
        return sdp

    @classmethod
    def from_sdp(cls, sdp: str) -> "ICECandidate":
        """Parse SDP candidate attribute."""
        parts = sdp.replace("candidate:", "").split()

        candidate = cls(
            foundation=parts[0],
            component=int(parts[1]),
            transport=parts[2].lower(),
            priority=int(parts[3]),
            address=parts[4],
            port=int(parts[5]),
            candidate_type=CandidateType(parts[7])
        )

        # Parse optional raddr/rport
        for i, part in enumerate(parts):
            if part == "raddr" and i + 1 < len(parts):
                candidate.related_address = parts[i + 1]
            elif part == "rport" and i + 1 < len(parts):
                candidate.related_port = int(parts[i + 1])

        return candidate

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "foundation": self.foundation,
            "component": self.component,
            "transport": self.transport,
            "priority": self.priority,
            "address": self.address,
            "port": self.port,
            "type": self.candidate_type.value,
            "related_address": self.related_address,
            "related_port": self.related_port
        }


@dataclass
class NATInfo:
    """Information about detected NAT configuration."""
    nat_type: NATType
    external_ip: str | None = None
    external_port: int | None = None
    internal_ip: str | None = None
    internal_port: int | None = None
    mapping_behavior: str | None = None  # endpoint-independent, address-dependent, address+port-dependent
    filtering_behavior: str | None = None  # same categories as mapping
    detected_at: datetime = field(default_factory=datetime.utcnow)
    stun_server_used: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "nat_type": self.nat_type.value,
            "external_ip": self.external_ip,
            "external_port": self.external_port,
            "internal_ip": self.internal_ip,
            "internal_port": self.internal_port,
            "mapping_behavior": self.mapping_behavior,
            "filtering_behavior": self.filtering_behavior,
            "detected_at": self.detected_at.isoformat(),
            "stun_server_used": self.stun_server_used
        }


@dataclass
class TURNAllocation:
    """TURN server allocation state."""
    relay_address: str
    relay_port: int
    server: TURNServer
    lifetime: int = TURN_ALLOCATION_LIFETIME
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    nonce: str = ""
    realm: str = ""

    def is_expired(self) -> bool:
        """Check if allocation has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def needs_refresh(self) -> bool:
        """Check if allocation needs refresh."""
        if self.expires_at is None:
            return False
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()
        return remaining < TURN_REFRESH_INTERVAL


# =============================================================================
# STUN Protocol Implementation
# =============================================================================

class STUNClient:
    """
    STUN (Session Traversal Utilities for NAT) client implementation.

    Implements RFC 5389 for discovering public IP/port mappings and
    detecting NAT type/behavior.
    """

    def __init__(self, servers: list[str] | None = None):
        """
        Initialize STUN client.

        Args:
            servers: List of STUN server URIs (default: Google's public servers)
        """
        self.servers = [
            STUNServer.from_uri(s) for s in (servers or DEFAULT_STUN_SERVERS)
        ]
        self._socket: socket.socket | None = None
        self._transaction_id: bytes | None = None

    def _create_transaction_id(self) -> bytes:
        """Generate random 96-bit transaction ID."""
        return secrets.token_bytes(12)

    def _build_binding_request(self) -> bytes:
        """Build STUN Binding Request message."""
        self._transaction_id = self._create_transaction_id()

        # Message header: type (2) + length (2) + magic cookie (4) + transaction ID (12)
        header = struct.pack(
            ">HHI",
            STUN_BINDING_REQUEST,
            0,  # No attributes yet
            STUN_MAGIC_COOKIE
        )

        return header + self._transaction_id

    def _parse_binding_response(self, data: bytes) -> tuple[str, int] | None:
        """
        Parse STUN Binding Response to extract mapped address.

        Returns:
            Tuple of (ip_address, port) or None if parsing fails
        """
        if len(data) < 20:
            return None

        # Parse header
        msg_type, msg_len, magic = struct.unpack(">HHI", data[:8])

        # Verify response type
        if msg_type != STUN_BINDING_RESPONSE:
            return None

        # Verify magic cookie
        if magic != STUN_MAGIC_COOKIE:
            return None

        # Verify transaction ID
        if data[8:20] != self._transaction_id:
            return None

        # Parse attributes
        offset = 20
        while offset < len(data):
            if offset + 4 > len(data):
                break

            attr_type, attr_len = struct.unpack(">HH", data[offset:offset + 4])
            offset += 4

            if attr_type == STUN_ATTR_XOR_MAPPED_ADDRESS:
                # XOR-MAPPED-ADDRESS (preferred)
                if attr_len >= 8:
                    family = data[offset + 1]
                    xor_port = struct.unpack(">H", data[offset + 2:offset + 4])[0]
                    port = xor_port ^ (STUN_MAGIC_COOKIE >> 16)

                    if family == 0x01:  # IPv4
                        xor_addr = struct.unpack(">I", data[offset + 4:offset + 8])[0]
                        addr_int = xor_addr ^ STUN_MAGIC_COOKIE
                        ip = socket.inet_ntoa(struct.pack(">I", addr_int))
                        return ip, port

            elif attr_type == STUN_ATTR_MAPPED_ADDRESS:
                # MAPPED-ADDRESS (fallback)
                if attr_len >= 8:
                    family = data[offset + 1]
                    port = struct.unpack(">H", data[offset + 2:offset + 4])[0]

                    if family == 0x01:  # IPv4
                        ip = socket.inet_ntoa(data[offset + 4:offset + 8])
                        return ip, port

            # Move to next attribute (with padding to 4-byte boundary)
            offset += attr_len
            if attr_len % 4 != 0:
                offset += 4 - (attr_len % 4)

        return None

    def get_mapped_address(
        self,
        server: STUNServer | None = None,
        local_port: int = 0,
        timeout: float = STUN_TIMEOUT
    ) -> tuple[str, int] | None:
        """
        Query STUN server for mapped (public) address.

        Args:
            server: Specific STUN server to use (None = try all)
            local_port: Local port to bind (0 = any)
            timeout: Timeout in seconds

        Returns:
            Tuple of (public_ip, public_port) or None if failed
        """
        servers_to_try = [server] if server else self.servers

        for srv in servers_to_try:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(timeout)

                if local_port > 0:
                    sock.bind(("", local_port))

                request = self._build_binding_request()
                sock.sendto(request, (srv.host, srv.port))

                for _ in range(STUN_RETRY_COUNT):
                    try:
                        data, _ = sock.recvfrom(1024)
                        result = self._parse_binding_response(data)
                        if result:
                            sock.close()
                            return result
                    except socket.timeout:
                        sock.sendto(request, (srv.host, srv.port))

                sock.close()

            except Exception as e:
                logger.debug(f"STUN query to {srv.host}:{srv.port} failed: {e}")
                continue

        return None

    def get_external_address(self, timeout: float = STUN_TIMEOUT) -> tuple[str, int] | None:
        """
        Get external (public) IP address and port.

        Convenience wrapper around get_mapped_address().

        Returns:
            Tuple of (public_ip, public_port) or None
        """
        return self.get_mapped_address(timeout=timeout)


# =============================================================================
# NAT Type Detection
# =============================================================================

class NATDetector:
    """
    Detects NAT type and behavior using STUN.

    Implements a simplified version of the algorithm from RFC 3489
    to classify NAT behavior for connectivity decisions.
    """

    def __init__(self, stun_servers: list[str] | None = None):
        """
        Initialize NAT detector.

        Args:
            stun_servers: List of STUN server URIs
        """
        self.stun_client = STUNClient(stun_servers)
        self._cached_info: NATInfo | None = None
        self._cache_expiry: datetime | None = None
        self._cache_duration = timedelta(minutes=15)

    def _get_local_ip(self) -> str | None:
        """Get local IP address."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
            sock.close()
            return local_ip
        except Exception:
            return None

    def detect_nat_type(self, force_refresh: bool = False) -> NATInfo:
        """
        Detect NAT type and configuration.

        Uses multiple STUN queries to determine NAT behavior:
        1. Query STUN server A from local port P1
        2. Query STUN server B from same port P1
        3. Compare mapped addresses to classify NAT type

        Args:
            force_refresh: Force new detection even if cached

        Returns:
            NATInfo with detected configuration
        """
        # Check cache
        if not force_refresh and self._cached_info:
            if self._cache_expiry and datetime.utcnow() < self._cache_expiry:
                return self._cached_info

        local_ip = self._get_local_ip()

        # Test 1: Basic STUN query
        result1 = self.stun_client.get_mapped_address()

        if result1 is None:
            # No response - UDP might be blocked
            info = NATInfo(
                nat_type=NATType.BLOCKED,
                internal_ip=local_ip
            )
            self._cached_info = info
            self._cache_expiry = datetime.utcnow() + self._cache_duration
            return info

        external_ip, external_port = result1

        # Check if public IP matches local IP (no NAT)
        if local_ip == external_ip:
            info = NATInfo(
                nat_type=NATType.OPEN,
                external_ip=external_ip,
                external_port=external_port,
                internal_ip=local_ip,
                stun_server_used=f"{self.stun_client.servers[0].host}:{self.stun_client.servers[0].port}"
            )
            self._cached_info = info
            self._cache_expiry = datetime.utcnow() + self._cache_duration
            return info

        # Test 2: Query second server from same local port
        # to detect if mapping is endpoint-independent
        if len(self.stun_client.servers) > 1:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(("", 0))
                local_port = sock.getsockname()[1]
                sock.close()

                result2 = self.stun_client.get_mapped_address(
                    server=self.stun_client.servers[0],
                    local_port=local_port
                )
                result3 = self.stun_client.get_mapped_address(
                    server=self.stun_client.servers[1],
                    local_port=local_port
                )

                if result2 and result3:
                    if result2[1] == result3[1]:
                        # Same port mapped - Endpoint-Independent Mapping
                        # This could be Full Cone, Restricted, or Port Restricted
                        nat_type = NATType.FULL_CONE  # Conservative assumption
                        mapping = "endpoint-independent"
                    else:
                        # Different ports - Symmetric NAT
                        nat_type = NATType.SYMMETRIC
                        mapping = "address+port-dependent"
                else:
                    nat_type = NATType.UNKNOWN
                    mapping = None

            except Exception as e:
                logger.debug(f"NAT type detection test 2 failed: {e}")
                nat_type = NATType.UNKNOWN
                mapping = None
        else:
            # Only one server - can't fully determine type
            nat_type = NATType.UNKNOWN
            mapping = None

        info = NATInfo(
            nat_type=nat_type,
            external_ip=external_ip,
            external_port=external_port,
            internal_ip=local_ip,
            mapping_behavior=mapping,
            stun_server_used=f"{self.stun_client.servers[0].host}:{self.stun_client.servers[0].port}"
        )

        self._cached_info = info
        self._cache_expiry = datetime.utcnow() + self._cache_duration

        logger.info(f"NAT type detected: {nat_type.value} (external: {external_ip}:{external_port})")
        return info

    def get_external_address(self) -> tuple[str, int] | None:
        """
        Get external address using cached detection or new query.

        Returns:
            Tuple of (ip, port) or None
        """
        info = self.detect_nat_type()
        if info.external_ip and info.external_port:
            return info.external_ip, info.external_port
        return None


# =============================================================================
# TURN Client Implementation
# =============================================================================

class TURNClient:
    """
    TURN (Traversal Using Relays around NAT) client implementation.

    Implements RFC 5766 for allocating relay addresses when direct
    peer-to-peer connectivity is not possible.
    """

    def __init__(self, server: TURNServer):
        """
        Initialize TURN client.

        Args:
            server: TURN server configuration
        """
        self.server = server
        self._socket: socket.socket | None = None
        self._transaction_id: bytes | None = None
        self._allocation: TURNAllocation | None = None
        self._refresh_thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    def _create_transaction_id(self) -> bytes:
        """Generate random 96-bit transaction ID."""
        return secrets.token_bytes(12)

    def _compute_message_integrity(self, message: bytes, key: bytes) -> bytes:
        """Compute HMAC-SHA1 message integrity."""
        return hmac.new(key, message, "sha1").digest()

    def _get_long_term_key(self) -> bytes:
        """Compute long-term credential key."""
        # Key = MD5(username:realm:password)
        key_input = f"{self.server.username}:{self.server.realm}:{self.server.password}"
        return hashlib.md5(key_input.encode()).digest()

    def _build_allocate_request(self, nonce: str = "", realm: str = "") -> bytes:
        """Build TURN Allocate Request message."""
        self._transaction_id = self._create_transaction_id()

        attrs = b""

        # REQUESTED-TRANSPORT (UDP = 17)
        transport_attr = struct.pack(">HH", TURN_ATTR_REQUESTED_TRANSPORT, 4)
        transport_attr += struct.pack(">BBH", 17, 0, 0)  # Protocol + RFFU
        attrs += transport_attr

        # Add authentication if we have nonce/realm
        if nonce and realm and self.server.username:
            # USERNAME
            username_bytes = self.server.username.encode()
            padded_len = len(username_bytes)
            if padded_len % 4 != 0:
                padded_len += 4 - (padded_len % 4)
            username_attr = struct.pack(">HH", TURN_ATTR_USERNAME, len(username_bytes))
            username_attr += username_bytes.ljust(padded_len, b"\x00")
            attrs += username_attr

            # REALM
            realm_bytes = realm.encode()
            padded_len = len(realm_bytes)
            if padded_len % 4 != 0:
                padded_len += 4 - (padded_len % 4)
            realm_attr = struct.pack(">HH", TURN_ATTR_REALM, len(realm_bytes))
            realm_attr += realm_bytes.ljust(padded_len, b"\x00")
            attrs += realm_attr

            # NONCE
            nonce_bytes = nonce.encode()
            padded_len = len(nonce_bytes)
            if padded_len % 4 != 0:
                padded_len += 4 - (padded_len % 4)
            nonce_attr = struct.pack(">HH", TURN_ATTR_NONCE, len(nonce_bytes))
            nonce_attr += nonce_bytes.ljust(padded_len, b"\x00")
            attrs += nonce_attr

        # Build header
        header = struct.pack(
            ">HHI",
            TURN_ALLOCATE_REQUEST,
            len(attrs),
            STUN_MAGIC_COOKIE
        )

        message = header + self._transaction_id + attrs

        # Add MESSAGE-INTEGRITY if authenticated
        if nonce and realm and self.server.username:
            # Update length to include MESSAGE-INTEGRITY (24 bytes)
            message = struct.pack(
                ">HHI",
                TURN_ALLOCATE_REQUEST,
                len(attrs) + 24,
                STUN_MAGIC_COOKIE
            ) + self._transaction_id + attrs

            key = self._get_long_term_key()
            integrity = self._compute_message_integrity(message, key)
            integrity_attr = struct.pack(">HH", STUN_ATTR_MESSAGE_INTEGRITY, 20) + integrity
            message += integrity_attr

        return message

    def _parse_allocate_response(self, data: bytes) -> tuple[bool, dict[str, Any]]:
        """
        Parse TURN Allocate Response.

        Returns:
            Tuple of (success, result_dict)
        """
        if len(data) < 20:
            return False, {"error": "Response too short"}

        msg_type, msg_len, magic = struct.unpack(">HHI", data[:8])

        if magic != STUN_MAGIC_COOKIE:
            return False, {"error": "Invalid magic cookie"}

        result: dict[str, Any] = {}

        if msg_type == TURN_ALLOCATE_ERROR:
            # Parse error response for nonce/realm
            offset = 20
            while offset + 4 <= len(data):
                attr_type, attr_len = struct.unpack(">HH", data[offset:offset + 4])
                offset += 4

                if attr_type == TURN_ATTR_REALM:
                    result["realm"] = data[offset:offset + attr_len].rstrip(b"\x00").decode()
                elif attr_type == TURN_ATTR_NONCE:
                    result["nonce"] = data[offset:offset + attr_len].rstrip(b"\x00").decode()
                elif attr_type == STUN_ATTR_ERROR_CODE:
                    if attr_len >= 4:
                        error_class = data[offset + 2] & 0x07
                        error_number = data[offset + 3]
                        result["error_code"] = error_class * 100 + error_number

                padded_len = attr_len
                if padded_len % 4 != 0:
                    padded_len += 4 - (padded_len % 4)
                offset += padded_len

            return False, result

        if msg_type != TURN_ALLOCATE_RESPONSE:
            return False, {"error": f"Unexpected message type: {msg_type}"}

        # Parse success response
        offset = 20
        while offset + 4 <= len(data):
            attr_type, attr_len = struct.unpack(">HH", data[offset:offset + 4])
            offset += 4

            if attr_type == TURN_ATTR_XOR_RELAYED_ADDRESS:
                if attr_len >= 8:
                    family = data[offset + 1]
                    xor_port = struct.unpack(">H", data[offset + 2:offset + 4])[0]
                    port = xor_port ^ (STUN_MAGIC_COOKIE >> 16)

                    if family == 0x01:  # IPv4
                        xor_addr = struct.unpack(">I", data[offset + 4:offset + 8])[0]
                        addr_int = xor_addr ^ STUN_MAGIC_COOKIE
                        ip = socket.inet_ntoa(struct.pack(">I", addr_int))
                        result["relay_address"] = ip
                        result["relay_port"] = port

            elif attr_type == TURN_ATTR_LIFETIME:
                if attr_len >= 4:
                    result["lifetime"] = struct.unpack(">I", data[offset:offset + 4])[0]

            padded_len = attr_len
            if padded_len % 4 != 0:
                padded_len += 4 - (padded_len % 4)
            offset += padded_len

        return "relay_address" in result, result

    def allocate(self, timeout: float = 5.0) -> TURNAllocation | None:
        """
        Allocate a relay address on the TURN server.

        Returns:
            TURNAllocation if successful, None otherwise
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(timeout)
            self._socket.connect((self.server.host, self.server.port))

            # First request (unauthenticated to get nonce/realm)
            request = self._build_allocate_request()
            self._socket.send(request)

            response, _ = self._socket.recvfrom(2048)
            success, result = self._parse_allocate_response(response)

            if not success and "nonce" in result:
                # 401 Unauthorized - retry with credentials
                self.server.realm = result.get("realm", "")
                nonce = result.get("nonce", "")

                request = self._build_allocate_request(nonce=nonce, realm=self.server.realm)
                self._socket.send(request)

                response, _ = self._socket.recvfrom(2048)
                success, result = self._parse_allocate_response(response)

            if success:
                lifetime = result.get("lifetime", TURN_ALLOCATION_LIFETIME)
                self._allocation = TURNAllocation(
                    relay_address=result["relay_address"],
                    relay_port=result["relay_port"],
                    server=self.server,
                    lifetime=lifetime,
                    expires_at=datetime.utcnow() + timedelta(seconds=lifetime),
                    nonce=result.get("nonce", ""),
                    realm=result.get("realm", "")
                )

                logger.info(
                    f"TURN allocation successful: {self._allocation.relay_address}:"
                    f"{self._allocation.relay_port} (lifetime: {lifetime}s)"
                )

                # Start refresh thread
                self._start_refresh_thread()

                return self._allocation

            logger.warning(f"TURN allocation failed: {result}")
            return None

        except Exception as e:
            logger.error(f"TURN allocation error: {e}")
            return None

    def _start_refresh_thread(self):
        """Start background thread to refresh allocation."""
        self._running = True
        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _refresh_loop(self):
        """Background loop to refresh allocation before expiry."""
        while self._running and self._allocation:
            try:
                if self._allocation.needs_refresh():
                    self._refresh_allocation()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"TURN refresh error: {e}")

    def _refresh_allocation(self) -> bool:
        """Refresh the current allocation."""
        if not self._socket or not self._allocation:
            return False

        # Build refresh request (similar to allocate but with REFRESH type)
        self._transaction_id = self._create_transaction_id()

        # LIFETIME attribute
        lifetime_attr = struct.pack(">HHI", TURN_ATTR_LIFETIME, 4, TURN_ALLOCATION_LIFETIME)

        header = struct.pack(
            ">HHI",
            TURN_REFRESH_REQUEST,
            len(lifetime_attr),
            STUN_MAGIC_COOKIE
        )

        request = header + self._transaction_id + lifetime_attr

        try:
            self._socket.send(request)
            response, _ = self._socket.recvfrom(2048)

            msg_type = struct.unpack(">H", response[:2])[0]
            if msg_type == TURN_REFRESH_RESPONSE:
                self._allocation.expires_at = datetime.utcnow() + timedelta(
                    seconds=TURN_ALLOCATION_LIFETIME
                )
                logger.debug("TURN allocation refreshed")
                return True

        except Exception as e:
            logger.error(f"TURN refresh failed: {e}")

        return False

    def deallocate(self):
        """Release the TURN allocation."""
        self._running = False

        if self._socket:
            try:
                # Send refresh with lifetime=0 to deallocate
                self._transaction_id = self._create_transaction_id()
                lifetime_attr = struct.pack(">HHI", TURN_ATTR_LIFETIME, 4, 0)

                header = struct.pack(
                    ">HHI",
                    TURN_REFRESH_REQUEST,
                    len(lifetime_attr),
                    STUN_MAGIC_COOKIE
                )

                request = header + self._transaction_id + lifetime_attr
                self._socket.send(request)

            except Exception as e:
                logger.debug(f"TURN deallocate error: {e}")
            finally:
                self._socket.close()
                self._socket = None

        self._allocation = None
        logger.info("TURN allocation released")

    def get_relay_address(self) -> tuple[str, int] | None:
        """
        Get the relay address for this allocation.

        Returns:
            Tuple of (relay_ip, relay_port) or None
        """
        if self._allocation and not self._allocation.is_expired():
            return self._allocation.relay_address, self._allocation.relay_port
        return None


# =============================================================================
# ICE Candidate Gathering
# =============================================================================

class CandidateGatherer:
    """
    Gathers ICE candidates for connectivity establishment.

    Collects host, server-reflexive (STUN), and relay (TURN) candidates
    with proper prioritization.
    """

    def __init__(
        self,
        stun_servers: list[str] | None = None,
        turn_servers: list[TURNServer] | None = None
    ):
        """
        Initialize candidate gatherer.

        Args:
            stun_servers: List of STUN server URIs
            turn_servers: List of TURNServer configurations
        """
        self.stun_client = STUNClient(stun_servers)
        self.turn_servers = turn_servers or []
        self.turn_clients: list[TURNClient] = []
        self._candidates: list[ICECandidate] = []
        self._lock = threading.Lock()

    def _calculate_priority(
        self,
        candidate_type: CandidateType,
        local_preference: int = 65535,
        component: int = 1
    ) -> int:
        """
        Calculate ICE candidate priority per RFC 8445.

        Priority = (2^24) * type_preference + (2^8) * local_preference + (256 - component)
        """
        type_prefs = {
            CandidateType.HOST: ICE_PRIORITY_HOST,
            CandidateType.SERVER_REFLEXIVE: ICE_PRIORITY_SERVER_REFLEXIVE,
            CandidateType.PEER_REFLEXIVE: ICE_PRIORITY_PEER_REFLEXIVE,
            CandidateType.RELAY: ICE_PRIORITY_RELAY,
        }

        type_pref = type_prefs.get(candidate_type, 0)
        priority = (2**24) * type_pref + (2**8) * local_preference + (256 - component)
        return priority

    def _get_local_addresses(self) -> list[tuple[str, int]]:
        """Get local network addresses."""
        addresses = []

        try:
            # Get hostname-based addresses
            hostname = socket.gethostname()
            for addr in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = addr[4][0]
                if not ip.startswith("127."):
                    addresses.append((ip, 0))
        except Exception:
            pass

        # Try to get default route address
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            default_ip = sock.getsockname()[0]
            sock.close()
            if (default_ip, 0) not in addresses:
                addresses.append((default_ip, 0))
        except Exception:
            pass

        return addresses if addresses else [("127.0.0.1", 0)]

    def gather_candidates(
        self,
        component: int = 1,
        gather_relay: bool = True
    ) -> list[ICECandidate]:
        """
        Gather all ICE candidates.

        Args:
            component: RTP/RTCP component (1 for RTP)
            gather_relay: Whether to gather TURN relay candidates

        Returns:
            List of gathered ICE candidates
        """
        candidates: list[ICECandidate] = []

        # 1. Gather host candidates
        local_addresses = self._get_local_addresses()
        for idx, (ip, _port) in enumerate(local_addresses):
            # Use ephemeral port for actual connection
            candidate = ICECandidate(
                foundation=f"host{idx}",
                component=component,
                transport="udp",
                priority=self._calculate_priority(
                    CandidateType.HOST,
                    local_preference=65535 - idx,
                    component=component
                ),
                address=ip,
                port=0,  # Will be assigned when socket is created
                candidate_type=CandidateType.HOST
            )
            candidates.append(candidate)

        # 2. Gather server-reflexive candidates (STUN)
        result = self.stun_client.get_mapped_address()
        if result:
            external_ip, external_port = result
            # Only add if different from host candidates
            if not any(c.address == external_ip for c in candidates):
                candidate = ICECandidate(
                    foundation="srflx0",
                    component=component,
                    transport="udp",
                    priority=self._calculate_priority(
                        CandidateType.SERVER_REFLEXIVE,
                        component=component
                    ),
                    address=external_ip,
                    port=external_port,
                    candidate_type=CandidateType.SERVER_REFLEXIVE,
                    related_address=local_addresses[0][0] if local_addresses else None,
                    related_port=0
                )
                candidates.append(candidate)

        # 3. Gather relay candidates (TURN)
        if gather_relay:
            for idx, turn_server in enumerate(self.turn_servers):
                turn_client = TURNClient(turn_server)
                allocation = turn_client.allocate()

                if allocation:
                    self.turn_clients.append(turn_client)
                    candidate = ICECandidate(
                        foundation=f"relay{idx}",
                        component=component,
                        transport="udp",
                        priority=self._calculate_priority(
                            CandidateType.RELAY,
                            local_preference=65535 - idx,
                            component=component
                        ),
                        address=allocation.relay_address,
                        port=allocation.relay_port,
                        candidate_type=CandidateType.RELAY,
                        related_address=turn_server.host,
                        related_port=turn_server.port
                    )
                    candidates.append(candidate)

        # Sort by priority (highest first)
        candidates.sort(key=lambda c: c.priority, reverse=True)

        with self._lock:
            self._candidates = candidates

        logger.info(f"Gathered {len(candidates)} ICE candidates")
        return candidates

    def get_candidates(self) -> list[ICECandidate]:
        """Get gathered candidates."""
        with self._lock:
            return list(self._candidates)

    def cleanup(self):
        """Clean up resources (TURN allocations)."""
        for client in self.turn_clients:
            try:
                client.deallocate()
            except Exception as e:
                logger.debug(f"TURN cleanup error: {e}")
        self.turn_clients.clear()


# =============================================================================
# Connection Manager
# =============================================================================

class NATTraversalManager:
    """
    High-level NAT traversal manager for P2P connections.

    Provides smart connection establishment with automatic fallback:
    1. Try direct connection
    2. Try STUN-assisted connection (hole punching)
    3. Fall back to TURN relay
    """

    def __init__(
        self,
        stun_servers: list[str] | None = None,
        turn_servers: list[TURNServer] | None = None,
        enable_relay: bool = True
    ):
        """
        Initialize NAT traversal manager.

        Args:
            stun_servers: STUN server URIs
            turn_servers: TURN server configurations
            enable_relay: Whether to use TURN relay as fallback
        """
        self.stun_servers = stun_servers or DEFAULT_STUN_SERVERS
        self.turn_servers = turn_servers or []
        self.enable_relay = enable_relay

        self.nat_detector = NATDetector(self.stun_servers)
        self.stun_client = STUNClient(self.stun_servers)
        self.candidate_gatherer = CandidateGatherer(
            stun_servers=self.stun_servers,
            turn_servers=self.turn_servers if enable_relay else None
        )

        self._nat_info: NATInfo | None = None
        self._candidates: list[ICECandidate] = []
        self._active_turn_client: TURNClient | None = None
        self._state = NATConnectionState.NEW

    def initialize(self) -> bool:
        """
        Initialize NAT traversal (detect NAT, gather candidates).

        Returns:
            True if initialization successful
        """
        try:
            # Detect NAT type
            self._nat_info = self.nat_detector.detect_nat_type()

            # Gather candidates
            self._candidates = self.candidate_gatherer.gather_candidates(
                gather_relay=self.enable_relay and self._nat_info.nat_type == NATType.SYMMETRIC
            )

            self._state = NATConnectionState.CHECKING
            return True

        except Exception as e:
            logger.error(f"NAT traversal initialization failed: {e}")
            self._state = NATConnectionState.FAILED
            return False

    def get_nat_info(self) -> NATInfo | None:
        """Get detected NAT information."""
        return self._nat_info

    def get_external_address(self) -> tuple[str, int] | None:
        """Get external (public) address."""
        if self._nat_info and self._nat_info.external_ip:
            return self._nat_info.external_ip, self._nat_info.external_port or 0
        return self.stun_client.get_external_address()

    def get_candidates(self) -> list[ICECandidate]:
        """Get gathered ICE candidates."""
        return self._candidates

    def get_best_candidate(self) -> ICECandidate | None:
        """Get highest priority candidate."""
        if self._candidates:
            return self._candidates[0]
        return None

    def get_relay_address(self) -> tuple[str, int] | None:
        """
        Get TURN relay address if available.

        Returns:
            Tuple of (relay_ip, relay_port) or None
        """
        for candidate in self._candidates:
            if candidate.candidate_type == CandidateType.RELAY:
                return candidate.address, candidate.port
        return None

    def can_traverse(self, peer_nat_type: NATType) -> bool:
        """
        Check if NAT traversal is possible with peer's NAT type.

        Args:
            peer_nat_type: Peer's NAT type

        Returns:
            True if direct connection might be possible
        """
        if not self._nat_info:
            return False

        my_type = self._nat_info.nat_type

        # Open NAT can connect to anything
        if my_type == NATType.OPEN or peer_nat_type == NATType.OPEN:
            return True

        # Full cone NAT can connect to most types
        if my_type == NATType.FULL_CONE or peer_nat_type == NATType.FULL_CONE:
            return True

        # Symmetric-to-Symmetric usually requires relay
        if my_type == NATType.SYMMETRIC and peer_nat_type == NATType.SYMMETRIC:
            return False

        # Restricted cone types might work with hole punching
        cone_types = {NATType.RESTRICTED_CONE, NATType.PORT_RESTRICTED_CONE}
        if my_type in cone_types and peer_nat_type in cone_types:
            return True

        return False

    def needs_relay(self, peer_nat_type: NATType) -> bool:
        """
        Check if TURN relay is needed for connectivity.

        Args:
            peer_nat_type: Peer's NAT type

        Returns:
            True if relay is recommended
        """
        return not self.can_traverse(peer_nat_type)

    def get_connection_info(self) -> dict[str, Any]:
        """
        Get connection information for peer exchange.

        Returns:
            Dictionary with NAT info and candidates for signaling
        """
        return {
            "nat_type": self._nat_info.nat_type.value if self._nat_info else "unknown",
            "external_address": {
                "ip": self._nat_info.external_ip if self._nat_info else None,
                "port": self._nat_info.external_port if self._nat_info else None
            },
            "candidates": [c.to_dict() for c in self._candidates],
            "supports_relay": self.enable_relay and len(self.turn_servers) > 0,
            "state": self._state.value
        }

    def cleanup(self):
        """Clean up resources."""
        self.candidate_gatherer.cleanup()
        self._state = NATConnectionState.DISCONNECTED


# =============================================================================
# Configuration Helper
# =============================================================================

def load_nat_config_from_env() -> dict[str, Any]:
    """
    Load NAT traversal configuration from environment variables.

    Environment variables:
        NATLANGCHAIN_NAT_ENABLED: Enable NAT traversal (default: true)
        NATLANGCHAIN_STUN_SERVERS: Comma-separated STUN server URIs
        NATLANGCHAIN_TURN_SERVERS: Comma-separated TURN server URIs
        NATLANGCHAIN_TURN_USERNAME: TURN authentication username
        NATLANGCHAIN_TURN_PASSWORD: TURN authentication password
        NATLANGCHAIN_NAT_RELAY_ENABLED: Enable TURN relay fallback (default: true)

    Returns:
        Configuration dictionary
    """
    config: dict[str, Any] = {
        "enabled": os.getenv("NATLANGCHAIN_NAT_ENABLED", "true").lower() == "true",
        "relay_enabled": os.getenv("NATLANGCHAIN_NAT_RELAY_ENABLED", "true").lower() == "true",
        "stun_servers": [],
        "turn_servers": []
    }

    # Parse STUN servers
    stun_env = os.getenv("NATLANGCHAIN_STUN_SERVERS", "")
    if stun_env:
        config["stun_servers"] = [s.strip() for s in stun_env.split(",") if s.strip()]
    else:
        config["stun_servers"] = DEFAULT_STUN_SERVERS

    # Parse TURN servers
    turn_env = os.getenv("NATLANGCHAIN_TURN_SERVERS", "")
    turn_username = os.getenv("NATLANGCHAIN_TURN_USERNAME", "")
    turn_password = os.getenv("NATLANGCHAIN_TURN_PASSWORD", "")

    if turn_env:
        for turn_uri in turn_env.split(","):
            turn_uri = turn_uri.strip()
            if turn_uri:
                server = TURNServer.from_uri(
                    turn_uri,
                    username=turn_username,
                    password=turn_password
                )
                config["turn_servers"].append(server)

    return config


def create_nat_manager_from_env() -> NATTraversalManager | None:
    """
    Create NAT traversal manager from environment configuration.

    Returns:
        NATTraversalManager instance or None if disabled
    """
    config = load_nat_config_from_env()

    if not config["enabled"]:
        logger.info("NAT traversal is disabled")
        return None

    manager = NATTraversalManager(
        stun_servers=config["stun_servers"],
        turn_servers=config["turn_servers"],
        enable_relay=config["relay_enabled"]
    )

    logger.info(
        f"NAT traversal manager created with {len(config['stun_servers'])} STUN servers "
        f"and {len(config['turn_servers'])} TURN servers"
    )

    return manager
