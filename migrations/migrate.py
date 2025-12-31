#!/usr/bin/env python3
"""
Database Migration Runner for NatLangChain.

Usage:
    python migrate.py                    # Apply all pending migrations
    python migrate.py --status           # Show migration status
    python migrate.py --version 2        # Migrate to specific version
    python migrate.py --rollback         # Rollback last migration
    python migrate.py --dry-run          # Show what would be executed

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
                  postgresql://user:pass@host:5432/dbname
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


MIGRATIONS_DIR = Path(__file__).parent


def get_connection(database_url: str):
    """Create database connection."""
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def get_migration_files() -> list[tuple[int, str, Path]]:
    """Get all migration files sorted by version."""
    migrations = []
    pattern = re.compile(r"^(\d+)_(.+)\.sql$")

    for file in MIGRATIONS_DIR.glob("*.sql"):
        match = pattern.match(file.name)
        if match:
            version = int(match.group(1))
            name = match.group(2)
            migrations.append((version, name, file))

    return sorted(migrations, key=lambda x: x[0])


def get_applied_migrations(conn) -> set[int]:
    """Get set of already applied migration versions."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT version FROM schema_migrations ORDER BY version
            """
            )
            return {row["version"] for row in cur.fetchall()}
    except psycopg2.errors.UndefinedTable:
        # schema_migrations table doesn't exist yet
        return set()


def apply_migration(conn, version: int, name: str, sql_path: Path, dry_run: bool = False):
    """Apply a single migration."""
    print(f"Applying migration {version:03d}_{name}...")

    sql = sql_path.read_text()

    if dry_run:
        print(f"  [DRY RUN] Would execute {len(sql)} bytes of SQL")
        return

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()
    print(f"  Applied successfully")


def show_status(conn):
    """Show migration status."""
    applied = get_applied_migrations(conn)
    migrations = get_migration_files()

    print("\nMigration Status")
    print("=" * 50)

    for version, name, _path in migrations:
        status = "APPLIED" if version in applied else "PENDING"
        marker = "✓" if version in applied else "○"
        print(f"  {marker} {version:03d}_{name}: {status}")

    print()
    print(f"Applied: {len(applied)} / {len(migrations)}")


def migrate(
    database_url: str,
    target_version: int | None = None,
    dry_run: bool = False,
):
    """Run pending migrations."""
    conn = get_connection(database_url)

    try:
        applied = get_applied_migrations(conn)
        migrations = get_migration_files()

        pending = [
            (v, n, p)
            for v, n, p in migrations
            if v not in applied and (target_version is None or v <= target_version)
        ]

        if not pending:
            print("No pending migrations")
            return

        print(f"Found {len(pending)} pending migration(s)")

        for version, name, path in pending:
            apply_migration(conn, version, name, path, dry_run)

        print("\nAll migrations applied successfully!")

    finally:
        conn.close()


def rollback(database_url: str, dry_run: bool = False):
    """Rollback the last migration (removes from tracking only)."""
    conn = get_connection(database_url)

    try:
        applied = get_applied_migrations(conn)
        if not applied:
            print("No migrations to rollback")
            return

        last_version = max(applied)
        migrations = get_migration_files()
        migration_name = next((n for v, n, _ in migrations if v == last_version), "unknown")

        print(f"Rolling back migration {last_version:03d}_{migration_name}...")
        print("\nWARNING: This only removes the migration record.")
        print("It does NOT undo schema changes.")
        print("You may need to manually revert changes.\n")

        if dry_run:
            print("[DRY RUN] Would remove migration record")
            return

        with conn.cursor() as cur:
            cur.execute("DELETE FROM schema_migrations WHERE version = %s", (last_version,))
        conn.commit()

        print(f"Migration record removed. Version now: {max(applied - {last_version}, default=0)}")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="NatLangChain Database Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python migrate.py                     Apply all pending migrations
    python migrate.py --status            Show migration status
    python migrate.py --version 2         Migrate up to version 2
    python migrate.py --dry-run           Preview what would run
        """,
    )

    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection string (default: $DATABASE_URL)",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status",
    )
    parser.add_argument(
        "--version",
        type=int,
        help="Target migration version",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Rollback last migration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without applying",
    )

    args = parser.parse_args()

    if not args.database_url:
        print("Error: DATABASE_URL not set")
        print("Set it via environment variable or --database-url flag")
        sys.exit(1)

    try:
        if args.status:
            conn = get_connection(args.database_url)
            show_status(conn)
            conn.close()
        elif args.rollback:
            rollback(args.database_url, args.dry_run)
        else:
            migrate(args.database_url, args.version, args.dry_run)

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
