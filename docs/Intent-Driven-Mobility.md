NatLangChain - Additional Features Specification: Intent-Driven Mobility & Logistics Resolution
NatLangChain v1 — Scope Boundaries

Version: 1.0
Status: Enforced at Protocol + UX + Policy Layers
Intent: Minimize legal, safety, and liability surface while proving economic viability

1. Core Definition (What v1 Is)

NatLangChain v1 is:

A decentralized intent-matching and contract-settlement protocol for non-passenger, ground-based delivery of goods and equipment by verified independent operators using road-legal vehicles.

It is not:

A ride-hailing service

A passenger transportation network

A logistics carrier of record

A fleet operator

The platform matches intent, verifies capability, and settles outcomes.

2. Explicitly Allowed (Green Zone)
2.1 Cargo & Delivery Types

Allowed cargo must be inert, legal, and non-hazardous.

Allowed Examples

Food (hot, cold, packaged)

Parcels and retail goods

Construction materials (non-hazardous)

Tools and equipment

Furniture

Rental equipment returns

Documents

Event supplies

Non-living objects only

Explicit Conditions

Cargo must fit within vehicle class limits

No special handling beyond basic securing

No temperature guarantees beyond reasonable effort

No chain-of-custody for regulated goods

2.2 Vehicle Classes (v1)
Vehicle Type	Status
Passenger cars	✅
Hatchbacks / wagons	✅
Pickup trucks	✅
Cargo vans	✅
Box trucks (non-CDL)	✅
Trailers (light)	⚠️ Conditional
Motorcycles / scooters	❌ (v2+)

CDL vehicles: ❌ excluded in v1 to avoid DOT escalation

2.3 Operator Eligibility

To search or accept intents, operators must have:

Valid, non-suspended driver license

Registered vehicle

Insurance explicitly covering commercial use

Identity verification passed

State residency or work eligibility

Platform safety agreement acceptance

No license → no visibility
Suspension → immediate access revocation

Fail closed.

2.4 Job Types

Allowed job categories:

Point-to-point delivery

Multi-stop delivery bundles

Time-bound courier runs

Retail pickup & drop-off

Construction site delivery (materials only)

Equipment repositioning (non-operational)

Emergency part delivery (non-medical)

3. Explicitly Banned (Red Zone)
3.1 Humans & Animals

❌ No human passengers
❌ No ride-sharing
❌ No ride-along helpers
❌ No pets or livestock
❌ No medical transport

If it breathes, it’s banned.

3.2 Regulated or Dangerous Goods

❌ Hazardous materials (any DOT class)
❌ Alcohol (v1)
❌ Cannabis (even if legal locally)
❌ Firearms or ammunition
❌ Explosives
❌ Controlled substances
❌ Medical specimens
❌ Cash or bearer instruments
❌ High-value items requiring bonded courier

No exceptions.

3.3 Vehicle & Operation Constraints

❌ Autonomous vehicles
❌ Heavy machinery operation
❌ Towing disabled vehicles
❌ Snowplows or emergency vehicles
❌ Oversized or overweight loads
❌ CDL-required operations
❌ Cross-border (international) delivery

3.4 Employment & Labor Substitution

❌ Passenger transport
❌ On-demand personal services
❌ Home entry or key handling
❌ Assembly, installation, or labor
❌ White-glove services
❌ Anything implying employment control

You deliver to the curb, not into the home.

4. Gray Zone Handling (Explicitly Deferred)

These are not allowed in v1, even if tempting:

Alcohol delivery

Prescription delivery

Medical devices

Refrigerated guarantees

Construction labor

Passenger accompaniment

Driver-assisted loading beyond reasonable effort

Shared custody or escrow goods

Deferred ≠ rejected forever — just not now.

5. Enforcement Layers
5.1 Protocol Layer

Intent schema rejects banned categories

Mediator node refuses disallowed contracts

Automatic suspension on violation signals

5.2 UX Layer

Job categories are constrained

No UI paths to forbidden actions

Search filters prevent category creep

5.3 Economic Layer

Burns escalate for misclassification

Collateral forfeiture for violations

Repeat offenders lose access permanently

5.4 Legal Layer

Platform is not carrier of record

Operators remain independent

Intent posters warrant legality of goods

Dispute resolution via protocol arbitration

6. Safety & Insurance Posture

v1 safety guarantees:

Verified operators only

Commercial insurance minimums enforced

Cargo-only risk profile

No passenger duty-of-care

No public accommodation obligations

This is intentional.

7. Expansion Gates (v2+ Conditions)

Any future expansion requires:

Proven loss ratios

Regulatory green lights

Separate product surfaces

Separate insurance pools

Explicit opt-in by operators

Passenger transport must be a separate protocol surface, not an extension.

8. One-Line Summary (Internal)

v1 moves objects, not people.

9. Strategic Benefit (Why This Boundary Matters)

This scope:

Keeps regulators calm

Keeps insurers willing

Keeps operators safe

Keeps abuse surface low

Keeps iteration fast

Most platforms fail because they expand too early.

This one survives because it doesn’t.
