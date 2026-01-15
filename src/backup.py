"""
NatLangChain - Automated Backup System

Production-ready backup infrastructure with:
- Local file backups with rotation
- Cloud storage support (S3, GCS)
- Scheduled automatic backups
- Retention policies (daily, weekly, monthly)
- Integrity verification with checksums
- Compression for efficient storage

Usage:
    # CLI backup
    python -m backup --backend s3 --bucket my-backups

    # Programmatic backup
    from backup import BackupManager, BackupConfig
    manager = BackupManager(BackupConfig(backend="s3", bucket="my-backups"))
    manager.create_backup()

    # Start scheduler
    manager.start_scheduler()

Environment Variables:
    BACKUP_ENABLED=true
    BACKUP_BACKEND=local|s3|gcs
    BACKUP_LOCAL_PATH=/backups
    BACKUP_S3_BUCKET=my-bucket
    BACKUP_S3_PREFIX=natlangchain/
    BACKUP_GCS_BUCKET=my-bucket
    BACKUP_GCS_PREFIX=natlangchain/
    BACKUP_SCHEDULE_HOURS=24
    BACKUP_RETENTION_DAILY=7
    BACKUP_RETENTION_WEEKLY=4
    BACKUP_RETENTION_MONTHLY=12
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_REGION=us-east-1
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
"""

import gzip
import hashlib
import json
import logging
import os
import shutil
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class BackupBackend(Enum):
    """Supported backup storage backends."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"


class BackupType(Enum):
    """Backup classification for retention policies."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MANUAL = "manual"


@dataclass
class BackupConfig:
    """Configuration for backup operations."""

    # Backend selection
    backend: str = "local"

    # Local storage
    local_path: str = "./backups"

    # S3 configuration
    s3_bucket: str = ""
    s3_prefix: str = "natlangchain/"
    s3_region: str = "us-east-1"

    # GCS configuration
    gcs_bucket: str = ""
    gcs_prefix: str = "natlangchain/"

    # Scheduling
    schedule_enabled: bool = True
    schedule_interval_hours: int = 24

    # Retention (number to keep)
    retention_daily: int = 7
    retention_weekly: int = 4
    retention_monthly: int = 12

    # Compression
    compression_enabled: bool = True
    compression_level: int = 6

    # Verification
    verify_after_backup: bool = True

    @classmethod
    def from_env(cls) -> "BackupConfig":
        """Create configuration from environment variables."""
        return cls(
            backend=os.getenv("BACKUP_BACKEND", "local"),
            local_path=os.getenv("BACKUP_LOCAL_PATH", "./backups"),
            s3_bucket=os.getenv("BACKUP_S3_BUCKET", ""),
            s3_prefix=os.getenv("BACKUP_S3_PREFIX", "natlangchain/"),
            s3_region=os.getenv("AWS_REGION", "us-east-1"),
            gcs_bucket=os.getenv("BACKUP_GCS_BUCKET", ""),
            gcs_prefix=os.getenv("BACKUP_GCS_PREFIX", "natlangchain/"),
            schedule_enabled=os.getenv("BACKUP_ENABLED", "true").lower() == "true",
            schedule_interval_hours=int(os.getenv("BACKUP_SCHEDULE_HOURS", "24")),
            retention_daily=int(os.getenv("BACKUP_RETENTION_DAILY", "7")),
            retention_weekly=int(os.getenv("BACKUP_RETENTION_WEEKLY", "4")),
            retention_monthly=int(os.getenv("BACKUP_RETENTION_MONTHLY", "12")),
            compression_enabled=os.getenv("BACKUP_COMPRESSION", "true").lower() == "true",
            compression_level=int(os.getenv("BACKUP_COMPRESSION_LEVEL", "6")),
            verify_after_backup=os.getenv("BACKUP_VERIFY", "true").lower() == "true",
        )


@dataclass
class BackupMetadata:
    """Metadata for a backup file."""

    backup_id: str
    timestamp: str
    backup_type: BackupType
    source_file: str
    size_bytes: int
    compressed_size_bytes: int
    checksum_sha256: str
    chain_blocks: int
    chain_entries: int
    compression_ratio: float
    backend: str
    location: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize backup metadata to a dictionary for storage or API response."""
        return {
            "backup_id": self.backup_id,
            "timestamp": self.timestamp,
            "backup_type": self.backup_type.value,
            "source_file": self.source_file,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "chain_blocks": self.chain_blocks,
            "chain_entries": self.chain_entries,
            "compression_ratio": self.compression_ratio,
            "backend": self.backend,
            "location": self.location,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupMetadata":
        """Deserialize backup metadata from a dictionary."""
        return cls(
            backup_id=data["backup_id"],
            timestamp=data["timestamp"],
            backup_type=BackupType(data["backup_type"]),
            source_file=data["source_file"],
            size_bytes=data["size_bytes"],
            compressed_size_bytes=data["compressed_size_bytes"],
            checksum_sha256=data["checksum_sha256"],
            chain_blocks=data["chain_blocks"],
            chain_entries=data["chain_entries"],
            compression_ratio=data["compression_ratio"],
            backend=data["backend"],
            location=data["location"],
        )


class BackupStorage(ABC):
    """Abstract base class for backup storage backends."""

    @abstractmethod
    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the storage backend."""

    @abstractmethod
    def download(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the storage backend."""

    @abstractmethod
    def delete(self, remote_path: str) -> bool:
        """Delete a file from the storage backend."""

    @abstractmethod
    def list_backups(self, prefix: str = "") -> list[str]:
        """List backup files in the storage backend."""

    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """Check if a file exists in the storage backend."""


class LocalBackupStorage(BackupStorage):
    """Local filesystem backup storage."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Copy file to local backup directory."""
        try:
            dest = self.base_path / remote_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            logger.info(f"Backup saved to {dest}")
            return True
        except Exception as e:
            logger.error(f"Local backup failed: {e}")
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """Copy file from local backup directory."""
        try:
            src = self.base_path / remote_path
            shutil.copy2(src, local_path)
            return True
        except Exception as e:
            logger.error(f"Local restore failed: {e}")
            return False

    def delete(self, remote_path: str) -> bool:
        """Delete file from local backup directory."""
        try:
            path = self.base_path / remote_path
            if path.exists():
                path.unlink()
                # Also delete metadata file if exists
                meta_path = path.with_suffix(path.suffix + ".meta.json")
                if meta_path.exists():
                    meta_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Local delete failed: {e}")
            return False

    def list_backups(self, prefix: str = "") -> list[str]:
        """List backup files in local directory."""
        try:
            pattern = f"{prefix}*.gz" if prefix else "*.gz"
            files = list(self.base_path.glob(pattern))
            return [str(f.relative_to(self.base_path)) for f in files]
        except Exception as e:
            logger.error(f"List backups failed: {e}")
            return []

    def exists(self, remote_path: str) -> bool:
        """Check if file exists in local backup directory."""
        return (self.base_path / remote_path).exists()


class S3BackupStorage(BackupStorage):
    """AWS S3 backup storage."""

    def __init__(self, bucket: str, prefix: str = "", region: str = "us-east-1"):
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self._client = None

    def _get_client(self):
        """Get or create S3 client."""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("s3", region_name=self.region)
            except ImportError:
                raise ImportError("boto3 required for S3 backup. Install with: pip install boto3")
        return self._client

    def _full_key(self, path: str) -> str:
        """Get full S3 key with prefix."""
        return f"{self.prefix}{path}" if self.prefix else path

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload file to S3."""
        try:
            client = self._get_client()
            key = self._full_key(remote_path)
            client.upload_file(local_path, self.bucket, key)
            logger.info(f"Backup uploaded to s3://{self.bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download file from S3."""
        try:
            client = self._get_client()
            key = self._full_key(remote_path)
            client.download_file(self.bucket, key, local_path)
            return True
        except Exception as e:
            logger.error(f"S3 download failed: {e}")
            return False

    def delete(self, remote_path: str) -> bool:
        """Delete file from S3."""
        try:
            client = self._get_client()
            key = self._full_key(remote_path)
            client.delete_object(Bucket=self.bucket, Key=key)
            # Also delete metadata
            client.delete_object(Bucket=self.bucket, Key=key + ".meta.json")
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    def list_backups(self, prefix: str = "") -> list[str]:
        """List backup files in S3."""
        try:
            client = self._get_client()
            full_prefix = self._full_key(prefix)
            response = client.list_objects_v2(Bucket=self.bucket, Prefix=full_prefix)

            files = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".gz") and not key.endswith(".meta.json"):
                    # Remove prefix to get relative path
                    rel_path = key[len(self.prefix) :] if self.prefix else key
                    files.append(rel_path)
            return files
        except Exception as e:
            logger.error(f"S3 list failed: {e}")
            return []

    def exists(self, remote_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            client = self._get_client()
            key = self._full_key(remote_path)
            client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


class GCSBackupStorage(BackupStorage):
    """Google Cloud Storage backup storage."""

    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket_name = bucket
        self.prefix = prefix
        self._client = None
        self._bucket = None

    def _get_bucket(self):
        """Get or create GCS bucket reference."""
        if self._bucket is None:
            try:
                from google.cloud import storage

                self._client = storage.Client()
                self._bucket = self._client.bucket(self.bucket_name)
            except ImportError:
                raise ImportError(
                    "google-cloud-storage required for GCS backup. "
                    "Install with: pip install google-cloud-storage"
                )
        return self._bucket

    def _full_key(self, path: str) -> str:
        """Get full GCS key with prefix."""
        return f"{self.prefix}{path}" if self.prefix else path

    def upload(self, local_path: str, remote_path: str) -> bool:
        """Upload file to GCS."""
        try:
            bucket = self._get_bucket()
            key = self._full_key(remote_path)
            blob = bucket.blob(key)
            blob.upload_from_filename(local_path)
            logger.info(f"Backup uploaded to gs://{self.bucket_name}/{key}")
            return True
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return False

    def download(self, remote_path: str, local_path: str) -> bool:
        """Download file from GCS."""
        try:
            bucket = self._get_bucket()
            key = self._full_key(remote_path)
            blob = bucket.blob(key)
            blob.download_to_filename(local_path)
            return True
        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            return False

    def delete(self, remote_path: str) -> bool:
        """Delete file from GCS."""
        try:
            bucket = self._get_bucket()
            key = self._full_key(remote_path)
            bucket.blob(key).delete()
            bucket.blob(key + ".meta.json").delete()
            return True
        except Exception as e:
            logger.error(f"GCS delete failed: {e}")
            return False

    def list_backups(self, prefix: str = "") -> list[str]:
        """List backup files in GCS."""
        try:
            bucket = self._get_bucket()
            full_prefix = self._full_key(prefix)
            blobs = bucket.list_blobs(prefix=full_prefix)

            files = []
            for blob in blobs:
                if blob.name.endswith(".gz") and not blob.name.endswith(".meta.json"):
                    rel_path = blob.name[len(self.prefix) :] if self.prefix else blob.name
                    files.append(rel_path)
            return files
        except Exception as e:
            logger.error(f"GCS list failed: {e}")
            return []

    def exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS."""
        try:
            bucket = self._get_bucket()
            key = self._full_key(remote_path)
            return bucket.blob(key).exists()
        except Exception:
            return False


class BackupManager:
    """
    Manages automated backups with scheduling and retention policies.

    Features:
    - Automatic scheduled backups
    - Multiple storage backends (local, S3, GCS)
    - Compression with gzip
    - Retention policies (daily/weekly/monthly)
    - Integrity verification
    - Restore functionality
    """

    def __init__(
        self, config: BackupConfig | None = None, chain_data_file: str = "chain_data.json"
    ):
        self.config = config or BackupConfig.from_env()
        self.chain_data_file = chain_data_file
        self.storage = self._create_storage()
        self._scheduler_thread: threading.Thread | None = None
        self._stop_scheduler = threading.Event()
        self._backup_lock = threading.Lock()

    def _create_storage(self) -> BackupStorage:
        """Create the appropriate storage backend."""
        backend = self.config.backend.lower()

        if backend == "local":
            return LocalBackupStorage(self.config.local_path)
        elif backend == "s3":
            if not self.config.s3_bucket:
                raise ValueError("S3 bucket not configured. Set BACKUP_S3_BUCKET")
            return S3BackupStorage(
                self.config.s3_bucket, self.config.s3_prefix, self.config.s3_region
            )
        elif backend == "gcs":
            if not self.config.gcs_bucket:
                raise ValueError("GCS bucket not configured. Set BACKUP_GCS_BUCKET")
            return GCSBackupStorage(self.config.gcs_bucket, self.config.gcs_prefix)
        else:
            raise ValueError(f"Unknown backup backend: {backend}")

    def _compute_checksum(self, file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _classify_backup_type(self, timestamp: datetime) -> BackupType:
        """Classify backup type based on timestamp for retention."""
        # First of month = monthly
        if timestamp.day == 1:
            return BackupType.MONTHLY
        # Monday = weekly
        elif timestamp.weekday() == 0:
            return BackupType.WEEKLY
        else:
            return BackupType.DAILY

    def _generate_backup_name(self, timestamp: datetime, backup_type: BackupType) -> str:
        """Generate backup filename."""
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        return f"natlangchain_{ts_str}_{backup_type.value}.json.gz"

    def create_backup(
        self, backup_type: BackupType | None = None, source_file: str | None = None
    ) -> BackupMetadata | None:
        """
        Create a backup of the blockchain data.

        Args:
            backup_type: Type of backup (auto-detected if None)
            source_file: Source file to backup (uses chain_data_file if None)

        Returns:
            BackupMetadata if successful, None otherwise
        """
        with self._backup_lock:
            try:
                source = source_file or self.chain_data_file

                if not os.path.exists(source):
                    logger.error(f"Source file not found: {source}")
                    return None

                timestamp = datetime.now()
                if backup_type is None:
                    backup_type = self._classify_backup_type(timestamp)

                backup_name = self._generate_backup_name(timestamp, backup_type)

                # Read and parse chain data for metadata
                with open(source) as f:
                    chain_data = json.load(f)

                chain_blocks = len(chain_data.get("chain", []))
                chain_entries = sum(
                    len(block.get("entries", [])) for block in chain_data.get("chain", [])
                )

                # Create temporary compressed file
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".gz") as tmp:
                    tmp_path = tmp.name

                try:
                    # Compress
                    original_size = os.path.getsize(source)

                    with (
                        open(source, "rb") as f_in,
                        gzip.open(
                            tmp_path, "wb", compresslevel=self.config.compression_level
                        ) as f_out,
                    ):
                        shutil.copyfileobj(f_in, f_out)

                    compressed_size = os.path.getsize(tmp_path)
                    checksum = self._compute_checksum(tmp_path)

                    # Upload to storage
                    if not self.storage.upload(tmp_path, backup_name):
                        logger.error("Failed to upload backup")
                        return None

                    # Create metadata
                    metadata = BackupMetadata(
                        backup_id=f"BACKUP-{timestamp.strftime('%Y%m%d%H%M%S')}",
                        timestamp=timestamp.isoformat(),
                        backup_type=backup_type,
                        source_file=source,
                        size_bytes=original_size,
                        compressed_size_bytes=compressed_size,
                        checksum_sha256=checksum,
                        chain_blocks=chain_blocks,
                        chain_entries=chain_entries,
                        compression_ratio=compressed_size / original_size
                        if original_size > 0
                        else 1.0,
                        backend=self.config.backend,
                        location=backup_name,
                    )

                    # Save metadata alongside backup
                    meta_path = tmp_path + ".meta.json"
                    with open(meta_path, "w") as f:
                        json.dump(metadata.to_dict(), f, indent=2)

                    self.storage.upload(meta_path, backup_name + ".meta.json")
                    os.unlink(meta_path)

                    # Verify if configured
                    if self.config.verify_after_backup:
                        if not self._verify_backup(backup_name, checksum):
                            logger.warning("Backup verification failed")

                    logger.info(
                        f"Backup created: {backup_name} "
                        f"({compressed_size:,} bytes, {metadata.compression_ratio:.1%} of original)"
                    )

                    return metadata

                finally:
                    # Cleanup temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                return None

    def _verify_backup(self, backup_name: str, expected_checksum: str) -> bool:
        """Verify a backup's integrity."""
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gz") as tmp:
                tmp_path = tmp.name

            if not self.storage.download(backup_name, tmp_path):
                return False

            actual_checksum = self._compute_checksum(tmp_path)
            os.unlink(tmp_path)

            if actual_checksum != expected_checksum:
                logger.error(
                    f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def restore_backup(self, backup_name: str, target_path: str | None = None) -> bool:
        """
        Restore a backup to the specified path.

        Args:
            backup_name: Name of the backup file
            target_path: Path to restore to (uses chain_data_file if None)

        Returns:
            True if successful
        """
        import tempfile

        target = target_path or self.chain_data_file

        try:
            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".gz") as tmp:
                tmp_path = tmp.name

            if not self.storage.download(backup_name, tmp_path):
                logger.error(f"Failed to download backup: {backup_name}")
                return False

            # Decompress
            with gzip.open(tmp_path, "rb") as f_in, open(target, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

            os.unlink(tmp_path)
            logger.info(f"Backup restored to {target}")
            return True

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def apply_retention_policy(self) -> dict[str, int]:
        """
        Apply retention policy to remove old backups.

        Returns:
            Dictionary with counts of deleted backups by type
        """
        deleted = {"daily": 0, "weekly": 0, "monthly": 0}

        try:
            backups = self.storage.list_backups()

            # Group by type
            by_type: dict[str, list[str]] = {
                "daily": [],
                "weekly": [],
                "monthly": [],
            }

            for backup in backups:
                if "_daily." in backup:
                    by_type["daily"].append(backup)
                elif "_weekly." in backup:
                    by_type["weekly"].append(backup)
                elif "_monthly." in backup:
                    by_type["monthly"].append(backup)

            # Apply retention for each type
            retention_limits = {
                "daily": self.config.retention_daily,
                "weekly": self.config.retention_weekly,
                "monthly": self.config.retention_monthly,
            }

            for backup_type, backups_list in by_type.items():
                limit = retention_limits[backup_type]
                # Sort by name (which includes timestamp)
                backups_list.sort(reverse=True)

                # Delete excess backups
                for backup in backups_list[limit:]:
                    if self.storage.delete(backup):
                        deleted[backup_type] += 1
                        logger.info(f"Deleted old backup: {backup}")

            total_deleted = sum(deleted.values())
            if total_deleted > 0:
                logger.info(f"Retention policy applied: deleted {total_deleted} old backups")

            return deleted

        except Exception as e:
            logger.error(f"Retention policy failed: {e}")
            return deleted

    def list_backups(self) -> list[BackupMetadata]:
        """List all available backups with metadata."""
        backups = []

        try:
            files = self.storage.list_backups()

            for file in files:
                # Try to load metadata
                import tempfile

                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                    tmp_path = tmp.name

                try:
                    if self.storage.download(file + ".meta.json", tmp_path):
                        with open(tmp_path) as f:
                            meta_dict = json.load(f)
                        backups.append(BackupMetadata.from_dict(meta_dict))
                except Exception:
                    # Create minimal metadata if meta file not found
                    backups.append(
                        BackupMetadata(
                            backup_id="unknown",
                            timestamp="unknown",
                            backup_type=BackupType.MANUAL,
                            source_file="unknown",
                            size_bytes=0,
                            compressed_size_bytes=0,
                            checksum_sha256="unknown",
                            chain_blocks=0,
                            chain_entries=0,
                            compression_ratio=0,
                            backend=self.config.backend,
                            location=file,
                        )
                    )
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            # Sort by timestamp (newest first)
            backups.sort(key=lambda b: b.timestamp, reverse=True)
            return backups

        except Exception as e:
            logger.error(f"List backups failed: {e}")
            return []

    def _scheduler_loop(self):
        """Background scheduler loop."""
        logger.info(f"Backup scheduler started (interval: {self.config.schedule_interval_hours}h)")

        while not self._stop_scheduler.is_set():
            try:
                # Create backup
                metadata = self.create_backup()
                if metadata:
                    # Apply retention policy after successful backup
                    self.apply_retention_policy()

            except Exception as e:
                logger.error(f"Scheduled backup failed: {e}")

            # Wait for next interval (check every minute for stop signal)
            interval_seconds = self.config.schedule_interval_hours * 3600
            waited = 0
            while waited < interval_seconds and not self._stop_scheduler.is_set():
                time.sleep(60)
                waited += 60

        logger.info("Backup scheduler stopped")

    def start_scheduler(self):
        """Start the background backup scheduler."""
        if self._scheduler_thread is not None and self._scheduler_thread.is_alive():
            logger.warning("Scheduler already running")
            return

        if not self.config.schedule_enabled:
            logger.info("Backup scheduling is disabled")
            return

        self._stop_scheduler.clear()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, name="BackupScheduler", daemon=True
        )
        self._scheduler_thread.start()

    def stop_scheduler(self):
        """Stop the background backup scheduler."""
        self._stop_scheduler.set()
        if self._scheduler_thread is not None:
            self._scheduler_thread.join(timeout=5)
            self._scheduler_thread = None


def main():
    """CLI entry point for backup operations."""
    import argparse

    parser = argparse.ArgumentParser(description="NatLangChain Backup Manager")
    parser.add_argument(
        "--backend", choices=["local", "s3", "gcs"], default="local", help="Backup storage backend"
    )
    parser.add_argument("--bucket", help="S3/GCS bucket name")
    parser.add_argument("--local-path", default="./backups", help="Local backup path")
    parser.add_argument("--source", default="chain_data.json", help="Source chain file")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument(
        "--type",
        choices=["daily", "weekly", "monthly", "manual"],
        default="manual",
        help="Backup type",
    )

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a backup")
    restore_parser.add_argument("backup_name", help="Name of backup to restore")
    restore_parser.add_argument("--target", help="Target path for restore")

    # List command
    subparsers.add_parser("list", help="List available backups")

    # Cleanup command
    subparsers.add_parser("cleanup", help="Apply retention policy")

    args = parser.parse_args()

    # Create config
    config = BackupConfig(
        backend=args.backend,
        local_path=args.local_path,
        s3_bucket=args.bucket or "",
        gcs_bucket=args.bucket or "",
    )

    manager = BackupManager(config, chain_data_file=args.source)

    if args.command == "backup":
        backup_type = BackupType(args.type) if args.type else None
        metadata = manager.create_backup(backup_type=backup_type)
        if metadata:
            print(f"Backup created: {metadata.location}")
            print(f"  Size: {metadata.compressed_size_bytes:,} bytes")
            print(f"  Compression: {metadata.compression_ratio:.1%}")
            print(f"  Checksum: {metadata.checksum_sha256[:16]}...")
        else:
            print("Backup failed")
            return 1

    elif args.command == "restore":
        if manager.restore_backup(args.backup_name, args.target):
            print(f"Restored: {args.backup_name}")
        else:
            print("Restore failed")
            return 1

    elif args.command == "list":
        backups = manager.list_backups()
        if not backups:
            print("No backups found")
        else:
            print(f"{'Timestamp':<25} {'Type':<10} {'Size':<15} {'Location'}")
            print("-" * 80)
            for b in backups:
                size_str = f"{b.compressed_size_bytes:,} bytes"
                print(f"{b.timestamp:<25} {b.backup_type.value:<10} {size_str:<15} {b.location}")

    elif args.command == "cleanup":
        deleted = manager.apply_retention_policy()
        total = sum(deleted.values())
        print(f"Deleted {total} old backups")
        for btype, count in deleted.items():
            if count > 0:
                print(f"  {btype}: {count}")

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    exit(main())
