"""
NatLangChain - Block Compression Module

Implements gzip compression for block data to reduce bandwidth and storage.
Natural language prose compresses exceptionally well (typically 70-90% reduction).

Features:
- Transparent gzip compression/decompression
- Compression statistics tracking
- HTTP header integration (Accept-Encoding/Content-Encoding)
- Configurable compression levels
- Streaming compression for large blocks
"""

import gzip
import io
import json
import logging
import threading
import time
import zlib
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# Constants
# ============================================================================

# Default compression level (1-9, higher = better compression but slower)
# Level 6 is a good balance for prose content
DEFAULT_COMPRESSION_LEVEL = 6

# Minimum size to compress (small blocks may not benefit)
MIN_COMPRESS_SIZE = 512  # bytes

# Maximum uncompressed size we'll accept (prevent decompression bombs)
MAX_DECOMPRESSED_SIZE = 100 * 1024 * 1024  # 100MB

# Magic bytes for gzip
GZIP_MAGIC = b"\x1f\x8b"

# Compression content type
CONTENT_TYPE_GZIP = "application/gzip"
CONTENT_TYPE_JSON = "application/json"

# HTTP headers
HEADER_CONTENT_ENCODING = "Content-Encoding"
HEADER_ACCEPT_ENCODING = "Accept-Encoding"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_ORIGINAL_SIZE = "X-Original-Size"
HEADER_COMPRESSED_SIZE = "X-Compressed-Size"
HEADER_COMPRESSION_RATIO = "X-Compression-Ratio"


class CompressionLevel(Enum):
    """Compression level presets."""

    NONE = 0  # No compression
    FAST = 1  # Fastest, lowest compression
    LOW = 3  # Low compression
    DEFAULT = 6  # Balanced
    HIGH = 9  # Maximum compression


@dataclass
class CompressionStats:
    """Statistics for compression operations."""

    total_compressed: int = 0
    total_decompressed: int = 0
    bytes_before: int = 0
    bytes_after: int = 0
    compression_time_ms: float = 0.0
    decompression_time_ms: float = 0.0
    skipped_too_small: int = 0
    errors: int = 0

    @property
    def compression_ratio(self) -> float:
        """Calculate overall compression ratio."""
        if self.bytes_before == 0:
            return 0.0
        return 1.0 - (self.bytes_after / self.bytes_before)

    @property
    def space_saved(self) -> int:
        """Calculate total bytes saved."""
        return self.bytes_before - self.bytes_after

    @property
    def avg_compression_time_ms(self) -> float:
        """Average time per compression operation."""
        if self.total_compressed == 0:
            return 0.0
        return self.compression_time_ms / self.total_compressed

    @property
    def avg_decompression_time_ms(self) -> float:
        """Average time per decompression operation."""
        if self.total_decompressed == 0:
            return 0.0
        return self.decompression_time_ms / self.total_decompressed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_compressed": self.total_compressed,
            "total_decompressed": self.total_decompressed,
            "bytes_before": self.bytes_before,
            "bytes_after": self.bytes_after,
            "space_saved": self.space_saved,
            "compression_ratio": round(self.compression_ratio * 100, 2),
            "compression_time_ms": round(self.compression_time_ms, 2),
            "decompression_time_ms": round(self.decompression_time_ms, 2),
            "avg_compression_time_ms": round(self.avg_compression_time_ms, 3),
            "avg_decompression_time_ms": round(self.avg_decompression_time_ms, 3),
            "skipped_too_small": self.skipped_too_small,
            "errors": self.errors,
        }


@dataclass
class CompressionResult:
    """Result of a compression operation."""

    data: bytes
    original_size: int
    compressed_size: int
    compression_ratio: float
    time_ms: float
    was_compressed: bool

    @property
    def space_saved(self) -> int:
        """Bytes saved by compression."""
        return self.original_size - self.compressed_size

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": round(self.compression_ratio * 100, 2),
            "space_saved": self.space_saved,
            "time_ms": round(self.time_ms, 3),
            "was_compressed": self.was_compressed,
        }


class BlockCompressor:
    """
    Handles compression and decompression of block data.

    Thread-safe with statistics tracking.
    """

    def __init__(
        self,
        compression_level: int = DEFAULT_COMPRESSION_LEVEL,
        min_size: int = MIN_COMPRESS_SIZE,
        max_decompressed_size: int = MAX_DECOMPRESSED_SIZE,
        enabled: bool = True,
    ):
        """
        Initialize the block compressor.

        Args:
            compression_level: Gzip compression level (1-9)
            min_size: Minimum size to compress (smaller data skipped)
            max_decompressed_size: Maximum allowed decompressed size
            enabled: Whether compression is enabled
        """
        self.compression_level = max(1, min(9, compression_level))
        self.min_size = min_size
        self.max_decompressed_size = max_decompressed_size
        self.enabled = enabled

        self.stats = CompressionStats()
        self._lock = threading.Lock()

        logger.info(
            f"BlockCompressor initialized: level={self.compression_level}, "
            f"min_size={self.min_size}, enabled={self.enabled}"
        )

    def compress(self, data: bytes | str | dict) -> CompressionResult:
        """
        Compress data using gzip.

        Args:
            data: Data to compress (bytes, string, or dict)

        Returns:
            CompressionResult with compressed data and stats
        """
        start_time = time.perf_counter()

        # Convert to bytes if needed
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        elif isinstance(data, str):
            data = data.encode("utf-8")

        original_size = len(data)

        # Check if compression should be skipped
        if not self.enabled or original_size < self.min_size:
            with self._lock:
                self.stats.skipped_too_small += 1

            elapsed = (time.perf_counter() - start_time) * 1000
            return CompressionResult(
                data=data,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=0.0,
                time_ms=elapsed,
                was_compressed=False,
            )

        try:
            # Compress with gzip
            compressed = gzip.compress(data, compresslevel=self.compression_level)
            compressed_size = len(compressed)

            # Calculate ratio
            ratio = 1.0 - (compressed_size / original_size) if original_size > 0 else 0.0

            elapsed = (time.perf_counter() - start_time) * 1000

            # Update stats
            with self._lock:
                self.stats.total_compressed += 1
                self.stats.bytes_before += original_size
                self.stats.bytes_after += compressed_size
                self.stats.compression_time_ms += elapsed

            logger.debug(
                f"Compressed {original_size} -> {compressed_size} bytes "
                f"({ratio * 100:.1f}% reduction, {elapsed:.2f}ms)"
            )

            return CompressionResult(
                data=compressed,
                original_size=original_size,
                compressed_size=compressed_size,
                compression_ratio=ratio,
                time_ms=elapsed,
                was_compressed=True,
            )

        except Exception as e:
            logger.error(f"Compression error: {e}")
            with self._lock:
                self.stats.errors += 1

            elapsed = (time.perf_counter() - start_time) * 1000
            return CompressionResult(
                data=data,
                original_size=original_size,
                compressed_size=original_size,
                compression_ratio=0.0,
                time_ms=elapsed,
                was_compressed=False,
            )

    def decompress(self, data: bytes) -> tuple[bytes, float]:
        """
        Decompress gzip data.

        Args:
            data: Compressed data

        Returns:
            Tuple of (decompressed data, time in ms)

        Raises:
            ValueError: If data is not valid gzip or exceeds size limit
        """
        start_time = time.perf_counter()

        # Check if data is gzip compressed
        if not self.is_compressed(data):
            elapsed = (time.perf_counter() - start_time) * 1000
            return data, elapsed

        try:
            # Check decompressed size before full decompression (security)
            estimated_size = self._estimate_decompressed_size(data)
            if estimated_size > self.max_decompressed_size:
                raise ValueError(
                    f"Decompressed size {estimated_size} exceeds maximum "
                    f"{self.max_decompressed_size} (possible decompression bomb)"
                )

            # Decompress
            decompressed = gzip.decompress(data)

            # Verify actual size
            if len(decompressed) > self.max_decompressed_size:
                raise ValueError(
                    f"Decompressed size {len(decompressed)} exceeds maximum "
                    f"{self.max_decompressed_size}"
                )

            elapsed = (time.perf_counter() - start_time) * 1000

            # Update stats
            with self._lock:
                self.stats.total_decompressed += 1
                self.stats.decompression_time_ms += elapsed

            logger.debug(f"Decompressed {len(data)} -> {len(decompressed)} bytes ({elapsed:.2f}ms)")

            return decompressed, elapsed

        except gzip.BadGzipFile as e:
            raise ValueError(f"Invalid gzip data: {e}") from e
        except zlib.error as e:
            raise ValueError(f"Decompression error: {e}") from e
        except Exception:
            with self._lock:
                self.stats.errors += 1
            raise

    def decompress_json(self, data: bytes) -> tuple[dict | list, float]:
        """
        Decompress and parse JSON data.

        Args:
            data: Compressed or uncompressed JSON data

        Returns:
            Tuple of (parsed JSON, time in ms)
        """
        decompressed, decomp_time = self.decompress(data)

        start_time = time.perf_counter()

        if isinstance(decompressed, bytes):
            decompressed = decompressed.decode("utf-8")

        result = json.loads(decompressed)
        parse_time = (time.perf_counter() - start_time) * 1000

        return result, decomp_time + parse_time

    def compress_blocks(self, blocks: list[dict]) -> CompressionResult:
        """
        Compress a list of blocks.

        Args:
            blocks: List of block dictionaries

        Returns:
            CompressionResult with compressed data
        """
        return self.compress({"blocks": blocks})

    def decompress_blocks(self, data: bytes) -> tuple[list[dict], float]:
        """
        Decompress a list of blocks.

        Args:
            data: Compressed block data

        Returns:
            Tuple of (list of blocks, time in ms)
        """
        result, elapsed = self.decompress_json(data)
        return result.get("blocks", []), elapsed

    @staticmethod
    def is_compressed(data: bytes) -> bool:
        """Check if data is gzip compressed."""
        return len(data) >= 2 and data[:2] == GZIP_MAGIC

    def _estimate_decompressed_size(self, data: bytes) -> int:
        """
        Estimate decompressed size from gzip footer.

        Note: This is the original size mod 2^32, so not reliable
        for files > 4GB, but good enough for our use case.
        """
        if len(data) < 4:
            return 0

        # Last 4 bytes of gzip contain original size (mod 2^32)
        size_bytes = data[-4:]
        return int.from_bytes(size_bytes, byteorder="little")

    def get_stats(self) -> dict[str, Any]:
        """Get compression statistics."""
        with self._lock:
            return self.stats.to_dict()

    def reset_stats(self) -> None:
        """Reset compression statistics."""
        with self._lock:
            self.stats = CompressionStats()

    def get_http_headers(self, result: CompressionResult) -> dict[str, str]:
        """
        Get HTTP headers for a compression result.

        Args:
            result: CompressionResult from compress()

        Returns:
            Dict of HTTP headers to add to response
        """
        headers = {}

        if result.was_compressed:
            headers[HEADER_CONTENT_ENCODING] = "gzip"
            headers[HEADER_CONTENT_TYPE] = CONTENT_TYPE_GZIP
        else:
            headers[HEADER_CONTENT_TYPE] = CONTENT_TYPE_JSON

        headers[HEADER_ORIGINAL_SIZE] = str(result.original_size)
        headers[HEADER_COMPRESSED_SIZE] = str(result.compressed_size)
        headers[HEADER_COMPRESSION_RATIO] = f"{result.compression_ratio * 100:.1f}%"

        return headers

    @staticmethod
    def accepts_gzip(headers: dict[str, str]) -> bool:
        """
        Check if client accepts gzip encoding.

        Args:
            headers: Request headers dict

        Returns:
            True if client accepts gzip
        """
        accept = headers.get(HEADER_ACCEPT_ENCODING, "")
        return "gzip" in accept.lower()


class StreamingCompressor:
    """
    Streaming compressor for large blocks.

    Useful when blocks are too large to fit in memory at once,
    or when streaming to network.
    """

    def __init__(self, compression_level: int = DEFAULT_COMPRESSION_LEVEL):
        """Initialize streaming compressor."""
        self.compression_level = compression_level

    def compress_stream(self, data_iterator, chunk_size: int = 64 * 1024):
        """
        Compress data from an iterator.

        Args:
            data_iterator: Iterator yielding bytes
            chunk_size: Size of chunks to yield

        Yields:
            Compressed chunks
        """
        buffer = io.BytesIO()

        with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=self.compression_level) as gz:
            for chunk in data_iterator:
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                gz.write(chunk)

                # Yield completed chunks
                if buffer.tell() >= chunk_size:
                    yield buffer.getvalue()
                    buffer = io.BytesIO()
                    gz.fileobj = buffer

        # Yield remaining data
        if buffer.tell() > 0:
            yield buffer.getvalue()

    def decompress_stream(self, data_iterator, max_size: int = MAX_DECOMPRESSED_SIZE):
        """
        Decompress data from an iterator.

        Args:
            data_iterator: Iterator yielding compressed bytes
            max_size: Maximum decompressed size allowed

        Yields:
            Decompressed chunks

        Raises:
            ValueError: If decompressed size exceeds limit
        """
        buffer = io.BytesIO()

        for chunk in data_iterator:
            buffer.write(chunk)

        buffer.seek(0)
        total_size = 0

        with gzip.GzipFile(fileobj=buffer, mode="rb") as gz:
            while True:
                chunk = gz.read(64 * 1024)
                if not chunk:
                    break

                total_size += len(chunk)
                if total_size > max_size:
                    raise ValueError(f"Decompressed size exceeds {max_size}")

                yield chunk


# ============================================================================
# Utility Functions
# ============================================================================


def compress_block_data(
    block_data: dict, level: int = DEFAULT_COMPRESSION_LEVEL
) -> tuple[bytes, dict[str, Any]]:
    """
    Convenience function to compress a single block.

    Args:
        block_data: Block dictionary
        level: Compression level

    Returns:
        Tuple of (compressed bytes, metadata dict with sizes/ratio)
    """
    compressor = BlockCompressor(compression_level=level)
    result = compressor.compress(block_data)

    return result.data, result.to_dict()


def decompress_block_data(data: bytes) -> dict:
    """
    Convenience function to decompress a single block.

    Args:
        data: Compressed block data

    Returns:
        Block dictionary
    """
    compressor = BlockCompressor()

    if not BlockCompressor.is_compressed(data):
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return json.loads(data)

    result, _ = compressor.decompress_json(data)
    return result


def estimate_compression_ratio(sample_text: str) -> float:
    """
    Estimate compression ratio for natural language text.

    Args:
        sample_text: Sample text to test

    Returns:
        Estimated compression ratio (0.0 to 1.0)
    """
    if not sample_text:
        return 0.0

    original = sample_text.encode("utf-8")
    compressed = gzip.compress(original, compresslevel=6)

    return 1.0 - (len(compressed) / len(original))


def create_compressor_from_env() -> BlockCompressor:
    """
    Create a BlockCompressor from environment variables.

    Environment variables:
        NATLANGCHAIN_COMPRESSION_ENABLED: true/false (default: true)
        NATLANGCHAIN_COMPRESSION_LEVEL: 1-9 (default: 6)
        NATLANGCHAIN_COMPRESSION_MIN_SIZE: bytes (default: 512)

    Returns:
        Configured BlockCompressor instance
    """
    import os

    enabled = os.getenv("NATLANGCHAIN_COMPRESSION_ENABLED", "true").lower() == "true"
    level = int(os.getenv("NATLANGCHAIN_COMPRESSION_LEVEL", str(DEFAULT_COMPRESSION_LEVEL)))
    min_size = int(os.getenv("NATLANGCHAIN_COMPRESSION_MIN_SIZE", str(MIN_COMPRESS_SIZE)))

    return BlockCompressor(compression_level=level, min_size=min_size, enabled=enabled)


# ============================================================================
# Compression Benchmarking
# ============================================================================


@dataclass
class BenchmarkResult:
    """Result of compression benchmark."""

    sample_name: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compress_time_ms: float
    decompress_time_ms: float
    throughput_mb_s: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sample_name": self.sample_name,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio_pct": round(self.compression_ratio * 100, 2),
            "space_saved_pct": round(self.compression_ratio * 100, 2),
            "compress_time_ms": round(self.compress_time_ms, 3),
            "decompress_time_ms": round(self.decompress_time_ms, 3),
            "throughput_mb_s": round(self.throughput_mb_s, 2),
        }


def benchmark_compression(
    samples: dict[str, str | bytes | dict], levels: list[int] | None = None, iterations: int = 3
) -> list[BenchmarkResult]:
    """
    Benchmark compression on sample data.

    Args:
        samples: Dict of {name: data} to benchmark
        levels: Compression levels to test (default: [1, 6, 9])
        iterations: Number of iterations per sample

    Returns:
        List of BenchmarkResult for each sample/level combination
    """
    if levels is None:
        levels = [1, 6, 9]

    results = []

    for name, data in samples.items():
        for level in levels:
            compressor = BlockCompressor(compression_level=level)

            # Average over iterations
            total_compress_time = 0.0
            total_decompress_time = 0.0

            for _ in range(iterations):
                # Compress
                result = compressor.compress(data)
                total_compress_time += result.time_ms

                # Decompress
                if result.was_compressed:
                    _, decomp_time = compressor.decompress(result.data)
                    total_decompress_time += decomp_time

            avg_compress = total_compress_time / iterations
            avg_decompress = total_decompress_time / iterations

            # Calculate throughput (MB/s for compression)
            throughput = (
                (result.original_size / (1024 * 1024)) / (avg_compress / 1000)
                if avg_compress > 0
                else 0
            )

            results.append(
                BenchmarkResult(
                    sample_name=f"{name}_level{level}",
                    original_size=result.original_size,
                    compressed_size=result.compressed_size,
                    compression_ratio=result.compression_ratio,
                    compress_time_ms=avg_compress,
                    decompress_time_ms=avg_decompress,
                    throughput_mb_s=throughput,
                )
            )

    return results


def print_benchmark_results(results: list[BenchmarkResult]) -> None:
    """Print benchmark results in a formatted table."""
    print("\n" + "=" * 80)
    print("COMPRESSION BENCHMARK RESULTS")
    print("=" * 80)
    print(f"{'Sample':<30} {'Original':>10} {'Compressed':>10} {'Ratio':>8} {'Time':>10}")
    print("-" * 80)

    for r in results:
        print(
            f"{r.sample_name:<30} "
            f"{r.original_size:>10,} "
            f"{r.compressed_size:>10,} "
            f"{r.compression_ratio * 100:>7.1f}% "
            f"{r.compress_time_ms:>9.2f}ms"
        )

    print("=" * 80)

    # Summary
    if results:
        avg_ratio = sum(r.compression_ratio for r in results) / len(results)
        total_original = sum(r.original_size for r in results)
        total_compressed = sum(r.compressed_size for r in results)
        total_saved = total_original - total_compressed

        print("\nSummary:")
        print(f"  Average compression ratio: {avg_ratio * 100:.1f}%")
        print(f"  Total space saved: {total_saved:,} bytes ({total_saved / 1024:.1f} KB)")
        print("  Prose compresses exceptionally well!")
