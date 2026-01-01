# NatLangChain Operational Runbooks

This directory contains operational runbooks for responding to alerts and managing NatLangChain in production.

## Runbook Index

| Alert/Scenario | Runbook | Severity |
|----------------|---------|----------|
| API Down | [api-down.md](api-down.md) | Critical |
| High Latency | [high-latency.md](high-latency.md) | Warning |
| High Error Rate | [high-error-rate.md](high-error-rate.md) | Warning/Critical |
| Chain Invalid | [chain-invalid.md](chain-invalid.md) | Critical |
| LLM API Failures | [llm-failures.md](llm-failures.md) | Warning |
| Rate Limiting Active | [rate-limiting.md](rate-limiting.md) | Info |
| Backup Stale | [backup-stale.md](backup-stale.md) | Warning |
| Disk Space Low | [disk-space.md](disk-space.md) | Warning |
| Deployment | [deployment.md](deployment.md) | - |
| Disaster Recovery | [disaster-recovery.md](disaster-recovery.md) | - |

## Quick Reference

### Health Check Endpoints

```bash
# Liveness probe (is the process alive?)
curl http://localhost:5000/health/live

# Readiness probe (is the service ready for traffic?)
curl http://localhost:5000/health/ready

# Full health check
curl http://localhost:5000/health
```

### Key Metrics

- `http_requests_total` - Total HTTP requests by status
- `http_request_duration_seconds` - Request latency histogram
- `natlangchain_chain_valid` - Chain validation status (1=valid, 0=invalid)
- `natlangchain_pending_entries` - Pending entry queue depth
- `natlangchain_blocks_total` - Total mined blocks

### Emergency Contacts

| Role | Contact |
|------|---------|
| On-Call | PagerDuty: #natlangchain-oncall |
| Platform Team | Slack: #platform-oncall |
| Security | security@natlangchain.io |

## Using These Runbooks

1. **Acknowledge the alert** in your alerting system
2. **Find the relevant runbook** in the index above
3. **Follow the diagnosis steps** to understand the issue
4. **Execute the remediation** procedures
5. **Verify the fix** using the verification steps
6. **Document the incident** with any learnings
