# Changelog

All notable changes to NatLangChain will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes._

---

## [0.1.0-alpha] - 2026-01-01

### Added

#### Boundary Protection System (`src/boundary_*.py`)
- **Boundary Daemon**: Six security modes (Open, Restricted, Trusted, Airgap, Coldroom, Lockdown)
- **Boundary SIEM Integration**: Security event monitoring and alerting
- **Input/Output Protection**: Prompt injection and RAG poisoning detection
- **Tripwire System**: Automatic security escalation on threshold violations
- **Human Override Ceremony**: Multi-step verification for security downgrades
- **Agent Attestation**: Cryptographic verification of AI agent capabilities
- **Dreaming Status Tracker**: Lightweight system activity monitoring

#### Security Panel GUI (`frontend/src/components/SecurityPanel.svelte`)
- Complete security management dashboard
- Five tabs: Overview, Violations, SIEM Alerts, Security Check, History
- Mode change interface with emergency lockdown button
- Real-time security statistics display
- Input security testing interface

#### Centralized Error Handling
- `BoundaryException` hierarchy for structured error handling
- Consistent logging across all boundary protection modules
- Graceful degradation on security check failures

#### Comprehensive Security Tests (`tests/test_exploit_backdoor.py`)
- 28 exploit and backdoor security tests
- Prompt injection attack prevention
- Data exfiltration prevention
- Privilege escalation prevention
- Encoded payload detection

#### Helm Chart & Kubernetes (`charts/natlangchain/`)
- Complete Helm chart for Kubernetes deployment
- 15 template files (Deployment, Service, Ingress, HPA, PDB, etc.)
- PostgreSQL and Redis as optional subcharts
- ServiceMonitor and PrometheusRule for monitoring
- Migration job for database setup
- Configurable values for all deployment scenarios

#### GitOps with ArgoCD (`argocd/`)
- App-of-apps pattern for multi-environment management
- Staging environment with auto-sync
- Production environment with manual sync
- ApplicationSet for dynamic environment creation
- ArgoCD project with RBAC roles (developer, operator, admin)
- ArgoCD Image Updater configuration
- Slack and PagerDuty notification templates

#### OpenAPI/Swagger Documentation (`src/swagger.py`)
- OpenAPI 3.0 specification for all 212+ endpoints
- Interactive Swagger UI at `/docs`
- OpenAPI spec available at `/openapi.json` and `/openapi.yaml`
- Request/response schemas for all endpoint categories

#### Load Testing Suite (`tests/load/`)
- k6 tests: smoke, TPS benchmark, stress, soak
- Locust tests with stepped load shape
- TPS targets: 100 (baseline), 500 (target), 1000 (stretch)
- Solana comparison at 65,000 TPS for context
- Automated test runner script

#### TPS Simulation Benchmark
- Solana network simulation for comparison
- 65,000 TPS benchmark target
- Performance profiling and bottleneck detection

#### Production Infrastructure
- **Storage Abstraction Layer** (`src/storage/`)
  - Pluggable storage backends for blockchain persistence
  - `JSONFileStorage`: Default file-based storage with atomic writes
  - `PostgreSQLStorage`: Production-ready with connection pooling
  - `MemoryStorage`: Fast in-memory storage for testing
  - Configuration via `STORAGE_BACKEND` environment variable

- **Monitoring & Metrics** (`src/monitoring/`)
  - `MetricsCollector`: Thread-safe counters, gauges, and histograms
  - Prometheus-compatible `/metrics` endpoint
  - Structured JSON logging with request context
  - Request middleware for automatic timing and logging
  - `@timed` and `@counted` decorators for instrumentation

- **Horizontal Scaling** (`src/scaling/`)
  - `LocalLockManager`: Thread-based locks for single instance
  - `RedisLockManager`: Distributed locks for multi-instance
  - `LocalCache`: In-memory LRU cache with TTL
  - `RedisCache`: Distributed cache for shared state
  - `InstanceCoordinator`: Leader election and instance discovery
  - `@with_lock` and `@cached` decorators

- **CLI Entry Point** (`src/cli.py`)
  - `natlangchain serve`: Start API server (dev or production)
  - `natlangchain check`: Verify installation and configuration
  - `natlangchain info`: Display system information

- **New API Endpoints**
  - `GET /metrics`: Prometheus text format metrics
  - `GET /metrics/json`: JSON format metrics
  - `GET /health/live`: Kubernetes liveness probe
  - `GET /health/ready`: Kubernetes readiness probe
  - `GET /health/detailed`: Comprehensive system diagnostics
  - `GET /cluster/instances`: List active API instances
  - `GET /cluster/info`: Cluster coordination status

#### Deployment
- **Kubernetes Manifests** (`k8s/`)
  - Namespace, ConfigMap, and Secret templates
  - Deployment with rolling updates and anti-affinity
  - Service (ClusterIP) and headless Service
  - HorizontalPodAutoscaler (CPU/memory based, 3-10 replicas)
  - PodDisruptionBudget (min 2 available)
  - NetworkPolicy for ingress/egress control
  - Ingress with TLS and rate limiting
  - ServiceAccount with RBAC for pod discovery
  - Kustomization for environment overlays

- **Database Migrations** (`migrations/`)
  - `001_initial_schema.sql`: Core tables (entries, blocks, contracts, disputes)
  - `002_add_semantic_search.sql`: pgvector embeddings for similarity search
  - `003_add_scaling_tables.sql`: Distributed locking, caching, job queue
  - `migrate.py`: Migration runner with status, rollback, dry-run support

#### Code Quality
- Modular API blueprint structure (`src/api/`)
- Strengthened mypy configuration with gradual typing
- Architecture documentation (`ARCHITECTURE.md`)

### Changed
- Package exports now include infrastructure accessors
- Optional dependencies reorganized: `redis`, `postgres`, `production`, `all`

### Fixed
- Moved misplaced test file from `src/` to `tests/`
- Thread safety in MemoryStorage using RLock

## [0.1.0] - 2024-01-15

### Added
- Initial release of NatLangChain
- Core blockchain implementation with natural language entries
- Proof of Understanding (PoU) validation via LLM
- Hybrid validation combining rules and LLM
- Flask REST API with 212+ endpoints
- Semantic search and drift detection
- Contract parsing and matching
- Dispute resolution system
- Mobile deployment support
- P2P network capabilities
- FIDO2 authentication support
- Zero-knowledge privacy features
- Docker and docker-compose configuration
- GitHub Actions CI/CD pipeline
- Comprehensive test suite (1300+ tests)

### Security
- API key authentication
- Rate limiting
- Input validation and sanitization
- Bandit security scanning in CI

---

## Version History

| Version | Date | Highlights |
|---------|------|------------|
| 0.1.0-alpha | 2026-01-01 | Boundary protection, Security Panel GUI, SIEM integration |
| 0.1.0 | 2024-01-15 | Initial release |

[Unreleased]: https://github.com/kase1111-hash/NatLangChain/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/kase1111-hash/NatLangChain/compare/v0.1.0...v0.1.0-alpha
[0.1.0]: https://github.com/kase1111-hash/NatLangChain/releases/tag/v0.1.0
