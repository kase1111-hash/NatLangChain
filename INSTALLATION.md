# Installation Guide

This guide covers how to set up NatLangChain for development and testing.

## Prerequisites

- **Python 3.9+**
- **Git**
- **pip** or **conda** for package management

### Optional

- **Docker** (for containerized deployment)
- **YubiKey** (for FIDO2 authentication features)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/kase1111-hash/NatLangChain.git
cd NatLangChain
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run the API Server

```bash
python src/api.py
```

The server will start at `http://localhost:5000`.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for Claude LLM validation | Required |
| `CHAIN_DIFFICULTY` | Proof-of-work difficulty | `4` |
| `CHAIN_FILE` | Path to chain persistence file | `chain.json` |
| `VALIDATION_MODE` | `llm`, `hybrid`, `multi` | `hybrid` |

### Validation Modes

- **`llm`**: Full LLM-based Proof of Understanding
- **`hybrid`**: Symbolic pre-validation + LLM for complex entries
- **`multi`**: Cross-model consensus verification

## Verification

### Run Tests

```bash
pytest tests/
```

### Check API Health

```bash
curl http://localhost:5000/chain
```

### Post a Test Entry

```bash
curl -X POST http://localhost:5000/entry \
  -H "Content-Type: application/json" \
  -d '{"content": "Test entry", "author": "test", "intent": "Testing"}'
```

## Docker Deployment

### Build Image

```bash
docker build -t natlangchain .
```

### Run Container

```bash
docker run -p 5000:5000 -e ANTHROPIC_API_KEY=your_key natlangchain
```

### Docker Compose (with Monitoring)

```bash
cd deploy/monitoring
docker-compose up -d
```

This starts NatLangChain with Prometheus, Grafana, and Alertmanager.

## Kubernetes Deployment

### Using Helm

```bash
# Add Bitnami repo for dependencies (Redis, PostgreSQL)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install NatLangChain
helm install natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  --create-namespace \
  --set config.anthropicApiKey=your_key

# With custom values
helm install natlangchain ./charts/natlangchain \
  -f my-values.yaml \
  --namespace natlangchain \
  --create-namespace
```

### Key Helm Values

| Value | Description | Default |
|-------|-------------|---------|
| `replicaCount` | Number of replicas | `2` |
| `image.tag` | Image tag | `latest` |
| `ingress.enabled` | Enable ingress | `false` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `postgresql.enabled` | Deploy PostgreSQL | `true` |
| `redis.enabled` | Deploy Redis | `true` |
| `metrics.enabled` | Enable Prometheus metrics | `true` |

### Direct Kubernetes

```bash
# Apply base manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/

# Or with kustomize
kubectl apply -k k8s/overlays/production
```

## GitOps Deployment (ArgoCD)

### Prerequisites

1. ArgoCD installed in your cluster
2. GitHub repository accessible to ArgoCD

### Deploy with App-of-Apps

```bash
# Bootstrap all applications
kubectl apply -f argocd/apps/root.yaml
```

This deploys:
- **natlangchain-staging**: Auto-sync from HEAD, 2 replicas
- **natlangchain-production**: Manual sync, 3 replicas
- **natlangchain-monitoring**: Prometheus stack

### Environment-Specific Configuration

```
argocd/
├── apps/
│   ├── root.yaml              # App-of-apps bootstrap
│   ├── natlangchain-staging.yaml
│   ├── natlangchain-production.yaml
│   └── applicationset.yaml    # Dynamic environments
├── envs/
│   ├── staging/values.yaml    # Staging overrides
│   └── production/values.yaml # Production overrides
└── projects/
    └── natlangchain.yaml      # ArgoCD project with RBAC
```

### ArgoCD Image Updater

For automatic image updates, install ArgoCD Image Updater:

```bash
kubectl apply -f argocd/image-updater.yaml
```

## Production Checklist

Before deploying to production:

- [ ] Set `ANTHROPIC_API_KEY` via sealed secret or external secrets
- [ ] Configure PostgreSQL for persistent storage
- [ ] Set up Redis for distributed caching/rate limiting
- [ ] Enable TLS via cert-manager
- [ ] Configure ingress with rate limiting
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure alerting (Slack/PagerDuty)
- [ ] Enable RBAC (`ENABLE_RBAC=true`)
- [ ] Review network policies
- [ ] Set appropriate resource limits

## Load Testing

Validate your deployment with the load testing suite:

```bash
# Run TPS benchmark
./tests/load/run-tests.sh tps

# Run stress test
./tests/load/run-tests.sh stress

# Run with Locust (interactive)
./tests/load/run-tests.sh locust
```

See `tests/load/README.md` for detailed load testing documentation.

## Ecosystem Integration

NatLangChain integrates with the broader ecosystem. See [SPEC.md](SPEC.md) for integration specifications:

| Repository | Purpose | Integration |
|------------|---------|-------------|
| Agent OS | AI infrastructure | Posts intents, receives alignments |
| IntentLog | Reasoning version control | Feeds reasoning context |
| Value Ledger | Meta-value accounting | Receives settlement interfaces |
| Memory Vault | Work artifact storage | Stores effort data for MP-02 |
| Mediator Node | Third-party mediation | Mines alignments |

## Troubleshooting

### Common Issues

**LLM Validation Errors**
- Ensure `ANTHROPIC_API_KEY` is set correctly
- Check API rate limits

**Chain Corruption**
- Delete `chain.json` to reset
- Genesis block will be recreated

**Port Already in Use**
- Change port: `python src/api.py --port 5001`

### Getting Help

- Check the [FAQ](FAQ.md)
- Review [API Documentation](API.md)
- Open a GitHub Issue

## Next Steps

1. Read the [Technical Specification](SPEC.md)
2. Explore the [NCIP Governance Framework](docs/NCIP-000+.md)
3. Review the [User Manual](docs/user-manual.md)
4. Check the [API Documentation](API.md)

---

**Last Updated:** January 1, 2026
