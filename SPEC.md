# NatLangChain Technical Specification
## Updated: December 19, 2025

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Ecosystem Architecture](#ecosystem-architecture)
3. [Core Architecture](#core-architecture)
4. [Mediator Protocol Suite (MP-01 to MP-05)](#mediator-protocol-suite)
5. [Implementation Status Matrix](#implementation-status-matrix)
6. [Implemented Features](#implemented-features)
7. [Unimplemented Ideas](#unimplemented-ideas)
8. [Cross-Repo Integration Specifications](#cross-repo-integration-specifications)
9. [Implementation Plans](#implementation-plans)
10. [Technical Roadmap](#technical-roadmap)

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
| **Daily Work Output Automation** | future.md | MEDIUM 🟡 | Medium | RRA-Module |
| **Chain Subscription & Sync** | future.md | MEDIUM 🟡 | High | NatLangChain |
| **Cosmos SDK Integration** | cosmos.md | MEDIUM 🟡 | Very High | NatLangChain |
| **Multilingual Support** | multilingual.md | MEDIUM 🟡 | High | Common |
| **Benchmark Suite** | roadmap.md | MEDIUM 🟡 | Medium | NatLangChain |
| **Database Backend** | API.md | MEDIUM 🟡 | Low | NatLangChain |
| **Async Validation Pipeline** | API.md | MEDIUM 🟡 | Medium | NatLangChain |
| **LNI Multi-Agent Testing** | lni-testable-theory.md | MEDIUM 🟡 | High | Agent OS |
| **Prediction Markets** | COMPLIANCE.md | LOW 🟢 | High | NatLangChain |
| **Narrative Staking** | COMPLIANCE.md | LOW 🟢 | High | NatLangChain |
| **Insurance Premium Integration** | COMPLIANCE.md | LOW 🟢 | Medium | Value Ledger |
| **ZK Proofs for Privacy** | README.md | LOW 🟢 | Very High | NatLangChain |
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
        "price": "500 NLC",
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

## Technical Roadmap

### Phase 1: Foundation (Complete ✅)
- ✅ Core blockchain
- ✅ Validation systems
- ✅ REST API
- ✅ Live contracts
- ✅ Advanced features

### Phase 2: Decentralization (Q1-Q2 2026)
**Priority:** HIGH 🔴
- Distributed P2P network
- Real-time mediation network
- Escrow integration

**Deliverables:**
- Multi-node testnet (10 nodes)
- Competitive mediation market
- End-to-end payment settlement

### Phase 3: User Experience (Q2-Q3 2026)
**Priority:** HIGH 🔴
- Web UI
- Database backend
- MP-03 Dispute Protocol

**Deliverables:**
- Public web interface
- Scalable storage
- Full dispute handling

### Phase 4: Automation & Intelligence (Q3-Q4 2026)
**Priority:** MEDIUM 🟡
- Daily work automation
- Agent-OS integration
- Multi-chain branching
- LNI testing

**Deliverables:**
- Automatic contract generation from Git
- Autonomous agent participation
- Privacy through branching

### Phase 5: Global & Enterprise (Q4 2026 - Q1 2027)
**Priority:** MEDIUM 🟡
- Multilingual support
- Cosmos SDK integration
- Benchmark suite

**Deliverables:**
- Multi-language contracts
- IBC interoperability
- Published performance metrics

### Phase 6: Advanced Features (2027+)
**Priority:** LOW 🟢
- Zero-knowledge proofs
- Prediction markets
- Narrative staking
- Smart contract execution

---

## Conclusion

NatLangChain has achieved **solid implementation** of its core vision:
- ✅ **Natural language as substrate** - Working
- ✅ **Proof of Understanding** - Working
- ✅ **Live contracts with AI mediation** - Working
- ✅ **Temporal fixity for legal defense** - Working
- ✅ **Semantic search and drift detection** - Working

**The gap** is primarily in **decentralization, scale, and ecosystem integration**:
- ❌ Single-node (needs P2P)
- ❌ Manual usage (needs automation via RRA-Module)
- ❌ Developer-only (needs Web UI)
- ❌ Prototype storage (needs database)
- ❌ Incomplete MP suite (MP-03, MP-04, MP-05)
- ❌ Limited cross-repo integration

**Next critical steps:**
1. **P2P Network** - Move from proof-of-concept to distributed system
2. **Web UI** - Enable non-technical user adoption
3. **Escrow** - Enable real economic transactions
4. **Mediation Network** - Realize the "mediation mining" vision
5. **Cross-Repo Integration** - Connect all 12 ecosystem repos

**The foundation is solid.** The architecture is sound. The innovation is real. Now it's time to scale.

---

**Document Version:** 2.0
**Last Updated:** December 19, 2025
**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
