# NatLangChain Kubernetes Deployment

This directory contains Kubernetes manifests for deploying NatLangChain in a production environment.

## Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- PostgreSQL database
- Redis (for distributed locking/caching)
- NGINX Ingress Controller (optional, for external access)
- cert-manager (optional, for TLS certificates)

## Quick Start

```bash
# Create namespace and deploy
kubectl apply -k k8s/

# Or apply individually
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml  # Edit secrets first!
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
kubectl apply -f k8s/pdb.yaml
```

## Configuration

### Secrets

Before deploying, update `secret.yaml` with your actual credentials:

```yaml
stringData:
  DATABASE_URL: "postgresql://user:password@host:5432/natlangchain"
  REDIS_URL: "redis://host:6379/0"
  ANTHROPIC_API_KEY: "your-api-key"
  API_KEY: "your-api-key"
```

For production, use a secrets management solution:
- External Secrets Operator
- HashiCorp Vault
- Sealed Secrets
- AWS Secrets Manager

### Environment Variables

Edit `configmap.yaml` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `STORAGE_BACKEND` | `postgresql` | Storage backend (json, postgresql, memory) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format (json, console) |
| `WORKERS` | `4` | Gunicorn worker count |

## Components

| File | Description |
|------|-------------|
| `namespace.yaml` | Dedicated namespace |
| `configmap.yaml` | Non-sensitive configuration |
| `secret.yaml` | Sensitive credentials |
| `deployment.yaml` | API deployment with 3 replicas |
| `service.yaml` | ClusterIP and headless services |
| `hpa.yaml` | Horizontal Pod Autoscaler (3-10 replicas) |
| `pdb.yaml` | Pod Disruption Budget (min 2 available) |
| `ingress.yaml` | External access via NGINX Ingress |
| `serviceaccount.yaml` | RBAC for pod discovery |
| `networkpolicy.yaml` | Network segmentation |
| `kustomization.yaml` | Kustomize configuration |

## Monitoring

The deployment includes Prometheus annotations for automatic scraping:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "5000"
  prometheus.io/path: "/metrics"
```

## Health Checks

- **Liveness**: `/health/live` - Basic process health
- **Readiness**: `/health/ready` - Full dependency check

## Scaling

The HPA scales based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)

Scale behavior:
- Scale up: Aggressive (up to 4 pods every 15s)
- Scale down: Conservative (10% every 60s, 5min stabilization)

## Network Security

NetworkPolicy restricts traffic to:
- Ingress: Only from ingress-nginx namespace
- Egress: Only to PostgreSQL, Redis, DNS, and external HTTPS (Anthropic API)

## Customization with Kustomize

Create overlays for different environments:

```
k8s/
├── base/
│   └── kustomization.yaml
├── overlays/
│   ├── development/
│   │   └── kustomization.yaml
│   ├── staging/
│   │   └── kustomization.yaml
│   └── production/
│       └── kustomization.yaml
```

Example production overlay:

```yaml
# k8s/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../

images:
  - name: natlangchain
    newName: ghcr.io/kase1111-hash/natlangchain
    newTag: v1.0.0

replicas:
  - name: natlangchain-api
    count: 5
```

Apply with:
```bash
kubectl apply -k k8s/overlays/production/
```
