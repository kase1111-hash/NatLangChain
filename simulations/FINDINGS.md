# What a year of operation found

`simulations/year_simulation.py` ran NatLangChain as a live single-node ledger
for 365 simulated days: 14,896 entries submitted, 13,997 accepted, 366 blocks
mined, 52 persistence snapshots, 12 node restarts, and a 21-probe adversarial
campaign. The full run record is in [`results/YEAR_REPORT.md`](results/YEAR_REPORT.md).

Six things came out of it. Five were defects and are fixed. One is a design
property that is worth stating plainly rather than fixing silently.

Before the fixes, 15 of 21 probes passed. After, 20 of 21 pass; the remaining
one is the characterization probe described in finding 6.

Every fix has a regression test in `tests/test_long_run_regressions.py`. Nine of
those fourteen tests fail against the pre-fix engine and all fourteen pass
against the fixed one. The existing 499-test suite passes unchanged throughout.

---

## 1. `KeyError` crash when an unmined entry is resubmitted

**Where:** `src/blockchain.py` — `_get_duplicate_rejection` reading
`duplicate_check["original_timestamp"]`

`_check_duplicate` returns three shapes. Two of them carry
`original_timestamp`; the pending-queue branch does not, because an unmined
entry has no block time to report. `_get_duplicate_rejection` indexed the key
unconditionally.

Reaching that branch requires the fingerprint registry to have *already*
forgotten the entry while the entry is still queued — that is, the dedup window
must expire before the entry is mined. With the defaults (3600s window, and a
node that mines on any cadence slower than hourly) that is not an edge case,
it is the steady state. The simulation hit it on day 24, the first time it
replayed an entry an hour after submitting it.

Through the REST API this is an unhandled exception, so a duplicate submission
returns a 500 rather than a rejection.

**Fix:** read the key with `.get()` and report which check matched via a new
`duplicate_source` field (`fingerprint_registry`, `mined_block`, or
`pending_queue`).

## 2. Rejected asset transfers leaked their reservation permanently

**Where:** `src/blockchain.py` — the `add_entry` pipeline, between
`_get_asset_transfer_rejection` and `_get_validation_rejection`

The asset check reserves the asset for transfer *before* Proof of Understanding
runs. Nothing released that reservation when validation subsequently rejected
the entry. The asset stayed marked "in transit" forever, and every later
transfer of it — including by its rightful owner — was refused with
`double_transfer`.

The stuck reservation is serialized into `chain.json` by
`AssetRegistry.to_dict()`, so it survives restarts. There is no expiry and no
API to clear it.

Triggering it needs nothing adversarial. The simulation used an entry reading
"transferred title in equipment EQ-… against an irrevocable letter of credit" —
ordinary trade-finance language that the validator's adversarial-pattern list
rejects on the word "irrevocable". One such entry permanently bricks the asset.

**Fix:** `_release_transfer_reservation()` cancels the reservation when
validation rejects the entry, matching on the entry's own fingerprint so it
only releases the reservation that entry took.

## 3. Entries accepted during mining were silently discarded

**Where:** `src/blockchain.py` — `mine_pending_entries`

The old sequence was: copy the pending queue, run proof-of-work, append the
block, then `self.pending_entries = []`. Meanwhile `add_entry` appended to that
same list without holding the mining lock. Anything accepted during the
proof-of-work window was neither in the block nor left pending — it was wiped by
the unconditional clear.

The submitter got `status: pending` and the entry's fingerprint was registered,
so an immediate resubmission was refused as a duplicate. The chain still
validated. Nothing anywhere reported a loss.

In the probe, **40 of 40** entries submitted during a single block's
proof-of-work vanished. This matters because the API is a Flask app: concurrent
submission during mining is the normal condition, not a contrived one.

**Fix:** swap the queue out under a short-held `_pending_lock` instead of
clearing it afterwards. Entries arriving during proof-of-work land in the fresh
list and are mined in the next block. Submissions are not blocked for the
duration of proof-of-work, and a failed or interrupted mine returns its entries
to the front of the queue rather than dropping them.

## 4. Encryption at rest was write-only

**Where:** `src/storage/json_file.py` — `_init_encryption`

`JSONFileStorage` encrypts the serialized (and optionally gzipped) payload,
which is *bytes*. It bound `encrypt_chain_data` / `decrypt_chain_data`, which
are declared over the chain **dictionary**. The two failure modes:

* compression on — `decrypt_chain_data` forces `return_type="json"` and fails
  outright trying to UTF-8 decode the gzip payload
* compression off — decryption returns a `dict`, which `load_chain` then treats
  as bytes and slices, raising `TypeError: unhashable type: 'slice'`

Either way, a node configured with `encryption_enabled=True` writes a ledger it
can never read back. `tests/test_encryption.py` passes because it exercises the
encryption module directly and never crosses the storage seam.

**Fix:** bind the byte-level primitives (`encrypt_data`, and `decrypt_data` with
`return_type="bytes"`) so the payload round-trips as the bytes it actually is.
Both compression modes now round-trip and the file on disk stays ciphertext.

## 5. High-impact verbs escaped detection at the end of a sentence

**Where:** `src/blockchain.py` — `MockValidator._detect_action_mismatch`

The check tokenized with `str.split()`, which leaves punctuation attached. The
token `"banned."` never matched the action word `"banned"`, so any restriction,
financial, or moderation verb sitting at the end of a sentence was invisible to
the intent-mismatch check.

Filed under an intent of "Update supplier profile record":

| Content | Before | After |
| --- | --- | --- |
| `…banned the supplier from the vendor portal today.` | `INVALID` | `INVALID` |
| `…reviewed the account and the supplier was banned.` | **`VALID`** | `INVALID` |

Same action, same mismatched intent, opposite outcome — decided by where the
period fell.

**Fix:** tokenize on word characters. The regression test also pins the
converse: `unbanned` and `reopened` must not register as `ban`/`open`.

## 6. Proof-of-work at the default difficulty offers no rewrite resistance

**Not a defect — a parameter worth stating.**

The probe took a copy of the year-end chain, edited a quantity in a block 40
deep, and re-mined every block from there to the head. It took **1.78 seconds**
(44 ms/block), and the rewritten chain then passed `validate_chain()` cleanly.
Rewriting the entire year of history extrapolates to about **12 seconds** on one
core.

Three things compound here:

* `mine_pending_entries` defaults to `difficulty=2` — roughly 256 hash attempts
  per block
* `validate_chain` defaults to `difficulty=1`, so it accepts blocks mined at a
  difficulty *lower* than the chain actually used, unless the caller passes the
  real value
* the core engine has no peer network and no fork-choice rule (`p2p_network.py`
  and `gossip_protocol.py` are in `_deferred/`), so nothing outside the node
  distinguishes a rewritten chain from the original

Tamper detection itself works: editing mined prose breaks the block hash, and
rehashing the tampered block breaks both linkage and proof-of-work. Both probes
pass. The gap is only that *re-mining* the tail is cheap. That is fine for a
single-node ledger with trusted storage, and not fine for anything where the
node operator is not trusted. Raising `difficulty` costs mining time
quadratically-ish (the year's mining cost 18s of CPU at difficulty 2), so it is
a knob, not a rewrite.

---

## What held up

Worth recording alongside the failures, because a year is a long time for these
to stay correct:

* **Chain integrity.** All 366 blocks hash-consistent, linked, and meeting
  difficulty at year end. Full-chain validation of 14,112 entries: 85 ms.
* **Restart recovery.** 12 monthly restarts from disk, every one with a matching
  head hash, intact asset ownership, preserved transfer history, and preserved
  derivative links.
* **Serialization.** Export/import round-trip byte-identical at year end.
* **Rate limiting.** Per-author cap held at 10/60s under a 120-entry burst;
  global cap held at 100/60s under a coordinated 200-entry burst from 80
  authors.
* **Double-spend prevention.** No asset ever ended up with an owner the ledger
  disagreed with; 0 ownership mismatches against an independently-kept book.
* **Deduplication memory.** The fingerprint registry stayed at single digits
  against 13,052 chain entries — expiry does collect.
* **Storage growth.** `chain.json` reached 1.05 MB gzipped for the year, about
  75 bytes per entry, with a 0.25s write.

## A note on the false-rejection rate

446 of 14,896 entries (3.0%) were rejected as `INVALID` for containing ordinary
commercial language — "non-refundable deposit", "minimum order", "perpetual
license", "irrevocable letter of credit". These are on
`MockValidator.ADVERSARIAL_PATTERNS`, matched as bare substrings.

This is a property of the mock validator, not of Proof of Understanding as
designed — the Anthropic-backed validator in `src/validator.py` would judge
these in context. But it is worth knowing that the fallback validator refuses a
measurable slice of legitimate contract prose, and that finding 2 above turned
one of those refusals into permanent asset loss.
