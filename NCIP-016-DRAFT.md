# NCIP-016 (PROVISIONAL DRAFT): Anti-Capture Mechanisms & Market Fairness

**Status:** Draft - Pending System Balancing
**Created:** 2024-12-24
**Dependencies:** NCIP-010 (Mediator Reputation)

---

## Abstract

Hardware costs for running mediator nodes are negligible relative to potential revenue. Without structural constraints, a well-funded actor could deploy thousands of nodes, undercut competitors, accumulate dominant reputation, and capture the market. This NCIP establishes anti-capture mechanisms to preserve fair market dynamics.

**Core Principle:** *A fair market requires that no actor can purchase dominance. Participation is earned through service, not capital.*

---

## 1. Verified Human Identity Requirement

### 1.1 One Human, One Mediator License

Each mediator node MUST be registered to a verified human identity. The mapping is:

```
1 verified human → 1 mediator license → N nodes (where N ≤ MAX_NODES_PER_LICENSE)
```

Recommended: `MAX_NODES_PER_LICENSE = 3` (for redundancy, not scale)

### 1.2 Self-Representation Mandate

Mediators MUST operate as themselves. Prohibited structures include:

| Prohibited | Reason |
|------------|--------|
| Franchise models | Obscures accountability |
| Corporate registration | Enables capital-based capture |
| Delegated identity | "Registering your dog" problem |
| Shell entities | Circumvents identity limits |
| Employment of mediators | Creates principal-agent misalignment |

**Rule:** *You come to market representing yourself. Your reputation is yours. Your liability is yours.*

### 1.3 Identity Verification

Verification mechanisms (implementation TBD):
- Cryptographic proof of personhood (e.g., WorldID, BrightID)
- Web of trust attestations from existing mediators
- Jurisdictional identity binding (optional, for regulated contexts)

Verification MUST NOT require:
- Government ID disclosure to the network
- Biometric data storage on-chain
- Real name publication

---

## 2. Randomized Selection Floor

### 2.1 Minimum Traffic Guarantee

All active mediators with `CTS >= MIN_CTS_THRESHOLD` receive a randomized selection floor:

```
P(selection) = max(FLOOR_PROBABILITY, trust_weighted_probability)
```

Recommended:
- `MIN_CTS_THRESHOLD = 0.3`
- `FLOOR_PROBABILITY = 0.05` (5% chance regardless of CTS ranking)

### 2.2 Rationale

- Prevents reputation lock-in by incumbents
- Allows new entrants to build track record
- Maintains competitive pressure on dominant mediators
- Reflects that even low-CTS mediators may be optimal for specific intents

### 2.3 Floor Decay for Inactivity

Mediators who decline or ignore assignments lose floor protection:

```
floor_probability = FLOOR_PROBABILITY * (1 - inactivity_penalty)
```

---

## 3. Fee Structure Constraints

### 3.1 Contract-Maker Fee Authority

Fee rates are set by **contract makers**, not mediators. Mediators compete on:
- Reputation (CTS)
- Domain expertise
- Response latency
- Semantic accuracy

NOT on fee undercutting.

### 3.2 Fee Floor (Anti-Dumping)

Minimum fee prevents predatory pricing:

```
fee >= max(ABSOLUTE_FLOOR, settlement_value * PERCENTAGE_FLOOR)
```

Recommended:
- `ABSOLUTE_FLOOR = 0.01 NLC`
- `PERCENTAGE_FLOOR = 0.1%` (one-tenth of one percent)

Mediators MAY NOT waive fees to gain market share.

### 3.3 Fee Ceiling (Optional)

Contract makers MAY set maximum fees. Network does not impose ceiling.

---

## 4. Concentration Monitoring

### 4.1 Market Share Tracking

The network MUST track:

```python
@dataclass
class ConcentrationMetrics:
    top_1_share: float      # % of settlements by #1 mediator
    top_5_share: float      # % of settlements by top 5
    top_10_share: float     # % of settlements by top 10
    herfindahl_index: float # HHI for market concentration
    new_entrant_rate: float # % of settlements going to <30 day mediators
```

### 4.2 Concentration Alerts

If `top_5_share > 0.50` (50%), the network SHOULD:
- Increase `FLOOR_PROBABILITY` for non-top-5 mediators
- Emit public concentration warning
- Trigger governance review

### 4.3 No Automatic Penalties

Concentration alerts are informational. Dominant mediators are not penalized for success—only for prohibited structures (Section 1.2).

---

## 5. Prohibited Coordination

### 5.1 Collusion Detection

Signals that MAY indicate prohibited coordination:
- Multiple mediator IDs from same IP ranges
- Identical proposal language across "different" mediators
- Synchronized fee changes
- Cross-mediator reputation boosting patterns

### 5.2 Consequences

Proven collusion results in:
- Slashing per NCIP-010 (COLLUSION_SIGNALS offense)
- License revocation for all involved identities
- Permanent ban from re-registration

---

## 6. Open Questions (To Be Resolved)

- [ ] Identity verification mechanism selection
- [ ] Optimal `FLOOR_PROBABILITY` value
- [ ] Whether fee floors should be protocol-level or governance-adjustable
- [ ] Cross-jurisdictional identity recognition
- [ ] Appeals process for wrongful collusion accusations
- [ ] Sybil resistance without centralized identity providers

---

## 7. Implementation Notes

This is a **provisional addendum**. Implementation SHOULD NOT proceed until:

1. Core NCIPs (001-015) are stable
2. Testnet data on organic concentration patterns exists
3. Identity verification partnerships are established
4. Governance mechanism for parameter adjustment is live

---

## 8. Relationship to Existing NCIPs

| NCIP | Relationship |
|------|--------------|
| NCIP-010 | Extends slashing for collusion; adds identity binding |
| NCIP-011 | Validator weighting unaffected by this NCIP |
| NCIP-008 | Precedent system may cite concentration as factor |

---

*This document is provisional. Parameters are recommendations, not specifications. Revisit after system balancing phase.*
