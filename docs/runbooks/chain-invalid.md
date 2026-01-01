# Runbook: Blockchain Validation Failing

**Alert:** `NatLangChainChainInvalid`
**Severity:** Critical
**Response Time:** Immediate

## Overview

This alert fires when the blockchain validation fails, indicating data corruption, tampering, or consistency issues.

## Impact

- Chain integrity compromised
- New blocks cannot be mined
- API may reject operations
- Trust in the system is affected

## Diagnosis

### 1. Check Validation Status

```bash
# API endpoint
curl http://localhost:5000/chain/validate

# Expected response for healthy chain:
# {"valid": true, "block_count": N, "message": "Chain is valid"}
```

### 2. Identify Invalid Block

```bash
# Get detailed validation
curl http://localhost:5000/chain/validate?detailed=true

# Response will show:
# - Which block failed validation
# - Type of validation failure
# - Hash mismatches
```

### 3. Check Recent Operations

```bash
# Check recent blocks
curl "http://localhost:5000/blocks?limit=10"

# Check for recent errors in logs
kubectl logs -n natlangchain -l app=natlangchain | grep -i "hash\|valid\|corrupt"
```

### 4. Compare with Peers

```bash
# If P2P enabled, check peer chain state
curl http://localhost:5000/p2p/peers
curl http://localhost:5000/p2p/sync/status
```

## Common Causes

### Hash Mismatch

**Symptoms:** "Previous hash mismatch at block N"

**Possible causes:**
- Data corruption during write
- Concurrent modification
- Disk errors

### Block Tampering

**Symptoms:** "Block hash does not match content"

**Possible causes:**
- Unauthorized modification
- Security breach
- Bug in serialization

### Storage Corruption

**Symptoms:** "Failed to load block" or JSON parse errors

**Possible causes:**
- Disk failure
- Incomplete write
- Power loss during save

## Remediation

### Option 1: Sync from Peers

If P2P network has valid copies:

```bash
# Check peer chain lengths
curl http://localhost:5000/p2p/peers

# Force sync from network
curl -X POST http://localhost:5000/p2p/sync/force

# Verify chain after sync
curl http://localhost:5000/chain/validate
```

### Option 2: Restore from Backup

```bash
# List available backups
curl http://localhost:5000/admin/backups

# Stop API to prevent writes
kubectl scale deployment natlangchain --replicas=0 -n natlangchain

# Restore backup (adjust path)
python -m backup restore --backup-name <backup-name> --target /data/chain_data.json

# Restart API
kubectl scale deployment natlangchain --replicas=2 -n natlangchain

# Verify
curl http://localhost:5000/chain/validate
```

### Option 3: Truncate to Last Valid Block

If corruption is recent and limited:

```bash
# Find last valid block
curl http://localhost:5000/chain/validate?detailed=true

# Truncate chain (CAUTION: Data loss)
# This requires direct database access
psql $DATABASE_URL -c "
  DELETE FROM entries WHERE block_id IN (
    SELECT id FROM blocks WHERE block_index > <last_valid_block>
  );
  DELETE FROM blocks WHERE block_index > <last_valid_block>;
"

# Restart and verify
kubectl rollout restart deployment/natlangchain -n natlangchain
curl http://localhost:5000/chain/validate
```

### Option 4: Full Reset (Last Resort)

If no valid backup or peers available:

```bash
# CAUTION: Complete data loss
# Only if absolutely necessary

# Stop service
kubectl scale deployment natlangchain --replicas=0 -n natlangchain

# Backup corrupted data for analysis
cp /data/chain_data.json /data/chain_data.corrupted.json

# Clear and reinitialize
rm /data/chain_data.json

# Restart
kubectl scale deployment natlangchain --replicas=2 -n natlangchain
```

## Verification

```bash
# Validate chain
curl http://localhost:5000/chain/validate

# Check block count
curl http://localhost:5000/chain/info

# Test entry submission
curl -X POST http://localhost:5000/entries \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"content": "Test entry", "agent_id": "test"}'

# Verify mining works
curl -X POST http://localhost:5000/mine \
  -H "X-API-Key: $API_KEY"
```

## Prevention

1. Enable automated backups with verification
2. Use P2P network with multiple nodes for redundancy
3. Monitor disk health
4. Use database replication for PostgreSQL backend
5. Implement write-ahead logging

## Escalation

This is a critical data integrity issue. Escalate immediately if:

- Unable to restore from backup
- Tampering is suspected (security incident)
- Multiple nodes are affected

## Post-Incident

1. Analyze corrupted data to determine cause
2. Review disk/storage health
3. Audit access logs for unauthorized changes
4. Consider forensic analysis if tampering suspected
