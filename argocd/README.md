# NatLangChain GitOps with ArgoCD

GitOps-based deployment using ArgoCD for declarative, version-controlled infrastructure.

## Architecture

```
argocd/
├── apps/                    # ArgoCD Applications
│   ├── root.yaml           # App-of-apps root
│   ├── natlangchain-staging.yaml
│   ├── natlangchain-production.yaml
│   ├── natlangchain-monitoring.yaml
│   └── applicationset.yaml # Multi-env generator
├── envs/                    # Environment-specific values
│   ├── staging/
│   │   └── values.yaml
│   └── production/
│       └── values.yaml
├── projects/               # ArgoCD Projects
│   └── natlangchain.yaml
├── notifications-cm.yaml   # Notification configuration
└── image-updater.yaml      # Automatic image updates
```

## Prerequisites

1. **Kubernetes Cluster** with ArgoCD installed
2. **ArgoCD CLI** (`brew install argocd`)
3. **kubectl** configured for your cluster

### Install ArgoCD

```bash
# Create namespace
kubectl create namespace argocd

# Install ArgoCD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for pods
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Port forward to access UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Access ArgoCD at https://localhost:8080 (username: `admin`)

## Quick Start

### 1. Create the Project

```bash
kubectl apply -f argocd/projects/natlangchain.yaml
```

### 2. Deploy the App-of-Apps

```bash
kubectl apply -f argocd/apps/root.yaml
```

This creates:
- `natlangchain-staging` - Auto-synced from HEAD
- `natlangchain-production` - Manual sync required
- `natlangchain-monitoring` - Prometheus/Grafana

### 3. Verify Deployment

```bash
# Using ArgoCD CLI
argocd login localhost:8080 --insecure
argocd app list

# Check sync status
argocd app get natlangchain-staging

# Sync manually
argocd app sync natlangchain-staging
```

## Environment Configuration

### Staging

| Setting | Value |
|---------|-------|
| Replicas | 2-5 |
| Image Tag | `main` (latest) |
| Auto-sync | Enabled |
| Domain | staging.natlangchain.io |
| Resources | 500m CPU, 512Mi RAM |

### Production

| Setting | Value |
|---------|-------|
| Replicas | 3-10 |
| Image Tag | Semver releases |
| Auto-sync | **Disabled** (manual) |
| Domain | api.natlangchain.io |
| Resources | 2 CPU, 2Gi RAM |

## Deployment Workflows

### Deploy to Staging

Staging auto-syncs on every push to `main`:

```bash
git push origin main
# ArgoCD automatically detects and syncs
```

### Deploy to Production

Production requires manual sync:

```bash
# Option 1: ArgoCD CLI
argocd app sync natlangchain-production

# Option 2: ArgoCD UI
# Navigate to natlangchain-production > Click "Sync"

# Option 3: kubectl
kubectl patch application natlangchain-production -n argocd \
  --type merge -p '{"operation": {"sync": {}}}'
```

### Rollback

```bash
# List history
argocd app history natlangchain-production

# Rollback to specific revision
argocd app rollback natlangchain-production <REVISION>
```

## Sync Policies

| Environment | Auto-Sync | Self-Heal | Prune |
|-------------|-----------|-----------|-------|
| Staging | Yes | Yes | Yes |
| Production | No | No | No |
| Monitoring | Yes | Yes | Yes |

## Notifications

Configure Slack/PagerDuty notifications:

1. Create secrets:

```bash
kubectl create secret generic argocd-notifications-secret -n argocd \
  --from-literal=slack-token=xoxb-... \
  --from-literal=pagerduty-token=...
```

2. Apply notification config:

```bash
kubectl apply -f argocd/notifications-cm.yaml
```

### Notification Triggers

| Event | Channel |
|-------|---------|
| Sync Succeeded | #natlangchain-deployments |
| Sync Failed | #natlangchain-alerts |
| Health Degraded | #natlangchain-alerts + PagerDuty |

## Image Updater

Enable automatic image updates:

### Install Image Updater

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml
```

### Configure

```bash
# Create registry credentials
kubectl create secret generic ghcr-credentials -n argocd \
  --from-literal=token=ghp_...

# Apply config
kubectl apply -f argocd/image-updater.yaml
```

### Update Strategies

| Environment | Strategy | Tags Allowed |
|-------------|----------|--------------|
| Staging | Latest | `main-*`, `sha-*` |
| Production | Semver | `v*.*.*` |

## RBAC

### Roles

| Role | Permissions |
|------|-------------|
| Developer | View all, sync staging |
| Operator | Full access all environments |
| Admin | Project admin |

### Configure Groups

```bash
argocd proj role add-group natlangchain developer my-ldap-dev-group
argocd proj role add-group natlangchain operator my-ldap-ops-group
```

## Troubleshooting

### Application Out of Sync

```bash
# Check diff
argocd app diff natlangchain-staging

# Force sync
argocd app sync natlangchain-staging --force
```

### Sync Failed

```bash
# View logs
argocd app logs natlangchain-staging

# Check events
kubectl get events -n natlangchain-staging
```

### Health Check Failed

```bash
# Check resource status
argocd app get natlangchain-production --show-operation

# View pod status
kubectl get pods -n natlangchain -l app.kubernetes.io/name=natlangchain
kubectl describe pod -n natlangchain <pod-name>
```

### Reset Application

```bash
# Hard refresh
argocd app get natlangchain-staging --hard-refresh

# Delete and recreate
argocd app delete natlangchain-staging
kubectl apply -f argocd/apps/natlangchain-staging.yaml
```

## Best Practices

1. **Never edit resources directly** - Always change via Git
2. **Use PRs for production** - Review before merge
3. **Pin production to releases** - Don't use `HEAD`
4. **Enable notifications** - Know when deploys happen
5. **Use sync windows** - Prevent off-hours deploys
6. **Monitor drift** - Set up alerts for manual changes

## Directory Structure

```
Repository
├── argocd/           # GitOps configuration (this directory)
├── charts/           # Helm charts
│   └── natlangchain/
├── k8s/              # Raw Kubernetes manifests
│   └── monitoring/
└── src/              # Application source code
```

## Related Resources

- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [Helm Chart](../charts/natlangchain/README.md)
- [Kubernetes Monitoring](../k8s/monitoring/README.md)
