"""
NatLangChain - Radio Blockchain Transport Layer

A hybrid radio transport system for blockchain data transmission over:
- LoRa: Local mesh networking (10-50km range)
- APRS: Existing amateur radio infrastructure (regional)
- JS8Call: Weak signal HF for global reach
- Olivia: Robust HF mode for difficult conditions

Design principles:
- Minimum viable packet size for radio constraints
- Redundant multi-path transmission
- Error correction and packet reassembly
- Header-only sync with SPV proofs
"""

import hashlib
import json
import time
import struct
import zlib
import base64
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Any, Tuple, Callable, Set
from collections import defaultdict
import threading
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Constants - Radio Constraints
# =============================================================================

# Maximum Transmission Unit (bytes) for each transport
MTU_LORA = 250          # LoRa typical packet size
MTU_APRS = 256          # AX.25 max payload
MTU_JS8CALL = 80        # JS8Call practical message limit (chars)
MTU_OLIVIA = 128        # Olivia practical limit per transmission

# Common MTU - lowest common denominator for universal packets
COMMON_MTU = 64         # Works across all transports

# Packet overhead (header size)
# Format: !BBBBHHIH = 1+1+1+1+2+2+4+2 = 14 bytes
PACKET_HEADER_SIZE = 14  # Fixed header for all packets

# Maximum payload per packet
MAX_PAYLOAD = COMMON_MTU - PACKET_HEADER_SIZE  # 48 bytes

# Block header size (compact format)
COMPACT_BLOCK_HEADER_SIZE = 80  # Similar to Bitcoin's 80-byte header

# Transmission timeouts (seconds)
TIMEOUT_LORA = 5
TIMEOUT_APRS = 30
TIMEOUT_JS8CALL = 120   # JS8Call is slow
TIMEOUT_OLIVIA = 90

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff

# Fragment reassembly timeout (seconds)
FRAGMENT_TIMEOUT = 300  # 5 minutes to receive all fragments


# =============================================================================
# Enums
# =============================================================================

class PacketType(IntEnum):
    """Types of radio packets."""
    BLOCK_HEADER = 0x01      # Compact block header (80 bytes)
    BLOCK_FRAGMENT = 0x02    # Fragment of full block data
    TX_PROOF = 0x03          # SPV transaction proof (Merkle path)
    PEER_ANNOUNCE = 0x04     # Peer discovery announcement
    ACK = 0x05               # Acknowledgment
    NACK = 0x06              # Negative acknowledgment (request retransmit)
    HEARTBEAT = 0x07         # Keep-alive / sync check
    QUERY = 0x08             # Request specific data
    RESPONSE = 0x09          # Response to query


class TransportType(Enum):
    """Available radio transports."""
    LORA = "lora"
    APRS = "aprs"
    JS8CALL = "js8call"
    OLIVIA = "olivia"


class TransportStatus(Enum):
    """Transport connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class Priority(IntEnum):
    """Packet transmission priority."""
    LOW = 0       # Background sync
    NORMAL = 1    # Regular operations
    HIGH = 2      # Time-sensitive
    CRITICAL = 3  # Must deliver (uses all transports)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class RadioPacket:
    """
    Universal radio packet format.

    Header (16 bytes):
    - Version: 1 byte
    - Type: 1 byte
    - Flags: 1 byte (fragmented, compressed, encrypted, ack_required)
    - Priority: 1 byte
    - Sequence: 2 bytes (packet sequence number)
    - Fragment: 2 bytes (fragment index / total fragments)
    - Checksum: 4 bytes (CRC32 of payload)
    - Reserved: 4 bytes

    Payload: Up to 48 bytes (64 - 16 header)
    """
    version: int = 1
    packet_type: PacketType = PacketType.HEARTBEAT
    flags: int = 0
    priority: Priority = Priority.NORMAL
    sequence: int = 0
    fragment_index: int = 0
    fragment_total: int = 1
    checksum: int = 0
    payload: bytes = b''

    # Metadata (not transmitted)
    source: str = ""
    destination: str = ""
    timestamp: float = 0.0
    transport: Optional[TransportType] = None

    # Flag constants
    FLAG_FRAGMENTED = 0x01
    FLAG_COMPRESSED = 0x02
    FLAG_ENCRYPTED = 0x04
    FLAG_ACK_REQUIRED = 0x08

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.checksum == 0 and self.payload:
            self.checksum = zlib.crc32(self.payload) & 0xFFFFFFFF

    @property
    def is_fragmented(self) -> bool:
        return bool(self.flags & self.FLAG_FRAGMENTED)

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & self.FLAG_COMPRESSED)

    @property
    def is_encrypted(self) -> bool:
        return bool(self.flags & self.FLAG_ENCRYPTED)

    @property
    def requires_ack(self) -> bool:
        return bool(self.flags & self.FLAG_ACK_REQUIRED)

    def to_bytes(self) -> bytes:
        """Serialize packet to bytes for transmission."""
        header = struct.pack(
            '!BBBBHHIH',  # Network byte order
            self.version,
            self.packet_type,
            self.flags,
            self.priority,
            self.sequence,
            (self.fragment_index << 8) | (self.fragment_total & 0xFF),
            self.checksum,
            0  # Reserved
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RadioPacket':
        """Deserialize packet from bytes."""
        if len(data) < PACKET_HEADER_SIZE:
            raise ValueError(f"Packet too short: {len(data)} bytes")

        header = struct.unpack('!BBBBHHIH', data[:PACKET_HEADER_SIZE])
        payload = data[PACKET_HEADER_SIZE:]

        fragment_combined = header[5]
        fragment_index = (fragment_combined >> 8) & 0xFF
        fragment_total = fragment_combined & 0xFF

        packet = cls(
            version=header[0],
            packet_type=PacketType(header[1]),
            flags=header[2],
            priority=Priority(header[3]),
            sequence=header[4],
            fragment_index=fragment_index,
            fragment_total=fragment_total,
            checksum=header[6],
            payload=payload
        )

        # Verify checksum
        expected_checksum = zlib.crc32(payload) & 0xFFFFFFFF
        if packet.checksum != expected_checksum:
            logger.warning(f"Checksum mismatch: expected {expected_checksum}, got {packet.checksum}")

        return packet

    def to_base64(self) -> str:
        """Encode packet as base64 string (for text-based transports)."""
        return base64.b64encode(self.to_bytes()).decode('ascii')

    @classmethod
    def from_base64(cls, data: str) -> 'RadioPacket':
        """Decode packet from base64 string."""
        return cls.from_bytes(base64.b64decode(data))


@dataclass
class CompactBlockHeader:
    """
    Compact block header for radio transmission.

    Total: 80 bytes (fits in single LoRa/APRS packet)
    - Version: 4 bytes
    - Previous hash: 32 bytes (SHA256, truncated from full hash)
    - Merkle root: 32 bytes
    - Timestamp: 4 bytes (Unix epoch)
    - Difficulty: 4 bytes
    - Nonce: 4 bytes
    """
    version: int = 1
    previous_hash: bytes = b'\x00' * 32
    merkle_root: bytes = b'\x00' * 32
    timestamp: int = 0
    difficulty: int = 0
    nonce: int = 0

    # Computed fields
    block_index: int = 0
    entry_count: int = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = int(time.time())

    def to_bytes(self) -> bytes:
        """Serialize to 80 bytes."""
        return struct.pack(
            '!I32s32sIII',
            self.version,
            self.previous_hash[:32].ljust(32, b'\x00'),
            self.merkle_root[:32].ljust(32, b'\x00'),
            self.timestamp,
            self.difficulty,
            self.nonce
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CompactBlockHeader':
        """Deserialize from 80 bytes."""
        if len(data) < 80:
            raise ValueError(f"Block header too short: {len(data)} bytes")

        unpacked = struct.unpack('!I32s32sIII', data[:80])
        return cls(
            version=unpacked[0],
            previous_hash=unpacked[1],
            merkle_root=unpacked[2],
            timestamp=unpacked[3],
            difficulty=unpacked[4],
            nonce=unpacked[5]
        )

    def calculate_hash(self) -> bytes:
        """Calculate block header hash."""
        return hashlib.sha256(self.to_bytes()).digest()

    @classmethod
    def from_block(cls, block: Dict[str, Any]) -> 'CompactBlockHeader':
        """Create compact header from full block data."""
        # Calculate merkle root from entries
        entries = block.get('entries', [])
        merkle_root = cls._calculate_merkle_root(entries)

        # Get previous hash (truncate to 32 bytes)
        prev_hash = block.get('previous_hash', '0' * 64)
        prev_hash_bytes = bytes.fromhex(prev_hash[:64].ljust(64, '0'))

        return cls(
            version=1,
            previous_hash=prev_hash_bytes,
            merkle_root=merkle_root,
            timestamp=int(block.get('timestamp', time.time())),
            difficulty=2,  # Default difficulty
            nonce=block.get('nonce', 0),
            block_index=block.get('index', 0),
            entry_count=len(entries)
        )

    @staticmethod
    def _calculate_merkle_root(entries: List[Dict]) -> bytes:
        """Calculate Merkle root from entries."""
        if not entries:
            return b'\x00' * 32

        # Hash each entry
        hashes = []
        for entry in entries:
            entry_str = json.dumps(entry, sort_keys=True)
            entry_hash = hashlib.sha256(entry_str.encode()).digest()
            hashes.append(entry_hash)

        # Build Merkle tree
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # Duplicate last if odd

            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined).digest())
            hashes = new_hashes

        return hashes[0] if hashes else b'\x00' * 32


@dataclass
class SPVProof:
    """
    Simplified Payment Verification proof.

    Contains:
    - Transaction/entry hash
    - Merkle path (list of sibling hashes)
    - Block header reference
    """
    entry_hash: bytes
    merkle_path: List[Tuple[bytes, bool]]  # (hash, is_left)
    block_hash: bytes
    block_height: int

    def verify(self, merkle_root: bytes) -> bool:
        """Verify the proof against a Merkle root."""
        current_hash = self.entry_hash

        for sibling_hash, is_left in self.merkle_path:
            if is_left:
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash
            current_hash = hashlib.sha256(combined).digest()

        return current_hash == merkle_root

    def to_bytes(self) -> bytes:
        """Serialize proof."""
        # Header: entry_hash (32) + block_hash (32) + height (4) + path_len (1)
        header = self.entry_hash + self.block_hash + struct.pack('!IB',
            self.block_height, len(self.merkle_path))

        # Path: each item is 33 bytes (32 hash + 1 position flag)
        path_bytes = b''
        for sibling_hash, is_left in self.merkle_path:
            path_bytes += sibling_hash + struct.pack('!B', 1 if is_left else 0)

        return header + path_bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> 'SPVProof':
        """Deserialize proof."""
        entry_hash = data[:32]
        block_hash = data[32:64]
        block_height, path_len = struct.unpack('!IB', data[64:69])

        merkle_path = []
        offset = 69
        for _ in range(path_len):
            sibling_hash = data[offset:offset + 32]
            is_left = data[offset + 32] == 1
            merkle_path.append((sibling_hash, is_left))
            offset += 33

        return cls(
            entry_hash=entry_hash,
            merkle_path=merkle_path,
            block_hash=block_hash,
            block_height=block_height
        )


@dataclass
class FragmentBuffer:
    """Buffer for reassembling fragmented packets."""
    total_fragments: int
    received: Dict[int, bytes] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    sequence: int = 0

    @property
    def is_complete(self) -> bool:
        return len(self.received) == self.total_fragments

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > FRAGMENT_TIMEOUT

    def add_fragment(self, index: int, data: bytes):
        """Add a fragment to the buffer."""
        self.received[index] = data

    def get_missing(self) -> List[int]:
        """Get list of missing fragment indices."""
        return [i for i in range(self.total_fragments) if i not in self.received]

    def reassemble(self) -> bytes:
        """Reassemble all fragments into original data."""
        if not self.is_complete:
            raise ValueError("Cannot reassemble incomplete buffer")

        return b''.join(self.received[i] for i in range(self.total_fragments))


# =============================================================================
# Transport Base Class
# =============================================================================

class RadioTransport(ABC):
    """Abstract base class for radio transports."""

    def __init__(
        self,
        callsign: str,
        transport_type: TransportType,
        mtu: int = COMMON_MTU
    ):
        """
        Initialize transport.

        Args:
            callsign: Amateur radio callsign (required for ham radio)
            transport_type: Type of transport
            mtu: Maximum transmission unit
        """
        self.callsign = callsign
        self.transport_type = transport_type
        self.mtu = mtu
        self.status = TransportStatus.DISCONNECTED

        # Callbacks
        self._on_receive: Optional[Callable[[RadioPacket], None]] = None
        self._on_status_change: Optional[Callable[[TransportStatus], None]] = None

        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'errors': 0,
            'retries': 0
        }

        # Receive queue
        self._receive_queue: queue.Queue = queue.Queue()

        # Running flag
        self._running = False
        self._receive_thread: Optional[threading.Thread] = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the radio interface."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from the radio interface."""
        pass

    @abstractmethod
    def send(self, packet: RadioPacket, destination: str = "") -> bool:
        """
        Send a packet.

        Args:
            packet: Packet to send
            destination: Optional destination callsign

        Returns:
            True if sent successfully
        """
        pass

    @abstractmethod
    def receive(self, timeout: float = 1.0) -> Optional[RadioPacket]:
        """
        Receive a packet.

        Args:
            timeout: Receive timeout in seconds

        Returns:
            Received packet or None
        """
        pass

    def on_receive(self, callback: Callable[[RadioPacket], None]):
        """Set receive callback."""
        self._on_receive = callback

    def on_status_change(self, callback: Callable[[TransportStatus], None]):
        """Set status change callback."""
        self._on_status_change = callback

    def _set_status(self, status: TransportStatus):
        """Update status and notify callback."""
        self.status = status
        if self._on_status_change:
            self._on_status_change(status)

    def start_receive_loop(self):
        """Start background receive loop."""
        if self._running:
            return

        self._running = True
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def stop_receive_loop(self):
        """Stop background receive loop."""
        self._running = False
        if self._receive_thread:
            self._receive_thread.join(timeout=2.0)

    def _receive_loop(self):
        """Background receive loop."""
        while self._running:
            try:
                packet = self.receive(timeout=1.0)
                if packet and self._on_receive:
                    self._on_receive(packet)
            except Exception as e:
                logger.error(f"Receive error on {self.transport_type.value}: {e}")
                self.stats['errors'] += 1


# =============================================================================
# LoRa Transport
# =============================================================================

class LoRaTransport(RadioTransport):
    """
    LoRa transport adapter.

    Uses LoRa radio for local mesh networking.
    Range: 10-50km typical, 700+ km records
    Data rate: 0.3-27 kbps depending on spreading factor
    """

    def __init__(
        self,
        callsign: str,
        device: str = "/dev/ttyUSB0",
        frequency: float = 915.0,  # MHz (US ISM band)
        spreading_factor: int = 10,
        bandwidth: int = 125000,  # Hz
        coding_rate: int = 5
    ):
        super().__init__(callsign, TransportType.LORA, MTU_LORA)

        self.device = device
        self.frequency = frequency
        self.spreading_factor = spreading_factor
        self.bandwidth = bandwidth
        self.coding_rate = coding_rate

        # LoRa hardware interface (would use actual library in production)
        self._interface = None

    def connect(self) -> bool:
        """Connect to LoRa radio."""
        try:
            self._set_status(TransportStatus.CONNECTING)

            # In production, initialize actual LoRa hardware
            # self._interface = LoRa(self.device)
            # self._interface.set_frequency(self.frequency)
            # self._interface.set_spreading_factor(self.spreading_factor)
            # etc.

            logger.info(f"LoRa connected on {self.device} @ {self.frequency} MHz")
            self._set_status(TransportStatus.CONNECTED)
            return True

        except Exception as e:
            logger.error(f"LoRa connection failed: {e}")
            self._set_status(TransportStatus.ERROR)
            return False

    def disconnect(self):
        """Disconnect from LoRa radio."""
        self._running = False
        if self._interface:
            # self._interface.close()
            self._interface = None
        self._set_status(TransportStatus.DISCONNECTED)

    def send(self, packet: RadioPacket, destination: str = "") -> bool:
        """Send packet over LoRa."""
        if self.status != TransportStatus.CONNECTED:
            return False

        try:
            data = packet.to_bytes()

            # In production: self._interface.send(data)
            # Simulated send
            logger.debug(f"LoRa TX: {len(data)} bytes to {destination or 'broadcast'}")

            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(data)
            return True

        except Exception as e:
            logger.error(f"LoRa send failed: {e}")
            self.stats['errors'] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[RadioPacket]:
        """Receive packet from LoRa."""
        if self.status != TransportStatus.CONNECTED:
            return None

        try:
            # In production: data = self._interface.receive(timeout)
            # Simulated receive - check queue
            try:
                data = self._receive_queue.get(timeout=timeout)
                packet = RadioPacket.from_bytes(data)
                packet.transport = TransportType.LORA

                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(data)
                return packet
            except queue.Empty:
                return None

        except Exception as e:
            logger.error(f"LoRa receive failed: {e}")
            self.stats['errors'] += 1
            return None

    def inject_packet(self, data: bytes):
        """Inject packet into receive queue (for testing)."""
        self._receive_queue.put(data)


# =============================================================================
# APRS Transport
# =============================================================================

class APRSTransport(RadioTransport):
    """
    APRS (Automatic Packet Reporting System) transport.

    Uses existing amateur radio packet infrastructure.
    Range: Regional (through digipeaters/IGates)
    Data rate: 1200 bps typical
    """

    def __init__(
        self,
        callsign: str,
        ssid: int = 0,
        device: str = "/dev/ttyUSB0",
        kiss_mode: bool = True,
        digipeaters: List[str] = None
    ):
        super().__init__(callsign, TransportType.APRS, MTU_APRS)

        self.ssid = ssid
        self.device = device
        self.kiss_mode = kiss_mode
        self.digipeaters = digipeaters or ["WIDE1-1", "WIDE2-1"]

        self._interface = None

    @property
    def full_callsign(self) -> str:
        """Get callsign with SSID."""
        return f"{self.callsign}-{self.ssid}" if self.ssid else self.callsign

    def connect(self) -> bool:
        """Connect to APRS TNC."""
        try:
            self._set_status(TransportStatus.CONNECTING)

            # In production, connect to TNC via KISS or AGWPE
            # self._interface = KISS(self.device)
            # self._interface.start()

            logger.info(f"APRS connected as {self.full_callsign}")
            self._set_status(TransportStatus.CONNECTED)
            return True

        except Exception as e:
            logger.error(f"APRS connection failed: {e}")
            self._set_status(TransportStatus.ERROR)
            return False

    def disconnect(self):
        """Disconnect from APRS."""
        self._running = False
        if self._interface:
            self._interface = None
        self._set_status(TransportStatus.DISCONNECTED)

    def _build_ax25_frame(self, destination: str, payload: bytes) -> bytes:
        """Build AX.25 frame for APRS."""
        # Simplified AX.25 UI frame construction
        # In production, use proper AX.25 library

        # Destination address (7 bytes, space padded, shifted left 1)
        dest_addr = destination.ljust(6)[:6].upper()
        dest_bytes = bytes([ord(c) << 1 for c in dest_addr]) + bytes([0x60])

        # Source address
        src_addr = self.callsign.ljust(6)[:6].upper()
        src_bytes = bytes([ord(c) << 1 for c in src_addr]) + bytes([0x61])

        # Digipeater addresses
        digi_bytes = b''
        for i, digi in enumerate(self.digipeaters):
            digi_call = digi.split('-')[0].ljust(6)[:6].upper()
            digi_ssid = 0x61 if i == len(self.digipeaters) - 1 else 0x60
            digi_bytes += bytes([ord(c) << 1 for c in digi_call]) + bytes([digi_ssid])

        # Control and PID for UI frame
        control_pid = bytes([0x03, 0xF0])

        return dest_bytes + src_bytes + digi_bytes + control_pid + payload

    def send(self, packet: RadioPacket, destination: str = "APNLC1") -> bool:
        """Send packet over APRS."""
        if self.status != TransportStatus.CONNECTED:
            return False

        try:
            # Encode packet as base64 for APRS (text-safe)
            payload = packet.to_base64().encode('ascii')

            # Build AX.25 frame
            frame = self._build_ax25_frame(destination, payload)

            # In production: self._interface.write(frame)
            logger.debug(f"APRS TX: {len(frame)} bytes to {destination}")

            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(frame)
            return True

        except Exception as e:
            logger.error(f"APRS send failed: {e}")
            self.stats['errors'] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[RadioPacket]:
        """Receive packet from APRS."""
        if self.status != TransportStatus.CONNECTED:
            return None

        try:
            # In production: frame = self._interface.read(timeout)
            try:
                data = self._receive_queue.get(timeout=timeout)
                # Decode base64 payload from APRS
                packet = RadioPacket.from_base64(data.decode('ascii'))
                packet.transport = TransportType.APRS

                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(data)
                return packet
            except queue.Empty:
                return None

        except Exception as e:
            logger.error(f"APRS receive failed: {e}")
            self.stats['errors'] += 1
            return None

    def inject_packet(self, data: bytes):
        """Inject packet into receive queue (for testing)."""
        self._receive_queue.put(data)


# =============================================================================
# JS8Call Transport
# =============================================================================

class JS8CallTransport(RadioTransport):
    """
    JS8Call transport adapter.

    Weak signal HF mode for global reach.
    Based on FT8 but allows keyboard-to-keyboard messaging.
    Range: Global (HF propagation)
    Data rate: ~8-50 bps effective
    """

    def __init__(
        self,
        callsign: str,
        host: str = "127.0.0.1",
        port: int = 2442,
        grid: str = "FN20",  # Maidenhead grid square
        speed: str = "normal"  # slow, normal, fast, turbo
    ):
        super().__init__(callsign, TransportType.JS8CALL, MTU_JS8CALL)

        self.host = host
        self.port = port
        self.grid = grid
        self.speed = speed

        self._socket = None
        self._message_queue: Dict[str, List[str]] = defaultdict(list)

    def connect(self) -> bool:
        """Connect to JS8Call API."""
        try:
            self._set_status(TransportStatus.CONNECTING)

            # In production, connect to JS8Call TCP API
            # self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # self._socket.connect((self.host, self.port))

            logger.info(f"JS8Call connected as {self.callsign} @ {self.grid}")
            self._set_status(TransportStatus.CONNECTED)
            return True

        except Exception as e:
            logger.error(f"JS8Call connection failed: {e}")
            self._set_status(TransportStatus.ERROR)
            return False

    def disconnect(self):
        """Disconnect from JS8Call."""
        self._running = False
        if self._socket:
            # self._socket.close()
            self._socket = None
        self._set_status(TransportStatus.DISCONNECTED)

    def _encode_for_js8(self, data: bytes) -> str:
        """Encode binary data for JS8Call transmission."""
        # JS8Call uses uppercase letters, numbers, and limited punctuation
        # Use a radix-64 encoding optimized for JS8Call's character set
        charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-./?@"

        # Convert to base-42 (JS8Call-safe characters)
        result = []
        num = int.from_bytes(data, 'big')

        if num == 0:
            return charset[0]

        while num:
            num, remainder = divmod(num, len(charset))
            result.append(charset[remainder])

        return ''.join(reversed(result))

    def _decode_from_js8(self, text: str) -> bytes:
        """Decode JS8Call-encoded data to binary."""
        charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-./?@"

        num = 0
        for char in text:
            num = num * len(charset) + charset.index(char)

        # Convert back to bytes
        byte_length = (num.bit_length() + 7) // 8
        return num.to_bytes(byte_length, 'big') if byte_length else b'\x00'

    def send(self, packet: RadioPacket, destination: str = "@ALLCALL") -> bool:
        """Send packet over JS8Call."""
        if self.status != TransportStatus.CONNECTED:
            return False

        try:
            # Encode packet for JS8Call
            encoded = self._encode_for_js8(packet.to_bytes())

            # Build JS8Call message
            # Format: DESTINATION: NLC[DATA]
            message = f"{destination}: NLC[{encoded}]"

            # JS8Call API command
            # In production: send to JS8Call API
            api_cmd = {
                "type": "TX.SEND_MESSAGE",
                "value": message,
                "params": {"DIAL": 7078000, "OFFSET": 1000}
            }

            logger.debug(f"JS8Call TX: {len(message)} chars to {destination}")

            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(message)
            return True

        except Exception as e:
            logger.error(f"JS8Call send failed: {e}")
            self.stats['errors'] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[RadioPacket]:
        """Receive packet from JS8Call."""
        if self.status != TransportStatus.CONNECTED:
            return None

        try:
            # In production: read from JS8Call API
            try:
                data = self._receive_queue.get(timeout=timeout)
                # Parse JS8Call message format
                # Expected: CALLSIGN: NLC[DATA]
                if isinstance(data, bytes):
                    data = data.decode('ascii')

                if 'NLC[' in data and ']' in data:
                    start = data.index('NLC[') + 4
                    end = data.index(']', start)
                    encoded = data[start:end]

                    packet_bytes = self._decode_from_js8(encoded)
                    packet = RadioPacket.from_bytes(packet_bytes)
                    packet.transport = TransportType.JS8CALL

                    # Extract source callsign
                    if ':' in data:
                        packet.source = data.split(':')[0].strip()

                    self.stats['packets_received'] += 1
                    self.stats['bytes_received'] += len(data)
                    return packet

            except queue.Empty:
                return None

        except Exception as e:
            logger.error(f"JS8Call receive failed: {e}")
            self.stats['errors'] += 1
            return None

    def inject_packet(self, data: str):
        """Inject message into receive queue (for testing)."""
        self._receive_queue.put(data)


# =============================================================================
# Olivia Transport
# =============================================================================

class OliviaTransport(RadioTransport):
    """
    Olivia MFSK transport adapter.

    Robust HF digital mode with excellent error correction.
    Range: Global (HF propagation)
    Data rate: ~30-60 bps depending on mode (8/250, 16/500, etc.)
    """

    def __init__(
        self,
        callsign: str,
        host: str = "127.0.0.1",
        port: int = 7362,  # Fldigi XML-RPC port
        mode: str = "OLIVIA-8-250",  # 8 tones, 250 Hz bandwidth
        frequency: float = 14.0725  # MHz
    ):
        super().__init__(callsign, TransportType.OLIVIA, MTU_OLIVIA)

        self.host = host
        self.port = port
        self.mode = mode
        self.frequency = frequency

        self._client = None

    def connect(self) -> bool:
        """Connect to Fldigi for Olivia."""
        try:
            self._set_status(TransportStatus.CONNECTING)

            # In production, connect to Fldigi XML-RPC API
            # import xmlrpc.client
            # self._client = xmlrpc.client.ServerProxy(f"http://{self.host}:{self.port}")
            # self._client.modem.set_by_name(self.mode)

            logger.info(f"Olivia connected as {self.callsign} mode {self.mode}")
            self._set_status(TransportStatus.CONNECTED)
            return True

        except Exception as e:
            logger.error(f"Olivia connection failed: {e}")
            self._set_status(TransportStatus.ERROR)
            return False

    def disconnect(self):
        """Disconnect from Fldigi."""
        self._running = False
        self._client = None
        self._set_status(TransportStatus.DISCONNECTED)

    def send(self, packet: RadioPacket, destination: str = "CQ") -> bool:
        """Send packet over Olivia."""
        if self.status != TransportStatus.CONNECTED:
            return False

        try:
            # Encode packet as base64
            encoded = packet.to_base64()

            # Build Olivia message with framing
            # Format: DE CALLSIGN NLC{DATA}
            message = f"DE {self.callsign} NLC{{{encoded}}}"

            # In production: self._client.text.add_tx(message)
            logger.debug(f"Olivia TX: {len(message)} chars")

            self.stats['packets_sent'] += 1
            self.stats['bytes_sent'] += len(message)
            return True

        except Exception as e:
            logger.error(f"Olivia send failed: {e}")
            self.stats['errors'] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[RadioPacket]:
        """Receive packet from Olivia."""
        if self.status != TransportStatus.CONNECTED:
            return None

        try:
            # In production: poll Fldigi receive buffer
            try:
                data = self._receive_queue.get(timeout=timeout)
                if isinstance(data, bytes):
                    data = data.decode('ascii')

                # Parse Olivia message format
                # Expected: DE CALLSIGN NLC{DATA}
                if 'NLC{' in data and '}' in data:
                    start = data.index('NLC{') + 4
                    end = data.index('}', start)
                    encoded = data[start:end]

                    packet = RadioPacket.from_base64(encoded)
                    packet.transport = TransportType.OLIVIA

                    # Extract source callsign
                    if 'DE ' in data:
                        parts = data.split()
                        de_idx = parts.index('DE')
                        if de_idx + 1 < len(parts):
                            packet.source = parts[de_idx + 1]

                    self.stats['packets_received'] += 1
                    self.stats['bytes_received'] += len(data)
                    return packet

            except queue.Empty:
                return None

        except Exception as e:
            logger.error(f"Olivia receive failed: {e}")
            self.stats['errors'] += 1
            return None

    def inject_packet(self, data: str):
        """Inject message into receive queue (for testing)."""
        self._receive_queue.put(data)


# =============================================================================
# Multi-Transport Manager
# =============================================================================

class RadioTransportManager:
    """
    Unified manager for multiple radio transports.

    Features:
    - Automatic failover between transports
    - Parallel transmission for critical packets
    - Fragment reassembly across transports
    - Priority-based routing
    """

    def __init__(self, callsign: str):
        """
        Initialize transport manager.

        Args:
            callsign: Amateur radio callsign
        """
        self.callsign = callsign
        self.transports: Dict[TransportType, RadioTransport] = {}
        self.transport_priority: List[TransportType] = [
            TransportType.LORA,      # Fastest, local
            TransportType.APRS,      # Regional infrastructure
            TransportType.JS8CALL,   # Global, slow
            TransportType.OLIVIA     # Global, robust
        ]

        # Fragment reassembly buffers
        self._fragment_buffers: Dict[int, FragmentBuffer] = {}

        # Sequence number counter
        self._sequence = 0
        self._sequence_lock = threading.Lock()

        # Callbacks
        self._on_packet: Optional[Callable[[RadioPacket], None]] = None
        self._on_block_header: Optional[Callable[[CompactBlockHeader], None]] = None
        self._on_spv_proof: Optional[Callable[[SPVProof], None]] = None

        # Statistics
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'fragments_sent': 0,
            'fragments_received': 0,
            'reassembly_success': 0,
            'reassembly_timeout': 0,
            'transport_failovers': 0
        }

    def add_transport(self, transport: RadioTransport):
        """Add a transport to the manager."""
        self.transports[transport.transport_type] = transport
        transport.on_receive(self._handle_received_packet)

    def connect_all(self) -> Dict[TransportType, bool]:
        """Connect all transports."""
        results = {}
        for transport_type, transport in self.transports.items():
            results[transport_type] = transport.connect()
            if results[transport_type]:
                transport.start_receive_loop()
        return results

    def disconnect_all(self):
        """Disconnect all transports."""
        for transport in self.transports.values():
            transport.stop_receive_loop()
            transport.disconnect()

    def get_active_transports(self) -> List[TransportType]:
        """Get list of connected transports."""
        return [
            t_type for t_type, transport in self.transports.items()
            if transport.status == TransportStatus.CONNECTED
        ]

    def _get_next_sequence(self) -> int:
        """Get next sequence number (thread-safe)."""
        with self._sequence_lock:
            self._sequence = (self._sequence + 1) % 65536
            return self._sequence

    def _fragment_data(self, data: bytes, packet_type: PacketType) -> List[RadioPacket]:
        """Fragment data into multiple packets."""
        fragments = []
        sequence = self._get_next_sequence()

        # Compress data if beneficial
        compressed = zlib.compress(data, level=9)
        use_compressed = len(compressed) < len(data)
        payload_data = compressed if use_compressed else data

        # Calculate number of fragments
        total_fragments = (len(payload_data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD

        for i in range(total_fragments):
            start = i * MAX_PAYLOAD
            end = min(start + MAX_PAYLOAD, len(payload_data))

            flags = RadioPacket.FLAG_FRAGMENTED
            if use_compressed:
                flags |= RadioPacket.FLAG_COMPRESSED

            packet = RadioPacket(
                packet_type=packet_type,
                flags=flags,
                sequence=sequence,
                fragment_index=i,
                fragment_total=total_fragments,
                payload=payload_data[start:end]
            )
            fragments.append(packet)

        return fragments

    def send_packet(
        self,
        packet: RadioPacket,
        priority: Priority = Priority.NORMAL,
        transport: Optional[TransportType] = None,
        destination: str = ""
    ) -> bool:
        """
        Send a packet using appropriate transport(s).

        Args:
            packet: Packet to send
            priority: Transmission priority
            transport: Specific transport to use (None for auto-select)
            destination: Destination identifier

        Returns:
            True if sent on at least one transport
        """
        packet.priority = priority

        # Critical priority: send on all available transports
        if priority == Priority.CRITICAL:
            success = False
            for t in self.get_active_transports():
                if self.transports[t].send(packet, destination):
                    success = True
            self.stats['packets_sent'] += 1 if success else 0
            return success

        # Specific transport requested
        if transport and transport in self.transports:
            if self.transports[transport].status == TransportStatus.CONNECTED:
                success = self.transports[transport].send(packet, destination)
                if success:
                    self.stats['packets_sent'] += 1
                return success

        # Auto-select based on priority order
        for t_type in self.transport_priority:
            if t_type in self.transports:
                t = self.transports[t_type]
                if t.status == TransportStatus.CONNECTED:
                    if t.send(packet, destination):
                        self.stats['packets_sent'] += 1
                        return True
                    else:
                        self.stats['transport_failovers'] += 1

        return False

    def send_block_header(
        self,
        header: CompactBlockHeader,
        priority: Priority = Priority.HIGH
    ) -> bool:
        """Send a compact block header."""
        packet = RadioPacket(
            packet_type=PacketType.BLOCK_HEADER,
            priority=priority,
            payload=header.to_bytes()
        )
        return self.send_packet(packet, priority)

    def send_full_block(
        self,
        block_data: bytes,
        priority: Priority = Priority.NORMAL
    ) -> bool:
        """Send full block data (fragmented)."""
        fragments = self._fragment_data(block_data, PacketType.BLOCK_FRAGMENT)

        success = True
        for fragment in fragments:
            if not self.send_packet(fragment, priority):
                success = False
            self.stats['fragments_sent'] += 1

        return success

    def send_spv_proof(
        self,
        proof: SPVProof,
        priority: Priority = Priority.NORMAL
    ) -> bool:
        """Send an SPV proof."""
        proof_bytes = proof.to_bytes()

        if len(proof_bytes) <= MAX_PAYLOAD:
            packet = RadioPacket(
                packet_type=PacketType.TX_PROOF,
                priority=priority,
                payload=proof_bytes
            )
            return self.send_packet(packet, priority)
        else:
            fragments = self._fragment_data(proof_bytes, PacketType.TX_PROOF)
            success = True
            for fragment in fragments:
                if not self.send_packet(fragment, priority):
                    success = False
            return success

    def request_block_header(self, block_hash: bytes) -> bool:
        """Request a block header by hash."""
        packet = RadioPacket(
            packet_type=PacketType.QUERY,
            payload=b'\x01' + block_hash[:31]  # 0x01 = header query
        )
        return self.send_packet(packet, Priority.NORMAL)

    def _handle_received_packet(self, packet: RadioPacket):
        """Handle received packet from any transport."""
        self.stats['packets_received'] += 1

        # Handle fragmented packets
        if packet.is_fragmented:
            self._handle_fragment(packet)
            return

        # Handle complete packets by type
        if packet.packet_type == PacketType.BLOCK_HEADER:
            self._handle_block_header(packet)
        elif packet.packet_type == PacketType.TX_PROOF:
            self._handle_spv_proof(packet)
        elif packet.packet_type == PacketType.ACK:
            self._handle_ack(packet)
        elif packet.packet_type == PacketType.QUERY:
            self._handle_query(packet)

        # Notify callback
        if self._on_packet:
            self._on_packet(packet)

    def _handle_fragment(self, packet: RadioPacket):
        """Handle a fragmented packet."""
        self.stats['fragments_received'] += 1

        # Get or create buffer
        if packet.sequence not in self._fragment_buffers:
            self._fragment_buffers[packet.sequence] = FragmentBuffer(
                total_fragments=packet.fragment_total,
                sequence=packet.sequence
            )

        buffer = self._fragment_buffers[packet.sequence]

        # Check for expiry
        if buffer.is_expired:
            self.stats['reassembly_timeout'] += 1
            del self._fragment_buffers[packet.sequence]
            buffer = FragmentBuffer(
                total_fragments=packet.fragment_total,
                sequence=packet.sequence
            )
            self._fragment_buffers[packet.sequence] = buffer

        # Add fragment
        buffer.add_fragment(packet.fragment_index, packet.payload)

        # Check if complete
        if buffer.is_complete:
            try:
                data = buffer.reassemble()

                # Decompress if needed
                if packet.is_compressed:
                    data = zlib.decompress(data)

                # Create reassembled packet
                reassembled = RadioPacket(
                    packet_type=packet.packet_type,
                    sequence=packet.sequence,
                    payload=data
                )
                reassembled.transport = packet.transport
                reassembled.source = packet.source

                self.stats['reassembly_success'] += 1
                self._handle_received_packet(reassembled)

            except Exception as e:
                logger.error(f"Fragment reassembly failed: {e}")

            del self._fragment_buffers[packet.sequence]

    def _handle_block_header(self, packet: RadioPacket):
        """Handle received block header."""
        try:
            header = CompactBlockHeader.from_bytes(packet.payload)
            logger.info(f"Received block header: height={header.block_index}, "
                       f"hash={header.calculate_hash().hex()[:16]}...")

            if self._on_block_header:
                self._on_block_header(header)

        except Exception as e:
            logger.error(f"Block header parse error: {e}")

    def _handle_spv_proof(self, packet: RadioPacket):
        """Handle received SPV proof."""
        try:
            proof = SPVProof.from_bytes(packet.payload)
            logger.info(f"Received SPV proof: entry={proof.entry_hash.hex()[:16]}..., "
                       f"height={proof.block_height}")

            if self._on_spv_proof:
                self._on_spv_proof(proof)

        except Exception as e:
            logger.error(f"SPV proof parse error: {e}")

    def _handle_ack(self, packet: RadioPacket):
        """Handle acknowledgment packet."""
        logger.debug(f"Received ACK for sequence {packet.sequence}")

    def _handle_query(self, packet: RadioPacket):
        """Handle data query."""
        if not packet.payload:
            return

        query_type = packet.payload[0]
        query_data = packet.payload[1:]

        logger.debug(f"Received query type {query_type}")
        # Query handling would be implemented here

    def on_packet(self, callback: Callable[[RadioPacket], None]):
        """Set packet receive callback."""
        self._on_packet = callback

    def on_block_header(self, callback: Callable[[CompactBlockHeader], None]):
        """Set block header receive callback."""
        self._on_block_header = callback

    def on_spv_proof(self, callback: Callable[[SPVProof], None]):
        """Set SPV proof receive callback."""
        self._on_spv_proof = callback

    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from all transports."""
        combined = self.stats.copy()
        combined['transports'] = {}

        for t_type, transport in self.transports.items():
            combined['transports'][t_type.value] = {
                'status': transport.status.value,
                **transport.stats
            }

        return combined

    def cleanup_expired_buffers(self):
        """Clean up expired fragment buffers."""
        expired = [
            seq for seq, buf in self._fragment_buffers.items()
            if buf.is_expired
        ]
        for seq in expired:
            self.stats['reassembly_timeout'] += 1
            del self._fragment_buffers[seq]


# =============================================================================
# Radio-Optimized Block Sync
# =============================================================================

class RadioBlockSync:
    """
    Lightweight block synchronization for radio networks.

    Uses header-only sync with on-demand full block retrieval.
    Maintains SPV-style verification for bandwidth efficiency.
    """

    def __init__(
        self,
        transport_manager: RadioTransportManager,
        chain: Optional[Any] = None  # NatLangChain instance
    ):
        """
        Initialize block sync.

        Args:
            transport_manager: Radio transport manager
            chain: Optional NatLangChain instance to sync
        """
        self.transport = transport_manager
        self.chain = chain

        # Header chain (lightweight)
        self.headers: List[CompactBlockHeader] = []
        self.header_index: Dict[bytes, int] = {}  # hash -> height

        # Pending block requests
        self._pending_requests: Dict[bytes, float] = {}  # hash -> request_time

        # Verified transactions (SPV)
        self._verified_entries: Set[bytes] = set()

        # Sync state
        self.syncing = False
        self.last_sync = 0.0
        self.sync_height = 0

        # Register callbacks
        transport_manager.on_block_header(self._on_header_received)
        transport_manager.on_spv_proof(self._on_proof_received)

    def start_sync(self):
        """Start background sync."""
        self.syncing = True
        self._request_headers()

    def stop_sync(self):
        """Stop sync."""
        self.syncing = False

    def _request_headers(self, from_height: int = 0):
        """Request block headers from peers."""
        # Request headers starting from our tip
        if self.headers:
            last_hash = self.headers[-1].calculate_hash()
        else:
            last_hash = b'\x00' * 32

        self.transport.request_block_header(last_hash)

    def _on_header_received(self, header: CompactBlockHeader):
        """Handle received block header."""
        header_hash = header.calculate_hash()

        # Check if we already have this header
        if header_hash in self.header_index:
            return

        # Validate header
        if not self._validate_header(header):
            logger.warning(f"Invalid header rejected: {header_hash.hex()[:16]}")
            return

        # Add to chain
        height = len(self.headers)
        self.headers.append(header)
        self.header_index[header_hash] = height
        self.sync_height = height
        self.last_sync = time.time()

        logger.info(f"Added header at height {height}: {header_hash.hex()[:16]}")

        # Request next header
        if self.syncing:
            self._request_headers(height + 1)

    def _validate_header(self, header: CompactBlockHeader) -> bool:
        """Validate a block header."""
        # Check chain linkage
        if self.headers:
            expected_prev = self.headers[-1].calculate_hash()
            if header.previous_hash != expected_prev:
                logger.warning("Header doesn't link to chain tip")
                return False

        # Check timestamp (not too far in future)
        if header.timestamp > time.time() + 7200:  # 2 hours tolerance
            logger.warning("Header timestamp too far in future")
            return False

        # Check proof of work (if applicable)
        header_hash = header.calculate_hash()
        difficulty_target = b'\x00' * (header.difficulty // 8)
        if not header_hash.startswith(difficulty_target):
            logger.warning("Header doesn't meet difficulty target")
            return False

        return True

    def _on_proof_received(self, proof: SPVProof):
        """Handle received SPV proof."""
        # Verify proof against our header chain
        if proof.block_hash not in self.header_index:
            logger.warning("SPV proof references unknown block")
            return

        height = self.header_index[proof.block_hash]
        header = self.headers[height]

        if proof.verify(header.merkle_root):
            self._verified_entries.add(proof.entry_hash)
            logger.info(f"SPV verified entry: {proof.entry_hash.hex()[:16]}")
        else:
            logger.warning(f"SPV proof verification failed")

    def verify_entry(self, entry_hash: bytes) -> bool:
        """Check if an entry has been SPV verified."""
        return entry_hash in self._verified_entries

    def get_tip(self) -> Optional[CompactBlockHeader]:
        """Get the current chain tip."""
        return self.headers[-1] if self.headers else None

    def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status."""
        return {
            'syncing': self.syncing,
            'height': self.sync_height,
            'headers_count': len(self.headers),
            'verified_entries': len(self._verified_entries),
            'last_sync': self.last_sync,
            'tip_hash': self.headers[-1].calculate_hash().hex() if self.headers else None
        }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_radio_manager(
    callsign: str,
    enable_lora: bool = True,
    enable_aprs: bool = True,
    enable_js8call: bool = True,
    enable_olivia: bool = True,
    **kwargs
) -> RadioTransportManager:
    """
    Create a radio transport manager with specified transports.

    Args:
        callsign: Amateur radio callsign
        enable_lora: Enable LoRa transport
        enable_aprs: Enable APRS transport
        enable_js8call: Enable JS8Call transport
        enable_olivia: Enable Olivia transport
        **kwargs: Additional transport-specific options

    Returns:
        Configured RadioTransportManager
    """
    manager = RadioTransportManager(callsign)

    if enable_lora:
        lora = LoRaTransport(
            callsign=callsign,
            device=kwargs.get('lora_device', '/dev/ttyUSB0'),
            frequency=kwargs.get('lora_frequency', 915.0)
        )
        manager.add_transport(lora)

    if enable_aprs:
        aprs = APRSTransport(
            callsign=callsign,
            device=kwargs.get('aprs_device', '/dev/ttyUSB1'),
            digipeaters=kwargs.get('aprs_digipeaters', ['WIDE1-1', 'WIDE2-1'])
        )
        manager.add_transport(aprs)

    if enable_js8call:
        js8 = JS8CallTransport(
            callsign=callsign,
            host=kwargs.get('js8_host', '127.0.0.1'),
            port=kwargs.get('js8_port', 2442),
            grid=kwargs.get('grid', 'FN20')
        )
        manager.add_transport(js8)

    if enable_olivia:
        olivia = OliviaTransport(
            callsign=callsign,
            host=kwargs.get('fldigi_host', '127.0.0.1'),
            port=kwargs.get('fldigi_port', 7362),
            mode=kwargs.get('olivia_mode', 'OLIVIA-8-250')
        )
        manager.add_transport(olivia)

    return manager


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Example: Create radio manager and send a block header

    callsign = "W1TEST"
    manager = create_radio_manager(
        callsign=callsign,
        enable_lora=True,
        enable_aprs=True,
        enable_js8call=True,
        enable_olivia=True
    )

    # Connect transports
    results = manager.connect_all()
    print(f"Transport connection results: {results}")

    # Create a sample block header
    header = CompactBlockHeader(
        version=1,
        previous_hash=b'\x00' * 32,
        merkle_root=hashlib.sha256(b"test entry").digest(),
        timestamp=int(time.time()),
        difficulty=2,
        nonce=12345
    )

    # Send block header
    if manager.send_block_header(header):
        print(f"Block header sent: {header.calculate_hash().hex()[:16]}...")

    # Print stats
    print(f"Stats: {manager.get_stats()}")

    # Cleanup
    manager.disconnect_all()
