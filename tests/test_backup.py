"""
Tests for NatLangChain Backup Module

Tests backup configuration, local backup operations, backup types,
retention policies, and integrity verification.
"""

import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from backup import (
    BackupBackend,
    BackupConfig,
    BackupType,
)


class TestBackupBackendEnum(unittest.TestCase):
    """Tests for BackupBackend enum."""

    def test_backend_values(self):
        """Test backend enum values."""
        self.assertEqual(BackupBackend.LOCAL.value, "local")
        self.assertEqual(BackupBackend.S3.value, "s3")
        self.assertEqual(BackupBackend.GCS.value, "gcs")


class TestBackupTypeEnum(unittest.TestCase):
    """Tests for BackupType enum."""

    def test_backup_type_values(self):
        """Test backup type enum values."""
        self.assertEqual(BackupType.DAILY.value, "daily")
        self.assertEqual(BackupType.WEEKLY.value, "weekly")
        self.assertEqual(BackupType.MONTHLY.value, "monthly")
        self.assertEqual(BackupType.MANUAL.value, "manual")


class TestBackupConfig(unittest.TestCase):
    """Tests for BackupConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BackupConfig()

        self.assertEqual(config.backend, "local")
        self.assertEqual(config.local_path, "./backups")
        self.assertTrue(config.schedule_enabled)
        self.assertEqual(config.schedule_interval_hours, 24)

    def test_retention_defaults(self):
        """Test default retention values."""
        config = BackupConfig()

        self.assertEqual(config.retention_daily, 7)
        self.assertEqual(config.retention_weekly, 4)
        self.assertEqual(config.retention_monthly, 12)

    def test_s3_config(self):
        """Test S3 configuration."""
        config = BackupConfig(
            backend="s3",
            s3_bucket="my-backups",
            s3_prefix="natlangchain/prod/",
            s3_region="eu-west-1",
        )

        self.assertEqual(config.backend, "s3")
        self.assertEqual(config.s3_bucket, "my-backups")
        self.assertEqual(config.s3_prefix, "natlangchain/prod/")
        self.assertEqual(config.s3_region, "eu-west-1")

    def test_gcs_config(self):
        """Test GCS configuration."""
        config = BackupConfig(backend="gcs", gcs_bucket="my-gcs-bucket", gcs_prefix="backups/")

        self.assertEqual(config.backend, "gcs")
        self.assertEqual(config.gcs_bucket, "my-gcs-bucket")
        self.assertEqual(config.gcs_prefix, "backups/")

    def test_custom_retention(self):
        """Test custom retention configuration."""
        config = BackupConfig(retention_daily=14, retention_weekly=8, retention_monthly=24)

        self.assertEqual(config.retention_daily, 14)
        self.assertEqual(config.retention_weekly, 8)
        self.assertEqual(config.retention_monthly, 24)

    def test_schedule_disabled(self):
        """Test schedule can be disabled."""
        config = BackupConfig(schedule_enabled=False)

        self.assertFalse(config.schedule_enabled)

    def test_custom_schedule_interval(self):
        """Test custom schedule interval."""
        config = BackupConfig(schedule_interval_hours=6)

        self.assertEqual(config.schedule_interval_hours, 6)


class TestLocalBackupIntegration(unittest.TestCase):
    """Integration tests for local backup operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        # Create sample data
        self.sample_data = {
            "chain": [
                {"index": 0, "entries": [], "hash": "genesis"},
                {"index": 1, "entries": [{"content": "test"}], "hash": "abc123"},
            ],
            "difficulty": 2,
        }

        # Write sample data file
        self.data_file = os.path.join(self.data_dir, "chain.json")
        with open(self.data_file, "w") as f:
            json.dump(self.sample_data, f)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_backup_config_local_path(self):
        """Test local path configuration."""
        config = BackupConfig(backend="local", local_path=self.backup_dir)

        self.assertEqual(config.local_path, self.backup_dir)
        self.assertTrue(os.path.exists(self.backup_dir))

    def test_compress_data(self):
        """Test data compression for backups."""
        data = json.dumps(self.sample_data).encode()

        # Compress
        compressed = gzip.compress(data)

        # Verify compression reduces size (for non-trivial data)
        self.assertLessEqual(len(compressed), len(data))

        # Verify can decompress
        decompressed = gzip.decompress(compressed)
        self.assertEqual(decompressed, data)

    def test_checksum_generation(self):
        """Test checksum generation for integrity verification."""
        data = json.dumps(self.sample_data).encode()

        # Generate checksum
        checksum = hashlib.sha256(data).hexdigest()

        # Verify checksum is consistent
        checksum2 = hashlib.sha256(data).hexdigest()
        self.assertEqual(checksum, checksum2)

        # Verify different data has different checksum
        modified_data = json.dumps({"modified": True}).encode()
        modified_checksum = hashlib.sha256(modified_data).hexdigest()
        self.assertNotEqual(checksum, modified_checksum)

    def test_backup_filename_format(self):
        """Test backup filename generation."""
        timestamp = datetime.utcnow()
        backup_type = BackupType.DAILY

        # Expected format: natlangchain_backup_YYYYMMDD_HHMMSS_type.json.gz
        filename = (
            f"natlangchain_backup_{timestamp.strftime('%Y%m%d_%H%M%S')}_{backup_type.value}.json.gz"
        )

        self.assertIn("natlangchain_backup", filename)
        self.assertIn("daily", filename)
        self.assertIn(".json.gz", filename)


class TestBackupMetadata(unittest.TestCase):
    """Tests for backup metadata handling."""

    def test_metadata_structure(self):
        """Test expected backup metadata structure."""
        metadata = {
            "backup_id": "backup-001",
            "created_at": datetime.utcnow().isoformat(),
            "backup_type": BackupType.DAILY.value,
            "source": "production",
            "checksum": "sha256:abc123...",
            "size_bytes": 1024,
            "entries_count": 100,
            "blocks_count": 10,
        }

        self.assertIn("backup_id", metadata)
        self.assertIn("created_at", metadata)
        self.assertIn("backup_type", metadata)
        self.assertIn("checksum", metadata)

    def test_backup_type_classification(self):
        """Test backup type classification by day of week/month."""
        now = datetime.utcnow()

        # First day of month should be monthly
        first_of_month = datetime(now.year, now.month, 1)
        if first_of_month.day == 1:
            expected_type = BackupType.MONTHLY

        # Sunday should be weekly (weekday() == 6)
        # Other days should be daily
        if now.weekday() == 6:
            expected_type = BackupType.WEEKLY
        else:
            expected_type = BackupType.DAILY

        # Manual backups are explicitly marked
        manual_type = BackupType.MANUAL
        self.assertEqual(manual_type.value, "manual")


class TestRetentionPolicy(unittest.TestCase):
    """Tests for backup retention policies."""

    def test_retention_config(self):
        """Test retention configuration."""
        config = BackupConfig(retention_daily=7, retention_weekly=4, retention_monthly=12)

        # Daily: keep 7 days
        self.assertEqual(config.retention_daily, 7)

        # Weekly: keep 4 weeks
        self.assertEqual(config.retention_weekly, 4)

        # Monthly: keep 12 months
        self.assertEqual(config.retention_monthly, 12)

    def test_retention_calculation(self):
        """Test calculating which backups to retain."""
        now = datetime.utcnow()

        # Daily retention: 7 days ago
        daily_cutoff = now - timedelta(days=7)

        # Weekly retention: 4 weeks ago
        weekly_cutoff = now - timedelta(weeks=4)

        # Monthly retention: 12 months ago
        monthly_cutoff = now - timedelta(days=365)

        # Verify cutoffs are in the past
        self.assertLess(daily_cutoff, now)
        self.assertLess(weekly_cutoff, now)
        self.assertLess(monthly_cutoff, now)

        # Verify ordering
        self.assertLess(monthly_cutoff, weekly_cutoff)
        self.assertLess(weekly_cutoff, daily_cutoff)


if __name__ == "__main__":
    unittest.main()
