NatLangChain Threat Model
Spanning MP-01 → MP-05 (Standalone)

Status: Draft (Normative)

1. Purpose

This threat model identifies, categorizes, and constrains risks across the full NatLangChain protocol suite (MP-01 through MP-05).

The goal is not to eliminate risk, but to:

Make failure modes explicit

Prevent silent corruption of intent

Preserve human authority under adversarial conditions

Ensure disputes remain reconstructable

2. System Boundary

NatLangChain governs:

Natural-language intent

Human ratification

Proof-of-effort receipts

Licensing and delegation

Settlement and capitalization interfaces

NatLangChain does not govern:

Model training data integrity

External payment or legal enforcement

Identity verification beyond explicit declarations

Threats are evaluated only within the protocol boundary.

3. Threat Taxonomy

Threats are grouped into six classes:

Intent Corruption

Authority Drift

Evidence Manipulation

Automation Overreach

Economic Exploitation

Governance Capture

Each class lists threats, affected MPs, and mitigations.

4. Intent Corruption
Threats

Ambiguous or strategic phrasing to create future leverage

Post-hoc reinterpretation of agreements

Model-induced paraphrasing that alters meaning

Affected Protocols

MP-01, MP-03, MP-05

Mitigations

Explicit human ratification in natural language (MP-01)

Provenance tagging of model-generated text

Immutable recording of original intents

No implied or inferred consent

Residual Risk: Humans may still misunderstand each other. This is preserved, not hidden.

5. Authority Drift
Threats

Agents exceeding delegated scope

Silent redelegation or sublicensing

Long-lived delegations becoming de facto ownership

Affected Protocols

MP-04, MP-01

Mitigations

Explicit scope, duration, and limits in all grants (MP-04)

Invalidity of actions outside declared authority

Human-authored revocation paths

Residual Risk: Humans may grant overly broad authority.

6. Evidence Manipulation
Threats

Fabricated or inflated proof-of-effort

Selective omission of failed work

Tampering with receipts after disputes arise

Affected Protocols

MP-02, MP-03, MP-05

Mitigations

Time-stamped, append-only receipts (MP-02)

Evidence freezing upon dispute initiation (MP-03)

Settlement preconditions requiring valid receipts (MP-05)

Residual Risk: Garbage-in remains possible; garbage-out is traceable.

7. Automation Overreach
Threats

LLMs inferring consent or settlement

Automated execution without human sign-off

Optimization toward efficiency over legitimacy

Affected Protocols

MP-01 through MP-05

Mitigations

LLMs may propose but never decide (global rule)

Explicit ratification and settlement declarations

No silent consent or timeout-based finality

Residual Risk: Humans may over-trust machine suggestions.

8. Economic Exploitation
Threats

Premature capitalization of disputed work

Value extraction without valid licensing

Financialization of ambiguous agreements

Affected Protocols

MP-04, MP-05, MP-03

Mitigations

Capitalization requires explicit settlement (MP-05)

Licensing preconditions for use (MP-04)

Dispute blocking of settlement finality (MP-03)

Residual Risk: External systems may misuse interfaces.

9. Governance Capture
Threats

Centralized control over mediators

Reputation systems becoming coercive

Soft pressure to ratify to “keep things moving”

Affected Protocols

MP-01, MP-03

Mitigations

Non-adjudicative mediators

Voluntary participation in clarification

Explicit exit and escalation rights

Residual Risk: Social pressure cannot be fully eliminated.

10. Cross-Protocol Failure Scenarios
Scenario A — Settlement Without Authority

Blocked by:

MP-04 invalid grant

MP-05 settlement preconditions

Scenario B — AI-Declared Agreement

Blocked by:

MP-01 ratification requirement

Scenario C — Retroactive Dispute Erasure

Blocked by:

MP-03 non-retroactivity

11. Threats Explicitly Out of Scope

Nation-state coercion

Compromised identity infrastructure

Malicious hardware or OS-level attacks

Fraud external to recorded artifacts

These must be handled externally.

12. Canonical Safety Rule

If a system action cannot be reconstructed from explicit human-authored records, it must be treated as untrusted.

End of Threat Model
