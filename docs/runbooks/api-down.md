# Runbook: API Down

**Alert:** `NatLangChainAPIDown`
**Severity:** Critical
**Response Time:** Immediate

## Overview

This alert fires when the NatLangChain API is unreachable or not responding to health checks for more than 1 minute.

## Impact

- All API operations are unavailable
- New entries cannot be submitted
- Contract operations fail
- P2P network may become inconsistent

## Diagnosis

### 1. Check Pod/Container Status

```bash
# Kubernetes
kubectl get pods -n natlangchain -l app=natlangchain
kubectl describe pod <pod-name> -n natlangchain

# Docker
docker ps -a | grep natlangchain
docker logs natlangchain-api
```

### 2. Check Service Health

```bash
# Direct health check
curl -v http://localhost:5000/health

# Check if port is listening
netstat -tlnp | grep 5000
# or
ss -tlnp | grep 5000
```

### 3. Check Logs

```bash
# Kubernetes
kubectl logs -n natlangchain -l app=natlangchain --tail=100

# Docker
docker logs --tail 100 natlangchain-api

# Systemd
journalctl -u natlangchain -n 100
```

### 4. Check Resource Usage

```bash
# CPU/Memory
kubectl top pods -n natlangchain

# Disk
df -h /data
```

## Common Causes

### Application Crash

**Symptoms:** Container restarts, OOMKilled status

**Resolution:**
```bash
# Check for OOM
kubectl describe pod <pod-name> | grep -A5 "Last State"

# Increase memory limits
kubectl edit deployment natlangchain -n natlangchain
# Adjust resources.limits.memory
```

### Port Conflict

**Symptoms:** "Address already in use" in logs

**Resolution:**
```bash
# Find process using port
lsof -i :5000
# Kill if necessary
kill -9 <pid>
```

### Configuration Error

**Symptoms:** "Configuration error" or "Missing required" in logs

**Resolution:**
```bash
# Check environment variables
kubectl get configmap natlangchain-config -n natlangchain -o yaml
kubectl get secret natlangchain-secrets -n natlangchain -o yaml

# Verify .env file
cat /app/.env
```

### Database Connection Failure

**Symptoms:** "Connection refused" or "timeout" for PostgreSQL

**Resolution:**
```bash
# Check database connectivity
kubectl exec -it <pod-name> -n natlangchain -- \
  psql $DATABASE_URL -c "SELECT 1"

# Check database service
kubectl get svc postgres -n natlangchain
```

## Remediation

### Restart the Service

```bash
# Kubernetes
kubectl rollout restart deployment/natlangchain -n natlangchain

# Docker
docker restart natlangchain-api

# Systemd
systemctl restart natlangchain
```

### Scale Up Replicas

```bash
# If single pod issue, scale up
kubectl scale deployment natlangchain --replicas=3 -n natlangchain
```

### Rollback Deployment

```bash
# Check deployment history
kubectl rollout history deployment/natlangchain -n natlangchain

# Rollback to previous version
kubectl rollout undo deployment/natlangchain -n natlangchain
```

## Verification

```bash
# Check health endpoints
curl http://localhost:5000/health/live
curl http://localhost:5000/health/ready

# Verify metrics are reporting
curl http://localhost:5000/metrics | grep up

# Check alert has resolved
# (Wait for alertmanager to clear)
```

## Escalation

If unable to restore service within 15 minutes:

1. Page the platform team lead
2. Open bridge call for major incident
3. Notify stakeholders of outage

## Post-Incident

1. Document timeline of events
2. Identify root cause
3. Create follow-up tickets for improvements
4. Update this runbook if needed
