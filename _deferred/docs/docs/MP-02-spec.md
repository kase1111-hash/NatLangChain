MP-02 — Proof-of-Effort Receipt Protocol
NatLangChain Effort Verification Specification (Standalone)

Status: Draft (Normative)

1. Purpose

MP-02 defines the protocol by which human intellectual effort is observed, validated, and recorded as cryptographically verifiable receipts on NatLangChain.

The protocol establishes a primitive that is:

Verifiable without trusting the issuer

Human-readable over long time horizons

Composable with negotiation, licensing, and settlement protocols

MP-02 does not assert value, ownership, or compensation. It asserts that effort occurred, with traceable provenance.

2. Design Principles

Process Over Artifact — Effort is validated as a process unfolding over time, not a single output.

Continuity Matters — Temporal progression is a primary signal of genuine work.

Receipts, Not Claims — The protocol records evidence, not conclusions about value.

Model Skepticism — LLM assessments are advisory and must be reproducible.

Partial Observability — Uncertainty is preserved, not collapsed.

3. Definitions
3.1 Effort

A temporally continuous sequence of human cognitive activity directed toward an intelligible goal.

3.2 Signal

A raw observable trace of effort, including but not limited to:

Voice transcripts

Text edits

Command history

Structured tool interaction

3.3 Effort Segment

A bounded time slice of signals treated as a unit of analysis.

3.4 Receipt

A cryptographic record attesting that a specific effort segment occurred, with references to its source signals and validation metadata.

4. Actors
4.1 Human Worker

The individual whose effort is being recorded.

4.2 Observer

A system component responsible for capturing raw signals.

4.3 Validator

An LLM-assisted process that analyzes effort segments for coherence and progression.

4.4 Ledger

An append-only system that anchors receipts and their hashes.

5. Effort Capture

Observers MAY record:

Continuous or intermittent signals

Multi-modal inputs

Observers MUST:

Time-stamp all signals

Preserve ordering

Disclose capture modality

Observers MUST NOT:

Alter raw signals

Infer intent beyond observed data

6. Segmentation

Signals are grouped into Effort Segments based on:

Time windows

Activity boundaries

Explicit human markers

Segmentation rules MUST be deterministic and disclosed.

7. Validation

Validators MAY assess:

Linguistic coherence

Conceptual progression

Internal consistency

Indicators of synthesis vs duplication

Validators MUST:

Produce deterministic summaries

Disclose model identity and version

Preserve dissent and uncertainty

Validators MUST NOT:

Declare effort as valuable

Assert originality or ownership

Collapse ambiguous signals into certainty

8. Receipt Construction

Each Effort Receipt MUST include:

Receipt ID

Time bounds

Hashes of referenced signals

Deterministic effort summary

Validation metadata

Observer and Validator identifiers

Receipts MAY reference:

Prior receipts

External artifacts

9. Anchoring

Receipts are anchored by:

Hashing receipt contents

Appending hashes to a ledger

The ledger MUST be:

Append-only

Time-ordered

Publicly verifiable

10. Verification

A third party MUST be able to:

Recompute receipt hashes

Inspect validation metadata

Confirm ledger inclusion

Trust in the Observer or Validator is not required.

11. Failure Modes

The protocol explicitly records:

Gaps in observation

Conflicting validations

Suspected manipulation

Incomplete segments

Failures reduce confidence but do not invalidate receipts.

12. Privacy and Agency

Raw signals MAY be encrypted or access-controlled

Receipts MUST not expose raw content by default

Humans MAY revoke future observation

Past receipts remain immutable.

13. Non-Goals

MP-02 does NOT:

Measure productivity

Enforce labor conditions

Replace authorship law

Rank humans by output

14. Compatibility

MP-02 receipts are compatible with:

MP-01 Negotiation & Ratification

Licensing and delegation modules

External audit systems

15. Canonical Rule

If effort cannot be independently verified as having occurred over time, it must not be capitalized.

End of MP-02
