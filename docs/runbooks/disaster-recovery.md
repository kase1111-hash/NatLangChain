# Runbook: Disaster Recovery

**Scenario:** Complete system failure or data loss
**Severity:** Critical
**Response Time:** Immediate

## Overview

This runbook covers recovery procedures for major incidents including:
- Complete data loss
- Data center failure
- Ransomware/security incident
- Catastrophic corruption

## Recovery Objectives

| Metric | Target |
|--------|--------|
| RPO (Recovery Point Objective) | 24 hours |
| RTO (Recovery Time Objective) | 4 hours |

## Pre-Requisites

Before starting recovery:

1. **Assess the situation** - Understand what failed and scope of impact
2. **Secure the environment** - Ensure threat is contained (if security incident)
3. **Notify stakeholders** - Inform relevant teams and users
4. **Document everything** - Keep timeline of actions taken

## Recovery Procedures

### Scenario 1: Single Node Failure

**Impact:** One API instance down, service degraded

**Recovery:**

```bash
# Check other nodes are healthy
kubectl get pods -n natlangchain

# Replace failed node
kubectl delete pod <failed-pod> -n natlangchain

# Kubernetes will create a new pod automatically
# Verify new pod is healthy
kubectl get pods -n natlangchain -w
```

### Scenario 2: Complete Data Loss (Single Node)

**Impact:** Chain data lost on one node

**Recovery:**

```bash
# 1. Sync from P2P network (if available)
curl -X POST http://localhost:5000/p2p/sync/force

# 2. Or restore from backup
# Stop the service first
kubectl scale deployment natlangchain --replicas=0 -n natlangchain

# List available backups
aws s3 ls s3://$BACKUP_BUCKET/natlangchain/ --recursive | sort -k1,2

# Download latest backup
aws s3 cp s3://$BACKUP_BUCKET/natlangchain/<latest-backup>.json.gz /tmp/

# Decompress
gunzip /tmp/<latest-backup>.json.gz

# Restore
cp /tmp/<latest-backup>.json /data/chain_data.json

# Restart
kubectl scale deployment natlangchain --replicas=2 -n natlangchain
```

### Scenario 3: Database Corruption (PostgreSQL)

**Impact:** PostgreSQL backend corrupted

**Recovery:**

```bash
# 1. Stop application
kubectl scale deployment natlangchain --replicas=0 -n natlangchain

# 2. Restore PostgreSQL from backup
# If using managed PostgreSQL (RDS, Cloud SQL):
# - Use point-in-time recovery through cloud console
# - Or restore from snapshot

# If self-managed:
pg_restore -d natlangchain /backups/latest.dump

# 3. Run migrations to ensure schema is current
python -m migrations upgrade

# 4. Restart application
kubectl scale deployment natlangchain --replicas=2 -n natlangchain

# 5. Validate chain
curl http://localhost:5000/chain/validate
```

### Scenario 4: Complete Infrastructure Failure

**Impact:** All services down, infrastructure destroyed

**Recovery:**

```bash
# 1. Provision new infrastructure
terraform apply -var-file=production.tfvars

# 2. Deploy Kubernetes resources
kubectl apply -k k8s/overlays/production/

# 3. Restore secrets
kubectl create secret generic natlangchain-secrets \
  --from-literal=api-key=$API_KEY \
  --from-literal=encryption-key=$ENCRYPTION_KEY \
  -n natlangchain

# 4. Restore data from backup
# Get latest backup from offsite storage
aws s3 cp s3://$BACKUP_BUCKET/natlangchain/latest.json.gz /tmp/

# 5. Deploy with restored data
kubectl create configmap chain-data \
  --from-file=chain_data.json=/tmp/latest.json \
  -n natlangchain

# 6. Scale up
kubectl scale deployment natlangchain --replicas=2 -n natlangchain

# 7. Verify
curl http://api.natlangchain.io/health
curl http://api.natlangchain.io/chain/validate
```

### Scenario 5: Security Incident (Ransomware/Breach)

**Impact:** System compromised, data integrity unknown

**Recovery:**

```bash
# 1. ISOLATE - Disconnect from network
# Disable external access immediately

# 2. CONTAIN - Prevent further damage
kubectl scale deployment natlangchain --replicas=0 -n natlangchain
# Disable all API keys

# 3. ASSESS - Determine scope
# Work with security team
# Review audit logs
# Identify compromised data

# 4. REBUILD - Fresh infrastructure
# Do NOT restore from potentially compromised backups
# Use known-good backup from before incident

# Find last known-good backup
aws s3 ls s3://$BACKUP_BUCKET/natlangchain/ | \
  grep "before_incident_date"

# 5. RESTORE - Using verified clean backup
# Deploy to completely new infrastructure
# Use fresh secrets and credentials

# 6. VALIDATE - Verify data integrity
curl http://new-api.natlangchain.io/chain/validate

# 7. HARDEN - Implement additional security
# - Rotate all credentials
# - Review and tighten access controls
# - Enable additional monitoring
```

## Backup Verification

Before relying on any backup:

```bash
# 1. Download and decompress
aws s3 cp s3://$BACKUP_BUCKET/natlangchain/<backup>.json.gz /tmp/
gunzip /tmp/<backup>.json.gz

# 2. Verify JSON is valid
python -c "import json; json.load(open('/tmp/<backup>.json'))"

# 3. Check chain integrity
python -c "
from blockchain import NatLangChain
chain = NatLangChain()
chain.load_from_file('/tmp/<backup>.json')
print('Valid:', chain.is_valid_chain())
print('Blocks:', len(chain.chain))
"

# 4. Verify encryption key works (if encrypted)
python -c "
from encryption import decrypt_chain_data
data = open('/tmp/<backup>.json').read()
decrypted = decrypt_chain_data(data)
print('Decryption successful')
"
```

## Communication Templates

### Internal Notification

```
INCIDENT: NatLangChain Major Service Disruption

Status: [Investigating/Identified/Recovering/Resolved]
Impact: [Description of user impact]
Start Time: [When incident began]
Current Actions: [What is being done]
Next Update: [When next update will be provided]

Bridge: [Link to incident bridge/channel]
```

### External Status Update

```
We are currently experiencing service disruptions with NatLangChain.

Current Status: [Operational/Degraded/Major Outage]
Affected: [What is affected]
Next Update: [Time of next update]

We apologize for any inconvenience and are working to resolve this as quickly as possible.
```

## Post-Recovery Checklist

- [ ] All services healthy and responding
- [ ] Chain validation passing
- [ ] Backups running and verified
- [ ] Monitoring alerts resolved
- [ ] Stakeholders notified of resolution
- [ ] Post-incident review scheduled
- [ ] Timeline documented
- [ ] Follow-up actions identified

## Contacts

| Role | Contact | When to Engage |
|------|---------|----------------|
| On-Call Engineer | PagerDuty | First response |
| Platform Lead | @platform-lead | Escalation |
| Security Team | security@company.com | Security incidents |
| Executive Sponsor | @exec-sponsor | Major incidents |
| Communications | comms@company.com | External messaging |

## Appendix: Key Locations

| Resource | Location |
|----------|----------|
| Backups (S3) | s3://natlangchain-backups/ |
| Backups (GCS) | gs://natlangchain-backups/ |
| Terraform State | s3://terraform-state/natlangchain/ |
| Kubernetes Configs | github.com/org/natlangchain-infra |
| Secrets (Vault) | vault.company.com/natlangchain |
| Runbooks | /docs/runbooks/ |
