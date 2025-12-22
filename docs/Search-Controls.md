NatLangChain - Additional Features Specification: Discovery Friction & Intent Search Controls
Version: 1.0
Feature Class: Controlled Intent Discovery
Status: Core (with Advanced Elements)
Last Updated: 2025-12-21
Maintained By: NatLangChain Development Team
Introduction
These features introduce deliberate friction into the intent discovery process, transforming passive browsing into committed exploration. By design, they prevent "high-seas sailing" (unbounded, low-effort scanning) while empowering serious solvers. This creates positive pressures: higher intent quality, reduced spam, and emergent alignment between posters and resolvers.
Tied to core principles: Prose as canonical ledger, deflationary burns (e.g., micro-fees for searches), and human supremacy (overrides via ceremonies). Integrates with mediator nodes for polling, ensuring solvers "earn" access through scoped, costed actions.
1. Narrow-Field Intent Search
Feature Name: Scoped Discovery Queries
Category: Anti-Trolling / Anti-Extraction
Status: Core
Description:
Queries must be tightly bounded by explicit parameters, rejecting vague or global scans of the intent pool.
Purpose:

Deters speculative harvesting or trolling by making broad queries impossible.
Promotes prepared, targeted participation, aligning with "intent economy" goals.

Mechanics:

Required Scopes:
Domain(s): e.g., "code", "logistics", "procurement".
Constraint Bands: e.g., budget $1K-$10K, difficulty "expert", timeline <30 days.
Resolver Capability Declaration: e.g., "Rust expert with 5+ years" (self-attested, verifiable via reputation).

Unscoped or overly broad queries auto-rejected with plain-language feedback: "Query too vague—specify domain and constraints."
LLM Validation: Mediator node uses local LLM to enforce scoping before ledger query.

Design Notes:

Not censorship, but "costed curiosity"—forces solvers to invest thought upfront.
Enhances deflation: Optional micro-burn (0.01%) per query, ramping with scope breadth.

2. Bundled Search Payloads (Laundry-List Queries)
Feature Name: Atomic Search Bundles
Category: Efficiency / Intentionality
Status: Core
Description:
A single request can bundle multiple scoped sub-queries, processed as one atomic operation.
Purpose:

Enables strategic planning without spammy repetition.
Rewards upfront effort, reducing overall network load.

Mechanics:

Bundle Limit: e.g., 5-10 sub-queries per request (configurable via load).
Each Sub-Query: Must independently meet scoping rules (e.g., domain + constraints).
Batch Results: Returned as aggregated JSON/prose summary, with partial matches if some fail.
Cooldown Application: Counts as one "action" for rate limiting.

Design Notes:

Mirrors real RFPs: Solvers scout workflows holistically.
Ties to burns: Bundle burns once, encouraging efficiency (e.g., 0.1% flat for bundle vs. per-query).

3. Search Cooldown / Timeout Window
Feature Name: Discovery Rate Limiter
Category: Anti-Abuse
Status: Core
Description:
Imposes time-based cooldowns between searches, scaled dynamically.
Purpose:

Slows iterative probing or automated scraping.
Makes abuse tedious, while genuine users adapt naturally.

Mechanics:

Base Cooldown: 5-15 minutes (identity-bound, via wallet/signer).
Scaling Factors:
Query Breadth: Broader scopes = longer cooldowns (e.g., +5min per extra domain).
System Load: Ramps up during peaks (e.g., 2x under high utilization).

Bundles: Treated as single cooldown event.
Exemptions: High-reputation solvers get reduced timers.

Design Notes:

Time as currency: No fiat cost, but enforces patience.
Prevents "pinging"—trollers can't refine attacks quickly.

4. Progressive Disclosure of Intent Details
Feature Name: Phased Intent Reveal
Category: Information Control
Status: Core
Description:
Initial results show metadata only; full details require commitment.
Purpose:

Shields authors from casual scraping.
Ensures solvers are invested before access.

Mechanics:

Teaser Results: Expose class (e.g., "code challenge"), reward band ($1K-$5K), verification type (e.g., "unit tests"), deadline window.
Full Unlock: Triggered by:
Commitment Post: Solver attests "Attempting resolution" (burns micro-fee).
Stake/Burn: Optional 0.1% token stake (refunded on valid attempt).

LLM Mediation: Node verifies commitment before revealing prose details.

Design Notes:

Ends "tourist mode"—access demands action.
Enhances security: Partial data useless for mass extraction.

5. Search-as-Commitment Signal
Feature Name: Discovery Commitment Weighting
Category: Behavioral Signaling
Status: Advanced
Description:
Search patterns feed into a reputation system, influencing access and costs.
Purpose:

Boosts focused solvers; weeds out explorers.
Builds trust signals for intent posters.

Mechanics:

Scoring: Narrow/focused searches +1; broad/frequent -1 (decaying over time).
Impacts:
High Score: Priority results, shorter cooldowns, lower burns.
Low Score: Increased fees, delayed access.

Transparency: Scores queryable; updates logged in IntentLog.

Design Notes:

Gentle nudge: Not punitive, but shapes behavior toward seriousness.
Game-Theoretic: Rewards long-term alignment over short-term gains.

Why This Prevents “High-Seas Sailing”
"High-seas sailing" (uncommitted, extractive browsing) relies on low-cost, rapid, broad access. This stack dismantles it:


Attack BehaviorResultBroad scansDisallowed by scopingRapid probingBlocked by cooldownsPassive scrapingThwarted by partial disclosureRepeated fishingDegraded by reputation decay
Legitimate solvers thrive: Bundle thoughtfully, commit decisively, build rep.
Emergent Effects

Behavioral: Solvers prepare holistically; browsing evolves to targeted hunting; intent quality improves (authors feel protected).
Economic: Discovery scarcity values information; serious actors coordinate cheaper/faster.
Security: Scrapers starve; trolling bores out; abuse self-limits.

Key Design Principle:
Discovery is a privilege earned by intent, not a right granted by curiosity.
Summary: Discovery Pressure Stack

LayerFunctionNarrow ScopePrevents trawlingBundled QueriesEncourages planningTimeoutsKills iteration abusePartial DisclosureStops harvestingReputation WeightingReinforces seriousness
This spec integrates seamlessly with mediator nodes, PoUW solving, and deflationary burns—ensuring traffic flows through committed, value-adding paths.
