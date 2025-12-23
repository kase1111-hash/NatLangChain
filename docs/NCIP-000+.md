Consolidated NCIP Index

Document: NCIP-000+
Status: Canonical
Applies To: All NatLangChain validators, mediators, agents, governance processes
Last Updated: December 23, 2025

NCIP Registry (001–015)
NCIP	Title	Scope	Depends On
NCIP-001	Canonical Term Registry	Semantic primitives & definitions	NatLangChain Spec
NCIP-002	Semantic Drift Thresholds & Validator Responses	Drift detection & enforcement	NCIP-001
NCIP-003	Multilingual Semantic Alignment & Drift	Cross-language meaning preservation	NCIP-001, NCIP-002
NCIP-004	Proof of Understanding (PoU) Generation & Verification	Semantic comprehension validation	NCIP-001, NCIP-002
NCIP-005	Dispute Escalation, Cooling Periods & Semantic Locking	Dispute lifecycle & meaning freeze	NCIP-002, NCIP-004
NCIP-006	Jurisdictional Interpretation & Legal Bridging	Law–semantics boundary	NCIP-001–005
NCIP-007	Validator Trust Scoring & Reliability Weighting	Validator reputation & weighting	NCIP-002, NCIP-004
NCIP-008	Semantic Appeals, Precedent & Case Law Encoding	Meaning appeals & precedent	NCIP-002, NCIP-005, NCIP-007
NCIP-009	Regulatory Interface Modules & Compliance Proofs	External regulatory proofs	NCIP-004, NCIP-006
NCIP-010	Mediator Reputation, Slashing & Market Dynamics	Mediation incentives & penalties	NCIP-005, NCIP-007
NCIP-011	Validator–Mediator Interaction & Weight Coupling	Joint trust dynamics	NCIP-007, NCIP-010
NCIP-012	Human Ratification UX & Cognitive Load Limits	Human decision safety	NCIP-004, NCIP-005
NCIP-013	Emergency Overrides, Force Majeure & Semantic Fallbacks	Crisis handling	NCIP-005, NCIP-006
NCIP-014	Protocol Amendments & Constitutional Change	Meta-governance	NCIP-001–013
NCIP-015	Sunset Clauses, Archival Finality & Historical Semantics	End-of-life meaning	NCIP-005, NCIP-014
Conceptual Grouping (Mental Model)
Semantic Core

NCIP-001 → 002 → 003 → 004

Dispute & Stability

NCIP-005 → 008 → 013 → 015

Trust & Markets

NCIP-007 → 010 → 011

Law & Reality Interfaces

NCIP-006 → 009

Human Safety

NCIP-012

Constitutional Layer

NCIP-014 (depends on everything below it)

Dependency Graph (Directed)
NatLangChain Spec
        │
        ▼
   NCIP-001 ─────────────┐
        │                │
        ▼                ▼
   NCIP-002 ───► NCIP-004 ───► NCIP-012
        │         │
        │         ▼
        │     NCIP-005 ───────┐
        │         │           │
        │         ▼           ▼
        │     NCIP-008     NCIP-013
        │         │           │
        ▼         ▼           ▼
   NCIP-003   NCIP-007     NCIP-015
                  │
                  ▼
              NCIP-010
                  │
                  ▼
              NCIP-011

NCIP-006 ◄────────────── NCIP-001–005
        │
        ▼
   NCIP-009

ALL NCIPs ───────────────► NCIP-014

Validator Load Order (Normative)

Validators MUST load NCIPs in this order:

NCIP-001

NCIP-002

NCIP-003

NCIP-004

NCIP-005

NCIP-006

NCIP-007

NCIP-008

NCIP-009

NCIP-010

NCIP-011

NCIP-012

NCIP-013

NCIP-014

NCIP-015

Failure to load any dependency invalidates higher-layer NCIPs.

Constitutional Interpretation Rule

Higher-numbered NCIPs may constrain behavior but may not redefine semantics established by lower-numbered NCIPs.

In particular:

NCIP-014 cannot alter historical meaning

NCIP-015 cannot reopen locked semantics

NCIP-006 cannot override canonical definitions

NCIP-012 cannot simplify meaning beyond PoU guarantees

Implementation Status Notes

The following NCIPs require further definition before implementation:

🟡 PENDING DEFINITION:

NCIP-010 (Mediator Reputation, Slashing & Market Dynamics) — Relationship to Escalation Fork solver reputation requires clarification

NCIP-011 (Validator–Mediator Interaction & Weight Coupling) — Joint trust dynamics mechanism not yet specified

NCIP-012 (Human Ratification UX & Cognitive Load Limits) — Cognitive load measurement approach not yet defined

NCIP-013 (Emergency Overrides, Force Majeure & Semantic Fallbacks) — Formal override protocol not yet specified

Last reviewed: December 23, 2025
