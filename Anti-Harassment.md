7.3 Anti-Harassment Design

NatLangChain introduces economic pressure to compress conflict. Without constraints, such pressure could be abused to impose unwanted cost, attention, or friction on another party. In this protocol, harassment is defined as any use of negotiation or dispute mechanisms without a legitimate intent to reach resolution, where the primary effect is to burden the counterparty.

NatLangChain does not attempt to detect intent or police behavior. Instead, it enforces a single economic rule:

Any attempt to harass must be strictly more expensive for the harasser than for the target.

This property is achieved through asymmetric initiation costs, free non-engagement, bounded interaction surfaces, and escalating penalties for non-resolving behavior.

7.3.1 Dual Initiation Paths

All interactions MUST fall into one of two mutually exclusive initiation paths.

Path	Trigger Condition	Initiator Cost	Counterparty Obligation	Harassment Exposure
Breach / Drift Dispute	On-chain evidence of violation or semantic drift in an existing agreement	Immediate symmetric stake S (escrowed)	Must match stake within T_stake or accept fallback outcome	Low — initiator is economically exposed first
Voluntary Request	New negotiation, amendment, or reconciliation request without breach	Small non-refundable burn fee	None — may ignore indefinitely at zero cost	Very Low — ignored requests impose only self-cost

Rationale:
No party can force interaction without paying upfront, and ignoring a voluntary request is always free.

7.3.2 Frivolous Breach Claim Protection

To prevent dispute-based harassment:

The initiator MUST stake first and fully in all breach or drift disputes.

If the counterparty declines to match the stake:

The dispute resolves immediately to the predefined fallback state.

The initiator gains no further leverage or escalation rights.

Repeated breach initiations on the same contract or asset MUST trigger escalating minimum stakes (e.g., +50% per recent non-resolving dispute).

Implementations MAY define a per-contract cooldown window (e.g., 30 days) after resolution before new breach claims are permitted.

Effect:
Frivolous or probing disputes require upfront capital and cannot be used to force engagement.

7.3.3 Counter-Proposal Griefing Limits

To bound adversarial dragging behavior:

The number of counter-proposals per dispute is strictly capped (default: 3).

Counter-proposal fees MUST increase exponentially (base_fee × 2ⁿ).

All counter-proposal fees are burned immediately.

Effect:
The maximum cost of prolonged disagreement is predictable, finite, and borne primarily by the party attempting to extend the interaction.

7.3.4 Protection for Low-Resource Parties

Recognizing that symmetric costs can still disproportionately impact low-resource participants:

The protocol treasury (funded by burns and counter-fees) MAY subsidize defensive stakes for participants with demonstrated histories of good-faith engagement.

Subsidies MUST be:

opt-in,

transparent,

derived solely from on-chain dispute outcomes.

A public harassment score, derived from dispute patterns (e.g., high initiator timeout rates or ignored voluntary requests), MUST automatically increase future initiation costs for flagged actors.

Effect:
Repeated harassment becomes progressively more expensive, while good-faith defendants gain structural protection without central discretion.

7.3.5 Transparency and Deterrence

All initiation attempts, stakes, burns, counters, and resolutions MUST be publicly queryable on-chain.

The protocol does not censor participants.

Persistent harassers become economically and reputationally visible to the ecosystem, enabling voluntary social and market responses.

7.3.6 Design Outcome

When correctly implemented, the anti-harassment design guarantees that:

Ignoring harassment is always free.

Engaging is optional and symmetrically priced.

Executing harassment is expensive, bounded, and self-limiting.

NatLangChain does not eliminate bad actors.
It ensures that conflict without resolution intent collapses under its own cost structure.

This provides stronger harassment resistance than most off-chain systems (e.g., email, social media, or traditional legal threats), where initiating harassment is often near-zero cost.

No additional authority, moderation, or judgment is required.
The economic layer itself neutralizes the abuse vector.
