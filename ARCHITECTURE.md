# NatLangChain Architecture

This document describes the architecture of NatLangChain, a prose-first, intent-native blockchain protocol.

## Overview

NatLangChain transforms professional relationships by using natural language as the primary substrate for immutable entries, rather than opaque bytecode. The system uses LLM-powered validation ("Proof of Understanding") to ensure semantic integrity.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            NatLangChain Stack                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend (Svelte + Tauri)    │  REST API (Flask)      │  P2P Network       │
├───────────────────────────────┼────────────────────────┼────────────────────┤
│  Desktop App                  │  api.py / api/         │  p2p_network.py    │
│  - Contract Management        │  - Core routes         │  - Peer discovery  │
│  - Wallet Integration         │  - Blueprints          │  - Sync            │
│  - Offline Support            │  - Authentication      │  - Broadcast       │
└───────────────────────────────┴────────────────────────┴────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│         Core Blockchain             │   │         Validation Layer            │
├─────────────────────────────────────┤   ├─────────────────────────────────────┤
│  blockchain.py                      │   │  validator.py                       │
│  - NatLangChain class               │   │  - Proof of Understanding (PoU)     │
│  - NaturalLanguageEntry             │   │  - HybridValidator                  │
│  - Block mining                     │   │  - Multi-model consensus            │
│  - Chain validation                 │   │                                     │
│                                     │   │  dialectic_consensus.py             │
│  encryption.py                      │   │  - Skeptic/Facilitator debate       │
│  - Data at-rest encryption          │   │                                     │
│  - AES-256                          │   │  pou_scoring.py                     │
│                                     │   │  - Scoring dimensions               │
└─────────────────────────────────────┘   └─────────────────────────────────────┘
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Feature Modules                                    │
├────────────────────┬────────────────────┬───────────────────────────────────┤
│  Semantic          │  Contracts         │  Governance                        │
├────────────────────┼────────────────────┼───────────────────────────────────┤
│  semantic_search   │  contract_parser   │  dispute.py                        │
│  semantic_diff     │  contract_matcher  │  appeals.py                        │
│  semantic_oracles  │  negotiation_engine│  escalation_fork.py                │
│                    │                    │  protocol_amendments.py            │
├────────────────────┼────────────────────┼───────────────────────────────────┤
│  Economic          │  Security          │  Advanced                          │
├────────────────────┼────────────────────┼───────────────────────────────────┤
│  treasury.py       │  boundary_daemon   │  mobile_deployment.py              │
│  market_pricing    │  anti_harassment   │  zk_privacy.py                     │
│  observance_burn   │  fido2_auth.py     │  mediator_reputation.py            │
└────────────────────┴────────────────────┴───────────────────────────────────┘
```

## Directory Structure

```
NatLangChain/
├── src/                    # Python source code (43 modules)
│   ├── api/               # NEW: Modular API blueprints
│   │   ├── __init__.py    # Blueprint registration
│   │   ├── core.py        # Core chain operations
│   │   ├── search.py      # Semantic search, drift detection
│   │   ├── mobile.py      # Mobile deployment endpoints
│   │   ├── state.py       # Shared state (blockchain instance)
│   │   └── utils.py       # Shared utilities (auth, validation)
│   ├── api.py             # Main API (monolithic, being refactored)
│   ├── blockchain.py      # Core blockchain data structures
│   ├── validator.py       # LLM-powered validation
│   └── ...                # Feature modules
│
├── tests/                 # Test suite (30+ test files)
├── frontend/             # Svelte + Tauri desktop app
├── docs/                 # Documentation (NCIP framework)
├── specs/               # Integration specifications
├── config/              # Configuration (canonical_terms.yaml)
└── data/                # Persistent blockchain storage
```

## Core Components

### 1. Blockchain (`blockchain.py`)

The foundation of the system:

```python
NatLangChain
├── chain: list[Block]              # Immutable block chain
├── pending_entries: list[Entry]    # Entries awaiting mining
├── add_entry(entry)                # Add natural language entry
├── mine_pending_entries()          # Create new block
├── validate_chain()                # Verify integrity
└── get_full_narrative()            # Human-readable history
```

**NaturalLanguageEntry**: Each entry contains:
- `content`: Natural language description
- `author`: Entry creator
- `intent`: Purpose summary
- `timestamp`: Creation time
- `validation_status`: PoU result
- `metadata`: Optional structured data

### 2. Validation Layer (`validator.py`)

**Proof of Understanding (PoU)**: LLM-based semantic validation

```
Entry → PoU Validator → Semantic Analysis → Decision (ACCEPT/REJECT/PENDING)
                ↓
        Multi-Model Consensus (optional)
                ↓
        Dialectic Debate (Skeptic vs Facilitator)
```

Validation modes:
- **Standard**: Single LLM validation
- **Multi-validator**: Multiple LLM perspectives
- **Dialectic**: Skeptic/Facilitator debate

### 3. API Layer (`api.py`, `api/`)

REST API with **212+ endpoints** organized into:

| Blueprint | Routes | Description |
|-----------|--------|-------------|
| core | `/health`, `/chain`, `/entry`, `/mine` | Basic blockchain operations |
| search | `/search/semantic`, `/drift/*` | Semantic search and drift |
| contracts | `/contract/*` | Contract parsing and matching |
| disputes | `/dispute/*` | Dispute management |
| mobile | `/mobile/*` | Mobile deployment |
| p2p | `/api/v1/*` | Peer-to-peer network |

### 4. Security Features

- **Rate Limiting**: 100 req/60 sec per IP
- **API Key Authentication**: Optional (default enabled)
- **Encryption at Rest**: AES-256 for chain data
- **Boundary Daemon**: Data sovereignty enforcement
- **FIDO2/WebAuthn**: Hardware security key support
- **ZK Privacy**: Zero-knowledge proofs for sensitive data

## Data Flow

### Entry Creation

```
1. Client → POST /entry
2. Validate JSON schema
3. Encrypt sensitive metadata (if enabled)
4. PoU validation (if requested)
   └── LLM analyzes content vs intent
5. Add to pending_entries
6. (Optional) Auto-mine into block
7. Persist to chain_data.json
```

### Semantic Search

```
1. Client → POST /search/semantic
2. Encode query with sentence-transformers
3. Compare embeddings across all entries
4. Return ranked results by semantic similarity
```

### Drift Detection

```
1. Original intent (on-chain) → Embedding
2. Execution log → Embedding
3. Calculate semantic distance
4. Return drift score and recommendations
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | LLM API key | Required for validation |
| `NATLANGCHAIN_API_KEY` | API authentication | None |
| `NATLANGCHAIN_REQUIRE_AUTH` | Require API key | `true` |
| `CHAIN_DATA_FILE` | Persistence file | `chain_data.json` |
| `RATE_LIMIT_REQUESTS` | Rate limit count | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window (sec) | `60` |

### Governance Configuration

Governance terms are defined in `config/canonical_terms.yaml`:
- Protocol amendment process (NCIP)
- Dispute resolution procedures
- Economic parameters

## Deployment

### Development

```bash
pip install -e ".[dev]"
python -m api  # or: python src/api.py
```

### Docker

```bash
# Single container
docker run -p 5000:5000 -e ANTHROPIC_API_KEY=your_key ghcr.io/kase1111-hash/natlangchain

# With monitoring (Prometheus, Grafana, Alertmanager)
cd deploy/monitoring && docker-compose up -d
```

### Kubernetes (Helm)

```bash
# Install with Helm
helm install natlangchain ./charts/natlangchain \
  --namespace natlangchain \
  --create-namespace \
  --set config.anthropicApiKey=your_key

# Key features included:
# - Deployment with rolling updates
# - HorizontalPodAutoscaler (3-10 replicas)
# - PodDisruptionBudget (min 2 available)
# - PostgreSQL and Redis as subcharts
# - ServiceMonitor for Prometheus
# - PrometheusRule for alerting
```

### GitOps (ArgoCD)

```bash
# Bootstrap app-of-apps pattern
kubectl apply -f argocd/apps/root.yaml

# Deploys:
# - natlangchain-staging (auto-sync, 2 replicas)
# - natlangchain-production (manual sync, 3 replicas)
# - natlangchain-monitoring (Prometheus stack)
```

See `argocd/README.md` for detailed GitOps configuration.

### Mobile

The `mobile_deployment.py` module provides:
- Device registration (iOS, Android, Web, Desktop)
- Edge AI model loading and inference
- Wallet integration (WalletConnect, MetaMask, Hardware)
- Offline state management and sync

## Extension Points

### Adding New Features

1. Create module in `src/`
2. Add optional import in `api.py` or create blueprint in `api/`
3. Register manager in `ManagerRegistry` (see `api/utils.py`)
4. Add routes with `@require_api_key` decorator
5. Write tests in `tests/`

### Adding New Blueprints

```python
# src/api/myfeature.py
from flask import Blueprint
from api.utils import managers, require_api_key

myfeature_bp = Blueprint('myfeature', __name__, url_prefix='/myfeature')

@myfeature_bp.route('/action', methods=['POST'])
@require_api_key
def action():
    if not managers.my_manager:
        return jsonify({"error": "Feature not available"}), 503
    # ... implementation
```

Register in `api/__init__.py`:
```python
from api.myfeature import myfeature_bp
ALL_BLUEPRINTS.append((myfeature_bp, ''))
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_blockchain.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Implementation Status

### Completed
- [x] Complete API blueprint refactoring (212+ endpoints)
- [x] Database abstraction layer (PostgreSQL support)
- [x] Horizontal scaling with Redis-backed distributed locking
- [x] Real-time monitoring and metrics (Prometheus/Grafana)
- [x] Helm chart for Kubernetes deployment
- [x] GitOps with ArgoCD (app-of-apps pattern)
- [x] OpenAPI/Swagger documentation (`/docs`)
- [x] Load testing suite (k6, Locust)
- [x] CI/CD with GitHub Actions
- [x] FIDO2/WebAuthn authentication
- [x] Zero-knowledge proof infrastructure

### Roadmap
- [ ] Web-based UI dashboard
- [ ] Multi-language semantic validation
- [ ] Cross-chain interoperability bridges
- [ ] Enhanced consensus algorithms (PoU v2)
