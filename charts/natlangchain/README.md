# NatLangChain Helm Chart

A Helm chart for deploying NatLangChain - Natural Language Blockchain Platform on Kubernetes.

## Prerequisites

- Kubernetes 1.23+
- Helm 3.8+
- PV provisioner support (if persistence enabled)

## Installation

```bash
# Add dependencies
helm dependency update

# Install
helm install natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  --create-namespace

# Install with custom values
helm install natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  --create-namespace \
  -f values-production.yaml
```

## Quick Start

### Minimal Installation

```bash
helm install natlangchain ./charts/natlangchain \
  --set redis.enabled=true
```

### Production Installation

```bash
helm install natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=api.example.com \
  --set ingress.tls[0].secretName=natlangchain-tls \
  --set ingress.tls[0].hosts[0]=api.example.com \
  --set autoscaling.enabled=true \
  --set metrics.serviceMonitor.enabled=true \
  --set config.boundaryMode=elevated
```

## Configuration

See [values.yaml](values.yaml) for the full list of configurable parameters.

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.repository` | Image repository | `ghcr.io/kase1111-hash/natlangchain` |
| `image.tag` | Image tag | `appVersion` |
| `service.type` | Service type | `ClusterIP` |
| `ingress.enabled` | Enable ingress | `false` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `persistence.enabled` | Enable persistence | `true` |
| `redis.enabled` | Deploy Redis | `true` |
| `postgresql.enabled` | Deploy PostgreSQL | `false` |

### Security Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.boundaryMode` | Security mode (open/standard/elevated/restricted/lockdown) | `standard` |
| `config.enableRbac` | Enable RBAC | `true` |
| `config.secretKey` | Flask secret key (auto-generated if empty) | `""` |
| `config.jwtSecretKey` | JWT secret key (auto-generated if empty) | `""` |

### External Services

#### External Redis

```yaml
redis:
  enabled: false
  external:
    enabled: true
    host: redis.example.com
    port: 6379
    existingSecret: my-redis-secret
    existingSecretPasswordKey: password
```

#### External PostgreSQL

```yaml
postgresql:
  enabled: false
  external:
    enabled: true
    host: postgres.example.com
    port: 5432
    database: natlangchain
    username: natlangchain
    existingSecret: my-pg-secret
    existingSecretPasswordKey: password
```

## Monitoring

Enable ServiceMonitor for Prometheus Operator:

```yaml
metrics:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 30s
```

Enable PrometheusRule for alerts:

```yaml
metrics:
  prometheusRule:
    enabled: true
```

## Upgrading

```bash
helm upgrade natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  -f values.yaml
```

## Uninstalling

```bash
helm uninstall natlangchain --namespace natlangchain
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n natlangchain -l app.kubernetes.io/name=natlangchain
```

### View logs

```bash
kubectl logs -n natlangchain -l app.kubernetes.io/name=natlangchain -f
```

### Check health

```bash
kubectl exec -n natlangchain deploy/natlangchain -- curl -s localhost:5000/health
```
