# Database Migrations

This directory contains PostgreSQL database migrations for NatLangChain.

## Prerequisites

- PostgreSQL 14+ (for vector support, PostgreSQL 15+ recommended)
- pgvector extension (for semantic search features)
- psycopg2-binary Python package

## Quick Start

```bash
# Set database URL
export DATABASE_URL="postgresql://user:password@localhost:5432/natlangchain"

# Check migration status
python migrations/migrate.py --status

# Apply all pending migrations
python migrations/migrate.py

# Preview what would run (dry run)
python migrations/migrate.py --dry-run
```

## Migration Files

| Version | Name | Description |
|---------|------|-------------|
| 001 | initial_schema | Core tables: entries, blocks, contracts, disputes |
| 002 | add_semantic_search | Vector embeddings for similarity search |
| 003 | add_scaling_tables | Distributed coordination infrastructure |

## Schema Overview

### Core Tables

```
entries              - Natural language blockchain entries
blocks               - Blocks containing grouped entries
block_entries        - Junction table for block-entry relationships
validation_results   - LLM and rule validation results
chain_state          - Singleton table for chain coordination
contracts            - Natural language smart contracts
disputes             - Dispute resolution records
audit_log            - Audit trail for operations
schema_migrations    - Migration version tracking
```

### Semantic Search Tables (requires pgvector)

```
entry_embeddings     - Vector embeddings for entry search
contract_embeddings  - Vector embeddings for contract search
```

### Scaling Infrastructure Tables

```
instance_registry    - Active API instance registry
distributed_locks    - PostgreSQL-based distributed locks
cache_entries        - PostgreSQL-based cache
metrics_snapshots    - Historical metrics data
scheduled_jobs       - Background job queue
```

## Installing pgvector

pgvector is required for semantic search features.

### Ubuntu/Debian

```bash
sudo apt install postgresql-15-pgvector
```

### macOS (Homebrew)

```bash
brew install pgvector
```

### Docker

Use a PostgreSQL image with pgvector:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
```

### Manual Installation

```bash
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

## Usage

### Applying Migrations

```bash
# Apply all pending migrations
python migrations/migrate.py

# Apply up to a specific version
python migrations/migrate.py --version 2

# Dry run (preview only)
python migrations/migrate.py --dry-run
```

### Checking Status

```bash
python migrations/migrate.py --status

# Output:
# Migration Status
# ==================================================
#   ✓ 001_initial_schema: APPLIED
#   ✓ 002_add_semantic_search: APPLIED
#   ○ 003_add_scaling_tables: PENDING
#
# Applied: 2 / 3
```

### Rollback

```bash
# Remove last migration record (does NOT undo schema changes)
python migrations/migrate.py --rollback
```

**Note**: Rollback only removes the migration record. It does not reverse schema changes. For true rollbacks, you need to manually create and run rollback SQL.

## Writing New Migrations

1. Create a new file with the pattern `NNN_name.sql`:
   ```
   004_add_feature.sql
   ```

2. Include migration record at the end:
   ```sql
   INSERT INTO schema_migrations (version, name)
   VALUES (4, '004_add_feature')
   ON CONFLICT (version) DO NOTHING;
   ```

3. Use `IF NOT EXISTS` for idempotent operations:
   ```sql
   CREATE TABLE IF NOT EXISTS new_table (...);
   CREATE INDEX IF NOT EXISTS idx_name ON table(column);
   ```

4. Add comments for documentation:
   ```sql
   COMMENT ON TABLE new_table IS 'Description of the table';
   ```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |

## Troubleshooting

### "Extension vector not found"

Install pgvector on your PostgreSQL server. Migration 002 will fail without it, but you can skip it if you don't need semantic search:

```bash
python migrations/migrate.py --version 1
python migrations/migrate.py --version 3  # Skip 002
```

### "Permission denied"

Ensure the database user has CREATE/ALTER privileges:

```sql
GRANT ALL PRIVILEGES ON DATABASE natlangchain TO your_user;
```

### Connection refused

Check that PostgreSQL is running and accepting connections:

```bash
pg_isready -h localhost -p 5432
```
