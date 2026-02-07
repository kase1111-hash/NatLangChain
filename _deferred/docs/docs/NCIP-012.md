NCIP-012: Human Ratification UX & Cognitive Load Limits

Status: Canonical
Type: Human Factors / Governance
Version: 1.0
Created: December 22, 2025
Applies To:

Ratification flows (MP-01, MP-04, MP-05)

Frontend UX (Web, CLI, Agent-assisted)

Validators

Mediator proposals

Agent OS interfaces

Depends On:

NatLangChain Technical Specification v3.0

NCIP-004: Proof of Understanding (PoU)

NCIP-005: Dispute Escalation & Semantic Locking

NCIP-007: Validator Trust Scoring

NCIP-010: Mediator Reputation & Slashing

NCIP-011: Validator–Mediator Weight Coupling

1. Purpose

This NCIP defines mandatory UX constraints and cognitive load limits for any action that requires human ratification, ensuring that:

Consent is informed, deliberate, and reversible where appropriate

AI speed does not overwhelm human judgment

Ratification remains a human act, not a rubber stamp

2. Core Principle (Normative)

If a human cannot reasonably understand the decision surface, ratification is invalid.

The protocol MUST slow down, compress, or block ratification rather than risk false consent.

3. What Requires Human Ratification

Human ratification is REQUIRED for:

Action	Protocol
Agreement finalization	MP-01
License grants & delegation	MP-04
Settlement & capitalization	MP-05
Dispute escalation	MP-03
Semantic overrides / amendments	All
Posthumous or delayed intents	FIE

No exception is permitted.

4. Cognitive Load Budget (CLB)
4.1 Definition

Each ratification event has a Cognitive Load Budget (CLB) measured in semantic units, not pages or words.

A semantic unit ≈ one independently meaningful decision concept.

4.2 Hard Limits (Normative)
Context	Max Semantic Units
Simple agreement	7
Financial settlement	9
Licensing / delegation	9
Dispute escalation	5
Emergency / time-bound	3

If exceeded:

Ratification UI MUST block

System MUST request segmentation

5. Mandatory Information Hierarchy

Ratification interfaces MUST present information in this order:

Intent Summary (1–2 sentences, PoU-derived)

Consequences (what changes if accepted)

Irreversibility Flags

Risks & Unknowns

Alternatives (including “do nothing”)

Canonical Term References

Full Text (optional, expandable)

Skipping levels is prohibited.

6. Proof of Understanding Gate
6.1 Required PoU Check

Before ratification, the user MUST:

View a PoU paraphrase

Confirm or correct it

Ratification without PoU confirmation is INVALID.

6.2 Mismatch Handling

If user correction diverges from PoU beyond D2:

Ratification blocked

Semantic clarification required

Mediator re-engagement optional

7. Anti-Fatigue Protections
7.1 Rate Limits
Action	Limit
Ratifications	≤ 5 / hour
Dispute escalations	≤ 2 / day
License grants	≤ 3 / day

Exceeded limits trigger:

Cooling period (see §9)

Optional delegation to trusted agent

7.2 UI Safeguards

Mandatory UX constraints:

No dark patterns

No default “accept”

No countdown pressure unless emergency-flagged

No bundling of unrelated decisions

Violations are validator-detectable.

8. Assisted Ratification (Agents & Mediators)

Agents MAY assist but MUST:

Clearly label recommendations as non-binding

Surface dissenting validator views

Display mediator reputation & stake at risk

Never auto-accept on behalf of a human

Auto-accept thresholds apply only to proposal intake, never final ratification.

9. Cooling Periods (Normative)
9.1 Default Cooling Periods
Action	Cooling Period
Agreement finalization	12 hours
Settlement > threshold	24 hours
License delegation	24 hours
Dispute escalation	6 hours

Cooling may be waived ONLY if:

Explicitly declared

Validator confidence ≥ threshold

Emergency justification recorded

10. Semantic Lock Interaction

Once ratified:

Semantic Lock engages immediately

UI must display lock status

Post-lock edits require new intent + ratification

No silent edits permitted.

11. Accessibility & Equity

Ratification UX MUST support:

Plain-language mode

Screen readers

Language switching (NCIP-003)

Cognitive compression summaries

Optional human mediator walkthroughs

Complexity must scale down, never up.

12. Machine-Readable UX Constraints (YAML)
human_ratification:
  version: 1.0

  cognitive_load_budget:
    simple: 7
    financial: 9
    licensing: 9
    dispute: 5
    emergency: 3

  proof_of_understanding:
    required: true
    max_allowed_drift: 0.20

  rate_limits:
    ratifications_per_hour: 5
    disputes_per_day: 2

  cooling_periods:
    agreement: "12h"
    settlement: "24h"
    licensing: "24h"
    dispute: "6h"

  ui_requirements:
    no_default_accept: true
    no_dark_patterns: true
    hierarchy_enforced: true
    lock_visibility_required: true

13. Validator Responsibilities

Validators MUST:

Measure semantic unit count

Detect UX violations

Downgrade confidence for rushed ratifications

Reject ratifications violating CLB or PoU rules

Repeated UX violations are slashable (see NCIP-010).

14. Design Outcome

When correctly implemented:

Humans remain the slowest, safest component

AI speed is throttled by comprehension

Consent is meaningful, auditable, and defensible

“I didn’t understand” becomes a verifiable claim

Final Statement

NatLangChain refuses to trade human dignity for throughput.

If a decision matters enough to be on-chain,
it matters enough to be understood.
