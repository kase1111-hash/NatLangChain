# Dependency Map for Refocus Plan

**Generated:** 2026-02-06 (Phase 0 deliverable)

## Verdict: NO BLOCKERS — All Cut/Defer Modules Are Safe to Remove

Every import from a CUT or DEFER module into a KEEP module is wrapped in a
`try/except` block with a feature flag (`NCIP_*_AVAILABLE`). Deleting these
modules will silently disable the features — exactly the intended behavior.

---

## Test Baseline

**Run:** `python -m pytest tests/ --tb=no -q --ignore=tests/test_boundary_rbac_integration.py`

| Metric | Count |
|--------|-------|
| **Passed** | 2,029 |
| **Failed** | 44 |
| **Skipped** | 34 |
| **Errors** | 54 |
| **Collection Errors** | 1 (`test_boundary_rbac_integration.py`) |

### Pre-existing Failures (NOT caused by refocus)

| File | Failures/Errors | Root Cause |
|------|----------------|------------|
| `test_e2e_blockchain_pipelines.py` | 32 errors | `api/state.py` import chain broken (`managers` not exported) |
| `test_api_endpoints.py` | 22 errors | Same import chain issue |
| `test_storage_postgresql.py` | 24 failures | PostgreSQL mock issues (`AttributeError: 'MagicMock'`) |
| `test_cli.py` | 6 failures | CLI module import issues |
| `test_validator_critical.py` | 5 failures | Sanitization behavior mismatches |
| `test_integration.py` | 3 failures | Missing sentence-transformers |
| `test_emergency_overrides.py` | 3 failures | Module-level issues |
| `test_p2p_network.py` | 1 failure | P2P config issues |
| `test_llm_providers.py` | 1 failure | Provider initialization |
| `test_fido2_auth.py` | 1 failure | FIDO2 mock issues |
| `test_boundary_rbac_integration.py` | 1 collection error | Circular import (`managers`) |

---

## Hard Dependencies of KEEP Modules

These are the **non-try/except** imports — the true dependency chain.

### Core Source Modules

| KEEP Module | Hard Dependencies |
|-------------|-------------------|
| `blockchain.py` | stdlib only (`hashlib`, `json`, `time`, `datetime`, `typing`) |
| `validator.py` | `anthropic` (pip) |
| `semantic_search.py` | `numpy` (pip), `blockchain` (KEEP) |
| `contract_parser.py` | `anthropic` (pip) |
| `contract_matcher.py` | `anthropic` (pip), `blockchain` (KEEP), `contract_parser` (KEEP) |
| `llm_providers.py` | `requests` (pip) |
| `entry_quality.py` | stdlib only |
| `rate_limiter.py` | stdlib only |
| `encryption.py` | `cryptography` (pip) |
| `pou_scoring.py` | `anthropic` (pip) |

### API Blueprints

| KEEP Blueprint | Hard Dependencies |
|----------------|-------------------|
| `api/core.py` | `api/state` (KEEP), `api/utils` (KEEP) |
| `api/contracts.py` | `api/state` (KEEP), `api/utils` (KEEP) |
| `api/search.py` | `api/state` (KEEP), `api/utils` (KEEP) |
| `api/state.py` | `blockchain` (KEEP), `storage` (KEEP) |
| `api/utils.py` | `api/ssrf_protection` (KEEP) |
| `api/derivatives.py` | `api/state` (KEEP), `api/utils` (KEEP) |
| `api/monitoring.py` | `api/state` (KEEP), `api/utils` (KEEP) |
| `api/ssrf_protection.py` | stdlib only (`ipaddress`, `urllib`) |

**Conclusion:** The KEEP set is fully self-contained. No hard dependency escapes to CUT or DEFER modules.

---

## CUT Module Import Map

For each CUT module, every file that imports it:

### `market_pricing.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_market_pricing.py` | none | Delete test file |

### `treasury.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_treasury.py` | none | Delete test file |

### `observance_burn.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/anti_harassment.py` (DEFER) | try/except | Archived with anti_harassment |
| `tests/test_observance_burn.py` | none | Delete test file |
| `tests/test_integration_escalation.py` | none | Review/trim |

### `revenue_sharing.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api/__init__.py` | try/except | Clean import block |
| `src/api/revenue.py` (CUT) | direct | Delete blueprint |

### `permanence_endowment.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api/__init__.py` | try/except | Clean import block |

### `zk_privacy.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_zk_privacy.py` | none | Delete test file |

### `boundary_siem.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/boundary_protection.py` | try/except | Also cut (boundary cluster) |
| `src/boundary_modes.py` | try/except | Also cut (boundary cluster) |
| `src/agent_security.py` | try/except | Also cut (boundary cluster) |
| `tests/test_boundary_protection.py` | none | Delete/trim test |
| `tests/test_boundary_integration.py` | none | Delete/trim test |
| `tests/test_external_integration.py` | none | Review/trim |

### `fido2_auth.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_fido2_auth.py` | none | Delete test file |

### `jurisdictional.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/validator.py` (KEEP) | **try/except** (`NCIP_006_AVAILABLE`) | **Safe — feature silently disabled** |
| `tests/test_jurisdictional.py` | none | Delete test file |

### `mobile_deployment.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/api/__init__.py` | try/except | Clean import block |
| `src/api/mobile.py` (CUT) | direct | Delete blueprint |
| `tests/test_mobile_deployment.py` | none | Delete test file |

### `compute_to_data.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api/__init__.py` | try/except | Clean import block |
| `src/api/compute.py` (CUT) | direct | Delete blueprint |

### `data_composability.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api/__init__.py` | try/except | Clean import block |
| `src/api/composability.py` (CUT) | direct | Delete blueprint |

---

## DEFER Module Import Map

### `cognitive_load.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/validator.py` (KEEP) | **try/except** (`NCIP_012_AVAILABLE`) | **Safe — feature silently disabled** |
| `tests/test_cognitive_load.py` | none | Move to `_deferred/tests/` |

### `p2p_network.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/gossip_protocol.py` (DEFER) | — | Archived together |
| `src/nat_traversal.py` (DEFER) | — | Archived together |
| `tests/test_p2p_network.py` | none | Move to `_deferred/tests/` |
| `tests/test_block_compression.py` | none | Review |
| `tests/test_gossip_protocol.py` | none | Move to `_deferred/tests/` |
| `tests/test_nat_traversal.py` | none | Move to `_deferred/tests/` |

**Note:** p2p_network, gossip_protocol, and nat_traversal form a cluster — must be archived together.

### `negotiation_engine.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_negotiation_engine.py` | none | Move to `_deferred/tests/` |
| `tests/test_e2e_mediator_integration.py` | none | Move to `_deferred/tests/` |

### `dispute.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/api/__init__.py` | try/except | Clean import block |
| `tests/test_dispute.py` | none | Move to `_deferred/tests/` |

### `dialectic_consensus.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/api/__init__.py` | try/except | Clean import block |

### `semantic_diff.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `src/api/__init__.py` | try/except | Clean import block |
| `tests/test_semantic_diff.py` | none | Move to `_deferred/tests/` |

### `multi_model_consensus.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |

### `anti_harassment.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api.py` | try/except | Clean import block |
| `tests/test_anti_harassment.py` | none | Move to `_deferred/tests/` |

### `did_identity.py`
| Importing File | Guard | Action |
|----------------|-------|--------|
| `src/api/__init__.py` | try/except | Clean import block |
| `src/api/identity.py` (CUT) | direct | Delete blueprint |

---

## Unclassified Modules — Final Classification

Modules in `src/` not in KEEP, CUT, or DEFER. All are imported by
validator.py via try/except and have no hard dependents in the KEEP set.

### Reclassify as DEFER (imported by validator.py, all try/except guarded)

| Module | Lines | validator.py Flag | Reason |
|--------|-------|-------------------|--------|
| `validator_trust.py` | ~800 | `NCIP_007_AVAILABLE` | Trust scoring extensions |
| `protocol_amendments.py` | ~600 | `NCIP_014_AVAILABLE` | Amendment governance |
| `multilingual.py` | ~500 | `NCIP_003_AVAILABLE` | Multi-language support |
| `appeals.py` | ~700 | `NCIP_008_AVAILABLE` | Appeal process |
| `validator_mediator_coupling.py` | ~400 | `NCIP_011_AVAILABLE` | Coupling extensions |

### Reclassify as CUT (no KEEP dependencies, enterprise/infra features)

| Module | Lines | Reason |
|--------|-------|--------|
| `boundary_protection.py` | 1,259 | Boundary cluster (depends on cut boundary_siem) |
| `boundary_modes.py` | ~400 | Boundary cluster |
| `boundary_exceptions.py` | ~200 | Boundary cluster |
| `boundary_daemon.py` | ~800 | Boundary cluster |
| `boundary_rbac_integration.py` | ~500 | Boundary cluster |
| `agent_security.py` | ~600 | Boundary cluster |
| `security_enforcement.py` | 1,952 | Boundary cluster |
| `external_daemon_client.py` | ~300 | Boundary cluster |
| `escalation_fork.py` | ~500 | Depends on dispute (DEFER) |
| `marketplace.py` | ~800 | Token economics |
| `voluntary_fees.py` | ~300 | Token economics |
| `dreaming.py` | ~300 | Experimental |
| `regulatory_interface.py` | ~400 | Enterprise compliance |
| `sunset_clauses.py` | ~300 | Governance |
| `external_anchoring.py` | ~500 | External blockchain anchoring |

### Reclassify as DEFER (useful utilities)

| Module | Lines | Reason |
|--------|-------|--------|
| `cli.py` | ~800 | CLI tool — useful but not core |
| `swagger.py` | 1,397 | API docs — useful after API stabilizes |
| `ollama_chat_helper.py` | ~300 | Local LLM chat — nice to have |
| `adaptive_cache.py` | ~500 | Performance optimization — premature |
| `mediator_reputation.py` | ~500 | Reputation system — premature |
| `semantic_locking.py` | ~400 | Semantic lock semantics — nice to have |
| `semantic_oracles.py` | ~600 | Oracle integration — nice to have |
| `temporal_fixity.py` | ~400 | Temporal features — nice to have |
| `tracing.py` | ~400 | Distributed tracing — premature |

### Keep as-is (infrastructure)

| Module | Lines | Reason |
|--------|-------|--------|
| `__init__.py` | ~100 | Package init — must stay |
| `retry.py` | 548 | Used by multiple modules — general utility |
| `rbac.py` | ~500 | API access control — review if needed |
| `chain_interface.py` | 1,291 | Chain abstraction — check if used by KEEP |
| `governance_help.py` | ~300 | Help text — check if used |
| `migrations.py` | ~400 | Storage migrations — check if used |
| `backup.py` | ~300 | Chain backup — check if used |
| `drift_thresholds.py` | ~300 | Used by appeals (now DEFER) |
| `term_registry.py` | ~300 | Governance terms — check if used |
| `block_compression.py` | ~400 | Block compression — check if used by P2P (DEFER) |
| `emergency_overrides.py` | ~300 | Emergency controls — check if needed |

---

## API Blueprint Classification

### KEEP (8 files, ~3,300 lines)
`core.py`, `contracts.py`, `search.py`, `state.py`, `utils.py`, `derivatives.py`, `monitoring.py`, `ssrf_protection.py`

### CUT (6 files, ~4,200 lines)
`mobile.py`, `compute.py`, `composability.py`, `revenue.py`, `endowment.py`, `identity.py`

### DEFER (6 files, ~3,800 lines)
`boundary.py`, `anchoring.py`, `marketplace.py`, `chat.py`, `help.py`, `__init__.py` (needs cleanup)
