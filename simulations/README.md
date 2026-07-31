# Long-horizon simulations

The unit suite proves that each piece of NatLangChain works. This directory
proves that the pieces keep working *together, over time* — with state
accumulating, windows expiring, blocks piling up, and a node restarting every
month.

## Running it

```bash
python -m simulations.year_simulation                  # a full 365-day year
python -m simulations.year_simulation --days 30        # a quick pass
python -m simulations.year_simulation --difficulty 4   # heavier proof-of-work
```

Outputs land in `simulations/results/`:

* `YEAR_REPORT.md` — the readable narrative of the year
* `year_results.json` — every day, probe, audit and snapshot as structured data

A compressed 28-day version runs as part of the test suite
(`tests/test_year_simulation.py`, marked `slow`), so the probes stay honest
without adding minutes to every `pytest` run.

## What is real and what is simulated

Real: the blockchain engine, the validation pipeline, block hashing,
proof-of-work, the asset and derivative registries, deduplication, rate
limiting, quality analysis, JSON persistence, gzip compression, encryption at
rest, and serialization round-trips. All of it is the code in `src/`.

Simulated: **the clock, and only the clock.** `simulations/virtual_clock.py`
replaces the `time` and `datetime` handles inside `src/blockchain.py` with a
clock the driver advances explicitly. That is what makes a year of rate-limit
windows, deduplication expiry, and timestamp-drift checks fit into a few
minutes of wall time — without any of those checks being stubbed out.

Proof of Understanding runs against `MockValidator`, the deterministic
heuristic validator that ships in `src/blockchain.py`. The Anthropic-backed
validator needs an API key and would need ~15,000 LLM calls for one simulated
year. Where a finding depends on validator behaviour, the report says so.

## The shape of a simulated year

| Cadence | What happens |
| --- | --- |
| Continuously | ~40 prose entries a day from a 60-actor supply-chain economy, with weekday seasonality, quarter-end spikes, and growth across the year |
| Daily | One block mined from the pending queue |
| Weekly | A persistence snapshot, with size and write latency recorded |
| Monthly | A node restart: save, load from disk, rebuild, verify, and continue on the restored instance |
| Quarterly | A full-chain audit: validation, narrative generation, author and intent queries, registry sizes — all timed, so cost-vs-length is visible |
| Scheduled | 21 adversarial and operational probes (see below) |

Traffic is generated in four classes so the report can separate "the chain
correctly refused this" from "the chain refused something legitimate":

* **clean** — well-formed prose that should be accepted
* **flagged** — ordinary commercial language ("non-refundable deposit",
  "irrevocable letter of credit") that the heuristic validator treats as
  hostile; measures the false-rejection rate
* **ambiguous** — vague prose that should land in `NEEDS_CLARIFICATION`
* **adversarial** — the scheduled probe campaign

## The probe campaign

| Probe | Asks |
| --- | --- |
| `replay_within_dedup_window` | Is an identical resubmission inside the window refused? |
| `replay_of_still_pending_entry` | Is a replay of an unmined entry refused *cleanly*? |
| `backdating_45_days` / `future_dating_6_hours` | Are manipulated timestamps refused? |
| `metadata_spoofing` | Are reserved metadata fields stripped and legitimate ones kept? |
| `sybil_flood_120_entries` | Does the per-author rate limit hold? |
| `global_flood_200_entries_80_authors` | Does the global rate limit hold? |
| `double_spend_same_queue` | Can an asset be sold twice before mining? |
| `transfer_by_non_owner` | Can a non-owner transfer a registered asset? |
| `asset_lock_leak_after_validation_failure` | Does a rejected transfer release its reservation? |
| `chain_bloat_oversized_entry` / `undersized_entry` | Are size limits enforced? |
| `silent_content_tamper` | Does editing mined prose break the hash? |
| `tamper_with_self_rehash` | Does rehashing the tampered block still fail? |
| `history_rewrite_cost` | How expensive is rewriting the tail of the ledger? |
| `action_intent_mismatch` | Is a restriction filed under a profile-update intent refused? |
| `action_mismatch_punctuation_evasion` | Is it still refused when the verb ends the sentence? |
| `adversarial_language` | Is a rights-waiver clause refused? |
| `encrypted_persistence` | Can a chain written with encryption at rest be read back? |
| `concurrent_submit_and_mine` | Do entries accepted during proof-of-work survive? |
| `dedup_fingerprint_growth` | Does the fingerprint registry stay bounded? |

Probes are scheduled on specific days of the year and rescaled proportionally
for shorter runs, so a 28-day pass still exercises every one of them in the
same order.

Each probe records an expectation and an observation. Probes that assert a
correctness property are pass/fail. `history_rewrite_cost` is a
characterization probe: it measures a tradeoff (proof-of-work difficulty)
rather than a defect, and reports the number rather than a verdict.

## Determinism

A run is reproducible from `(seed, days, difficulty, entries-per-day)`. The
workload generator, the daily volume curve, and the probe calendar are all
seeded. Wall-clock timings naturally vary between machines; nothing else does.

## Adding a probe

1. Write a `_probe_<name>(self, day)` method on `YearSimulation`.
2. Call `self._record(day, name, expectation, outcome, passed=...)` with a
   plainly stated expectation — the report prints it verbatim next to what
   actually happened.
3. Register it in `_probe_calendar()` on the day it should run.
4. If it asserts a correctness property, add its name to `MUST_PASS_PROBES` in
   `tests/test_year_simulation.py`.

Use `self._add_entry(...)` rather than `self.chain.add_entry(...)`: it captures
an uncaught exception as an engine fault and lets the year continue, which is
how the `KeyError` in the deduplication path was found rather than crashing the
run on day 24.
