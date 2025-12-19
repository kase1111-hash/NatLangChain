# NatLangChain Cross-Repository Integration Specifications

This directory contains detailed integration specifications for all 11 repositories in the NatLangChain ecosystem.

## Overview

NatLangChain is the spine of a 12-repository ecosystem. These specifications define how each component integrates with the core NatLangChain protocol.

## Repository Map

| Repository | Integration Spec | Purpose |
|------------|-----------------|---------|
| **Agent OS** | [AGENT-OS-INTEGRATION.md](./AGENT-OS-INTEGRATION.md) | Locally-controlled AI infrastructure |
| **Synth-Mind** | [SYNTH-MIND-INTEGRATION.md](./SYNTH-MIND-INTEGRATION.md) | Cognitive drift and hallucination regulation |
| **IntentLog** | [INTENTLOG-INTEGRATION.md](./INTENTLOG-INTEGRATION.md) | Version control for human reasoning |
| **Value Ledger** | [VALUE-LEDGER-INTEGRATION.md](./VALUE-LEDGER-INTEGRATION.md) | Accounting and capitalization layer |
| **Learning Contracts** | [LEARNING-CONTRACTS-INTEGRATION.md](./LEARNING-CONTRACTS-INTEGRATION.md) | AI learning governance |
| **Memory Vault** | [MEMORY-VAULT-INTEGRATION.md](./MEMORY-VAULT-INTEGRATION.md) | Secure work artifact storage |
| **Boundary Daemon** | [BOUNDARY-DAEMON-INTEGRATION.md](./BOUNDARY-DAEMON-INTEGRATION.md) | Trust boundary enforcement |
| **Finite-Intent-Executor** | [FINITE-INTENT-EXECUTOR-INTEGRATION.md](./FINITE-INTENT-EXECUTOR-INTEGRATION.md) | Posthumous/delayed intent execution |
| **RRA-Module** | [RRA-MODULE-INTEGRATION.md](./RRA-MODULE-INTEGRATION.md) | Dormant repository resurrection |
| **Mediator Node** | [MEDIATOR-NODE-INTEGRATION.md](./MEDIATOR-NODE-INTEGRATION.md) | Third-party contract mediation |
| **Common** | [COMMON-INTEGRATION.md](./COMMON-INTEGRATION.md) | Shared schemas and primitives |

## Architecture Diagram

```
                    ┌────────────────────────────────────────────┐
                    │               USER LAYER                    │
                    │  (Humans post intents, ratify agreements)   │
                    └─────────────────────┬──────────────────────┘
                                          │
┌─────────────────────────────────────────┼─────────────────────────────────────────┐
│                           LOCAL SOVEREIGNTY LAYER                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────┐   │
│  │  Agent OS   │  │ Synth-Mind   │  │ Learning        │  │ Boundary Daemon    │   │
│  │             │  │              │  │ Contracts       │  │                    │   │
│  └──────┬──────┘  └──────┬───────┘  └───────┬─────────┘  └─────────┬──────────┘   │
└─────────┼────────────────┼──────────────────┼──────────────────────┼──────────────┘
          │                │                  │                      │
┌─────────┼────────────────┼──────────────────┼──────────────────────┼──────────────┐
│         │          INTENT & EFFORT LAYER    │                      │              │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌───────▼────────┐             │              │
│  │ IntentLog   │  │ Memory Vault │  │ Value Ledger   │             │              │
│  │ (Why Track) │  │ (Work Store) │  │ (Meta-Value)   │             │              │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘             │              │
└─────────┼────────────────┼──────────────────┼──────────────────────┼──────────────┘
          │                │                  │                      │
┌─────────▼────────────────▼──────────────────▼──────────────────────▼──────────────┐
│                              NATLANGCHAIN CORE                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐ │
│  │                         NatLangChain Blockchain                               │ │
│  │  • MP-01: Negotiation & Ratification                                          │ │
│  │  • MP-02: Proof-of-Effort Receipts                                            │ │
│  │  • MP-03: Dispute & Escalation                                                │ │
│  │  • MP-04: Licensing & Delegation                                              │ │
│  │  • MP-05: Settlement & Capitalization                                         │ │
│  └──────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────┬───────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼───────────────────────────────────────────┐
│                              MEDIATION LAYER                                       │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────────────┐ │
│  │   Mediator Node    │  │    RRA-Module      │  │  Finite-Intent-Executor      │ │
│  │  (Third-party      │  │  (Repo Resurrection│  │  (Posthumous intent          │ │
│  │   mediation)       │  │   as agents)       │  │   execution)                 │ │
│  └────────────────────┘  └────────────────────┘  └──────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼───────────────────────────────────────────┐
│                              COMMON LAYER                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐ │
│  │  Shared schemas • Cryptographic primitives • Receipt formats • Provenance    │ │
│  └──────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## How to Use These Specs

### For Implementers

1. **Read the main SPEC.md** - Understand the overall architecture
2. **Read the relevant integration spec** - Get detailed API contracts
3. **Implement the API endpoints** - Follow the schemas exactly
4. **Test against the interfaces** - Ensure compatibility

### For Repo Maintainers

1. **Copy your integration spec** to your repo
2. **Implement the NatLangChain client** as specified
3. **Follow the Common schemas** for data structures
4. **Submit PRs** when implementation is complete

## Specification Status

| Spec | Status | Priority |
|------|--------|----------|
| Agent OS | Draft | HIGH |
| Synth-Mind | Draft | HIGH |
| Mediator Node | Draft | HIGH |
| Value Ledger | Draft | HIGH |
| Memory Vault | Draft | MEDIUM |
| IntentLog | Draft | MEDIUM |
| RRA-Module | Draft | MEDIUM |
| Learning Contracts | Draft | MEDIUM |
| Boundary Daemon | Draft | MEDIUM |
| Finite-Intent-Executor | Draft | LOW |
| Common | Draft | HIGH |

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-19 | Initial specifications for all 11 repos |

---

**Maintained By:** kase1111-hash
**License:** CC BY-SA 4.0
