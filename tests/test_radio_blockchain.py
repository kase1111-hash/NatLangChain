"""
Tests for the Radio Blockchain Transport Layer.

Tests cover:
- Packet serialization/deserialization
- Block header creation and validation
- SPV proof generation and verification
- Fragment assembly/reassembly
- Transport adapters (LoRa, APRS, JS8Call, Olivia)
- Multi-transport manager
- Block synchronization
"""

import pytest
import hashlib
import time
import zlib
import base64
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from radio_blockchain import (
    # Constants
    COMMON_MTU, MAX_PAYLOAD, PACKET_HEADER_SIZE,
    MTU_LORA, MTU_APRS, MTU_JS8CALL, MTU_OLIVIA,

    # Enums
    PacketType, TransportType, TransportStatus, Priority,

    # Data structures
    RadioPacket, CompactBlockHeader, SPVProof, FragmentBuffer,

    # Transports
    RadioTransport, LoRaTransport, APRSTransport, JS8CallTransport, OliviaTransport,

    # Manager and sync
    RadioTransportManager, RadioBlockSync,

    # Helper functions
    create_radio_manager,
)


# =============================================================================
# RadioPacket Tests
# =============================================================================

class TestRadioPacket:
    """Tests for RadioPacket serialization and handling."""

    def test_packet_creation_defaults(self):
        """Test packet creation with default values."""
        packet = RadioPacket()
        assert packet.version == 1
        assert packet.packet_type == PacketType.HEARTBEAT
        assert packet.flags == 0
        assert packet.priority == Priority.NORMAL
        assert packet.sequence == 0
        assert packet.fragment_index == 0
        assert packet.fragment_total == 1
        assert packet.payload == b''
        assert packet.timestamp > 0

    def test_packet_creation_with_payload(self):
        """Test packet creation with payload."""
        payload = b'Hello, Radio World!'
        packet = RadioPacket(
            packet_type=PacketType.BLOCK_HEADER,
            priority=Priority.HIGH,
            payload=payload
        )

        assert packet.packet_type == PacketType.BLOCK_HEADER
        assert packet.priority == Priority.HIGH
        assert packet.payload == payload
        assert packet.checksum == (zlib.crc32(payload) & 0xFFFFFFFF)

    def test_packet_serialization_roundtrip(self):
        """Test packet to_bytes and from_bytes roundtrip."""
        original = RadioPacket(
            packet_type=PacketType.TX_PROOF,
            flags=RadioPacket.FLAG_FRAGMENTED | RadioPacket.FLAG_COMPRESSED,
            priority=Priority.CRITICAL,
            sequence=12345,
            fragment_index=3,
            fragment_total=10,
            payload=b'test payload data'
        )

        # Serialize and deserialize
        data = original.to_bytes()
        restored = RadioPacket.from_bytes(data)

        assert restored.version == original.version
        assert restored.packet_type == original.packet_type
        assert restored.flags == original.flags
        assert restored.priority == original.priority
        assert restored.sequence == original.sequence
        assert restored.fragment_index == original.fragment_index
        assert restored.fragment_total == original.fragment_total
        assert restored.payload == original.payload
        assert restored.checksum == original.checksum

    def test_packet_base64_roundtrip(self):
        """Test base64 encoding/decoding for text-based transports."""
        original = RadioPacket(
            packet_type=PacketType.PEER_ANNOUNCE,
            payload=b'peer info here'
        )

        encoded = original.to_base64()
        assert isinstance(encoded, str)

        restored = RadioPacket.from_base64(encoded)
        assert restored.payload == original.payload
        assert restored.packet_type == original.packet_type

    def test_packet_flags(self):
        """Test packet flag properties."""
        packet = RadioPacket(
            flags=(RadioPacket.FLAG_FRAGMENTED |
                   RadioPacket.FLAG_COMPRESSED |
                   RadioPacket.FLAG_ENCRYPTED |
                   RadioPacket.FLAG_ACK_REQUIRED)
        )

        assert packet.is_fragmented
        assert packet.is_compressed
        assert packet.is_encrypted
        assert packet.requires_ack

    def test_packet_size_constraints(self):
        """Test packet fits within MTU constraints."""
        # Maximum size payload
        max_payload = b'x' * MAX_PAYLOAD
        packet = RadioPacket(payload=max_payload)

        data = packet.to_bytes()
        assert len(data) == COMMON_MTU

    def test_short_packet_rejection(self):
        """Test that short packets are rejected."""
        with pytest.raises(ValueError, match="Packet too short"):
            RadioPacket.from_bytes(b'short')


# =============================================================================
# CompactBlockHeader Tests
# =============================================================================

class TestCompactBlockHeader:
    """Tests for compact block header operations."""

    def test_header_creation_defaults(self):
        """Test header creation with defaults."""
        header = CompactBlockHeader()

        assert header.version == 1
        assert header.previous_hash == b'\x00' * 32
        assert header.merkle_root == b'\x00' * 32
        assert header.timestamp > 0
        assert header.difficulty == 0
        assert header.nonce == 0

    def test_header_serialization_size(self):
        """Test header serializes to exactly 80 bytes."""
        header = CompactBlockHeader(
            version=1,
            previous_hash=hashlib.sha256(b'prev').digest(),
            merkle_root=hashlib.sha256(b'merkle').digest(),
            timestamp=1700000000,
            difficulty=4,
            nonce=999999
        )

        data = header.to_bytes()
        assert len(data) == 80

    def test_header_serialization_roundtrip(self):
        """Test header to_bytes and from_bytes roundtrip."""
        original = CompactBlockHeader(
            version=2,
            previous_hash=hashlib.sha256(b'previous block').digest(),
            merkle_root=hashlib.sha256(b'merkle root').digest(),
            timestamp=1700000000,
            difficulty=3,
            nonce=42
        )

        data = original.to_bytes()
        restored = CompactBlockHeader.from_bytes(data)

        assert restored.version == original.version
        assert restored.previous_hash == original.previous_hash
        assert restored.merkle_root == original.merkle_root
        assert restored.timestamp == original.timestamp
        assert restored.difficulty == original.difficulty
        assert restored.nonce == original.nonce

    def test_header_hash_calculation(self):
        """Test header hash is consistent."""
        header = CompactBlockHeader(
            version=1,
            previous_hash=b'a' * 32,
            merkle_root=b'b' * 32,
            timestamp=1700000000,
            difficulty=2,
            nonce=100
        )

        hash1 = header.calculate_hash()
        hash2 = header.calculate_hash()

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_header_from_block(self):
        """Test creating header from block data."""
        block = {
            'index': 5,
            'previous_hash': 'abcd' * 16,
            'entries': [
                {'content': 'entry 1', 'author': 'alice'},
                {'content': 'entry 2', 'author': 'bob'}
            ],
            'timestamp': 1700000000,
            'nonce': 12345
        }

        header = CompactBlockHeader.from_block(block)

        assert header.block_index == 5
        assert header.entry_count == 2
        assert header.nonce == 12345
        assert header.merkle_root != b'\x00' * 32

    def test_merkle_root_calculation(self):
        """Test Merkle root calculation."""
        entries = [
            {'content': 'a', 'author': 'alice'},
            {'content': 'b', 'author': 'bob'},
            {'content': 'c', 'author': 'charlie'},
        ]

        root = CompactBlockHeader._calculate_merkle_root(entries)
        assert len(root) == 32
        assert root != b'\x00' * 32

        # Same entries should give same root
        root2 = CompactBlockHeader._calculate_merkle_root(entries)
        assert root == root2

    def test_merkle_root_empty_entries(self):
        """Test Merkle root with no entries."""
        root = CompactBlockHeader._calculate_merkle_root([])
        assert root == b'\x00' * 32


# =============================================================================
# SPVProof Tests
# =============================================================================

class TestSPVProof:
    """Tests for SPV proof generation and verification."""

    def test_proof_creation(self):
        """Test SPV proof creation."""
        entry_hash = hashlib.sha256(b'entry').digest()
        block_hash = hashlib.sha256(b'block').digest()
        merkle_path = [
            (hashlib.sha256(b'sibling1').digest(), True),
            (hashlib.sha256(b'sibling2').digest(), False),
        ]

        proof = SPVProof(
            entry_hash=entry_hash,
            merkle_path=merkle_path,
            block_hash=block_hash,
            block_height=100
        )

        assert proof.entry_hash == entry_hash
        assert proof.block_height == 100
        assert len(proof.merkle_path) == 2

    def test_proof_serialization_roundtrip(self):
        """Test proof to_bytes and from_bytes roundtrip."""
        entry_hash = hashlib.sha256(b'test entry').digest()
        block_hash = hashlib.sha256(b'test block').digest()
        merkle_path = [
            (hashlib.sha256(b's1').digest(), True),
            (hashlib.sha256(b's2').digest(), False),
            (hashlib.sha256(b's3').digest(), True),
        ]

        original = SPVProof(
            entry_hash=entry_hash,
            merkle_path=merkle_path,
            block_hash=block_hash,
            block_height=42
        )

        data = original.to_bytes()
        restored = SPVProof.from_bytes(data)

        assert restored.entry_hash == original.entry_hash
        assert restored.block_hash == original.block_hash
        assert restored.block_height == original.block_height
        assert len(restored.merkle_path) == len(original.merkle_path)

        for (h1, l1), (h2, l2) in zip(restored.merkle_path, original.merkle_path):
            assert h1 == h2
            assert l1 == l2

    def test_proof_verification_valid(self):
        """Test SPV proof verification with valid proof."""
        # Create a simple 2-entry Merkle tree
        entry1_hash = hashlib.sha256(b'entry1').digest()
        entry2_hash = hashlib.sha256(b'entry2').digest()
        merkle_root = hashlib.sha256(entry1_hash + entry2_hash).digest()

        # Proof for entry1 (sibling is entry2 on right)
        proof = SPVProof(
            entry_hash=entry1_hash,
            merkle_path=[(entry2_hash, False)],
            block_hash=b'\x00' * 32,
            block_height=1
        )

        assert proof.verify(merkle_root) is True

    def test_proof_verification_invalid(self):
        """Test SPV proof verification with invalid proof."""
        entry_hash = hashlib.sha256(b'entry').digest()
        wrong_merkle_root = hashlib.sha256(b'wrong').digest()

        proof = SPVProof(
            entry_hash=entry_hash,
            merkle_path=[(hashlib.sha256(b'sibling').digest(), False)],
            block_hash=b'\x00' * 32,
            block_height=1
        )

        assert proof.verify(wrong_merkle_root) is False


# =============================================================================
# FragmentBuffer Tests
# =============================================================================

class TestFragmentBuffer:
    """Tests for fragment reassembly buffer."""

    def test_buffer_creation(self):
        """Test fragment buffer creation."""
        buffer = FragmentBuffer(total_fragments=5)

        assert buffer.total_fragments == 5
        assert len(buffer.received) == 0
        assert not buffer.is_complete
        assert not buffer.is_expired

    def test_buffer_add_fragments(self):
        """Test adding fragments to buffer."""
        buffer = FragmentBuffer(total_fragments=3)

        buffer.add_fragment(0, b'part1')
        buffer.add_fragment(2, b'part3')

        assert len(buffer.received) == 2
        assert buffer.get_missing() == [1]
        assert not buffer.is_complete

    def test_buffer_complete(self):
        """Test buffer completion detection."""
        buffer = FragmentBuffer(total_fragments=2)

        buffer.add_fragment(0, b'first')
        assert not buffer.is_complete

        buffer.add_fragment(1, b'second')
        assert buffer.is_complete

    def test_buffer_reassembly(self):
        """Test fragment reassembly."""
        buffer = FragmentBuffer(total_fragments=3)

        buffer.add_fragment(0, b'AAA')
        buffer.add_fragment(1, b'BBB')
        buffer.add_fragment(2, b'CCC')

        result = buffer.reassemble()
        assert result == b'AAABBBCCC'

    def test_buffer_reassembly_incomplete(self):
        """Test that incomplete buffer raises error."""
        buffer = FragmentBuffer(total_fragments=3)
        buffer.add_fragment(0, b'part')

        with pytest.raises(ValueError, match="Cannot reassemble incomplete"):
            buffer.reassemble()

    def test_buffer_expiry(self):
        """Test buffer expiry detection."""
        buffer = FragmentBuffer(total_fragments=2)
        buffer.created_at = time.time() - 400  # 400 seconds ago

        assert buffer.is_expired  # Default timeout is 300 seconds


# =============================================================================
# Transport Adapter Tests
# =============================================================================

class TestLoRaTransport:
    """Tests for LoRa transport adapter."""

    def test_lora_creation(self):
        """Test LoRa transport creation."""
        lora = LoRaTransport(
            callsign="W1TEST",
            device="/dev/ttyUSB0",
            frequency=915.0,
            spreading_factor=10
        )

        assert lora.callsign == "W1TEST"
        assert lora.transport_type == TransportType.LORA
        assert lora.mtu == MTU_LORA
        assert lora.status == TransportStatus.DISCONNECTED

    def test_lora_connect(self):
        """Test LoRa connection."""
        lora = LoRaTransport(callsign="W1TEST")
        result = lora.connect()

        assert result is True
        assert lora.status == TransportStatus.CONNECTED

    def test_lora_disconnect(self):
        """Test LoRa disconnection."""
        lora = LoRaTransport(callsign="W1TEST")
        lora.connect()
        lora.disconnect()

        assert lora.status == TransportStatus.DISCONNECTED

    def test_lora_send(self):
        """Test sending packet over LoRa."""
        lora = LoRaTransport(callsign="W1TEST")
        lora.connect()

        packet = RadioPacket(
            packet_type=PacketType.HEARTBEAT,
            payload=b'ping'
        )

        result = lora.send(packet)
        assert result is True
        assert lora.stats['packets_sent'] == 1

    def test_lora_receive(self):
        """Test receiving packet from LoRa."""
        lora = LoRaTransport(callsign="W1TEST")
        lora.connect()

        # Inject a packet
        packet = RadioPacket(packet_type=PacketType.HEARTBEAT, payload=b'test')
        lora.inject_packet(packet.to_bytes())

        # Receive it
        received = lora.receive(timeout=1.0)
        assert received is not None
        assert received.payload == b'test'
        assert received.transport == TransportType.LORA


class TestAPRSTransport:
    """Tests for APRS transport adapter."""

    def test_aprs_creation(self):
        """Test APRS transport creation."""
        aprs = APRSTransport(
            callsign="W1TEST",
            ssid=5,
            digipeaters=["WIDE1-1", "WIDE2-2"]
        )

        assert aprs.callsign == "W1TEST"
        assert aprs.ssid == 5
        assert aprs.full_callsign == "W1TEST-5"
        assert aprs.transport_type == TransportType.APRS

    def test_aprs_connect(self):
        """Test APRS connection."""
        aprs = APRSTransport(callsign="W1TEST")
        result = aprs.connect()

        assert result is True
        assert aprs.status == TransportStatus.CONNECTED

    def test_aprs_send(self):
        """Test sending packet over APRS."""
        aprs = APRSTransport(callsign="W1TEST")
        aprs.connect()

        packet = RadioPacket(
            packet_type=PacketType.BLOCK_HEADER,
            payload=b'header data'
        )

        result = aprs.send(packet, destination="APNLC1")
        assert result is True

    def test_aprs_receive(self):
        """Test receiving packet from APRS."""
        aprs = APRSTransport(callsign="W1TEST")
        aprs.connect()

        # Inject a base64-encoded packet
        packet = RadioPacket(packet_type=PacketType.HEARTBEAT, payload=b'test')
        aprs.inject_packet(packet.to_base64().encode('ascii'))

        received = aprs.receive(timeout=1.0)
        assert received is not None
        assert received.transport == TransportType.APRS


class TestJS8CallTransport:
    """Tests for JS8Call transport adapter."""

    def test_js8call_creation(self):
        """Test JS8Call transport creation."""
        js8 = JS8CallTransport(
            callsign="W1TEST",
            grid="FN20",
            speed="normal"
        )

        assert js8.callsign == "W1TEST"
        assert js8.grid == "FN20"
        assert js8.transport_type == TransportType.JS8CALL
        assert js8.mtu == MTU_JS8CALL

    def test_js8call_connect(self):
        """Test JS8Call connection."""
        js8 = JS8CallTransport(callsign="W1TEST")
        result = js8.connect()

        assert result is True
        assert js8.status == TransportStatus.CONNECTED

    def test_js8call_encoding(self):
        """Test JS8Call text encoding/decoding."""
        js8 = JS8CallTransport(callsign="W1TEST")

        original = b'\x01\x02\x03\x04'
        encoded = js8._encode_for_js8(original)

        # Should be text-safe
        assert isinstance(encoded, str)
        assert all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-./?@" for c in encoded)

        decoded = js8._decode_from_js8(encoded)
        assert decoded == original

    def test_js8call_send(self):
        """Test sending packet over JS8Call."""
        js8 = JS8CallTransport(callsign="W1TEST")
        js8.connect()

        packet = RadioPacket(payload=b'data')
        result = js8.send(packet, destination="@ALLCALL")

        assert result is True


class TestOliviaTransport:
    """Tests for Olivia transport adapter."""

    def test_olivia_creation(self):
        """Test Olivia transport creation."""
        olivia = OliviaTransport(
            callsign="W1TEST",
            mode="OLIVIA-8-250",
            frequency=14.0725
        )

        assert olivia.callsign == "W1TEST"
        assert olivia.mode == "OLIVIA-8-250"
        assert olivia.transport_type == TransportType.OLIVIA

    def test_olivia_connect(self):
        """Test Olivia connection."""
        olivia = OliviaTransport(callsign="W1TEST")
        result = olivia.connect()

        assert result is True
        assert olivia.status == TransportStatus.CONNECTED

    def test_olivia_send(self):
        """Test sending packet over Olivia."""
        olivia = OliviaTransport(callsign="W1TEST")
        olivia.connect()

        packet = RadioPacket(payload=b'olivia test')
        result = olivia.send(packet)

        assert result is True


# =============================================================================
# RadioTransportManager Tests
# =============================================================================

class TestRadioTransportManager:
    """Tests for multi-transport manager."""

    def test_manager_creation(self):
        """Test manager creation."""
        manager = RadioTransportManager(callsign="W1TEST")

        assert manager.callsign == "W1TEST"
        assert len(manager.transports) == 0

    def test_manager_add_transport(self):
        """Test adding transports to manager."""
        manager = RadioTransportManager(callsign="W1TEST")

        lora = LoRaTransport(callsign="W1TEST")
        aprs = APRSTransport(callsign="W1TEST")

        manager.add_transport(lora)
        manager.add_transport(aprs)

        assert TransportType.LORA in manager.transports
        assert TransportType.APRS in manager.transports

    def test_manager_connect_all(self):
        """Test connecting all transports."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.add_transport(APRSTransport(callsign="W1TEST"))

        results = manager.connect_all()

        assert results[TransportType.LORA] is True
        assert results[TransportType.APRS] is True
        assert len(manager.get_active_transports()) == 2

    def test_manager_send_packet(self):
        """Test sending packet through manager."""
        manager = RadioTransportManager(callsign="W1TEST")
        lora = LoRaTransport(callsign="W1TEST")
        manager.add_transport(lora)
        manager.connect_all()

        packet = RadioPacket(payload=b'test')
        result = manager.send_packet(packet)

        assert result is True
        assert manager.stats['packets_sent'] == 1

    def test_manager_critical_priority(self):
        """Test critical priority sends on all transports."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.add_transport(APRSTransport(callsign="W1TEST"))
        manager.connect_all()

        packet = RadioPacket(payload=b'critical')
        result = manager.send_packet(packet, priority=Priority.CRITICAL)

        assert result is True

    def test_manager_send_block_header(self):
        """Test sending block header."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.connect_all()

        header = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'test').digest()
        )

        result = manager.send_block_header(header)
        assert result is True

    def test_manager_fragmentation(self):
        """Test data fragmentation."""
        import os
        manager = RadioTransportManager(callsign="W1TEST")

        # Create incompressible random data larger than MAX_PAYLOAD
        # (repetitive data like b'x' * 200 compresses too well)
        large_data = os.urandom(200)

        fragments = manager._fragment_data(large_data, PacketType.BLOCK_FRAGMENT)

        assert len(fragments) > 1
        assert all(f.is_fragmented for f in fragments)
        assert fragments[0].fragment_total == len(fragments)

    def test_manager_fragment_reassembly(self):
        """Test fragment reassembly through manager."""
        manager = RadioTransportManager(callsign="W1TEST")

        # Create fragments
        large_data = b'ABCDEFGHIJ' * 10  # 100 bytes
        fragments = manager._fragment_data(large_data, PacketType.BLOCK_FRAGMENT)

        # Simulate receiving fragments
        for fragment in fragments:
            manager._handle_received_packet(fragment)

        # Check stats
        assert manager.stats['fragments_received'] == len(fragments)

    def test_manager_get_stats(self):
        """Test statistics collection."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.connect_all()

        stats = manager.get_stats()

        assert 'packets_sent' in stats
        assert 'transports' in stats
        assert 'lora' in stats['transports']

    def test_manager_cleanup_expired_buffers(self):
        """Test expired fragment buffer cleanup."""
        manager = RadioTransportManager(callsign="W1TEST")

        # Create an expired buffer
        manager._fragment_buffers[999] = FragmentBuffer(
            total_fragments=5,
            sequence=999
        )
        manager._fragment_buffers[999].created_at = time.time() - 400

        manager.cleanup_expired_buffers()

        assert 999 not in manager._fragment_buffers
        assert manager.stats['reassembly_timeout'] == 1


# =============================================================================
# RadioBlockSync Tests
# =============================================================================

class TestRadioBlockSync:
    """Tests for block synchronization."""

    def test_sync_creation(self):
        """Test sync creation."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        assert sync.syncing is False
        assert len(sync.headers) == 0

    def test_sync_start_stop(self):
        """Test sync start and stop."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        sync.start_sync()
        assert sync.syncing is True

        sync.stop_sync()
        assert sync.syncing is False

    def test_sync_header_validation(self):
        """Test header validation."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        # First header (genesis)
        header = CompactBlockHeader(
            version=1,
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'genesis').digest(),
            timestamp=int(time.time()),
            difficulty=0
        )

        assert sync._validate_header(header) is True

    def test_sync_header_chain_linkage(self):
        """Test header chain linkage validation."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        # Add genesis header
        genesis = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'genesis').digest(),
            timestamp=int(time.time()) - 100,
            difficulty=0
        )
        sync._on_header_received(genesis)
        assert len(sync.headers) == 1

        # Add properly linked header
        header2 = CompactBlockHeader(
            previous_hash=genesis.calculate_hash(),
            merkle_root=hashlib.sha256(b'block2').digest(),
            timestamp=int(time.time()),
            difficulty=0
        )
        sync._on_header_received(header2)
        assert len(sync.headers) == 2

    def test_sync_reject_bad_linkage(self):
        """Test rejection of header with bad linkage."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        # Add genesis
        genesis = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'genesis').digest(),
            timestamp=int(time.time()) - 100,
            difficulty=0
        )
        sync._on_header_received(genesis)

        # Try to add header with wrong previous hash
        bad_header = CompactBlockHeader(
            previous_hash=b'\xff' * 32,  # Wrong!
            merkle_root=hashlib.sha256(b'bad').digest(),
            timestamp=int(time.time()),
            difficulty=0
        )
        sync._on_header_received(bad_header)

        # Should still only have 1 header
        assert len(sync.headers) == 1

    def test_sync_spv_verification(self):
        """Test SPV proof verification through sync."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        # Create and add a header
        entry_hash = hashlib.sha256(b'entry').digest()
        merkle_root = entry_hash  # Single entry = root is entry hash

        header = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=merkle_root,
            timestamp=int(time.time()),
            difficulty=0
        )
        sync._on_header_received(header)

        # Create SPV proof
        proof = SPVProof(
            entry_hash=entry_hash,
            merkle_path=[],  # No siblings for single entry
            block_hash=header.calculate_hash(),
            block_height=0
        )
        sync._on_proof_received(proof)

        # Entry should be verified
        assert sync.verify_entry(entry_hash) is True

    def test_sync_get_status(self):
        """Test sync status reporting."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        status = sync.get_sync_status()

        assert 'syncing' in status
        assert 'height' in status
        assert 'headers_count' in status
        assert 'verified_entries' in status

    def test_sync_get_tip(self):
        """Test getting chain tip."""
        manager = RadioTransportManager(callsign="W1TEST")
        sync = RadioBlockSync(manager)

        # No tip initially
        assert sync.get_tip() is None

        # Add header
        header = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'test').digest(),
            timestamp=int(time.time()),
            difficulty=0
        )
        sync._on_header_received(header)

        tip = sync.get_tip()
        assert tip is not None
        assert tip.merkle_root == header.merkle_root


# =============================================================================
# Integration Tests
# =============================================================================

class TestRadioBlockchainIntegration:
    """Integration tests for radio blockchain."""

    def test_full_block_transmission(self):
        """Test sending a full block through the radio layer."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.connect_all()

        # Create a mock block
        block_data = {
            'index': 1,
            'entries': [
                {'content': 'Transaction 1', 'author': 'alice'},
                {'content': 'Transaction 2', 'author': 'bob'}
            ],
            'previous_hash': '00' * 32,
            'timestamp': time.time(),
            'nonce': 12345
        }

        # Send header
        header = CompactBlockHeader.from_block(block_data)
        result = manager.send_block_header(header)
        assert result is True

        # Send full block (fragmented)
        block_bytes = bytes(str(block_data), 'utf-8')
        result = manager.send_full_block(block_bytes)
        assert result is True

    def test_cross_transport_sync(self):
        """Test synchronization across multiple transports."""
        manager = RadioTransportManager(callsign="W1TEST")
        manager.add_transport(LoRaTransport(callsign="W1TEST"))
        manager.add_transport(APRSTransport(callsign="W1TEST"))
        manager.connect_all()

        sync = RadioBlockSync(manager)
        sync.start_sync()

        # Simulate receiving headers from different transports
        header1 = CompactBlockHeader(
            previous_hash=b'\x00' * 32,
            merkle_root=hashlib.sha256(b'block1').digest(),
            timestamp=int(time.time()) - 100,
            difficulty=0
        )

        # Header comes in via callback
        sync._on_header_received(header1)
        assert sync.sync_height == 0

        header2 = CompactBlockHeader(
            previous_hash=header1.calculate_hash(),
            merkle_root=hashlib.sha256(b'block2').digest(),
            timestamp=int(time.time()),
            difficulty=0
        )
        sync._on_header_received(header2)
        assert sync.sync_height == 1

        sync.stop_sync()

    def test_create_radio_manager_helper(self):
        """Test the create_radio_manager helper function."""
        manager = create_radio_manager(
            callsign="W1TEST",
            enable_lora=True,
            enable_aprs=True,
            enable_js8call=True,
            enable_olivia=True,
            grid="FN20",
            lora_frequency=915.0
        )

        assert TransportType.LORA in manager.transports
        assert TransportType.APRS in manager.transports
        assert TransportType.JS8CALL in manager.transports
        assert TransportType.OLIVIA in manager.transports

    def test_create_radio_manager_selective(self):
        """Test creating manager with selective transports."""
        manager = create_radio_manager(
            callsign="W1TEST",
            enable_lora=True,
            enable_aprs=False,
            enable_js8call=False,
            enable_olivia=True
        )

        assert TransportType.LORA in manager.transports
        assert TransportType.APRS not in manager.transports
        assert TransportType.JS8CALL not in manager.transports
        assert TransportType.OLIVIA in manager.transports


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_send_without_connection(self):
        """Test sending without connecting fails gracefully."""
        lora = LoRaTransport(callsign="W1TEST")
        # Don't connect

        packet = RadioPacket(payload=b'test')
        result = lora.send(packet)

        assert result is False

    def test_receive_without_connection(self):
        """Test receiving without connection returns None."""
        lora = LoRaTransport(callsign="W1TEST")

        result = lora.receive(timeout=0.1)
        assert result is None

    def test_empty_fragment_buffer(self):
        """Test handling empty fragment buffer."""
        buffer = FragmentBuffer(total_fragments=0)
        assert buffer.is_complete

    def test_packet_with_empty_payload(self):
        """Test packet with empty payload."""
        packet = RadioPacket(payload=b'')
        data = packet.to_bytes()
        restored = RadioPacket.from_bytes(data)

        assert restored.payload == b''

    def test_header_with_truncated_hashes(self):
        """Test header creation with short hashes."""
        header = CompactBlockHeader(
            previous_hash=b'short',
            merkle_root=b'alsoshort'
        )

        data = header.to_bytes()
        assert len(data) == 80  # Should still be 80 bytes (padded)

    def test_manager_no_active_transports(self):
        """Test manager behavior with no active transports."""
        manager = RadioTransportManager(callsign="W1TEST")

        packet = RadioPacket(payload=b'orphan')
        result = manager.send_packet(packet)

        assert result is False

    def test_transport_failover(self):
        """Test transport failover when primary fails."""
        manager = RadioTransportManager(callsign="W1TEST")

        # Add transports but only connect some
        lora = LoRaTransport(callsign="W1TEST")
        aprs = APRSTransport(callsign="W1TEST")

        manager.add_transport(lora)
        manager.add_transport(aprs)

        # Only connect APRS
        aprs.connect()

        packet = RadioPacket(payload=b'fallback')
        result = manager.send_packet(packet)

        # Should succeed via APRS
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
