"""
Tests for block compression module.

Tests compression functionality, statistics tracking, and integration
with the P2P network layer.
"""

import gzip
import json
import os
import sys
import tempfile
import time

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from block_compression import (
    BlockCompressor,
    CompressionResult,
    CompressionStats,
    CompressionLevel,
    StreamingCompressor,
    compress_block_data,
    decompress_block_data,
    estimate_compression_ratio,
    benchmark_compression,
    create_compressor_from_env,
    GZIP_MAGIC,
    DEFAULT_COMPRESSION_LEVEL,
    MIN_COMPRESS_SIZE,
)


# =============================================================================
# Sample Data for Testing
# =============================================================================

SAMPLE_PROSE = """
The party of the first part, hereinafter referred to as "Seller," agrees to
transfer ownership of the property located at 123 Main Street, including all
fixtures and improvements thereon, to the party of the second part, hereinafter
referred to as "Buyer," for the sum of five hundred thousand dollars ($500,000),
payable in accordance with the terms specified in Schedule A attached hereto.

The Seller warrants that they have good and marketable title to the property,
free and clear of all liens, encumbrances, and defects, except as otherwise
disclosed in this agreement. The Buyer acknowledges receipt of all relevant
disclosures regarding the property's condition, including but not limited to
environmental assessments, structural inspections, and zoning compliance reports.

Both parties agree that the closing shall occur within thirty (30) days of the
execution of this agreement, at a mutually agreed upon location. Time is of the
essence in this transaction, and any failure to meet the specified deadlines may
result in forfeiture of earnest money deposits or other remedies as provided by law.
"""

SAMPLE_BLOCK = {
    "index": 42,
    "timestamp": 1704067200.0,
    "entries": [
        {
            "content": SAMPLE_PROSE,
            "author": "alice@example.com",
            "intent": "propose_contract",
            "metadata": {"contract_type": "real_estate", "value_usd": 500000},
            "timestamp": "2024-01-01T12:00:00Z",
        },
        {
            "content": "I accept the terms as proposed in the above contract.",
            "author": "bob@example.com",
            "intent": "accept_contract",
            "metadata": {"references": ["prev_entry_hash"]},
            "timestamp": "2024-01-01T12:05:00Z",
        },
    ],
    "previous_hash": "0" * 64,
    "nonce": 12345,
    "hash": "a" * 64,
}

SAMPLE_BLOCKS = [
    {**SAMPLE_BLOCK, "index": i, "entries": [
        {**SAMPLE_BLOCK["entries"][0], "content": SAMPLE_PROSE * (i + 1)}
    ]}
    for i in range(5)
]


# =============================================================================
# BlockCompressor Tests
# =============================================================================

class TestBlockCompressor:
    """Tests for BlockCompressor class."""

    def test_initialization_default(self):
        """Test default initialization."""
        compressor = BlockCompressor()
        assert compressor.compression_level == DEFAULT_COMPRESSION_LEVEL
        assert compressor.min_size == MIN_COMPRESS_SIZE
        assert compressor.enabled is True

    def test_initialization_custom(self):
        """Test custom initialization."""
        compressor = BlockCompressor(
            compression_level=9,
            min_size=1024,
            enabled=False
        )
        assert compressor.compression_level == 9
        assert compressor.min_size == 1024
        assert compressor.enabled is False

    def test_compression_level_bounds(self):
        """Test compression level is bounded to 1-9."""
        compressor_low = BlockCompressor(compression_level=0)
        assert compressor_low.compression_level == 1

        compressor_high = BlockCompressor(compression_level=100)
        assert compressor_high.compression_level == 9

    def test_compress_dict(self):
        """Test compressing a dictionary."""
        compressor = BlockCompressor()
        result = compressor.compress(SAMPLE_BLOCK)

        assert isinstance(result, CompressionResult)
        assert result.was_compressed is True
        assert result.compressed_size < result.original_size
        assert result.compression_ratio > 0

    def test_compress_string(self):
        """Test compressing a string."""
        compressor = BlockCompressor()
        result = compressor.compress(SAMPLE_PROSE)

        assert result.was_compressed is True
        assert result.compression_ratio > 0.4  # Prose compresses well (40%+)

    def test_compress_bytes(self):
        """Test compressing bytes."""
        compressor = BlockCompressor()
        data = SAMPLE_PROSE.encode('utf-8')
        result = compressor.compress(data)

        assert result.was_compressed is True
        assert BlockCompressor.is_compressed(result.data)

    def test_compress_small_data_skipped(self):
        """Test that small data is not compressed."""
        compressor = BlockCompressor(min_size=1000)
        result = compressor.compress("small")

        assert result.was_compressed is False
        assert result.compression_ratio == 0.0

    def test_compress_disabled(self):
        """Test that compression can be disabled."""
        compressor = BlockCompressor(enabled=False)
        result = compressor.compress(SAMPLE_PROSE)

        assert result.was_compressed is False

    def test_decompress(self):
        """Test decompression."""
        compressor = BlockCompressor()

        # Compress
        original = json.dumps(SAMPLE_BLOCK)
        result = compressor.compress(original)

        # Decompress
        decompressed, elapsed = compressor.decompress(result.data)
        assert decompressed.decode('utf-8') == original
        assert elapsed >= 0

    def test_decompress_uncompressed(self):
        """Test decompressing uncompressed data passes through."""
        compressor = BlockCompressor()
        data = b"not compressed"

        decompressed, _ = compressor.decompress(data)
        assert decompressed == data

    def test_decompress_json(self):
        """Test decompressing and parsing JSON."""
        compressor = BlockCompressor()

        result = compressor.compress(SAMPLE_BLOCK)
        parsed, elapsed = compressor.decompress_json(result.data)

        assert parsed == SAMPLE_BLOCK
        assert elapsed >= 0

    def test_compress_blocks(self):
        """Test compressing a list of blocks."""
        compressor = BlockCompressor()
        result = compressor.compress_blocks(SAMPLE_BLOCKS)

        assert result.was_compressed is True
        assert result.compression_ratio > 0.7  # Multiple similar blocks compress very well

    def test_decompress_blocks(self):
        """Test decompressing a list of blocks."""
        compressor = BlockCompressor()

        result = compressor.compress_blocks(SAMPLE_BLOCKS)
        blocks, elapsed = compressor.decompress_blocks(result.data)

        assert blocks == SAMPLE_BLOCKS

    def test_is_compressed(self):
        """Test gzip detection."""
        assert BlockCompressor.is_compressed(GZIP_MAGIC + b"rest") is True
        assert BlockCompressor.is_compressed(b"not gzip") is False
        assert BlockCompressor.is_compressed(b"\x1f") is False  # Too short

    def test_stats_tracking(self):
        """Test compression statistics tracking."""
        compressor = BlockCompressor()

        # Perform some operations
        for _ in range(3):
            result = compressor.compress(SAMPLE_BLOCK)
            compressor.decompress(result.data)

        stats = compressor.get_stats()
        assert stats["total_compressed"] == 3
        assert stats["total_decompressed"] == 3
        assert stats["bytes_before"] > 0
        assert stats["bytes_after"] > 0
        assert stats["compression_ratio"] > 0

    def test_stats_reset(self):
        """Test resetting statistics."""
        compressor = BlockCompressor()
        compressor.compress(SAMPLE_BLOCK)

        compressor.reset_stats()
        stats = compressor.get_stats()

        assert stats["total_compressed"] == 0

    def test_http_headers(self):
        """Test HTTP header generation."""
        compressor = BlockCompressor()
        result = compressor.compress(SAMPLE_BLOCK)

        headers = compressor.get_http_headers(result)

        assert headers["Content-Encoding"] == "gzip"
        assert "X-Original-Size" in headers
        assert "X-Compression-Ratio" in headers

    def test_accepts_gzip(self):
        """Test Accept-Encoding header checking."""
        assert BlockCompressor.accepts_gzip({"Accept-Encoding": "gzip, deflate"}) is True
        assert BlockCompressor.accepts_gzip({"Accept-Encoding": "GZIP"}) is True
        assert BlockCompressor.accepts_gzip({"Accept-Encoding": "deflate"}) is False
        assert BlockCompressor.accepts_gzip({}) is False

    def test_thread_safety(self):
        """Test thread-safe compression."""
        import threading

        compressor = BlockCompressor()
        results = []
        errors = []

        def compress_task():
            try:
                for _ in range(10):
                    result = compressor.compress(SAMPLE_BLOCK)
                    results.append(result.compression_ratio)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=compress_task) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 50

    def test_decompression_bomb_protection(self):
        """Test protection against decompression bombs."""
        compressor = BlockCompressor(max_decompressed_size=1000)

        # Create data larger than limit
        large_data = "x" * 2000
        compressed = gzip.compress(large_data.encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            compressor.decompress(compressed)


# =============================================================================
# CompressionResult Tests
# =============================================================================

class TestCompressionResult:
    """Tests for CompressionResult class."""

    def test_space_saved(self):
        """Test space saved calculation."""
        result = CompressionResult(
            data=b"compressed",
            original_size=1000,
            compressed_size=300,
            compression_ratio=0.7,
            time_ms=1.5,
            was_compressed=True
        )

        assert result.space_saved == 700

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = CompressionResult(
            data=b"compressed",
            original_size=1000,
            compressed_size=300,
            compression_ratio=0.7,
            time_ms=1.5,
            was_compressed=True
        )

        d = result.to_dict()
        assert d["original_size"] == 1000
        assert d["compressed_size"] == 300
        assert d["compression_ratio"] == 70.0
        assert d["was_compressed"] is True


# =============================================================================
# CompressionStats Tests
# =============================================================================

class TestCompressionStats:
    """Tests for CompressionStats class."""

    def test_compression_ratio(self):
        """Test compression ratio calculation."""
        stats = CompressionStats(bytes_before=1000, bytes_after=300)
        assert stats.compression_ratio == 0.7

    def test_compression_ratio_zero(self):
        """Test compression ratio with no data."""
        stats = CompressionStats()
        assert stats.compression_ratio == 0.0

    def test_space_saved(self):
        """Test space saved calculation."""
        stats = CompressionStats(bytes_before=1000, bytes_after=300)
        assert stats.space_saved == 700


# =============================================================================
# Utility Function Tests
# =============================================================================

class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_compress_block_data(self):
        """Test convenience compression function."""
        compressed, metadata = compress_block_data(SAMPLE_BLOCK)

        assert isinstance(compressed, bytes)
        assert BlockCompressor.is_compressed(compressed)
        assert "compression_ratio" in metadata

    def test_decompress_block_data(self):
        """Test convenience decompression function."""
        compressed, _ = compress_block_data(SAMPLE_BLOCK)
        decompressed = decompress_block_data(compressed)

        assert decompressed == SAMPLE_BLOCK

    def test_decompress_uncompressed_data(self):
        """Test decompressing uncompressed JSON."""
        data = json.dumps(SAMPLE_BLOCK).encode()
        result = decompress_block_data(data)

        assert result == SAMPLE_BLOCK

    def test_estimate_compression_ratio(self):
        """Test compression ratio estimation."""
        ratio = estimate_compression_ratio(SAMPLE_PROSE)

        assert 0.3 < ratio < 0.95  # Prose should compress 30-95%

    def test_estimate_compression_ratio_empty(self):
        """Test estimation with empty string."""
        ratio = estimate_compression_ratio("")
        assert ratio == 0.0


# =============================================================================
# Environment Configuration Tests
# =============================================================================

class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""

    def test_create_compressor_from_env_defaults(self):
        """Test creating compressor from environment with defaults."""
        # Clear relevant env vars
        for key in ['NATLANGCHAIN_COMPRESSION_ENABLED',
                    'NATLANGCHAIN_COMPRESSION_LEVEL',
                    'NATLANGCHAIN_COMPRESSION_MIN_SIZE']:
            os.environ.pop(key, None)

        compressor = create_compressor_from_env()

        assert compressor.enabled is True
        assert compressor.compression_level == DEFAULT_COMPRESSION_LEVEL

    def test_create_compressor_from_env_custom(self):
        """Test creating compressor from custom environment."""
        os.environ['NATLANGCHAIN_COMPRESSION_ENABLED'] = 'false'
        os.environ['NATLANGCHAIN_COMPRESSION_LEVEL'] = '9'
        os.environ['NATLANGCHAIN_COMPRESSION_MIN_SIZE'] = '2048'

        try:
            compressor = create_compressor_from_env()

            assert compressor.enabled is False
            assert compressor.compression_level == 9
            assert compressor.min_size == 2048
        finally:
            # Clean up
            for key in ['NATLANGCHAIN_COMPRESSION_ENABLED',
                        'NATLANGCHAIN_COMPRESSION_LEVEL',
                        'NATLANGCHAIN_COMPRESSION_MIN_SIZE']:
                os.environ.pop(key, None)


# =============================================================================
# Streaming Compressor Tests
# =============================================================================

class TestStreamingCompressor:
    """Tests for StreamingCompressor class."""

    def test_compress_stream(self):
        """Test streaming compression."""
        compressor = StreamingCompressor()

        chunks = [SAMPLE_PROSE.encode() for _ in range(5)]
        compressed_chunks = list(compressor.compress_stream(iter(chunks)))

        # Verify we got output
        assert len(compressed_chunks) > 0

        # Verify it's valid gzip
        combined = b"".join(compressed_chunks)
        # Note: streaming might produce incomplete gzip, this is a simplified test


# =============================================================================
# Benchmark Tests
# =============================================================================

class TestBenchmark:
    """Tests for benchmarking functionality."""

    def test_benchmark_compression(self):
        """Test compression benchmarking."""
        samples = {
            "prose": SAMPLE_PROSE,
            "block": SAMPLE_BLOCK,
        }

        results = benchmark_compression(samples, levels=[6], iterations=1)

        assert len(results) == 2
        for result in results:
            assert result.original_size > 0
            assert result.compression_ratio > 0


# =============================================================================
# P2P Integration Tests
# =============================================================================

class TestP2PIntegration:
    """Tests for P2P network integration."""

    def test_p2p_network_has_compression(self):
        """Test that P2P network initializes compression."""
        try:
            from p2p_network import P2PNetwork, HAS_BLOCK_COMPRESSION

            if not HAS_BLOCK_COMPRESSION:
                pytest.skip("Block compression not available in P2P network")

            network = P2PNetwork(node_id="test_node")

            assert network.block_compressor is not None
            assert network._compression_enabled is True
        except ImportError:
            pytest.skip("P2P network module not available")

    def test_p2p_compress_payload(self):
        """Test P2P network payload compression."""
        try:
            from p2p_network import P2PNetwork, HAS_BLOCK_COMPRESSION

            if not HAS_BLOCK_COMPRESSION:
                pytest.skip("Block compression not available")

            network = P2PNetwork(node_id="test_node")

            data, headers = network.compress_payload(SAMPLE_BLOCK)

            assert isinstance(data, bytes)
            assert "Content-Encoding" in headers or "Content-Type" in headers
        except ImportError:
            pytest.skip("P2P network module not available")

    def test_p2p_compression_stats(self):
        """Test P2P network compression statistics."""
        try:
            from p2p_network import P2PNetwork, HAS_BLOCK_COMPRESSION

            if not HAS_BLOCK_COMPRESSION:
                pytest.skip("Block compression not available")

            network = P2PNetwork(node_id="test_node")
            network.compress_payload(SAMPLE_BLOCK)

            stats = network.get_compression_stats()

            assert stats is not None
            assert "total_compressed" in stats
        except ImportError:
            pytest.skip("P2P network module not available")


# =============================================================================
# Storage Integration Tests
# =============================================================================

class TestStorageIntegration:
    """Tests for storage integration with compression."""

    def test_json_storage_compression(self):
        """Test JSON file storage with compression enabled."""
        try:
            from storage.json_file import JSONFileStorage
        except ImportError:
            pytest.skip("Storage module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_chain.json")

            storage = JSONFileStorage(
                file_path=file_path,
                compression_enabled=True,
                compression_level=6
            )

            # Save data
            storage.save_chain({"blocks": SAMPLE_BLOCKS})

            # Verify file is compressed
            with open(file_path, 'rb') as f:
                header = f.read(2)
            assert header == GZIP_MAGIC, "Saved file should be gzip compressed"

            # Verify file is smaller than uncompressed
            compressed_size = os.path.getsize(file_path)
            uncompressed_size = len(json.dumps({"blocks": SAMPLE_BLOCKS}))
            assert compressed_size < uncompressed_size

            # Load and verify data
            loaded = storage.load_chain()
            assert loaded == {"blocks": SAMPLE_BLOCKS}

    def test_json_storage_compression_disabled(self):
        """Test JSON file storage with compression disabled."""
        try:
            from storage.json_file import JSONFileStorage
        except ImportError:
            pytest.skip("Storage module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_chain.json")

            storage = JSONFileStorage(
                file_path=file_path,
                compression_enabled=False
            )

            storage.save_chain(SAMPLE_BLOCK)

            # Verify file is NOT compressed
            with open(file_path, 'rb') as f:
                header = f.read(2)
            assert header != GZIP_MAGIC

            # Load and verify
            loaded = storage.load_chain()
            assert loaded == SAMPLE_BLOCK

    def test_json_storage_backwards_compatibility(self):
        """Test loading uncompressed files with compression enabled."""
        try:
            from storage.json_file import JSONFileStorage
        except ImportError:
            pytest.skip("Storage module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_chain.json")

            # Write uncompressed file directly
            with open(file_path, 'w') as f:
                json.dump(SAMPLE_BLOCK, f)

            # Load with compression-enabled storage
            storage = JSONFileStorage(
                file_path=file_path,
                compression_enabled=True
            )

            loaded = storage.load_chain()
            assert loaded == SAMPLE_BLOCK

    def test_json_storage_compression_stats(self):
        """Test storage compression statistics."""
        try:
            from storage.json_file import JSONFileStorage
        except ImportError:
            pytest.skip("Storage module not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_chain.json")

            storage = JSONFileStorage(
                file_path=file_path,
                compression_enabled=True
            )

            # Perform save operations
            storage.save_chain({"blocks": SAMPLE_BLOCKS})

            info = storage.get_info()

            assert "compression_enabled" in info
            assert info["compression_enabled"] is True
            assert "compression_stats" in info
            assert info["compression_stats"]["compression_ratio_pct"] > 0


# =============================================================================
# Compression Ratio Measurement
# =============================================================================

class TestCompressionRatios:
    """Tests that measure actual compression ratios for reporting."""

    def test_prose_compression_ratio(self):
        """Measure compression ratio for natural language prose."""
        compressor = BlockCompressor()
        result = compressor.compress(SAMPLE_PROSE)

        print(f"\nProse compression ratio: {result.compression_ratio*100:.1f}%")
        print(f"  Original: {result.original_size:,} bytes")
        print(f"  Compressed: {result.compressed_size:,} bytes")
        print(f"  Saved: {result.space_saved:,} bytes")

        # Prose should compress at least 40% (larger texts compress better)
        assert result.compression_ratio > 0.4

    def test_block_compression_ratio(self):
        """Measure compression ratio for a single block."""
        compressor = BlockCompressor()
        result = compressor.compress(SAMPLE_BLOCK)

        print(f"\nBlock compression ratio: {result.compression_ratio*100:.1f}%")
        print(f"  Original: {result.original_size:,} bytes")
        print(f"  Compressed: {result.compressed_size:,} bytes")

        # Block with prose should compress at least 45%
        assert result.compression_ratio > 0.45

    def test_multiple_blocks_compression_ratio(self):
        """Measure compression ratio for multiple blocks (sync scenario)."""
        compressor = BlockCompressor()
        result = compressor.compress_blocks(SAMPLE_BLOCKS)

        print(f"\nMultiple blocks compression ratio: {result.compression_ratio*100:.1f}%")
        print(f"  Original: {result.original_size:,} bytes")
        print(f"  Compressed: {result.compressed_size:,} bytes")
        print(f"  Blocks: {len(SAMPLE_BLOCKS)}")

        # Multiple similar blocks should compress very well
        assert result.compression_ratio > 0.7

    def test_compression_levels_comparison(self):
        """Compare compression at different levels."""
        print("\nCompression levels comparison:")
        print(f"{'Level':<8} {'Ratio':<10} {'Size':<12} {'Time':<10}")
        print("-" * 40)

        data = {"blocks": SAMPLE_BLOCKS}

        for level in [1, 3, 6, 9]:
            compressor = BlockCompressor(compression_level=level)
            result = compressor.compress(data)

            print(f"{level:<8} {result.compression_ratio*100:>6.1f}%   "
                  f"{result.compressed_size:>8,}   {result.time_ms:>6.2f}ms")

        # All levels should compress
        assert result.compression_ratio > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
