# NatLangChain Technical Specification
## Updated: January 1, 2026

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Ecosystem Architecture](#ecosystem-architecture)
3. [Core Architecture](#core-architecture)
4. [Mediator Protocol Suite (MP-01 to MP-05)](#mediator-protocol-suite)
5. [NCIP Governance Framework](#ncip-governance-framework)
6. [Anti-Harassment Design](#anti-harassment-design)
7. [Treasury System](#treasury-system)
8. [FIDO2/YubiKey Security Integration](#fido2yubikey-security-integration)
9. [ZK Privacy Infrastructure](#zk-privacy-infrastructure)
10. [Implementation Status Matrix](#implementation-status-matrix)
11. [Implemented Features](#implemented-features)
12. [Unimplemented Ideas](#unimplemented-ideas)
13. [Cross-Repo Integration Specifications](#cross-repo-integration-specifications)
14. [Implementation Plans](#implementation-plans)
15. [Technical Roadmap](#technical-roadmap)

---

## Project Overview

**NatLangChain** is a prose-first, intent-native blockchain protocol whose sole purpose is to record explicit human intent in natural language and let the system find alignment.

### Core Principle
> "Post intent. Let the system find alignment."

### Key Innovation
Unlike traditional blockchains where transactions are opaque bytecode, NatLangChain entries are human-readable prose. The system uses LLM-powered validation ("Proof of Understanding") to ensure semantic integrity while preserving full auditability.

### Mission
Transform professional relationships by eliminating the "first contact" barrier—enabling work to sell itself without cold outreach, through AI-mediated autonomous matching and negotiation.

### Canonical Doctrines
- **Refusal Doctrine**: What we refuse to automate (consent, agreement, authority, value finality, dispute resolution, moral judgment)
- **Automation Doctrine**: What we do automate (possibility expansion, consistency checking, evidence collection, provenance, risk surfacing, mediation support)

---

## Ecosystem Architecture

NatLangChain is the spine of a 12-repository ecosystem. Each repo has distinct responsibilities:

### Repository Map

| Repository | Purpose | Integration with NatLangChain |
|------------|---------|------------------------------|
| **NatLangChain** | Prose-first blockchain for intent recording | Core ledger |
| **Agent OS** | Locally-controlled AI infrastructure | Posts intents, receives alignments |
| **IntentLog** | Version control for reasoning ("why") | Feeds reasoning context to NatLangChain |
| **Value Ledger** | Meta-value accounting layer | Receives settlement interfaces (MP-05) |
| **Learning Contracts** | AI learning governance | Enforces what agents may learn |
| **Memory Vault** | Secure work artifact storage | Stores raw effort data for MP-02 |
| **Boundary Daemon** | Trust boundary enforcement | Prevents unauthorized data flow |
| **Finite-Intent-Executor** | Posthumous intent execution | Executes delayed NatLangChain agreements |
| **RRA-Module** | Resurrects dormant repos as agents | Converts repos to autonomous contract posters |
| **Mediator Node** | Third-party contract mediation | Mines alignments, earns facilitation fees |
| **Common** | Shared schemas and primitives | Provides common data formats |

### Architectural Premise

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER LAYER                                   │
│   (Humans post intents, ratify agreements, declare settlements)     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                    LOCAL SOVEREIGNTY LAYER                          │
│  ┌─────────────┐  ┌────────────────┐  ┌────────────────────┐        │
│  │  Agent OS   │  │ Learning       │  │ Boundary Daemon    │        │
│  │ (Root of    │  │ Contracts      │  │ (Trust Boundary    │        │
│  │  Trust)     │  │ (AI Governance)│  │  Enforcement)      │        │
│  └──────┬──────┘  └───────┬────────┘  └─────────┬──────────┘        │
│         │                 │                     │                   │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────┐
│                    INTENT & EFFORT LAYER                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐              │
│  │ IntentLog   │  │ Memory Vault │  │ Value Ledger   │              │
│  │ (Why Track) │  │ (Work Store) │  │ (Meta-Value)   │              │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘              │
└─────────┼────────────────┼──────────────────┼───────────────────────┘
          │                │                  │
┌─────────▼────────────────▼──────────────────▼───────────────────────┐
│                      NATLANGCHAIN CORE                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 NatLangChain Blockchain                       │   │
│  │  • Natural Language Entries (Canonical Record)                │   │
│  │  • MP-01: Negotiation & Ratification                          │   │
│  │  • MP-02: Proof-of-Effort Receipts                            │   │
│  │  • MP-03: Dispute & Escalation                                │   │
│  │  • MP-04: Licensing & Delegation                              │   │
│  │  • MP-05: Settlement & Capitalization                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────┐
│                      MEDIATION LAYER                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Mediator Node (Third-Party)                      │   │
│  │  • Discovers alignments between intents                       │   │
│  │  • Proposes settlements (never decides)                       │   │
│  │  • Earns facilitation fees for successful matches             │   │
│  │  • User-selectable LLM models                                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              RRA-Module (Repo Resurrection)                   │   │
│  │  • Converts dormant repos to autonomous agents                │   │
│  │  • Auto-posts daily work as contracts                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Finite-Intent-Executor                           │   │
│  │  • Executes predefined posthumous intent                      │   │
│  │  • Delayed agreement execution                                │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Architecture

### Current Architecture (Implemented)

```
┌─────────────────────────────────────────────────┐
│              REST API Layer                     │
│  (Flask - Agent OS Integration)                 │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│         NatLangChain Core Blockchain            │
│  - Natural Language Entries                     │
│  - Block Mining (PoW)                           │
│  - Chain Validation                             │
│  - Pending Entry Pool                           │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│           Validation Layer                      │
│  - Proof of Understanding (LLM)                 │
│  - Hybrid Validator (Symbolic + LLM)            │
│  - Dialectic Consensus (Skeptic/Facilitator)   │
│  - Multi-Model Consensus                        │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│         Advanced Features Layer                 │
│  - Semantic Search (embeddings)                 │
│  - Semantic Drift Detection                     │
│  - Temporal Fixity (T0 snapshots)               │
│  - Semantic Oracles                             │
│  - Live Contracts (matching/negotiation)        │
└─────────────────────────────────────────────────┘
```

---

## Mediator Protocol Suite

The Mediator Protocol (MP) suite defines five normative specifications:

### MP-01: Negotiation & Ratification Protocol
**Status:** Implemented (Core)
**Purpose:** Governs how intents are declared, mediated, and ratified into agreements.

**Key Rules:**
- LLMs may propose; humans must decide
- No inferred consent; explicit ratification required
- All proposals are provisional until human sign-off
- Mutual acceptance required for finality

**Escalation Fork (Optional Extension):** ✅ IMPLEMENTED
When mediation fails, either party can trigger an Escalation Fork:
- Fee pool splits 50/50 (mediator retained / bounty pool)
- Community solvers compete to resolve the deadlock
- Effort-based bounty distribution (word count + iterations + alignment score)
- 7-day solver window with timeout refund mechanism
- Requires **Observance Burn** (5% of stake) to trigger
- See [Escalation-Protocol.md](docs/Escalation-Protocol.md) for full specification
- Implementation: `src/escalation_fork.py`, 8 API endpoints (`/fork/*`)

**Observance Burn Protocol:** ✅ IMPLEMENTED
Ceremonial token destruction that serves economic and signaling purposes:
- Permanently removes tokens from circulation
- Proportional redistribution to remaining holders
- Burn reasons: VoluntarySignal, EscalationCommitment, RateLimitExcess, ProtocolViolation, CommunityDirective
- Epitaphs allow burners to leave meaningful messages
- See [Observance-Burn.md](docs/Observance-Burn.md) for full specification
- Implementation: `src/observance_burn.py`, 8 API endpoints (`/burn/*`)

### MP-02: Proof-of-Effort Receipt Protocol
**Status:** Partially Implemented (70%)
**Purpose:** Records cryptographically verifiable receipts of human intellectual effort.

**Key Rules:**
- Effort is validated as process over time, not single output
- Receipts are append-only and time-stamped
- Validators assess coherence, progression, consistency
- Uncertainty is preserved, not collapsed

**Implementation Gaps:**
- [ ] Continuous effort capture integration (voice, text, edits)
- [ ] Automatic segmentation of effort units
- [ ] Integration with Memory Vault for artifact storage

### MP-03: Dispute & Escalation Protocol
**Status:** ✅ Implemented (100%)
**Purpose:** Governs how disputes are surfaced, recorded, and escalated.

**Key Rules:**
- Disputes are signals, not failures
- Evidence freezing upon dispute initiation
- No automated resolution; human judgment required
- Explicit escalation declarations

**Implementation Status:** ✅ IMPLEMENTED (src/dispute.py)
- ✅ Dispute Declaration entry type
- ✅ Evidence freezing mechanism
- ✅ Escalation to mediator/arbitrator/court
- ✅ Dispute Package export for external arbitration
- ✅ LLM-assisted dispute analysis
- ✅ 9 API endpoints for full dispute lifecycle

### MP-04: Licensing & Delegation Protocol
**Status:** Partially Implemented (30%)
**Purpose:** Governs how rights to use, delegate, or sublicense are granted.

**Key Rules:**
- All authority is explicit, scoped, time-bounded
- Delegation requires human ratification
- Revocation paths must exist
- Actions outside scope are invalid

**Implementation Gaps:**
- [ ] License entry type with scope/duration/transferability
- [ ] Delegation chain tracking
- [ ] Revocation mechanism
- [ ] Scope violation detection

### MP-05: Settlement & Capitalization Protocol
**Status:** Partially Implemented (40%)
**Purpose:** Governs how agreements are settled and transformed into value.

**Key Rules:**
- Settlement is a human act, not automated
- Capitalization is optional
- Separation of meaning and execution
- Explicit finality required

**Implementation Gaps:**
- [ ] Mutual settlement declaration
- [ ] Capitalization Interface generator
- [ ] External system hooks (accounting, payment rails)
- [ ] Partial/staged settlement support

---

## NCIP Governance Framework

> **Reference Document:** [NCIP-000+](docs/NCIP-000+.md) — Consolidated NCIP Index (Canonical)

The NatLangChain Improvement Proposals (NCIPs) establish a comprehensive semantic governance framework. All validators, mediators, agents, and governance processes MUST comply with this framework.

### NCIP Registry (001–015)

| NCIP | Title | Scope | Depends On |
|------|-------|-------|------------|
| NCIP-001 | Canonical Term Registry | Semantic primitives & definitions | NatLangChain Spec |
| NCIP-002 | Semantic Drift Thresholds & Validator Responses | Drift detection & enforcement | NCIP-001 |
| NCIP-003 | Multilingual Semantic Alignment & Drift | Cross-language meaning preservation | NCIP-001, NCIP-002 |
| NCIP-004 | Proof of Understanding (PoU) Generation & Verification | Semantic comprehension validation | NCIP-001, NCIP-002 |
| NCIP-005 | Dispute Escalation, Cooling Periods & Semantic Locking | Dispute lifecycle & meaning freeze | NCIP-002, NCIP-004 |
| NCIP-006 | Jurisdictional Interpretation & Legal Bridging | Law–semantics boundary | NCIP-001–005 |
| NCIP-007 | Validator Trust Scoring & Reliability Weighting | Validator reputation & weighting | NCIP-002, NCIP-004 |
| NCIP-008 | Semantic Appeals, Precedent & Case Law Encoding | Meaning appeals & precedent | NCIP-002, NCIP-005, NCIP-007 |
| NCIP-009 | Regulatory Interface Modules & Compliance Proofs | External regulatory proofs | NCIP-004, NCIP-006 |
| NCIP-010 | Mediator Reputation, Slashing & Market Dynamics | Mediation incentives & penalties | NCIP-005, NCIP-007 |
| NCIP-011 | Validator–Mediator Interaction & Weight Coupling | Joint trust dynamics | NCIP-007, NCIP-010 |
| NCIP-012 | Human Ratification UX & Cognitive Load Limits | Human decision safety | NCIP-004, NCIP-005 |
| NCIP-013 | Emergency Overrides, Force Majeure & Semantic Fallbacks | Crisis handling | NCIP-005, NCIP-006 |
| NCIP-014 | Protocol Amendments & Constitutional Change | Meta-governance | NCIP-001–013 |
| NCIP-015 | Sunset Clauses, Archival Finality & Historical Semantics | End-of-life meaning | NCIP-005, NCIP-014 |

### Conceptual Groupings

| Group | NCIPs | Purpose |
|-------|-------|---------|
| **Semantic Core** | 001 → 002 → 003 → 004 | Foundational definitions and validation |
| **Dispute & Stability** | 005 → 008 → 013 → 015 | Conflict resolution and archival |
| **Trust & Markets** | 007 → 010 → 011 | Reputation and economic incentives |
| **Law & Reality Interfaces** | 006 → 009 | Legal compliance bridging |
| **Human Safety** | 012 | UX and cognitive limits |
| **Constitutional Layer** | 014 | Meta-governance (depends on all lower NCIPs) |

### Validator Load Order (Normative)

Validators MUST load NCIPs in sequential order from 001 through 015:

```
NCIP-001 → NCIP-002 → NCIP-003 → NCIP-004 → NCIP-005 → NCIP-006 →
NCIP-007 → NCIP-008 → NCIP-009 → NCIP-010 → NCIP-011 → NCIP-012 →
NCIP-013 → NCIP-014 → NCIP-015
```

> **Failure to load any dependency invalidates higher-layer NCIPs.**

### Constitutional Interpretation Rule (Normative)

> **"Higher-numbered NCIPs may constrain behavior but may not redefine semantics established by lower-numbered NCIPs."**

Specific prohibitions:
- NCIP-014 cannot alter historical meaning
- NCIP-015 cannot reopen locked semantics
- NCIP-006 cannot override canonical definitions
- NCIP-012 cannot simplify meaning beyond PoU guarantees

### MP-to-NCIP Mapping

The Mediator Protocol (MP) suite maps to the NCIP governance framework:

| MP | Primary NCIP Alignment | Notes |
|----|------------------------|-------|
| MP-01 (Negotiation & Ratification) | NCIP-001, NCIP-004 | Uses canonical terms and PoU validation |
| MP-02 (Proof-of-Effort) | NCIP-004 | Direct implementation of PoU Generation & Verification |
| MP-03 (Dispute & Escalation) | NCIP-005, NCIP-008 | Implements dispute lifecycle and semantic locking |
| MP-04 (Licensing & Delegation) | NCIP-001 | Relies on canonical definitions |
| MP-05 (Settlement & Capitalization) | NCIP-015, NCIP-014 | End-of-life semantics and protocol amendments |

### Discrepancy Resolution Status

The following discrepancies between NCIP-000+ governance and current implementation have been reviewed:

#### NCIP Authoritative (Implementation Required)

#### 1. Semantic Locking ✅ RESOLVED
- **NCIP-005 requires:** "Semantic Locking" — the ability to freeze meaning during disputes
- **Status:** ✅ IMPLEMENTED in `src/semantic_locking.py`, integrated with `src/dispute.py`
- **Features:** LockedState (registry version, prose hash, anchor language, PoUs, NCIPs), SemanticLock dataclass, SemanticLockManager, lock verification, action logging
- **Resolution:** ✅ NCIP-005 IS AUTHORITATIVE — full semantic locking implemented

#### 2. Cooling Periods ✅ RESOLVED
- **NCIP-005 requires:** "Cooling Periods" — mandatory waiting periods during dispute lifecycle
- **Status:** ✅ IMPLEMENTED in `src/semantic_locking.py`, integrated with `src/dispute.py`
- **Features:** D3 (24h) and D4 (72h) cooling periods, CoolingPeriodStatus, action enforcement (allowed/forbidden during cooling), automatic cooling period calculation
- **Resolution:** ✅ NCIP-005 IS AUTHORITATIVE — full cooling periods implemented

#### 3. Validator Trust Scoring ✅ RESOLVED
- **NCIP-007 requires:** Validator Trust Scoring & Reliability Weighting
- **Status:** ✅ IMPLEMENTED in `src/validator_trust.py`
- **Features:** Trust profiles, scoped scores, decay/recovery, weighting function, anti-centralization safeguards
- **Resolution:** ✅ NCIP-007 IS AUTHORITATIVE — full validator trust scoring implemented

#### 9. Multilingual Alignment
- **NCIP-003 requires:** Cross-language meaning preservation with drift detection
- **Current implementation:** English only (noted in gaps)
- **Gap:** No parallel language entries or cross-language validation
- **Resolution:** ✅ NCIP-003 IS AUTHORITATIVE — implement when prioritized (marked MEDIUM in roadmap)

#### Pending Definition (Both Documents)

#### 4. Mediator Reputation ✅ RESOLVED
- **NCIP-010 requires:** Mediator Reputation, Slashing & Market Dynamics
- **Status:** ✅ IMPLEMENTED in `src/mediator_reputation.py`
- **Features:** CTS scoring (6 dimensions), bonding, slashing (5 offense types), cooldowns, treasury, market dynamics
- **Resolution:** ✅ NCIP-010 IS AUTHORITATIVE — full mediator reputation implemented

#### 5. Validator-Mediator Weight Coupling ✅ RESOLVED
- **NCIP-011 requires:** Joint trust dynamics between validators and mediators
- **Status:** ✅ IMPLEMENTED in `src/validator_mediator_coupling.py`
- **Features:** Role separation enforcement, ValidatorWeight & MediatorWeight classes, SemanticConsistencyScore, influence gate mechanism, competitive mediation, dispute phase handling, delayed weight updates, collusion resistance
- **Resolution:** ✅ NCIP-011 IS AUTHORITATIVE — full validator-mediator coupling implemented

#### 6. Human Ratification UX Limits ✅ RESOLVED
- **NCIP-012 requires:** Cognitive Load Limits for human decision-making
- **Status:** ✅ IMPLEMENTED in `src/cognitive_load.py`
- **Features:** Cognitive Load Budget (CLB), rate limits, cooling periods, information hierarchy, PoU gate, UI safeguards
- **Resolution:** ✅ NCIP-012 IS AUTHORITATIVE — full cognitive load management implemented

#### 7. Emergency Override Protocol ✅ RESOLVED
- **NCIP-013 requires:** Emergency Overrides, Force Majeure & Semantic Fallbacks
- **Status:** ✅ IMPLEMENTED in `src/emergency_overrides.py`
- **Features:** 6 force majeure classes, emergency declarations, semantic fallbacks, oracle evidence, dispute handling, timeout/expiry, abuse prevention
- **Resolution:** ✅ NCIP-013 IS AUTHORITATIVE — full emergency override protocol implemented

#### Pre-Launch Requirement

#### 8. Constitutional Amendment Process ✅ RESOLVED
- **NCIP-014 requires:** Formal Protocol Amendments & Constitutional Change procedures
- **Status:** ✅ IMPLEMENTED in `src/protocol_amendments.py`
- **Features:** Amendment classes A-E, 6-stage ratification process, PoU voting, semantic compatibility, emergency amendments, constitution versioning
- **Resolution:** ✅ NCIP-014 IS AUTHORITATIVE — full protocol amendment system implemented

### Comprehensive NCIP Implementation Gaps

The following table summarizes all NCIP requirements and their implementation status:

| NCIP | Title | Implementation Status | Key Gaps |
|------|-------|----------------------|----------|
| NCIP-001 | Canonical Term Registry | ✅ Implemented | `config/canonical_terms.yaml`, `src/term_registry.py`, validator integration |
| NCIP-002 | Semantic Drift Thresholds | ✅ Implemented | `src/drift_thresholds.py`, integrated with `src/semantic_diff.py` |
| NCIP-003 | Multilingual Semantic Alignment | ✅ Implemented | `src/multilingual.py`, CSAL declarations, cross-language drift, validator integration |
| NCIP-004 | Proof of Understanding | ✅ Implemented | `src/pou_scoring.py`, integrated with `src/validator.py` |
| NCIP-005 | Dispute Escalation & Semantic Locking | ✅ Implemented | `src/semantic_locking.py`, integrated with `src/dispute.py` |
| NCIP-006 | Jurisdictional Interpretation | ✅ Implemented | `src/jurisdictional.py`, integrated with `src/validator.py` |
| NCIP-007 | Validator Trust Scoring | ✅ Implemented | `src/validator_trust.py`, integrated with `src/validator.py` |
| NCIP-008 | Semantic Appeals & Precedent | ✅ Implemented | `src/appeals.py`, SCR generation, precedent decay, validator integration |
| NCIP-009 | Regulatory Interface Modules | ✅ Implemented | `src/regulatory_interface.py`, RIMs for SEC/GDPR/HIPAA/SOX, ZK proofs, WORM certificates |
| NCIP-010 | Mediator Reputation & Slashing | ✅ Implemented | `src/mediator_reputation.py`, integrated with `src/dispute.py` |
| NCIP-011 | Validator-Mediator Weight Coupling | ✅ Implemented | `src/validator_mediator_coupling.py`, influence gate, role separation, collusion resistance |
| NCIP-012 | Human Ratification UX Limits | ✅ Implemented | `src/cognitive_load.py`, integrated with `src/validator.py` |
| NCIP-013 | Emergency Overrides & Force Majeure | ✅ Implemented | `src/emergency_overrides.py`, 6 force majeure classes, semantic fallbacks, oracle evidence, dispute handling |
| NCIP-014 | Protocol Amendments | ✅ Implemented | `src/protocol_amendments.py`, full amendment lifecycle, ratification process |
| NCIP-015 | Sunset Clauses & Archival Finality | ✅ Implemented | `src/sunset_clauses.py`, 6 trigger types, state machine, archival finality, temporal context binding |

### Detailed NCIP Implementation Requirements

#### NCIP-001: Canonical Term Registry
**Status:** ✅ IMPLEMENTED
**Files:** `src/term_registry.py`, `config/canonical_terms.yaml`, `tests/test_term_registry.py`

**Implemented Features:**
- [x] YAML registry file with 33 canonical terms (17 core, 8 protocol-bound, 8 extension)
- [x] Term class enforcement (core, protocol-bound, extension)
- [x] Validator integration to flag deprecated terms as issues
- [x] Synonym mapping with recommendations to use canonical form
- [x] Registry versioning (v1.0)
- [x] `HybridValidator.validate_terms()` method for NCIP-001 compliance
- [x] Comprehensive test suite

#### NCIP-002: Semantic Drift Thresholds
**Status:** ✅ IMPLEMENTED
**Files:** `src/drift_thresholds.py`, `src/semantic_diff.py`, `tests/test_drift_thresholds.py`

**Implemented Features:**
- [x] Formal drift levels: D0 (0.00-0.10), D1 (0.10-0.25), D2 (0.25-0.45), D3 (0.45-0.70), D4 (0.70-1.00)
- [x] Mandatory validator responses per level (proceed, warn, pause, require_ratification, reject, escalate_dispute)
- [x] Drift aggregation rules (max score governs per NCIP-002 Section 6)
- [x] Temporal Fixity context (`TemporalFixityContext` class with T₀ binding)
- [x] Logging requirements for D1+ events with `DriftLogEntry`
- [x] Human override constraints (D2/D3 allowed, D4 requires formal dispute)
- [x] Integration with `SemanticDriftDetector` for NCIP-002 compliance
- [x] `SemanticDriftClassifier` with 54 passing tests

#### NCIP-003: Multilingual Semantic Alignment
**Status:** ✅ IMPLEMENTED
**Files:** `src/multilingual.py`, `tests/test_multilingual.py`

**Implemented Features:**
- [x] Canonical Semantic Anchor Language (CSAL) declaration per contract (default: English)
- [x] Language roles: anchor (canonical source), aligned (semantic equivalent), informational (non-executable)
- [x] Cross-language drift measurement using NCIP-002 thresholds (D0-D4)
- [x] Translation validation (no added/removed obligations, no scope changes)
- [x] Validator language pair reporting with drift scores
- [x] MultilingualAlignmentManager class for contract management
- [x] CanonicalTermMapping for registry integration per NCIP-001
- [x] Human ratification in multilingual contexts (reference CSAL, acknowledge aligned)
- [x] Machine-readable alignment spec (YAML structure per Section 10)
- [x] 40+ supported ISO 639-1 language codes
- [x] HybridValidator integration with 12 methods for multilingual operations
- [x] Comprehensive test suite

#### NCIP-004: Proof of Understanding Scoring
**Status:** ✅ IMPLEMENTED
**Files:** `src/pou_scoring.py`, `src/validator.py`, `tests/test_pou_scoring.py`

**Implemented Features:**
- [x] PoU scoring dimensions: Coverage, Fidelity, Consistency, Completeness
- [x] Score thresholds: ≥0.90 Verified, 0.75-0.89 Marginal, 0.50-0.74 Insufficient, <0.50 Failed
- [x] Minimum dimension score governs overall status (per NCIP-004 Section 6)
- [x] Binding effect: verified PoU fixes meaning, waives misunderstanding claims
- [x] Semantic fingerprint generation with SHA-256 hashing
- [x] PoU structure validation per NCIP-004 Section 4.1
- [x] Mandatory validator actions per status level
- [x] `BindingPoURecord` for storing bound PoUs
- [x] `HybridValidator.validate_pou()` method for NCIP-004 compliance
- [x] `is_pou_required()` helper per NCIP-004 Section 3
- [x] 47 passing unit tests

#### NCIP-005: Semantic Locking & Cooling Periods
**Status:** ✅ IMPLEMENTED
**Files:** `src/semantic_locking.py`, `src/dispute.py`, `tests/test_semantic_locking.py`

**Implemented Features:**
- [x] Semantic Lock mechanism (freezes registry version, prose wording, anchor semantics, PoUs, NCIPs)
- [x] Lock Time (Tₗ = Tᵢ) tracking per NCIP-005 Section 4
- [x] Cooling periods: 24h for D3 disputes, 72h for D4 disputes
- [x] Allowed actions during cooling (clarification, settlement_proposal, mediator_assignment, evidence_submission)
- [x] Prohibited actions during cooling (escalation, enforcement, semantic_change)
- [x] Prohibited actions during ANY lock (contract_amendment, re_translation, registry_upgrade, pou_regeneration)
- [x] Escalation path state machine: COOLING → MUTUAL_SETTLEMENT → MEDIATOR_REVIEW → ADJUDICATION → BINDING_RESOLUTION → RESOLVED
- [x] Resolution outcomes: dismissed, clarified, amended, terminated, compensated
- [x] Lock verification against frozen state
- [x] `DisputeManager.create_dispute_ncip_005()` for full NCIP-005 compliance
- [x] 37 passing unit tests

#### NCIP-006: Jurisdictional Bridging
**Status:** ✅ IMPLEMENTED
**Files:** `src/jurisdictional.py`, `tests/test_jurisdictional.py`

**Implemented Features:**
- [x] Jurisdiction declaration requirement (ISO 3166-1 country codes + US state subdivisions)
- [x] Jurisdiction roles: enforcement, interpretive, procedural (NCIP-006 Section 4)
- [x] Legal Translation Artifacts (LTAs) with non-authoritative status
- [x] LTA validation: reject if introduces obligations, narrows/broadens scope
- [x] LTA drift detection (D3/D4 = excessive drift, rejection required)
- [x] Semantic authority disclaimer auto-generation
- [x] Court ruling handling with semantic lock preservation
- [x] Semantic override rulings automatically rejected
- [x] Cross-jurisdiction conflict resolution with most-restrictive enforcement
- [x] Machine-readable jurisdiction bridge spec (YAML format, Section 11)
- [x] Core principle enforced: "Law constrains enforcement, not meaning"
- [x] Validator integration: 10+ integration methods in `validator.py`
- [x] Comprehensive test suite (12+ tests)

#### NCIP-007: Validator Trust Scoring
**Status:** ✅ IMPLEMENTED
**Files:** `src/validator_trust.py`, `tests/test_validator_trust.py`

**Implemented Features:**
- [x] Trust Profile structure with overall and scoped scores
- [x] Scopes: semantic_parsing, drift_detection, proof_of_understanding, dispute_analysis, legal_translation_review
- [x] Positive signals: consensus_match, pou_ratified, correct_drift_flag, dispute_performance, consistency
- [x] Negative signals: overruled_by_lock, false_positive_drift, unauthorized_interpretation, consensus_disagreement, harassment_pattern
- [x] Weighting function: `effective_weight = base_weight × trust_score × scope_modifier`
- [x] Base weights by validator type: LLM=1.0, hybrid=1.1, symbolic=0.9, human=1.2
- [x] Trust decay formula: `score_t = score_0 × e^(−λΔt)` with λ=0.002 after 30 days inactivity
- [x] Maximum weight cap (0.35) and minimum diversity threshold (3 validators)
- [x] Trust freeze during disputes (retroactive updates prohibited)
- [x] Harassment accelerated decay (2× magnitude)
- [x] HybridValidator integration with `register_as_trusted_validator()`, `record_validation_outcome()`, `calculate_validator_weight()`, `weighted_multi_validator_consensus()`
- [x] Comprehensive test suite (18 tests)

#### NCIP-008: Semantic Appeals & Precedent
**Status:** ✅ IMPLEMENTED
**Files:** `src/appeals.py`, `tests/test_appeals.py`

**Implemented Features:**
- [x] Appeal lifecycle: declared → scoped lock → review → awaiting_ratification → resolved
- [x] Appealable items: validator_rejection (D2-D4), drift_classification, pou_mismatch, mediator_interpretation
- [x] Non-appealable items: term_registry_mapping (requires NCIP-001), settlement_outcome
- [x] Appeal review panel (N≥3 validators, distinct implementations, no original validator overlap)
- [x] Semantic Case Records (SCR) with all required fields per Section 5.2
- [x] SCR integrity verification (hash-based, append-only)
- [x] Precedent weight decay: <3 months High, 3-12 months Medium, >12 months Low, superseded registry Zero
- [x] Precedent indexing by canonical_term_id, drift_class, jurisdiction_context, date_range
- [x] Advisory precedent signals (increase confidence, reduce uncertainty, flag interpretations)
- [x] Validators MUST NOT auto-accept/reject based on precedent (explicit prose takes priority)
- [x] Abuse prevention: non-refundable burn fees, escalating fees for repeated appeals
- [x] Cooldown periods after failed appeals (30 days default, escalating)
- [x] Harassment score impact for frivolous appeals
- [x] Scoped semantic lock during appeals (only disputed terms locked)
- [x] Human ratification required for outcome finalization
- [x] Precedent divergence warnings per Section 7
- [x] Machine-readable SCR index per Section 11
- [x] HybridValidator integration with 15+ methods for appeal management
- [x] Core principle enforced: "Past meaning may inform — but never replace explicit present intent"
- [x] Comprehensive test suite (35 tests)

#### NCIP-009: Regulatory Interface Modules & Compliance Proofs
**Status:** ✅ IMPLEMENTED
**Files:** `src/regulatory_interface.py`, `tests/test_regulatory_interface.py`

**Implemented Features:**
- [x] RegulatoryInterfaceManager with full compliance proof lifecycle
- [x] Default RIMs for SEC 17a-4, GDPR, HIPAA, SOX regimes
- [x] 8 compliance claim types: immutability, retention, consent, access_control, privacy, authorship, integrity, audit_trail
- [x] Proof mechanisms: hash_chain, worm_certificate, ratified_pou, zero_knowledge, merkle_proof, signature
- [x] Zero-Knowledge Proof generation and verification for privacy claims
- [x] WORM (Write-Once-Read-Many) certificates for retention proofs
- [x] Access logging with Boundary Daemon integration
- [x] Proof constraints enforcement: minimal, purpose-bound, non-semantic
- [x] Disclosure scopes: regulator_only, auditor_only, court_order, public
- [x] Abuse prevention: fishing expedition detection, semantic leakage prevention
- [x] Validator verification with scope minimality checks
- [x] Proof package structure per NCIP-009 Section 6
- [x] Proof expiration and revocation
- [x] HybridValidator integration with NCIP-009 imports
- [x] Comprehensive test suite (42 tests)
- [x] Core principle: "Compliance is proven cryptographically, not narratively."

#### NCIP-010: Mediator Reputation & Slashing
**Status:** ✅ IMPLEMENTED
**Files:** `src/mediator_reputation.py`, `tests/test_mediator_reputation.py`

**Implemented Features:**
- [x] Mediator registration with stake bond (minimum 10,000 units, default 50,000 units in configured currency)
- [x] Reputation dimensions: Acceptance Rate, Semantic Accuracy, Appeal Survival, Dispute Avoidance, Coercion Signal, Latency Discipline
- [x] Composite Trust Score (CTS) calculation with configurable weights
- [x] Slashing conditions: semantic_manipulation (10-30%), repeated_invalid_proposals (5-15%), coercive_framing (15%), appeal_reversal (5-20%), collusion_signals (progressive)
- [x] Cooldowns and market throttling (offense-specific durations)
- [x] Treasury integration for slashed funds (50% treasury, 50% affected party)
- [x] Proposal ranking by CTS with diversity weighting
- [x] Trust-weighted sampling for validator attention
- [x] Harassment accelerated decay (coercion signal tracking)
- [x] DisputeManager integration with `register_mediator()`, `slash_mediator()`, `rank_mediator_proposals()`, `get_treasury_balance()`
- [x] Comprehensive test suite (15 tests)

#### NCIP-011: Validator-Mediator Weight Coupling
**Status:** ✅ IMPLEMENTED
**Files:** `src/validator_mediator_coupling.py`, `tests/test_validator_mediator_coupling.py`

**Implemented Features:**
- [x] Role separation enforcement (Protocol Violation PV-V3 for crossing roles)
- [x] Validators: assess semantic validity, drift, PoU quality (may NOT propose or negotiate)
- [x] Mediators: propose alignments and settlements (may NOT validate or override)
- [x] Humans: ratify, reject, escalate (may NOT delegate final authority)
- [x] Separate weight domains: ValidatorWeight (VW) from NCIP-007, MediatorWeight (MW) from NCIP-010
- [x] Influence gate: `∑(Validator VW × semantic_consistency_score) >= GateThreshold` (default 0.68)
- [x] Semantic consistency scoring: intent alignment, term registry consistency, drift risk, PoU symmetry
- [x] Competitive mediation: proposals sorted by MW (primary), time ordering, human selection
- [x] Hidden proposals: those below gate threshold are not visible
- [x] Dispute-time behavior: VW elevated, MW reduced, no new proposals during lock
- [x] Delayed weight updates: 3 epochs (anti-gaming per Section 8.2)
- [x] Retroactive adjustment allowed for appeal-based scoring
- [x] Collusion resistance: separate weight ledgers, gated interaction, delayed updates
- [x] Collusion detection: high pass rate detection, synchronized update detection
- [x] Machine-readable coupling schema per Section 11
- [x] HybridValidator integration with 15+ methods for coupling management
- [x] Core principle enforced: "Validators measure meaning. Mediators surface alignment. Neither may substitute."
- [x] Comprehensive test suite (36 tests)

#### NCIP-012: Human Ratification UX Limits
**Status:** ✅ IMPLEMENTED
**Files:** `src/cognitive_load.py`, `tests/test_cognitive_load.py`

**Implemented Features:**
- [x] Cognitive Load Budget (CLB) with context-specific limits: simple=7, financial=9, licensing=9, dispute=5, emergency=3 semantic units
- [x] Budget exceeded detection with automatic segmentation request
- [x] Information hierarchy with 7 mandatory levels: Intent Summary → Consequences → Irreversibility Flags → Risks & Unknowns → Alternatives → Canonical Term References → Full Text (optional)
- [x] Presentation order enforcement (skipping levels prohibited)
- [x] Rate limits: ≤5 ratifications/hour, ≤2 disputes/day, ≤3 licenses/day
- [x] Automatic counter reset after time windows
- [x] Cooling periods: 12h agreement, 24h settlement/licensing, 6h dispute
- [x] Cooling period waiver with validator confidence threshold (≥0.85)
- [x] PoU Gate: paraphrase must be viewed, user must confirm, correction drift max 0.20
- [x] UI safeguards validation: no dark patterns, no default accept, no countdown pressure (unless emergency), no bundled unrelated decisions
- [x] Dark pattern detection (confirm-shaming, hidden costs, trick questions, forced continuity, misdirection, roach motel)
- [x] Lock visibility requirement post-ratification
- [x] Validator integration: `validator_measure_cognitive_load()`, `validator_detect_ux_violations()`
- [x] HybridValidator integration: `create_ratification()`, `check_cognitive_load_budget()`, `check_rate_limits()`, `check_cooling_period()`, `validate_information_hierarchy()`, `validate_pou_gate()`, `validate_ui_compliance()`, `attempt_ratification()`
- [x] Comprehensive test suite (40+ tests)

#### NCIP-013: Emergency Overrides & Force Majeure
**Status:** ✅ IMPLEMENTED
**Files:** `src/emergency_overrides.py`, `tests/test_emergency_overrides.py`

**Implemented Features:**
- [x] EmergencyManager class with full emergency lifecycle management
- [x] Force majeure classes: natural_disaster, government_action, armed_conflict, infrastructure_failure, medical_incapacity, systemic_protocol_failure
- [x] Emergency declarations with required fields (scope, affected_refs, declared_reason, review_after, max_duration)
- [x] Semantic fallbacks declared at contract creation (post-hoc fallbacks rejected per Section 7)
- [x] Execution effects: pause_execution, delay_deadlines, freeze_settlement, trigger_fallback
- [x] Prohibited effects enforcement: redefine_obligations, impose_new_duties, alter_intent, collapse_uncertainty
- [x] Oracle evidence handling (evidence, not authority per Section 5)
- [x] Emergency disputes with semantic lock and burden of proof on declarer
- [x] Timeout and reversion rules (review_after, max_duration, silent continuation forbidden)
- [x] Escalation threshold (30 days unresolved)
- [x] Abuse prevention with harassment penalties and repeat multiplier
- [x] Machine-readable emergency policy generation
- [x] Validator behavior checks (skeptical treatment, scope/duration validation)
- [x] HybridValidator integration with NCIP-013 imports
- [x] Comprehensive test suite (39 tests)

#### NCIP-014: Protocol Amendments
**Status:** ✅ IMPLEMENTED
**Files:** `src/protocol_amendments.py`, `tests/test_protocol_amendments.py`

**Implemented Features:**
- [x] Amendment classes: A (Editorial >50%), B (Procedural >67%), C (Semantic >75%), D (Structural >90%), E (Existential/Fork-only 100%)
- [x] AmendmentManager class with full amendment lifecycle management
- [x] Amendment proposal format with affected artifacts tracking
- [x] Mandatory PoU for voting participants (what changes, what doesn't, who affected, why agree/disagree)
- [x] 6-stage ratification process: PROPOSAL_POSTING → COOLING_PERIOD → DELIBERATION_WINDOW → HUMAN_RATIFICATION → SEMANTIC_LOCK → FUTURE_ACTIVATION
- [x] Context-specific cooling periods: A=7d, B=14d, C=21d, D=30d, E=90d
- [x] Deliberation windows by class: A=7d, B=14d, C=30d, D=60d, E=180d
- [x] Semantic compatibility checks with drift measurement
- [x] D3+ drift requires migration guidance (rejects proposals without migration path)
- [x] Emergency amendments with auto-expiry protection (max 30 days)
- [x] Constitution versioning: major.minor.patch format, version bound at entry creation
- [x] Non-retroactivity enforcement (past meaning is inviolable)
- [x] Prohibited action enforcement (silent upgrades, retroactive changes, meaning rewriting, fork suppression)
- [x] HybridValidator integration with 12 methods for amendment management
- [x] Comprehensive test suite

#### NCIP-015: Sunset Clauses & Archival Finality
**Status:** ✅ IMPLEMENTED
**Files:** `src/sunset_clauses.py`, `tests/test_sunset_clauses.py`

**Implemented Features:**
- [x] SunsetManager class with full lifecycle management
- [x] Sunset trigger types: time_based, event_based, condition_fulfilled, exhaustion, revocation, constitutional
- [x] State machine: DRAFT → RATIFIED → ACTIVE → SUNSET_PENDING → SUNSET → ARCHIVED (no backward transitions)
- [x] Archival finality: semantics frozen forever, drift detection disabled, no reinterpretation permitted
- [x] Temporal context binding (registry version, language, jurisdiction, PoUs, validator snapshot)
- [x] Default sunset policies: contracts=20yr, licenses=10yr, delegations=2yr, standing_intents=1yr, settlements=immediate
- [x] Historical semantics preservation (meaning at T₀ retained regardless of later changes)
- [x] Validator behavior: enforce triggers exactly, disable drift post-archive, reject reactivation without restatement
- [x] Mediator constraints: can cite as context, cannot propose actions on expired authority, must restate to reactivate
- [x] Emergency integration: sunset timers pause during emergency, semantics unchanged
- [x] Archive integrity verification with hash
- [x] Machine-readable sunset & archive schema
- [x] HybridValidator integration with NCIP-015 imports
- [x] Comprehensive test suite (51 tests)

---

## Anti-Harassment Design

NatLangChain introduces economic pressure to compress conflict. Without constraints, such pressure could be abused to impose unwanted cost, attention, or friction on another party. Harassment is defined as any use of negotiation or dispute mechanisms without a legitimate intent to reach resolution.

### Core Principle
> **Any attempt to harass must be strictly more expensive for the harasser than for the target.**

This property is achieved through asymmetric initiation costs, free non-engagement, bounded interaction surfaces, and escalating penalties for non-resolving behavior.

### Dual Initiation Paths

All interactions MUST fall into one of two mutually exclusive initiation paths:

| Path | Trigger Condition | Initiator Cost | Counterparty Obligation | Harassment Exposure |
|------|-------------------|----------------|-------------------------|---------------------|
| **Breach / Drift Dispute** | On-chain evidence of violation or semantic drift in existing agreement | Immediate symmetric stake S (escrowed) | Must match stake within T_stake or accept fallback outcome | Low — initiator is economically exposed first |
| **Voluntary Request** | New negotiation, amendment, or reconciliation request without breach | Small non-refundable burn fee | None — may ignore indefinitely at zero cost | Very Low — ignored requests impose only self-cost |

### Frivolous Breach Claim Protection

- Initiator MUST stake first and fully in all breach or drift disputes
- If counterparty declines to match stake:
  - Dispute resolves immediately to predefined fallback state
  - Initiator gains no further leverage or escalation rights
- Repeated breach initiations on same contract trigger escalating minimum stakes (+50% per recent non-resolving dispute)
- Per-contract cooldown window (e.g., 30 days) after resolution before new breach claims permitted

### Counter-Proposal Griefing Limits

- Counter-proposals per dispute strictly capped (default: 3)
- Counter-proposal fees increase exponentially (base_fee × 2ⁿ)
- All counter-proposal fees burned immediately
- Maximum cost of prolonged disagreement is predictable, finite, and borne primarily by the extending party

### Protection for Low-Resource Parties

- Protocol treasury MAY subsidize defensive stakes for participants with demonstrated good-faith engagement
- Subsidies MUST be: opt-in, transparent, derived solely from on-chain dispute outcomes
- Public harassment score derived from dispute patterns automatically increases future initiation costs for flagged actors

### Design Outcome

When correctly implemented, the anti-harassment design guarantees:
- Ignoring harassment is always free
- Engaging is optional and symmetrically priced
- Executing harassment is expensive, bounded, and self-limiting

No additional authority, moderation, or judgment is required. The economic layer itself neutralizes the abuse vector.

---

## Treasury System

### Purpose

The NatLangChain Treasury is a fully on-chain, algorithmic fund that:
- Holds protocol funds from burns, counter-fees, and escalated stakes
- Subsidizes defensive stakes for low-resource participants in ILRM disputes
- Maintains no discretionary control by nodes or humans

### High-Level Flow

#### Inflows
- Burns from unresolved disputes (TimeoutWithBurn)
- Counter-proposal fees (exponential fees burned to treasury)
- Escalated stakes from repeated frivolous initiation

#### Eligibility Check
- Participant must be target of dispute (not initiator)
- Must opt in for subsidy (e.g., call `requestSubsidy`)
- Must have good on-chain dispute history (low harassment score)

#### Subsidy Calculation
- Match stake required to participate in ILRM
- Partial subsidy (50–100%) based on treasury balance and per-user caps

### Anti-Sybil / Abuse Protections

| Protection | Mechanism |
|------------|-----------|
| Single subsidy per dispute | `disputeSubsidized[disputeId]` mapping |
| Rolling window per participant | `maxPerParticipant` cap |
| Reputation check | `harassmentScore` threshold |
| Treasury sustainability | Balance check before payout |

### Key Features

| Feature | Design Choice | Reason |
|---------|---------------|--------|
| Treasury holder | Smart contract only | Trustless, transparent |
| Subsidy mechanism | Opt-in, dispute-specific | Avoid Sybil / abuse |
| Anti-Sybil | Single subsidy per dispute, rolling caps, reputation check | Prevent griefer exploitation |
| Maximum exposure | Max per dispute, max per participant | Treasury sustainability |
| Automatic inflows | Burns, counter-fees, escalated stakes | Closed-loop economy |
| Transparency | All actions emitted as events | On-chain verification |

### Currency-Agnostic Design

NatLangChain does not have its own native cryptocurrency. The treasury and economic layer are designed to operate with established cryptocurrencies (ETH, USDC, or other ERC-20 tokens). All stake amounts, fees, and subsidies are denominated in whichever currency is configured for a given deployment.

**Key principles:**
- Treasury holds and disburses funds in the configured staking currency
- All economic parameters (stakes, fees, caps) are currency-agnostic numerical values
- Deployments can configure their preferred currency (ETH, stablecoins, etc.)
- Burns and fees are executed in the same currency as stakes

### Optional Enhancements
- Dynamic caps: Scale max per participant based on treasury size
- Tiered subsidies: Low harassment score → full subsidy, higher score → partial
- Cross-contract integration: ILRM calls treasury to automatically fund defensive stake escrow
- Time-window enforcement: Reset `participantSubsidyUsed` periodically
- Multi-token support: Accept multiple staking tokens (ETH, USDC, DAI, etc.)

---

## FIDO2/YubiKey Security Integration

FIDO2 hardware security keys (YubiKeys) provide phishing-resistant authentication and hardware-backed signing across NatLangChain modules.

### Module Integration Priority

#### 1. IP & Licensing Reconciliation Module (ILRM) — High Priority
**Purpose:** Handle disputes, stakes, proposals, and acceptances with identity-sensitive operations.

**Integration Points:**
- FIDO2 signature verification in `acceptProposal` and `submitLLMProposal`
- YubiKey public key registration on-chain (via WebAuthn challenge-response)
- Sign proposals with FIDO2 message (e.g., hash of `disputeId + "accept"`)

**Benefits:**
- Proves initiator identity without address exposure
- Aligns with ZKP privacy layer
- Secures reactive dispute flows

#### 2. NatLangChain Negotiation Module — Medium-High Priority
**Purpose:** Proactive drafting layer for intent alignment and contract finalization.

**Integration Points:**
- Frontend: Auth users via YubiKey before submitting clauses/hashes
- On-Chain: Verify FIDO2 signatures for commitment transactions

**Benefits:**
- Passwordless login to negotiation interface
- Prevents unauthorized clause changes
- Hardware-backed contract signing

#### 3. RRA Module — Medium Priority
**Purpose:** Autonomous agent orchestration across modules.

**Integration Points:**
- FIDO2 auth in agent's mobile/off-chain component
- Sign agent delegation commands
- On-Chain: RRA contracts verify signatures for automated executions

**Benefits:**
- Hardware-backed agent control
- Secure user auth for triggering RRA actions

---

## ZK Privacy Infrastructure

### Dispute Membership Circuit

A Circom circuit using Poseidon hashing for Ethereum-compatible ZK proofs. Proves "I know a secret that hashes to the on-chain `identityManager`" without leaking the secret.

**Circuit: `prove_identity.circom`**
```circom
pragma circom 2.1.6;
include "circomlib/poseidon.circom";

template ProveIdentity() {
    signal input identitySecret;    // Private: User's secret salt/key
    signal input identityManager;   // Public: On-chain hash (e.g., initiatorHash)

    component hasher = Poseidon(1);
    hasher.inputs[0] <== identitySecret;
    hasher.out === identityManager; // Constraint: Must match public hash
}

component main {public [identityManager]} = ProveIdentity();
```

**On-Chain Verification:**
```solidity
function submitIdentityProof(
    uint256 _disputeId,
    uint[2] calldata _proofA,
    uint[2][2] calldata _proofB,
    uint[2] calldata _proofC,
    uint[1] calldata _publicSignals
) external {
    Dispute storage d = disputes[_disputeId];
    require(verifyProof(_proofA, _proofB, _proofC, _publicSignals), "Invalid proof");
    // _publicSignals[0] == d.initiatorHash or counterpartyHash
}
```

### Viewing Key Infrastructure

Selective de-anonymization for legal compliance while maintaining privacy.

**Components:**
| Component | Purpose |
|-----------|---------|
| **Pedersen Commitment** | On-chain commitment to evidence/identity without revelation |
| **Off-Chain Storage** | Encrypt metadata with viewing key, store on IPFS/Arweave |
| **Viewing Key (ECIES)** | Per-dispute key on secp256k1 curve |
| **Shamir's Secret Sharing** | m-of-n key split (e.g., 3-of-5: user, protocol DAO, neutral escrows) |

**Implementation:**
- Add `viewingKeyCommitment` to Dispute struct
- User submits ZKP proving they hold the key
- On legal request, reconstruct key from shares to decrypt IPFS data

### Inference Attack Mitigations

| Mitigation | Implementation |
|------------|----------------|
| **Batching** | Buffer submissions in queue contract; release in batches every X blocks |
| **Dummy Transactions** | Treasury funds automated "noop" calls at random intervals via oracles |
| **Mixnet Integration** | Nym or Hopr for tx submission to obscure origins |
| **Aggregate ZK Stats** | Prove "X disputes this week" without per-dispute details |

### Threshold Decryption for Legal Compliance

Decentralized "Compliance Council" using BLS or FROST threshold signatures:
- Key reconstruction requires m-of-n signatures (e.g., 3: user opt-in rep, protocol gov, independent auditor)
- Legal warrants trigger governance vote to release shares
- Transparent on-chain voting for reveals (emits events)
- No single point of failure

---

## Implementation Status Matrix

### ✅ FULLY IMPLEMENTED (Production Ready)

| Feature | Status | Files | API Endpoints |
|---------|--------|-------|---------------|
| **Core Blockchain** | ✅ Complete | `blockchain.py` | `/chain`, `/block/<id>` |
| Natural Language Entries | ✅ Complete | `blockchain.py` | `/entry` |
| Genesis Block | ✅ Complete | `blockchain.py` | Auto-created |
| Proof-of-Work Mining | ✅ Complete | `blockchain.py` | `/mine` |
| Chain Validation | ✅ Complete | `blockchain.py` | `/validate/chain` |
| Persistence (JSON) | ✅ Complete | `api.py` | Auto-save |
| **Validation Systems** | ✅ Complete | `validator.py` | `/entry/validate` |
| Proof of Understanding | ✅ Complete | `validator.py` | `/entry` (LLM mode) |
| Hybrid Validation | ✅ Complete | `validator.py` | `/entry` (default) |
| Multi-Validator Consensus | ✅ Complete | `validator.py` | `/entry` (multi mode) |
| Dialectic Consensus | ✅ Complete | `dialectic_consensus.py` | `/validate/dialectic` |
| Multi-Model Consensus | ✅ Complete | `multi_model_consensus.py` | Built-in |
| **Advanced Features** | ✅ Complete | Multiple | Various |
| Semantic Search | ✅ Complete | `semantic_search.py` | `/search/semantic` |
| Semantic Drift Detection | ✅ Complete | `semantic_diff.py` | `/drift/check` |
| Temporal Fixity (T0) | ✅ Complete | `temporal_fixity.py` | Embedded in entries |
| Semantic Oracles | ✅ Complete | `semantic_oracles.py` | Python API |
| Circuit Breakers | ✅ Complete | `semantic_oracles.py` | Python API |
| **Live Contracts** | ✅ Complete | `contract_*.py` | `/contract/*` |
| Contract Parsing | ✅ Complete | `contract_parser.py` | `/contract/post` |
| Contract Matching | ✅ Complete | `contract_matcher.py` | `/mine` (auto) |
| Contract Negotiation | ✅ Complete | `contract_matcher.py` | `/contract/respond` |
| Mediation Mining | ✅ Complete | `contract_matcher.py` | `/mine` |
| **REST API** | ✅ Complete | `api.py` | 20+ endpoints |

### 🚧 PARTIALLY IMPLEMENTED

| Feature | Status | What's Done | What's Missing |
|---------|--------|-------------|----------------|
| **WORM Archival** | 🚧 70% | T0 export format, legal certificates | Physical LTO tape writing automation |
| **MP-02 Proof-of-Effort** | 🚧 70% | Receipt structure, hashing | Continuous capture, segmentation |
| **MP-04 Licensing** | 🚧 30% | Basic contract terms | Full license lifecycle, delegation |
| **MP-05 Settlement** | 🚧 40% | Settlement concepts | Mutual declaration, capitalization interface |
| **Multi-Chain Branching** | 🚧 30% | Architecture designed | Git-like fork/merge implementation |
| **Agent-Driven Participation** | 🚧 20% | API ready for agents | Agent-OS integration, standing intents |
| **Reputation Systems** | 🚧 10% | Miner tracking in contracts | Full reputation scoring, stake slashing |

### ❌ NOT IMPLEMENTED (Documented Only)

| Feature | Documentation | Priority | Complexity | Target Repo |
|---------|---------------|----------|------------|-------------|
| **Distributed P2P Network** | README.md | HIGH 🔴 | Very High | NatLangChain |
| **Real-time Mediation Network** | future.md | HIGH 🔴 | High | Mediator Node |
| **Escrow Integration** | CONTRACTS.md | HIGH 🔴 | Medium | Value Ledger |
| **Web UI / Sandbox** | roadmap.md | HIGH 🔴 | Medium | NatLangChain |
| **MP-03 Dispute Protocol** | MP-03-spec.md | HIGH 🔴 | Medium | NatLangChain |
| **Anti-Harassment Economic Layer** | Anti-Harassment.md | HIGH 🔴 | Medium | NatLangChain |
| **Treasury System** | Treasury.md | HIGH 🔴 | Medium | NatLangChain |
| **FIDO2/YubiKey Integration** | FIDO-Yubi.md | HIGH 🔴 | Medium | ILRM, NatLangChain |
| **ZK Dispute Membership Circuit** | Dispute-membership-circuit.md | HIGH 🔴 | High | NatLangChain |
| **Viewing Key Infrastructure** | Dispute-membership-circuit.md | HIGH 🔴 | High | NatLangChain |
| **Automated Negotiation Engine** | final-features.md | HIGH 🔴 | Medium | NatLangChain |
| **Market-Aware Pricing** | final-features.md | MEDIUM 🟡 | Medium | NatLangChain |
| **Mobile Deployment** | final-features.md | MEDIUM 🟡 | High | All Modules |
| **Daily Work Output Automation** | future.md | MEDIUM 🟡 | Medium | RRA-Module |
| **Chain Subscription & Sync** | future.md | MEDIUM 🟡 | High | NatLangChain |
| **Cosmos SDK Integration** | cosmos.md | MEDIUM 🟡 | Very High | NatLangChain |
| **Multilingual Support** | multilingual.md | MEDIUM 🟡 | High | Common |
| **Benchmark Suite** | roadmap.md | MEDIUM 🟡 | Medium | NatLangChain |
| **Database Backend** | API.md | MEDIUM 🟡 | Low | NatLangChain |
| **Async Validation Pipeline** | API.md | MEDIUM 🟡 | Medium | NatLangChain |
| **LNI Multi-Agent Testing** | lni-testable-theory.md | MEDIUM 🟡 | High | Agent OS |
| **Threshold Decryption Compliance** | Dispute-membership-circuit.md | MEDIUM 🟡 | High | NatLangChain |
| **Inference Attack Mitigations** | Dispute-membership-circuit.md | MEDIUM 🟡 | Medium | NatLangChain |
| **Prediction Markets** | COMPLIANCE.md | LOW 🟢 | High | NatLangChain |
| **Narrative Staking** | COMPLIANCE.md | LOW 🟢 | High | NatLangChain |
| **Insurance Premium Integration** | COMPLIANCE.md | LOW 🟢 | Medium | Value Ledger |
| **Smart Contracts in NL** | API.md | LOW 🟢 | High | NatLangChain |

---

## Implemented Features (Detailed)

### 1. Core Blockchain ✅

**Files:** `src/blockchain.py`

**Capabilities:**
- Natural language entries as primary substrate
- SHA-256 cryptographic block chaining
- Genesis block with constitutional text
- Configurable proof-of-work difficulty
- Full chain validation and integrity checks
- JSON-based serialization/deserialization
- Persistent storage with auto-save
- Pending entry pool for mining

### 2. Validation Systems ✅

**Files:** `src/validator.py`, `src/dialectic_consensus.py`, `src/multi_model_consensus.py`

**Modes:**
- **Proof of Understanding**: LLM paraphrases to demonstrate comprehension
- **Hybrid Validator**: Symbolic pre-validation + LLM for complex entries
- **Dialectic Consensus**: Skeptic/Facilitator debate for precision
- **Multi-Model Consensus**: Cross-model verification (Claude + future GPT/Llama)

### 3. Semantic Features ✅

**Files:** `src/semantic_search.py`, `src/semantic_diff.py`

**Capabilities:**
- Embedding-based semantic search (sentence-transformers)
- Semantic drift detection ("Semantic Firewall")
- Circuit breakers for agent safety
- Duplicate detection

### 4. Temporal Fixity ✅

**Files:** `src/temporal_fixity.py`

**Capabilities:**
- T0 snapshot creation with cryptographic proof
- Legal certificate generation
- WORM archival export format
- SEC 17a-4, HIPAA compliance ready

### 5. Semantic Oracles ✅

**Files:** `src/semantic_oracles.py`

**Capabilities:**
- Verify external events against contract spirit
- OTC derivatives settlement support
- Force majeure verification
- Agent safety monitoring

### 6. Live Contracts ✅

**Files:** `src/contract_parser.py`, `src/contract_matcher.py`

**Capabilities:**
- Natural language contract parsing
- Automatic contract matching during mining
- AI-mediated negotiation
- Facilitation fee tracking

---

## Unimplemented Ideas

### Priority: HIGH 🔴

#### 1. Distributed P2P Network
**Target Repo:** NatLangChain
**Documentation:** README.md, future.md
**Gap:** No peer discovery, distributed consensus, or network security

#### 2. Real-Time Mediation Network
**Target Repo:** Mediator Node
**Documentation:** future.md, foundation.md
**Gap:** No decentralized mediator nodes, competitive mediation market

#### 3. Escrow Integration
**Target Repo:** Value Ledger
**Documentation:** CONTRACTS.md, future.md
**Gap:** No on-chain or referenced escrow, no automatic payouts

#### 4. Web UI / Interactive Sandbox
**Target Repo:** NatLangChain
**Documentation:** roadmap.md
**Gap:** No visual interface for non-technical users

#### 5. MP-03 Dispute Protocol
**Target Repo:** NatLangChain
**Documentation:** MP-03-spec.md
**Gap:** No dispute declaration, evidence freezing, escalation

### Priority: MEDIUM 🟡

#### 6. Multi-Chain Branching & Merging
**Target Repo:** NatLangChain
**Gap:** No fork/merge, no context separation

#### 7. Daily Work Output Automation
**Target Repo:** RRA-Module, Memory Vault, IntentLog
**Gap:** No Git integration, no auto-posting

#### 8. Multilingual Support
**Target Repo:** Common
**Gap:** English only, no parallel language entries

#### 9. Benchmark Suite
**Target Repo:** NatLangChain
**Gap:** No TPS metrics, no ambiguity resolution benchmarks

#### 10. Cosmos SDK Integration
**Target Repo:** NatLangChain
**Gap:** No IBC, no token, no Cosmos ecosystem access

#### 11. Database Backend
**Target Repo:** NatLangChain
**Gap:** JSON only, no scalable storage

#### 12. Agent-OS Full Integration
**Target Repo:** Agent OS
**Gap:** No standing intents, no agent bidding

#### 13. LNI Multi-Agent Testing
**Target Repo:** Agent OS
**Gap:** No empirical validation of LNI hypothesis

### Priority: LOW 🟢

#### 14. Prediction Markets
#### 15. Narrative Staking
#### 16. Zero-Knowledge Proofs
#### 17. Smart Contract Execution
#### 18. Insurance Premium Integration

---

## Cross-Repo Integration Specifications

### Agent OS ↔ NatLangChain Integration

**Purpose:** Enable Agent OS to post intents and receive alignments autonomously.

**API Contract:**
```python
# Agent OS → NatLangChain
POST /entry
{
    "content": "Agent posting standing intent for code review services",
    "author": "agent_os_instance_1",
    "intent": "Offer code review",
    "metadata": {
        "source": "agent_os",
        "learning_contract_ref": "LC-001",
        "standing_intent": true,
        "auto_accept_threshold": 85
    }
}

# NatLangChain → Agent OS (callback)
POST {agent_callback_url}/alignment
{
    "alignment_id": "ALIGN-123",
    "match_score": 92,
    "counterparty": "bob",
    "proposed_terms": {...}
}
```

**Implementation Tasks:**
- [ ] Agent authentication protocol
- [ ] Standing intent templates
- [ ] Callback webhook system
- [ ] Auto-accept/counter logic
- [ ] Learning Contract verification

---

### IntentLog ↔ NatLangChain Integration

**Purpose:** Capture reasoning ("why") for intents before they are posted.

**API Contract:**
```python
# IntentLog → NatLangChain
POST /entry
{
    "content": "I offer web development services at $100/hour",
    "author": "alice",
    "intent": "Offer services",
    "metadata": {
        "intentlog_ref": "INTENT-456",
        "reasoning_summary": "Need income, prefer remote work",
        "decision_path": ["Considered full-time", "Rejected due to...", "Freelance preferred"]
    }
}
```

**Implementation Tasks:**
- [ ] IntentLog reference field in entries
- [ ] Reasoning summary attachment
- [ ] Decision path preservation
- [ ] Bi-directional linking

---

### Memory Vault ↔ NatLangChain Integration (MP-02)

**Purpose:** Store raw work artifacts for Proof-of-Effort receipts.

**API Contract:**
```python
# Memory Vault stores artifacts
# NatLangChain references them in receipts

# Effort Receipt Entry
POST /entry
{
    "content": "Effort receipt for code module development",
    "author": "alice",
    "intent": "Record effort",
    "metadata": {
        "is_effort_receipt": true,
        "vault_refs": ["MV-001", "MV-002", "MV-003"],
        "time_bounds": {"start": "2025-12-18T09:00:00", "end": "2025-12-18T17:00:00"},
        "signal_hashes": ["SHA256...", "SHA256..."],
        "validation_metadata": {
            "coherence_score": 0.92,
            "progression_detected": true
        }
    }
}
```

**Implementation Tasks:**
- [ ] Vault reference protocol
- [ ] Signal hash verification
- [ ] Time-bound validation
- [ ] Append-only receipt chain

---

### Value Ledger ↔ NatLangChain Integration (MP-05)

**Purpose:** Receive settlement interfaces for accounting and capitalization.

**API Contract:**
```python
# NatLangChain → Value Ledger
POST /capitalization
{
    "settlement_id": "SETTLE-789",
    "agreement_ref": "AGREE-456",
    "receipts": ["R-101", "R-102", "R-103"],
    "value_description": {
        "amount": 25000,
        "currency": "USD",
        "facilitation_fee": 375
    },
    "parties": ["alice", "bob"],
    "payment_rails": {
        "type": "USDC",
        "escrow_address": "0xABC..."
    }
}
```

**Implementation Tasks:**
- [ ] Settlement ID generation
- [ ] Value description schema
- [ ] Multi-party support
- [ ] Payment rails abstraction

---

### Mediator Node ↔ NatLangChain Integration

**Purpose:** Third-party mediation with facilitation fee rewards.

**API Contract:**
```python
# Mediator Node subscribes to pending contracts
GET /contract/list?status=open

# Mediator Node proposes alignment
POST /contract/propose
{
    "offer_ref": "CONTRACT-001",
    "seek_ref": "CONTRACT-002",
    "proposal_content": "Match between alice and bob...",
    "match_score": 87,
    "terms": {
        "facilitation_fee": "2%",
        "mediator_id": "mediator_node_alpha"
    }
}

# Parties ratify → Mediator earns fee
POST /contract/payout
{
    "settlement_ref": "SETTLE-789",
    "mediator_id": "mediator_node_alpha",
    "fee_amount": 500,
    "wallet": "0xDEF..."
}
```

**Implementation Tasks:**
- [ ] Mediator node registration
- [ ] Subscription protocol (WebSocket or polling)
- [ ] Competitive proposal submission
- [ ] Fee distribution on closure

---

### Boundary Daemon Integration

**Purpose:** Enforce trust boundaries and prevent unauthorized data flow.

**Integration Points:**
- Validate that Agent OS actions respect Learning Contract bounds
- Block outbound data that violates privacy constraints
- Audit all cross-repo communications

**Implementation Tasks:**
- [ ] Trust boundary rules engine
- [ ] Data flow monitoring
- [ ] Violation alerting
- [ ] Audit log integration

---

### RRA-Module ↔ NatLangChain Integration

**Purpose:** Resurrect dormant repos as autonomous agents.

**Workflow:**
1. RRA-Module scans GitHub repo for activity
2. Generates daily/weekly output summary
3. Posts as OFFER contract on NatLangChain
4. Matches with SEEK contracts
5. Negotiates licensing terms
6. Records settlement

**API Contract:**
```python
# RRA-Module → NatLangChain
POST /contract/post
{
    "content": "[CONTRACT: OFFER] Async Fluid Dynamics library in Rust. 400 hours of optimization. Perpetual commercial license available.",
    "author": "rra_module_repo_xyz",
    "intent": "Offer library licensing",
    "contract_type": "offer",
    "terms": {
        "license_type": "perpetual_commercial",
        "price": "500",  # In configured staking currency (e.g., USDC, ETH)
        "facilitation": "1%"
    },
    "metadata": {
        "source": "rra_module",
        "repo_url": "github.com/user/repo",
        "last_commit": "2025-12-15",
        "total_commits": 847
    }
}
```

---

### Finite-Intent-Executor ↔ NatLangChain Integration

**Purpose:** Execute predefined posthumous or delayed intent.

**Compatibility Status:** ✅ VERIFIED (11 tests passing)
- See `tests/test_fie_compatibility.py` for full test suite

**Workflow:**
1. User posts delayed intent on NatLangChain
2. Trigger conditions specified (date, event, death certificate)
3. Finite-Intent-Executor monitors triggers
4. On trigger, executes recorded intent
5. Records execution as new entry
6. 20-year sunset transitions assets to public domain

**Supported Intent Types:**
- Posthumous intents (trigger: death verification)
- Time-delayed intents (trigger: datetime)
- Conditional intents (trigger: external events)
- Incapacity intents (trigger: incapacity declaration)

**API Contract:**
```python
# Delayed Intent Entry (FIE-Compatible)
POST /entry
{
    "content": "Upon my passing, transfer IP rights of all repositories to Foundation XYZ",
    "author": "alice",
    "intent": "Posthumous IP transfer",
    "metadata": {
        "is_delayed_intent": true,
        "delayed_intent_type": "posthumous",
        "delayed_intent_id": "DI-001",
        "trigger": {
            "type": "death",
            "verification_method": "death_certificate_oracle",
            "minimum_confirmations": 2
        },
        "executor": {
            "primary": "finite_intent_executor_mainnet"
        },
        "beneficiary": {
            "name": "Foundation XYZ",
            "identifier": "foundation_xyz"
        },
        "revocation": {
            "revocable": true,
            "revocation_method": "author_signature"
        }
    }
}
```

**Implementation Gaps (for enhanced integration):**
- [ ] Dedicated `/delayed-intent` query endpoint
- [ ] Active trigger monitoring integration
- [ ] Revocation chain tracking
- [ ] Oracle network callbacks

---

### Common Schema Definitions

**Purpose:** Shared data formats across all repositories.

**Schemas:**
```python
# Entry Schema (Common)
{
    "content": str,           # Natural language prose
    "author": str,            # Author identifier
    "intent": str,            # Brief purpose summary
    "timestamp": datetime,    # ISO 8601
    "metadata": {
        "validation_status": "valid" | "pending" | "invalid",
        "is_contract": bool,
        "contract_type": "offer" | "seek" | "proposal" | "response" | "closure",
        "is_effort_receipt": bool,
        "is_license": bool,
        "is_settlement": bool,
        "is_dispute": bool,
        "temporal_fixity_enabled": bool,
        "t0_snapshot": {...}
    }
}

# Receipt Schema (MP-02)
{
    "receipt_id": str,
    "time_bounds": {"start": datetime, "end": datetime},
    "signal_hashes": [str],
    "effort_summary": str,
    "validation_metadata": {
        "coherence_score": float,
        "progression_detected": bool,
        "validator_id": str,
        "model_version": str
    },
    "observer_id": str,
    "prior_receipts": [str]
}

# License Schema (MP-04)
{
    "license_id": str,
    "subject": str,           # What is licensed
    "purpose": str,           # Allowed use cases
    "limits": str,            # Prohibited actions
    "duration": str,          # Time-bounded or perpetual
    "transferability": str,   # Sublicensing rules
    "grantor": str,
    "grantee": str,
    "agreement_ref": str,
    "receipt_refs": [str]
}

# Settlement Schema (MP-05)
{
    "settlement_id": str,
    "agreement_refs": [str],
    "receipt_refs": [str],
    "value_description": {
        "amount": float,
        "currency": str,
        "formula": str        # Optional
    },
    "conditions": str,        # Vesting rules
    "parties": [str],
    "declarations": [str],    # Each party's declaration
    "capitalization_interface": {...}
}

# Dispute Schema (MP-03)
{
    "dispute_id": str,
    "claimant": str,
    "respondent": str,
    "contested_refs": [str],  # Receipts/agreements contested
    "description": str,
    "escalation_path": str,
    "evidence_frozen": bool,
    "status": "open" | "clarifying" | "escalated" | "resolved"
}
```

---

## Implementation Plans

### Plan 1: Distributed P2P Network 🔴
**Target:** NatLangChain

#### Phase 1A: Peer Discovery
- Design P2P protocol specification
- Implement peer discovery module (`src/p2p/discovery.py`)
- Add peer endpoints to API

**Deliverables:**
- Working peer discovery with 3+ nodes
- Automatic reconnection

#### Phase 1B: Distributed Consensus
- Implement Proof-of-Alignment consensus
- Block propagation protocol
- Distributed mining

**Deliverables:**
- Consensus across 5+ nodes
- Byzantine fault tolerance (67% honest nodes)

#### Phase 1C: Network Security
- Cryptographic peer authentication
- DDoS protection
- Sybil attack resistance

---

### Plan 2: Real-Time Mediation Network 🔴
**Target:** Mediator Node

#### Phase 2A: Mediator Registration
- Mediator node identity system
- On-chain registration
- Stake requirements

#### Phase 2B: Competitive Matching
- Multiple mediators propose simultaneously
- Multi-model voting on best proposal
- Fee distribution

#### Phase 2C: Reputation & Slashing
- Track mediator success rate
- Slash stake for bad proposals
- Reputation-weighted selection

---

### Plan 3: Escrow Integration 🔴
**Target:** Value Ledger

#### Phase 3A: Escrow Reference System
- Add escrow fields to contract metadata
- Support USDC, BTC, ETH

#### Phase 3B: Payment Verification
- Oracle integration for on-chain verification
- Verify escrow funding and payouts

#### Phase 3C: Automatic Payout
- Trigger payouts on contract closure
- Multi-sig releases
- Dispute resolution holds

---

### Plan 4: Web UI 🔴
**Target:** NatLangChain

#### Phase 4A: Basic UI
- React/Svelte frontend
- Chain explorer, narrative view, search, contracts

#### Phase 4B: Visualization
- Narrative graph (D3.js)
- Contract matching visualization

#### Phase 4C: Interactive Sandbox
- Try posting entries
- Real-time validation viewer
- Dialectic debate visualization

---

### Plan 5: MP-03 Dispute Protocol 🔴
**Target:** NatLangChain

#### Phase 5A: Dispute Initiation
- Dispute Declaration entry type
- Reference to contested entries
- Escalation path specification

#### Phase 5B: Evidence Freezing
- Mark referenced entries as UNDER DISPUTE
- Prevent mutation/deletion
- Append-only new evidence

#### Phase 5C: Escalation & Resolution
- Escalation Declaration mechanism
- Dispute Package export
- Post-resolution recording

---

### Plan 6: Multi-Chain Branching 🟡
**Target:** NatLangChain

- Add `parent_chain_id` to blocks
- Fork command creates new chain
- LLM-mediated merge conflict resolution
- Private branch encryption

---

### Plan 7: Daily Work Automation 🟡
**Target:** RRA-Module, Memory Vault, IntentLog

- Git hook scripts
- Commit summarization (LLM)
- Auto-contract generation
- Auction/banking logic

---

### Plan 8: Multilingual Support 🟡
**Target:** Common

- Parallel language entries
- Explicit precedence declarations
- Cross-language validation
- Clarification protocol for conflicts

---

### Plan 9: Database Backend 🟡
**Target:** NatLangChain

- PostgreSQL schema design
- SQLAlchemy ORM models
- Migration from JSON
- Index optimization

---

### Plan 10: LNI Multi-Agent Testing 🟡
**Target:** Agent OS

- Implement SMAS baseline
- Implement LNIS treatment
- Run benchmark tasks
- Measure semantic drift, cooperation, interpretability

---

### Plan 11: Anti-Harassment Economic Layer 🔴
**Target:** NatLangChain

#### Phase 11A: Dual Initiation Paths
- Implement Breach/Drift Dispute path with symmetric staking
- Implement Voluntary Request path with burn fees
- Add fallback resolution for unmatched stakes

**Deliverables:**
- Stake escrow contract
- Voluntary request burn mechanism

#### Phase 11B: Griefing Limits
- Counter-proposal cap (default: 3)
- Exponential fee escalation (base_fee × 2ⁿ)
- Immediate fee burning

#### Phase 11C: Harassment Scoring
- On-chain harassment score derivation
- Escalating initiation costs for flagged actors
- Cooldown windows per contract

---

### Plan 12: Treasury System 🔴
**Target:** NatLangChain

#### Phase 12A: Treasury Contract
- Deploy NatLangChainTreasury contract
- Implement deposit mechanisms (burns, counter-fees, escalated stakes)
- Add balance queries and event emission

#### Phase 12B: Subsidy System
- Implement `requestSubsidy` function
- Add eligibility checks (target-only, opt-in, reputation)
- Per-dispute and per-participant caps

#### Phase 12C: Anti-Sybil Protections
- Single subsidy per dispute enforcement
- Rolling window cap per participant
- Harassment score integration

**Deliverables:**
- Fully autonomous treasury with no discretionary control
- Closed-loop economic system

---

### Plan 13: FIDO2/YubiKey Integration 🔴
**Target:** ILRM, NatLangChain

#### Phase 13A: ILRM Integration (High Priority)
- Add FIDO2 signature verification to `acceptProposal` and `submitLLMProposal`
- Implement YubiKey public key registration on-chain
- WebAuthn challenge-response flow

#### Phase 13B: Negotiation Module Integration
- Frontend YubiKey authentication
- On-chain FIDO2 signature verification for commitment transactions
- Passwordless login flow

#### Phase 13C: RRA Module Integration
- FIDO2 auth for agent mobile/off-chain components
- Agent delegation signature verification

**Deliverables:**
- Phishing-resistant authentication across all modules
- Hardware-backed contract signing

---

### Plan 14: ZK Privacy Infrastructure 🔴
**Target:** NatLangChain

#### Phase 14A: Dispute Membership Circuit
- Implement Circom circuit (`prove_identity.circom`)
- Deploy Poseidon hasher with verifier contract
- Integrate `submitIdentityProof` into ILRM

#### Phase 14B: Viewing Key Infrastructure
- Pedersen commitment integration
- Off-chain encrypted storage (IPFS/Arweave)
- ECIES viewing key generation per dispute
- Shamir's Secret Sharing (m-of-n) for key escrow

#### Phase 14C: Inference Attack Mitigations
- Batching queue contract
- Dummy transaction automation via Chainlink
- Mixnet integration exploration

#### Phase 14D: Threshold Decryption
- BLS/FROST threshold signature implementation
- Compliance Council governance
- Legal warrant voting mechanism

**Deliverables:**
- ZK proof verification on-chain
- Selective de-anonymization for legal compliance
- No single point of failure in key management

---

### Plan 15: Automated Negotiation Engine 🔴
**Target:** NatLangChain

- Core natural-language contract negotiation engine
- Proactive alignment layer for intent matching
- LLM-powered clause generation and counter-offer drafting
- Integration with existing contract_matcher.py

**Deliverables:**
- Fully automated negotiation from intent to agreement proposal

---

### Plan 16: Market-Aware Pricing 🟡
**Target:** NatLangChain

- Oracle integration for real-time market data
- Dynamic offer/counteroffer generation based on market conditions
- Price suggestion during negotiation prompts
- Historical pricing analysis

---

### Plan 17: Mobile Deployment 🟡
**Target:** All Modules

- Edge AI optimization for on-device inference
- Mobile wallet integration (WalletConnect, native)
- Portable system architecture (NatLangChain, ILRM, RRA)
- Offline-first capability with sync

**Deliverables:**
- Full protocol functionality on mobile devices
- Hardware wallet support via mobile

---

## Technical Roadmap

### Phase 1: Foundation (Complete ✅)
- ✅ Core blockchain
- ✅ Validation systems
- ✅ REST API
- ✅ Live contracts
- ✅ Advanced features

### Phase 2: Security & Economic Safety (Q1 2026)
**Priority:** HIGH 🔴
- Anti-Harassment Economic Layer
- Treasury System
- FIDO2/YubiKey Integration

**Deliverables:**
- Harassment-resistant initiation paths
- Autonomous treasury for defensive subsidies
- Hardware-backed authentication

### Phase 3: Privacy Infrastructure (Q1-Q2 2026)
**Priority:** HIGH 🔴
- ZK Dispute Membership Circuit
- Viewing Key Infrastructure
- Threshold Decryption for Compliance

**Deliverables:**
- On-chain ZK proof verification
- Selective de-anonymization
- Decentralized key management

### Phase 4: Decentralization (Q2-Q3 2026)
**Priority:** HIGH 🔴
- Distributed P2P network
- Real-time mediation network
- Escrow integration

**Deliverables:**
- Multi-node testnet (10 nodes)
- Competitive mediation market
- End-to-end payment settlement

### Phase 5: User Experience (Q3-Q4 2026)
**Priority:** HIGH 🔴
- Web UI
- Database backend
- MP-03 Dispute Protocol
- Automated Negotiation Engine

**Deliverables:**
- Public web interface
- Scalable storage
- Full dispute handling
- AI-driven negotiation from intent to agreement

### Phase 6: Automation & Intelligence (Q4 2026 - Q1 2027)
**Priority:** MEDIUM 🟡
- Daily work automation
- Agent-OS integration
- Multi-chain branching
- LNI testing
- Market-Aware Pricing

**Deliverables:**
- Automatic contract generation from Git
- Autonomous agent participation
- Privacy through branching
- Oracle-integrated dynamic pricing

### Phase 7: Global & Enterprise (Q1-Q2 2027)
**Priority:** MEDIUM 🟡
- Multilingual support
- Cosmos SDK integration
- Benchmark suite
- Mobile Deployment

**Deliverables:**
- Multi-language contracts
- IBC interoperability
- Published performance metrics
- Full protocol on mobile devices

### Phase 8: Advanced Features (2027+)
**Priority:** LOW 🟢
- Prediction markets
- Narrative staking
- Smart contract execution
- Inference Attack Mitigations

---

## Conclusion

NatLangChain has achieved **solid implementation** of its core vision:
- ✅ **Natural language as substrate** - Working
- ✅ **Proof of Understanding** - Working
- ✅ **Live contracts with AI mediation** - Working
- ✅ **Temporal fixity for legal defense** - Working
- ✅ **Semantic search and drift detection** - Working

**The gap** is primarily in **security, privacy, decentralization, and ecosystem integration**:
- ❌ Single-node (needs P2P)
- ❌ Manual usage (needs automation via RRA-Module)
- ❌ Developer-only (needs Web UI)
- ❌ Prototype storage (needs database)
- ❌ Incomplete MP suite (MP-03, MP-04, MP-05)
- ❌ Limited cross-repo integration
- ❌ No anti-harassment economic layer
- ❌ No treasury system for defensive subsidies
- ❌ No hardware-backed authentication (FIDO2/YubiKey)
- ❌ No ZK privacy infrastructure

**Next critical steps:**
1. **Anti-Harassment & Treasury** - Economic safety layer for harassment resistance
2. **FIDO2/YubiKey Integration** - Hardware-backed security for identity-sensitive operations
3. **ZK Privacy Infrastructure** - Dispute membership proofs and viewing keys
4. **P2P Network** - Move from proof-of-concept to distributed system
5. **Web UI** - Enable non-technical user adoption
6. **Automated Negotiation** - AI-driven negotiation from intent to agreement
7. **Mobile Deployment** - Full protocol functionality on edge devices
8. **Cross-Repo Integration** - Connect all 12 ecosystem repos

**The foundation is solid.** The architecture is sound. The innovation is real. Now it's time to scale.

---

**Document Version:** 3.7
**Last Updated:** December 24, 2025
**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
