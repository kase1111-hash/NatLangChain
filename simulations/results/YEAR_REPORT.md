# NatLangChain — One Year of Simulated Operation

A single node ran for **365 simulated days** (2026-01-01 to 2026-12-20) in 280.23s of wall clock time. The blockchain engine, validation pipeline, registries, proof-of-work, and JSON persistence are the real implementations from `src/`. Only the clock is simulated, so rate-limit windows, deduplication expiry, and timestamp-drift checks experience a full year.

Proof of Understanding ran against `MockValidator`, the deterministic validator shipped in `src/blockchain.py`. No `ANTHROPIC_API_KEY` is available in this environment, so the LLM validator itself was not exercised; every other component was.

## Ledger at year end

| Measure | Value |
| --- | --- |
| Blocks mined | 366 |
| Entries on chain | 14,112 |
| Entries submitted | 14,896 |
| Entries accepted | 13,997 (94.0%) |
| Entries rejected | 899 |
| Mean entries per block | 38.6 |
| Busiest day | 109 submissions |
| Deepest pending queue | 119 entries |
| Head block hash | `0034655a72a5bf54d2512fa34c9296a5…` |

## Integrity

| Check | Result |
| --- | --- |
| `validate_chain()` at difficulty 2 | yes |
| Every block hash recomputes | yes |
| Every `previous_hash` links | yes |
| Every mined block meets difficulty | yes |
| Serialization round-trip identical | yes |
| Entries missing validation status | 0 |
| Duplicate entries on chain | 0 |
| Dangling derivative links | 0 |
| Asset ownership mismatches | 0 |
| Full-chain validation time | 0.0853s |

## Growth over the year

| Day | Blocks | Entries | Validate (s) | Narrative (chars) | Dedup fingerprints held |
| --- | --- | --- | --- | --- | --- |
| 91 | 92 | 3,040 | 0.0177 | 1,751,582 | 101 |
| 182 | 183 | 6,273 | 0.0374 | 3,620,290 | 2 |
| 273 | 274 | 10,003 | 0.0599 | 5,773,195 | 2 |
| 364 | 365 | 14,047 | 0.0867 | 8,102,434 | 2 |
| 365 | 366 | 14,112 | 0.086 | 8,140,487 | 3 |

Persisted `chain.json` grew from 14,962 bytes on day 7 to 1,055,524 bytes on day 364 (75 bytes per entry). The final snapshot write took 0.2504s.

## Mining

At difficulty 2, block production averaged 0.0502s (median 0.033s, worst 0.422s) with a mean nonce of 233 and a worst case of 1,485. The whole year of mining cost 18.33s of CPU.

## Rejections

| Reason | Count |
| --- | --- |
| `validation:INVALID` | 446 |
| `validation:NEEDS_CLARIFICATION` | 416 |
| `double_transfer` | 37 |

Proof of Understanding decisions on rejected entries:

| Decision | Count |
| --- | --- |
| `INVALID` | 446 |
| `NEEDS_CLARIFICATION` | 416 |

Outcome by traffic class:

| Traffic class | Submitted | Accepted | Rejected |
| --- | --- | --- | --- |
| ambiguous | 416 | 0 | 416 |
| clean | 14,034 | 13,997 | 37 |
| flagged | 446 | 0 | 446 |

## Restart recovery

| Day | Blocks | Load (s) | Chain valid | Head hash | Ownership | Derivatives | Transfer history |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 30 | 31 | 0.0136 | yes | yes | yes | yes | yes |
| 60 | 61 | 0.0287 | yes | yes | yes | yes | yes |
| 90 | 91 | 0.0475 | yes | yes | yes | yes | yes |
| 120 | 121 | 0.0654 | yes | yes | yes | yes | yes |
| 150 | 151 | 0.0804 | yes | yes | yes | yes | yes |
| 180 | 181 | 0.159 | yes | yes | yes | yes | yes |
| 210 | 211 | 0.1163 | yes | yes | yes | yes | yes |
| 240 | 241 | 0.1408 | yes | yes | yes | yes | yes |
| 270 | 271 | 0.1576 | yes | yes | yes | yes | yes |
| 300 | 301 | 0.1866 | yes | yes | yes | yes | yes |
| 330 | 331 | 0.211 | yes | yes | yes | yes | yes |
| 360 | 361 | 0.3 | yes | yes | yes | yes | yes |

## Engine faults

No uncaught exception escaped `add_entry()` during the year.

## Adversarial campaign

20 of 21 probes behaved as expected.

| Day | Probe | Expected | Observed | Result |
| --- | --- | --- | --- | --- |
| 23 | `replay_within_dedup_window` | an identical resubmission inside the 1h window is rejected as a duplicate | first=pending, replay=rejected/duplicate | PASS |
| 24 | `replay_of_still_pending_entry` | replaying an entry that is still in the pending queue is rejected cleanly | first=pending; replay one hour later=rejected/duplicate | PASS |
| 47 | `backdating_45_days` | an entry stamped 45 days in the past is rejected | rejected/invalid_timestamp | PASS |
| 48 | `future_dating_6_hours` | an entry stamped 6 hours in the future is rejected | rejected/invalid_timestamp | PASS |
| 61 | `metadata_spoofing` | reserved metadata fields are stripped, legitimate fields survive | stripped 4/4 reserved fields; legitimate_field kept=True | PASS |
| 90 | `sybil_flood_120_entries` | a 120-entry burst from one author in one instant is rate limited | 10 accepted, 110 rejected ({'rate_limit': 110}) | PASS |
| 91 | `global_flood_200_entries_80_authors` | a coordinated 200-entry burst is capped by the global rate limit | 99 accepted, 29 rejected ({'rate_limit': 29}); global cap is 100 per 60s | PASS |
| 118 | `double_spend_same_queue` | selling the same asset twice before mining is rejected | first=pending, second=rejected/double_transfer | PASS |
| 119 | `transfer_by_non_owner` | a non-owner cannot transfer a registered asset | rejected/double_transfer; owner still solstice_electronics | PASS |
| 150 | `chain_bloat_oversized_entry` | an entry of 50,869 characters is refused | rejected/quality_check_failed (quality score 0.12999999999999998) | PASS |
| 151 | `undersized_entry` | a two-character entry is refused | rejected/quality_check_failed | PASS |
| 181 | `silent_content_tamper` | editing mined prose breaks the block hash and is detected | clone valid before=True, tamper detected=True, valid after restore=True | PASS |
| 182 | `tamper_with_self_rehash` | rehashing the tampered block still fails linkage and proof-of-work | detected=True; linkage broken=True; proof-of-work broken=True | PASS |
| 210 | `action_intent_mismatch` | a restriction action filed under a profile-update intent is rejected | rejected/INVALID | PASS |
| 211 | `action_mismatch_punctuation_evasion` | the same restriction action is still caught when the verb ends a sentence | rejected/INVALID | PASS |
| 240 | `adversarial_language` | a rights-waiver clause is rejected by Proof of Understanding | rejected/INVALID | PASS |
| 255 | `asset_lock_leak_after_validation_failure` | a rejected transfer releases its asset reservation so the owner can retry | rejected=rejected/INVALID; reservation still held=False; clean retry=pending/None | PASS |
| 270 | `history_rewrite_cost` | rewriting mined history should be computationally prohibitive | rewrote 40 blocks in 1.78s (44 ms/block); rewritten chain passes validate_chain=True; whole-chain rewrite would take about 12.0s on one core | FAIL |
| 300 | `encrypted_persistence` | a chain written with encryption at rest can be read back | compressed: round-trip ok; uncompressed: round-trip ok | PASS |
| 330 | `concurrent_submit_and_mine` | every entry accepted while a block is being mined is still on the chain or still pending | 190 accepted overall (40 of them during proof-of-work), 150 on chain, 40 pending, 0 unaccounted for; chain valid=True | PASS |
| 345 | `dedup_fingerprint_growth` | the fingerprint registry stays bounded rather than growing with the chain | 3 fingerprints held against 13052 chain entries (window 3600s) | PASS |

## Findings

### 1. history_rewrite_cost (day 270)

**Expected:** rewriting mined history should be computationally prohibitive

**Observed:** rewrote 40 blocks in 1.78s (44 ms/block); rewritten chain passes validate_chain=True; whole-chain rewrite would take about 12.0s on one core


## Notes from the run

- Genesis block created at virtual 2026-01-01 with hash 1e08f7f8396fe809.
- Proof-of-work at difficulty 2 provides no meaningful rewrite resistance. A tampered copy of a full year of history re-mines and passes validate_chain() in roughly 12.0 seconds on a single core. With no peer network or fork-choice rule in the core engine, nothing else distinguishes the rewritten chain from the original.
