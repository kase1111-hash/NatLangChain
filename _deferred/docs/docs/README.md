# NatLangChain Documentation

This directory contains governance specifications, protocol documentation, and guides for the NatLangChain project.

## Quick Navigation

### Getting Started
- [User Manual](user-manual.md) - Guide for writing effective intent posts
- [API Documentation](../API.md) - Complete REST API reference
- [Installation Guide](../INSTALLATION.md) - Setup and deployment instructions

### Core Documentation (Root Level)
- [README](../README.md) - Project overview and quick start
- [Architecture](../ARCHITECTURE.md) - System design and components
- [Specification](../SPEC.md) - Technical specification and protocol details
- [Design Philosophy](DESIGN-PHILOSOPHY.md) - Why non-determinism is a feature, not a bug
- [FAQ](../FAQ.md) - Frequently asked questions

### NCIP Governance Framework

The NatLangChain Improvement Proposal (NCIP) system defines project governance:

| NCIP | Title |
|------|-------|
| [NCIP-000](NCIP-000.md) | Terminology & Semantics Governance |
| [NCIP-000+](NCIP-000+.md) | Consolidated NCIP Index |
| [NCIP-001](NCIP-001.md) | Canonical Term Registry |
| [NCIP-002](NCIP-002.md) | Semantic Drift Thresholds & Validator Responses |
| [NCIP-003](NCIP-003.md) | Multilingual Semantic Alignment & Drift |
| [NCIP-004](NCIP-004.md) | Proof of Understanding (PoU) Generation & Verification |
| [NCIP-005](NCIP-005.md) | Dispute Escalation, Cooling Periods & Semantic Locking |
| [NCIP-006](NCIP-006.md) | Jurisdictional Interpretation & Legal Bridging |
| [NCIP-007](NCIP-007.md) | Validator Trust Scoring & Reliability Weighting |
| [NCIP-008](NCIP-008.md) | Semantic Appeals, Precedent & Case Law Encoding |
| [NCIP-009](NCIP-009.md) | Regulatory Interface Modules & Compliance Proofs |
| [NCIP-010](NCIP-010.md) | Mediator Reputation, Slashing & Market Dynamics |
| [NCIP-011](NCIP-011.md) | Validator–Mediator Interaction & Weight Coupling |
| [NCIP-012](NCIP-012.md) | Human Ratification UX & Cognitive Load Limits |
| [NCIP-013](NCIP-013.md) | Emergency Overrides, Force Majeure & Semantic Fallbacks |
| [NCIP-014](NCIP-014.md) | Protocol Amendments & Constitutional Change |
| [NCIP-015](NCIP-015.md) | Sunset Clauses, Archival Finality & Historical Semantics |

See also: [NCIP-016 Draft](../NCIP-016-DRAFT.md) (provisional)

### Mediator Protocol Specifications

| Protocol | Description |
|----------|-------------|
| [MP-02](MP-02-spec.md) | Proof-of-Effort Receipts |
| [MP-03](MP-03-spec.md) | Dispute & Escalation |
| [MP-04](MP-04-spec.md) | Licensing & Delegation |
| [MP-05](MP-05-spec.md) | Settlement & Capitalization |

### Operations & Security
- [Security Documentation](../SECURITY.md) - Consolidated security audits and configuration
- [Validator Reference Guide](Validator-Reference-Guide.md) - Validator operations
- [Escalation Protocol](Escalation-Protocol.md) - Escalation procedures
- [Observance Burn](Observance-Burn.md) - Token burn mechanism
- [Threat Model](Threat-Model.md) - Protocol-level threat analysis

### Legal & Community
- [Terms of Service](terms-of-service.md) - Platform terms
- [License](../LICENSE.md) - CC BY-SA 4.0
- [Code of Conduct](../CODE_OF_CONDUCT.md) - Community standards
- [Contributing](../CONTRIBUTING.md) - Contribution guidelines
- [Founding Contributor Pledge](../Founding-Contributor-Pledge.md) - Contributor commitment

## Related Documentation

- [Integration Specs](../specs/README.md) - Multi-repository integration specifications
- [Frontend](../frontend/README.md) - Svelte/Tauri desktop application
- [Kubernetes Deployment](../k8s/README.md) - Production K8s manifests
- [Database Migrations](../migrations/README.md) - PostgreSQL migrations

## Contributing to Documentation

When adding new documentation:
1. Use lowercase file names with hyphens (e.g., `my-new-doc.md`)
2. Follow the existing structure and formatting
3. Update this README with a link to your new document
4. Ensure all internal links are relative and correct
