"""
NatLangChain - Database Migration System

A lightweight, production-ready migration system for PostgreSQL.

Features:
- Version-controlled schema migrations
- Forward and rollback support
- Transaction safety
- Migration locking to prevent concurrent runs
- Checksum verification
- Dry-run mode

Usage:
    # CLI
    python -m migrations upgrade           # Apply all pending migrations
    python -m migrations downgrade --to 5  # Rollback to version 5
    python -m migrations status            # Show migration status

    # Programmatic
    from migrations import MigrationManager
    manager = MigrationManager(database_url)
    manager.upgrade()

Environment Variables:
    DATABASE_URL=postgresql://user:pass@host:port/dbname
"""

import hashlib
import importlib.util
import logging
import os
import re
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Migration Data Structures
# =============================================================================


@dataclass
class Migration:
    """Represents a database migration."""

    version: int
    name: str
    description: str
    upgrade_sql: str | None = None
    downgrade_sql: str | None = None
    upgrade_fn: Callable | None = None
    downgrade_fn: Callable | None = None
    checksum: str = ""

    def __post_init__(self):
        """Calculate checksum if not provided."""
        if not self.checksum:
            content = (self.upgrade_sql or "") + (self.downgrade_sql or "")
            self.checksum = hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class MigrationRecord:
    """Record of an applied migration."""

    version: int
    name: str
    checksum: str
    applied_at: datetime
    execution_time_ms: int


# =============================================================================
# Migration Manager
# =============================================================================


class MigrationManager:
    """
    Manages database migrations for NatLangChain.

    This manager handles:
    - Loading migrations from files
    - Tracking applied migrations
    - Applying upgrades and downgrades
    - Transaction safety
    - Concurrent migration locking
    """

    MIGRATIONS_TABLE = "natlangchain_migrations"
    LOCK_TABLE = "natlangchain_migration_lock"

    def __init__(
        self,
        database_url: str | None = None,
        migrations_dir: str | None = None,
    ):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.migrations_dir = migrations_dir or self._default_migrations_dir()

        self._connection = None
        self._lock = threading.Lock()
        self._migrations: dict[int, Migration] = {}

        # Load migrations from directory
        self._load_migrations()

    def _default_migrations_dir(self) -> str:
        """Get the default migrations directory."""
        # Look for migrations/ relative to this file
        src_dir = Path(__file__).parent
        return str(src_dir.parent / "migrations")

    def _get_connection(self):
        """Get a database connection."""
        if self._connection is None:
            try:
                import psycopg2

                self._connection = psycopg2.connect(self.database_url)
            except ImportError:
                raise RuntimeError(
                    "psycopg2 is required for PostgreSQL migrations. "
                    "Install with: pip install psycopg2-binary"
                )

        return self._connection

    def _load_migrations(self):
        """Load migrations from the migrations directory."""
        migrations_path = Path(self.migrations_dir)

        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {migrations_path}")
            return

        # Find all migration files (V001__name.sql or V001__name.py)
        pattern = re.compile(r"V(\d+)__(.+)\.(sql|py)$")

        for file_path in sorted(migrations_path.iterdir()):
            match = pattern.match(file_path.name)
            if not match:
                continue

            version = int(match.group(1))
            name = match.group(2)
            ext = match.group(3)

            if ext == "sql":
                migration = self._load_sql_migration(file_path, version, name)
            else:
                migration = self._load_python_migration(file_path, version, name)

            if migration:
                self._migrations[version] = migration
                logger.debug(f"Loaded migration V{version:04d}__{name}")

    def _load_sql_migration(self, file_path: Path, version: int, name: str) -> Migration | None:
        """Load a SQL migration file."""
        try:
            content = file_path.read_text()

            # Split into upgrade and downgrade sections
            parts = re.split(r"--\s*@DOWN(?:GRADE)?\s*\n", content, maxsplit=1)

            upgrade_sql = parts[0].strip()
            downgrade_sql = parts[1].strip() if len(parts) > 1 else None

            # Extract description from first comment
            desc_match = re.match(r"--\s*(.+)", upgrade_sql)
            description = desc_match.group(1) if desc_match else name

            return Migration(
                version=version,
                name=name,
                description=description,
                upgrade_sql=upgrade_sql,
                downgrade_sql=downgrade_sql,
            )
        except Exception as e:
            logger.error(f"Failed to load SQL migration {file_path}: {e}")
            return None

    def _load_python_migration(self, file_path: Path, version: int, name: str) -> Migration | None:
        """Load a Python migration file."""
        try:
            spec = importlib.util.spec_from_file_location(f"migration_{version}", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            description = getattr(module, "DESCRIPTION", name)
            upgrade_fn = getattr(module, "upgrade", None)
            downgrade_fn = getattr(module, "downgrade", None)

            if not upgrade_fn:
                logger.warning(f"Migration {file_path} has no upgrade function")
                return None

            return Migration(
                version=version,
                name=name,
                description=description,
                upgrade_fn=upgrade_fn,
                downgrade_fn=downgrade_fn,
            )
        except Exception as e:
            logger.error(f"Failed to load Python migration {file_path}: {e}")
            return None

    def _ensure_migrations_table(self, cursor):
        """Ensure the migrations tracking table exists."""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
                version INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                checksum VARCHAR(32) NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER NOT NULL DEFAULT 0
            )
        """)

    def _ensure_lock_table(self, cursor):
        """Ensure the migration lock table exists."""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.LOCK_TABLE} (
                id INTEGER PRIMARY KEY DEFAULT 1,
                locked_at TIMESTAMP,
                locked_by VARCHAR(255),
                CONSTRAINT single_lock CHECK (id = 1)
            )
        """)
        cursor.execute(f"""
            INSERT INTO {self.LOCK_TABLE} (id, locked_at, locked_by)
            VALUES (1, NULL, NULL)
            ON CONFLICT (id) DO NOTHING
        """)

    def _acquire_lock(self, cursor, timeout_seconds: int = 60) -> bool:
        """Acquire the migration lock."""
        import socket

        hostname = socket.gethostname()
        pid = os.getpid()
        lock_id = f"{hostname}:{pid}"

        # Try to acquire lock with timeout check
        cursor.execute(
            f"""
            UPDATE {self.LOCK_TABLE}
            SET locked_at = CURRENT_TIMESTAMP, locked_by = %s
            WHERE id = 1
            AND (
                locked_at IS NULL
                OR locked_at < CURRENT_TIMESTAMP - INTERVAL '%s seconds'
            )
            RETURNING id
        """,
            (lock_id, timeout_seconds),
        )

        result = cursor.fetchone()
        return result is not None

    def _release_lock(self, cursor):
        """Release the migration lock."""
        cursor.execute(f"""
            UPDATE {self.LOCK_TABLE}
            SET locked_at = NULL, locked_by = NULL
            WHERE id = 1
        """)

    def get_applied_migrations(self) -> list[MigrationRecord]:
        """Get list of applied migrations."""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            self._ensure_migrations_table(cursor)
            conn.commit()

            cursor.execute(f"""
                SELECT version, name, checksum, applied_at, execution_time_ms
                FROM {self.MIGRATIONS_TABLE}
                ORDER BY version
            """)

            records = []
            for row in cursor.fetchall():
                records.append(
                    MigrationRecord(
                        version=row[0],
                        name=row[1],
                        checksum=row[2],
                        applied_at=row[3],
                        execution_time_ms=row[4],
                    )
                )

            return records
        finally:
            cursor.close()

    def get_pending_migrations(self) -> list[Migration]:
        """Get list of pending migrations."""
        applied = {r.version for r in self.get_applied_migrations()}
        pending = [m for v, m in sorted(self._migrations.items()) if v not in applied]
        return pending

    def get_current_version(self) -> int:
        """Get the current migration version."""
        applied = self.get_applied_migrations()
        if not applied:
            return 0
        return max(r.version for r in applied)

    def status(self) -> dict[str, Any]:
        """Get migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        return {
            "current_version": self.get_current_version(),
            "latest_version": max(self._migrations.keys()) if self._migrations else 0,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": [
                {
                    "version": r.version,
                    "name": r.name,
                    "applied_at": r.applied_at.isoformat(),
                    "execution_time_ms": r.execution_time_ms,
                }
                for r in applied
            ],
            "pending": [
                {
                    "version": m.version,
                    "name": m.name,
                    "description": m.description,
                }
                for m in pending
            ],
        }

    def upgrade(
        self,
        target_version: int | None = None,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Apply pending migrations.

        Args:
            target_version: Stop at this version (None = apply all)
            dry_run: Show what would be done without executing

        Returns:
            List of applied migration results
        """
        pending = self.get_pending_migrations()

        if target_version is not None:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            logger.info("No pending migrations")
            return []

        if dry_run:
            return [
                {
                    "version": m.version,
                    "name": m.name,
                    "action": "would_apply",
                }
                for m in pending
            ]

        conn = self._get_connection()
        cursor = conn.cursor()

        results = []

        try:
            self._ensure_migrations_table(cursor)
            self._ensure_lock_table(cursor)
            conn.commit()

            # Acquire lock
            if not self._acquire_lock(cursor):
                raise RuntimeError("Could not acquire migration lock")
            conn.commit()

            try:
                for migration in pending:
                    result = self._apply_migration(cursor, conn, migration)
                    results.append(result)

                    if not result.get("success"):
                        break

            finally:
                self._release_lock(cursor)
                conn.commit()

        finally:
            cursor.close()

        return results

    def _apply_migration(self, cursor, conn, migration: Migration) -> dict[str, Any]:
        """Apply a single migration."""
        import time

        logger.info(f"Applying migration V{migration.version:04d}__{migration.name}")
        start_time = time.time()

        try:
            # Execute migration
            if migration.upgrade_sql:
                cursor.execute(migration.upgrade_sql)
            elif migration.upgrade_fn:
                migration.upgrade_fn(cursor, conn)

            # Record migration
            execution_time_ms = int((time.time() - start_time) * 1000)
            cursor.execute(
                f"""
                INSERT INTO {self.MIGRATIONS_TABLE}
                (version, name, checksum, execution_time_ms)
                VALUES (%s, %s, %s, %s)
            """,
                (migration.version, migration.name, migration.checksum, execution_time_ms),
            )

            conn.commit()

            logger.info(
                f"Applied V{migration.version:04d}__{migration.name} in {execution_time_ms}ms"
            )

            return {
                "version": migration.version,
                "name": migration.name,
                "success": True,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration V{migration.version} failed: {e}")

            return {
                "version": migration.version,
                "name": migration.name,
                "success": False,
                "error": str(e),
            }

    def downgrade(
        self,
        target_version: int = 0,
        dry_run: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Rollback migrations to a target version.

        Args:
            target_version: Version to rollback to (0 = rollback all)
            dry_run: Show what would be done without executing

        Returns:
            List of rollback results
        """
        applied = self.get_applied_migrations()
        to_rollback = [r for r in reversed(applied) if r.version > target_version]

        if not to_rollback:
            logger.info("No migrations to rollback")
            return []

        if dry_run:
            return [
                {
                    "version": r.version,
                    "name": r.name,
                    "action": "would_rollback",
                }
                for r in to_rollback
            ]

        conn = self._get_connection()
        cursor = conn.cursor()

        results = []

        try:
            self._ensure_lock_table(cursor)
            conn.commit()

            if not self._acquire_lock(cursor):
                raise RuntimeError("Could not acquire migration lock")
            conn.commit()

            try:
                for record in to_rollback:
                    result = self._rollback_migration(cursor, conn, record)
                    results.append(result)

                    if not result.get("success"):
                        break

            finally:
                self._release_lock(cursor)
                conn.commit()

        finally:
            cursor.close()

        return results

    def _rollback_migration(self, cursor, conn, record: MigrationRecord) -> dict[str, Any]:
        """Rollback a single migration."""
        import time

        migration = self._migrations.get(record.version)

        if not migration:
            return {
                "version": record.version,
                "name": record.name,
                "success": False,
                "error": "Migration file not found",
            }

        if not migration.downgrade_sql and not migration.downgrade_fn:
            return {
                "version": record.version,
                "name": record.name,
                "success": False,
                "error": "No downgrade defined for this migration",
            }

        logger.info(f"Rolling back V{migration.version:04d}__{migration.name}")
        start_time = time.time()

        try:
            if migration.downgrade_sql:
                cursor.execute(migration.downgrade_sql)
            elif migration.downgrade_fn:
                migration.downgrade_fn(cursor, conn)

            # Remove migration record
            cursor.execute(
                f"""
                DELETE FROM {self.MIGRATIONS_TABLE}
                WHERE version = %s
            """,
                (record.version,),
            )

            conn.commit()

            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Rolled back V{migration.version:04d}__{migration.name} in {execution_time_ms}ms"
            )

            return {
                "version": record.version,
                "name": record.name,
                "success": True,
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Rollback V{record.version} failed: {e}")

            return {
                "version": record.version,
                "name": record.name,
                "success": False,
                "error": str(e),
            }

    def verify_checksums(self) -> list[dict[str, Any]]:
        """Verify that applied migrations match current files."""
        applied = self.get_applied_migrations()
        issues = []

        for record in applied:
            migration = self._migrations.get(record.version)

            if not migration:
                issues.append(
                    {
                        "version": record.version,
                        "name": record.name,
                        "issue": "Migration file missing",
                    }
                )
            elif migration.checksum != record.checksum:
                issues.append(
                    {
                        "version": record.version,
                        "name": record.name,
                        "issue": "Checksum mismatch",
                        "expected": record.checksum,
                        "actual": migration.checksum,
                    }
                )

        return issues

    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """CLI entry point for migrations."""
    import argparse

    parser = argparse.ArgumentParser(description="NatLangChain Database Migrations")
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Apply pending migrations")
    upgrade_parser.add_argument(
        "--to", type=int, dest="target", help="Target version to migrate to"
    )
    upgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without executing"
    )

    # downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Rollback migrations")
    downgrade_parser.add_argument(
        "--to", type=int, dest="target", default=0, help="Target version to rollback to"
    )
    downgrade_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without executing"
    )

    # status command
    subparsers.add_parser("status", help="Show migration status")

    # verify command
    subparsers.add_parser("verify", help="Verify migration checksums")

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("name", help="Migration name (use underscores)")
    create_parser.add_argument(
        "--type", choices=["sql", "py"], default="sql", help="Migration file type"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if args.command == "upgrade":
        manager = MigrationManager()
        results = manager.upgrade(
            target_version=args.target,
            dry_run=args.dry_run,
        )

        for r in results:
            status = "OK" if r.get("success", True) else "FAILED"
            print(f"  V{r['version']:04d}__{r['name']}: {status}")

        manager.close()

    elif args.command == "downgrade":
        manager = MigrationManager()
        results = manager.downgrade(
            target_version=args.target,
            dry_run=args.dry_run,
        )

        for r in results:
            status = "OK" if r.get("success", True) else "FAILED"
            print(f"  V{r['version']:04d}__{r['name']}: {status}")

        manager.close()

    elif args.command == "status":
        manager = MigrationManager()
        status = manager.status()

        print(f"\nCurrent version: {status['current_version']}")
        print(f"Latest version:  {status['latest_version']}")
        print(f"Applied:         {status['applied_count']}")
        print(f"Pending:         {status['pending_count']}")

        if status["applied"]:
            print("\nApplied migrations:")
            for m in status["applied"]:
                print(f"  V{m['version']:04d}__{m['name']} ({m['applied_at']})")

        if status["pending"]:
            print("\nPending migrations:")
            for m in status["pending"]:
                print(f"  V{m['version']:04d}__{m['name']}")

        manager.close()

    elif args.command == "verify":
        manager = MigrationManager()
        issues = manager.verify_checksums()

        if issues:
            print("Checksum verification issues:")
            for issue in issues:
                print(f"  V{issue['version']:04d}__{issue['name']}: {issue['issue']}")
            sys.exit(1)
        else:
            print("All checksums verified")

        manager.close()

    elif args.command == "create":
        manager = MigrationManager()
        migrations_dir = Path(manager.migrations_dir)
        migrations_dir.mkdir(parents=True, exist_ok=True)

        # Find next version number
        existing = list(migrations_dir.glob("V*__*"))
        if existing:
            max_version = max(int(re.match(r"V(\d+)", p.name).group(1)) for p in existing)
            next_version = max_version + 1
        else:
            next_version = 1

        # Create file
        ext = args.type
        filename = f"V{next_version:04d}__{args.name}.{ext}"
        filepath = migrations_dir / filename

        if ext == "sql":
            content = f"""-- {args.name.replace("_", " ").title()}
-- Migration V{next_version:04d}

-- Add your upgrade SQL here



-- @DOWNGRADE
-- Add your rollback SQL here

"""
        else:
            content = f'''"""
{args.name.replace("_", " ").title()}
Migration V{next_version:04d}
"""

DESCRIPTION = "{args.name.replace("_", " ").title()}"


def upgrade(cursor, connection):
    """Apply this migration."""
    pass


def downgrade(cursor, connection):
    """Rollback this migration."""
    pass
'''

        filepath.write_text(content)
        print(f"Created: {filepath}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
