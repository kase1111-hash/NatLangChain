NCIP-004: Proof of Understanding (PoU) Generation & Verification

Status: Canonical
Type: Semantic Safety / Human Verification
Version: 1.0
Created: December 22, 2025
Applies To:

Prose Contracts

Validators

Mediators

LLM Agents

Dispute Resolution Protocols

Depends On:

NatLangChain Technical Specification v3.0

NCIP-001: Canonical Term Registry

NCIP-002: Semantic Drift Thresholds & Validator Responses

NCIP-003: Multilingual Semantic Alignment & Drift

1. Purpose

This NCIP defines Proof of Understanding (PoU) as a required, verifiable artifact demonstrating that a party:

Has read the Prose Contract

Has comprehended its meaning

Accepts its obligations as written

Cannot plausibly claim misunderstanding later

PoU is semantic, not merely cryptographic.

2. Definition (Normative)

Proof of Understanding (PoU)
An explicit, structured response demonstrating accurate comprehension of an Intent or Agreement’s meaning, constraints, and consequences, evaluated against canonical semantics.

A PoU is invalid if it:

Restates text verbatim without interpretation

Omits material obligations

Introduces contradictory meaning

3. When PoU Is Required

PoU is mandatory when any of the following apply:

Drift level ≥ D2 (NCIP-002)

Multilingual alignment is used (NCIP-003)

Economic or legal obligations exist

Human ratification is required

Mediator escalation has occurred

Validators MAY require PoU in additional cases.

4. PoU Generation Requirements
4.1 Format (Normative)

A PoU MUST include:

Summary of Intent (in own words)

Key Obligations (what the party must do)

Key Rights (what the party receives)

Failure Consequences

Explicit Acceptance Statement

4.2 Prohibited Content

A PoU MUST NOT:

Quote the Prose Contract verbatim

Use only canonical phrasing

Omit any material clause

5. Canonical Evaluation Criteria

Validators evaluate PoU using semantic comparison, not string matching.

Each PoU is scored on:

Dimension	Description
Coverage	All material clauses addressed
Fidelity	Meaning matches canonical intent
Consistency	No contradictions
Completeness	Obligations + consequences acknowledged
6. PoU Scoring & Thresholds

Each dimension yields a score ∈ [0.0, 1.0].

The minimum dimension score governs outcome.

Score	Classification	Result
≥ 0.90	Verified	Accept
0.75 – 0.89	Marginal	Warn, allow resubmission
0.50 – 0.74	Insufficient	Reject, require retry
< 0.50	Failed	Reject, escalate
7. Mandatory Validator Responses
Verified

Accept PoU

Bind interpretation to signer

Store PoU hash + semantic fingerprint

Marginal

Accept temporarily

Flag for review

Recommend clarification

Insufficient / Failed

Reject PoU

Block execution

Require new PoU or mediator review

8. Multilingual PoU Rules

PoU MUST be authored in the CSAL or explicitly mapped to it

If authored in another language:

Drift scoring applies (NCIP-003)

Anchor reference is required

9. Binding Effect (Normative)

A verified PoU:

Fixes meaning for the signer

Waives claims of misunderstanding

Overrides later reinterpretations by that party

Is admissible in dispute resolution

10. Machine-Readable PoU Schema (YAML)

Validators MUST support this schema.

proof_of_understanding:
  version: 1.0
  contract_id: "prose-contract-uuid"
  signer:
    id: "did:natlang:abc123"
    role: "provider"
  language: en
  anchor_language: en

  sections:
    summary:
      text: >
        I understand that I am providing 5TB of storage
        with a minimum sustained read speed of 100MB/s
        for a monthly fee, and that availability affects payout.

    obligations:
      - Provide 5TB usable storage
      - Maintain ≥100MB/s sustained read throughput
      - Respond to retrieval proofs

    rights:
      - Receive monthly payment
      - Earn performance multiplier if uptime targets met

    consequences:
      - Reduced multiplier for downtime
      - Contract termination if sustained breach occurs

    acceptance:
      statement: >
        I confirm that this reflects my understanding
        and I agree to these terms.
      timestamp: 2025-12-22T18:40:00Z

  semantic_fingerprint:
    method: "llm-embedding-v3"
    hash: "0x8f9c…"

  validator_result:
    coverage_score: 0.96
    fidelity_score: 0.94
    consistency_score: 0.98
    completeness_score: 0.95
    final_score: 0.94
    status: verified

11. Security & Abuse Resistance
Prevented:

“I didn’t understand” defenses

LLM hallucinated acceptance

Copy-paste compliance

Language laundering

Remaining Risks:

Good-faith misunderstanding (handled via mediators)

Coercion (out of scope)

12. Final Statement

NCIP-004 ensures that:

Understanding is provable

Consent is semantic, not symbolic

Automation follows comprehension

Disputes start from shared ground truth

Signatures prove identity.
PoU proves meaning.
