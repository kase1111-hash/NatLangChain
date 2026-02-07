MP-04 — Licensing & Delegation Protocol
NatLangChain Rights, Authority, and Use Specification (Standalone)

Status: Draft (Normative)

1. Purpose

MP-04 defines how rights to use, delegate, sublicense, or act upon verified effort and negotiated agreements are explicitly granted, scoped, and revoked within NatLangChain.

The protocol ensures that licensing and delegation are:

Human-authored and human-ratified

Legible in natural language

Cryptographically referenceable

Composable with MP-01, MP-02, and MP-03

MP-04 does not create ownership by default. It records permissioned authority.

2. Design Principles

Authority Is Explicit — No rights are implied.

Delegation Is Bounded — Scope, duration, and purpose must be stated.

Licenses Are Conditional — Use may depend on verified effort or settlement.

Revocability Where Possible — Delegation is not permanent unless stated.

Human Ratification Required — All grants require explicit consent.

3. Core Concepts
3.1 License

A human-ratified grant permitting specified use of referenced material or effort receipts.

3.2 Delegation

A human-ratified grant allowing another party or agent to act on one’s behalf within defined constraints.

3.3 Grantor

The human or institution issuing a license or delegation.

3.4 Grantee

The recipient of authority.

4. Scope of Authority

Each license or delegation MUST specify:

Subject — What is being licensed or delegated (receipts, artifacts, negotiation rights)

Purpose — Allowed use cases

Limits — Prohibited actions

Duration — Time-bounded or perpetual

Transferability — Whether sublicensing or redelegation is allowed

Ambiguous grants are invalid.

5. Licensing Lifecycle
Phase 1 — Proposal

Licenses MAY be proposed by:

Grantor

Counterparty

Mediator (non-binding)

All proposals are provisional.

Phase 2 — Ratification

The Grantor MUST ratify the license in natural language, explicitly referencing:

Scope

Duration

Transferability

Example:

“I license the use of receipts R-123 through R-130 for non-exclusive research purposes for one year.”

Phase 3 — Activation

Upon ratification:

The license is recorded on the ledger

References to underlying receipts or agreements are immutable

6. Delegation Lifecycle
Phase 1 — Delegation Proposal

Delegations MAY be proposed by any party but remain non-binding.

Phase 2 — Ratification

The delegator MUST ratify:

Delegated powers

Constraints

Revocation conditions

Example:

“I delegate negotiation authority for licensing discussions to Agent X, excluding settlement ratification.”

Phase 3 — Execution

Delegated actions MUST:

Reference the delegation grant

Stay within declared bounds

Actions outside scope are invalid.

7. Revocation and Expiry

Licenses and delegations MAY:

Expire automatically

Be revoked explicitly

Revocation MUST:

Be human-authored

Be time-stamped

Reference the original grant

Past authorized actions remain valid.

8. Abuse and Overreach

The protocol records:

Scope violations

Unauthorized redelegation

Use outside licensed purpose

Such events MAY trigger MP-03 dispute escalation.

9. Non-Goals

MP-04 does NOT:

Enforce IP law

Determine fair compensation

Assume exclusivity by default

Replace legal licensing agreements

10. Compatibility

MP-04 integrates with:

MP-01 for negotiated grants

MP-02 for effort-based licensing

MP-03 for dispute handling

External legal or contractual frameworks

11. Canonical Rule

If authority cannot be traced to an explicit human-ratified grant, it must be treated as invalid.

End of MP-04
