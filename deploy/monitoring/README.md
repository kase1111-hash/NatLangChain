# NatLangChain Monitoring Stack

Production-ready monitoring for NatLangChain using Prometheus, Grafana, and Alertmanager.

## Quick Start (Docker Compose)

```bash
cd deploy/monitoring
docker-compose up -d
```

**Access:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Alertmanager: http://localhost:9093

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  NatLangChain   │────▶│   Prometheus    │────▶│    Grafana      │
│  /metrics       │     │   (scrape)      │     │  (visualize)    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Alertmanager   │
                        │  (route alerts) │
                        └────────┬────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
               ┌────────┐  ┌─────────┐  ┌─────────┐
               │ Slack  │  │PagerDuty│  │  Email  │
               └────────┘  └─────────┘  └─────────┘
```

## Components

### Prometheus (`prometheus/prometheus.yml`)

Metrics collection and alerting engine.

**Scrape Targets:**
- NatLangChain API (`/metrics`)
- Node Exporter (host metrics)
- Redis Exporter (optional)

### Grafana (`grafana/`)

Visualization and dashboards.

**Pre-configured Dashboards:**
- NatLangChain Overview - Key metrics at a glance
- Request latency percentiles
- Error rates by endpoint
- Blockchain activity
- Security violations

### Alertmanager (`alertmanager/alertmanager.yml`)

Alert routing and notifications.

**Severity Routing:**
| Severity | Destination | Response Time |
|----------|-------------|---------------|
| critical | PagerDuty + Slack | Immediate |
| warning | Slack | 5 minutes |
| info | Slack | 24 hours |

## Configuration

### 1. Configure NatLangChain Target

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'natlangchain'
    static_configs:
      - targets: ['your-api-host:5000']
```

### 2. Configure Notifications

Edit `alertmanager/alertmanager.yml`:

**Slack:**
```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/XXX/YYY/ZZZ'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - channel: '#natlangchain-alerts'
```

**PagerDuty:**
```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'your-service-key'
```

**Email:**
```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@example.com'
  smtp_auth_username: 'alerts@example.com'
  smtp_auth_password: 'app-password'
```

### 3. Add Custom Alerts

Edit `prometheus/alerts.yml` to add organization-specific rules.

## Alerts Reference

| Alert | Severity | Threshold | Description |
|-------|----------|-----------|-------------|
| NatLangChainDown | critical | up == 0 for 1m | API unreachable |
| NatLangChainHighLatency | warning | P95 > 5s for 5m | Slow responses |
| NatLangChainHighErrorRate | warning | > 5% errors | Server errors |
| NatLangChainChainInvalid | critical | valid == 0 | Blockchain corruption |
| NatLangChainLockdownMode | critical | mode == lockdown | Emergency mode |
| NatLangChainBackupStale | warning | > 48h since backup | Backup overdue |

## Kubernetes Deployment

For Kubernetes with Prometheus Operator:

```bash
kubectl apply -k k8s/monitoring/
```

This deploys:
- ServiceMonitor for automatic scraping
- PrometheusRule for alerts
- Grafana dashboards via ConfigMap

## Metrics Reference

### API Metrics
- `http_requests_total{status, endpoint}` - Request count
- `http_request_duration_seconds` - Latency histogram

### Blockchain Metrics
- `natlangchain_chain_valid` - Chain validation status
- `natlangchain_blocks_total` - Total blocks mined
- `natlangchain_pending_entries` - Pending entry queue

### Security Metrics
- `natlangchain_security_violations_total{type}` - Violations
- `natlangchain_boundary_mode{mode}` - Current mode
- `natlangchain_auth_failures_total` - Auth failures

### LLM Metrics
- `natlangchain_llm_requests_total{provider, status}` - LLM calls
- `natlangchain_llm_request_duration_seconds` - LLM latency
- `natlangchain_circuit_breaker_state{name, state}` - Circuit status

## Troubleshooting

### Prometheus not scraping NatLangChain

1. Check target status: http://localhost:9090/targets
2. Verify NatLangChain is exposing `/metrics`
3. Check network connectivity

### Alerts not firing

1. Check Prometheus rules: http://localhost:9090/rules
2. Verify alert expression in Prometheus UI
3. Check Alertmanager: http://localhost:9093

### Grafana shows no data

1. Verify Prometheus datasource is configured
2. Check time range selection
3. Inspect query in panel edit mode
