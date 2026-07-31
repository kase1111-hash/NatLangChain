#!/usr/bin/env python3
"""Run NatLangChain as a live ledger for a simulated year.

This drives the real engine — real hashing, real proof-of-work, real validation
pipeline, real registries, real JSON persistence — through 365 simulated days of
continuous operation. Only the clock is simulated (see ``virtual_clock.py``) so
that rate-limit windows, deduplication expiry, and timestamp-drift checks
experience a full year rather than a few seconds.

What the year contains:

* daily prose traffic from a ~60-actor supply-chain economy, with weekday
  seasonality, quarter-end spikes, and year-over-year growth
* one mined block per day at the configured proof-of-work difficulty
* weekly persistence snapshots and monthly node restarts from disk
* quarterly full-chain audits with timing captured as the chain grows
* a scheduled adversarial campaign: replay, backdating, metadata spoofing,
  Sybil flooding, double-spend, chain tampering, and history rewriting

Run::

    python -m simulations.year_simulation                 # full year
    python -m simulations.year_simulation --days 30       # quick pass
    python -m simulations.year_simulation --report out.md
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import statistics
import sys
import threading
import time as real_time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SIM_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, REPO_ROOT)

import blockchain as bc  # noqa: E402
from blockchain import (  # noqa: E402
    MockValidator,
    NatLangChain,
    NaturalLanguageEntry,
    compute_entry_fingerprint,
)
from simulations.virtual_clock import VirtualClock, virtual_time  # noqa: E402
from simulations.workload import MinedRef, WorkloadGenerator  # noqa: E402
from storage.json_file import JSONFileStorage  # noqa: E402

DAY_SECONDS = 86400
YEAR_START = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()  # noqa: UP017


# ==========================================================================
# Configuration and results
# ==========================================================================


@dataclass
class SimConfig:
    days: int = 365
    seed: int = 20260101
    difficulty: int = 2
    base_entries_per_day: int = 38
    growth_rate: float = 0.55  # fractional volume growth across the year
    snapshot_every: int = 7
    restart_every: int = 30
    audit_every: int = 91
    workdir: str = ""
    rewrite_probe_blocks: int = 40


@dataclass
class Incident:
    """One adversarial or operational probe with a stated expectation."""

    day: int
    name: str
    expectation: str
    outcome: str
    passed: bool
    detail: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class DayRecord:
    day: int
    date: str
    submitted: int = 0
    accepted: int = 0
    rejected: int = 0
    block_index: int | None = None
    block_entries: int = 0
    mine_seconds: float = 0.0
    nonce: int = 0
    rejections: dict = field(default_factory=dict)


# ==========================================================================
# Simulation driver
# ==========================================================================


class YearSimulation:
    def __init__(self, config: SimConfig):
        self.cfg = config
        self.clock = VirtualClock(YEAR_START)
        self.gen = WorkloadGenerator(seed=config.seed)
        self.validator = MockValidator()

        self.chain: NatLangChain | None = None
        self.storage: JSONFileStorage | None = None

        self.days: list[DayRecord] = []
        self.incidents: list[Incident] = []
        self.audits: list[dict] = []
        self.snapshots: list[dict] = []
        self.restarts: list[dict] = []
        self.mined_refs: list[MinedRef] = []
        self.rejection_totals: dict[str, int] = {}
        self.class_outcomes: dict[str, dict[str, int]] = {}
        self.pending_by_day: list[int] = []
        self.notes: list[str] = []
        self.engine_faults: list[dict] = []

        self._accepted_this_day: list[tuple[NaturalLanguageEntry, str]] = []
        self._schedule_cache: dict[int, Any] | None = None
        self.validation_decisions: dict[str, int] = {}

    # -- fault-tolerant engine calls ---------------------------------------
    def _add_entry(self, entry: NaturalLanguageEntry) -> dict:
        """Submit an entry, recording engine crashes instead of dying on them.

        A node that runs for a year has to survive its own bugs, and a test that
        runs for a year has to record them rather than abort. An uncaught
        exception out of ``add_entry`` is exactly what the API layer would turn
        into a 500, so it is captured as a fault and the day continues.
        """
        try:
            return self.chain.add_entry(entry)
        except Exception as exc:
            frames = traceback.extract_tb(exc.__traceback__)
            where = f"{os.path.basename(frames[-1].filename)}:{frames[-1].lineno}" if frames else "?"
            fault = {
                "day": len(self.days) + 1,
                "author": entry.author,
                "intent": entry.intent,
                "exception": type(exc).__name__,
                "message": str(exc),
                "location": where,
                "source_line": frames[-1].line if frames else "",
            }
            self.engine_faults.append(fault)
            return {
                "status": "engine_fault",
                "reason": "engine_fault",
                "error": f"{type(exc).__name__}: {exc}",
                "fault": fault,
                "entry": entry.to_dict(),
            }

    # -- setup -------------------------------------------------------------
    def _new_chain(self) -> NatLangChain:
        return NatLangChain(
            require_validation=True,
            validator=self.validator,
            allow_needs_clarification=False,
            enable_deduplication=True,
            enable_rate_limiting=True,
            enable_timestamp_validation=True,
            enable_metadata_sanitization=True,
            enable_asset_tracking=True,
            enable_quality_checks=True,
            enable_derivative_tracking=True,
        )

    # -- main loop ---------------------------------------------------------
    def run(self) -> dict:
        # The engine logs every rejection; the simulation counts them itself and
        # would otherwise emit tens of thousands of lines over a year.
        logging.getLogger("blockchain").setLevel(logging.ERROR)

        os.makedirs(self.cfg.workdir, exist_ok=True)
        chain_path = os.path.join(self.cfg.workdir, "chain.json")
        self.storage = JSONFileStorage(
            file_path=chain_path, encryption_enabled=False, compression_enabled=True
        )

        wall_start = real_time.perf_counter()
        with virtual_time(bc, self.clock):
            self.chain = self._new_chain()
            self._note(
                f"Genesis block created at virtual {self.clock.date_str()} "
                f"with hash {self.chain.chain[0].hash[:16]}."
            )

            for day in range(1, self.cfg.days + 1):
                self._run_day(day)

            final = self._final_audit()

        wall_seconds = real_time.perf_counter() - wall_start
        return self._assemble_results(final, wall_seconds)

    def _run_day(self, day: int) -> None:
        record = DayRecord(day=day, date=self.clock.date_str())
        self._accepted_this_day = []

        count = self._volume_for_day(day)
        parents = self.mined_refs
        drafts = self.gen.day_drafts(day, count, parents)

        # A few new tracked assets enter the economy each week.
        if day % 5 == 0:
            reg_draft, asset_id, owner = self.gen.asset_registration(day)
            drafts.insert(0, reg_draft)
            self.chain._asset_registry.register_asset(asset_id, owner)
            self.gen.assets[asset_id] = owner

        # Spread the day's submissions across the simulated 24 hours.
        step = DAY_SECONDS / (len(drafts) + 1)
        for draft in drafts:
            self.clock.advance(step)
            self._submit(draft, record)

        # Scheduled adversarial and operational probes run inside the day.
        self._run_scheduled_probes(day)

        # End of day: mine everything pending into one block.
        self.pending_by_day.append(len(self.chain.pending_entries))
        self._mine_day(day, record)

        self.clock.advance(max(0.0, DAY_SECONDS - (step * (len(drafts) + 1))))
        self.days.append(record)

        if day % self.cfg.snapshot_every == 0:
            self._snapshot(day)
        if day % self.cfg.restart_every == 0:
            self._restart_node(day)
        if day % self.cfg.audit_every == 0 or day == self.cfg.days:
            self._quarterly_audit(day)

    def _volume_for_day(self, day: int) -> int:
        """Entry volume with weekday seasonality, growth, and quarter-end spikes."""
        rng = self.gen.rng
        weekday = (day - 1) % 7
        seasonal = 0.35 if weekday >= 5 else 1.0
        growth = 1.0 + self.cfg.growth_rate * (day / max(1, self.cfg.days))
        spike = 1.9 if day % 91 in (88, 89, 90, 0) else 1.0
        base = self.cfg.base_entries_per_day * seasonal * growth * spike
        jitter = rng.uniform(0.75, 1.25)
        return max(3, int(base * jitter))

    def _submit(self, draft, record: DayRecord) -> dict:
        entry = NaturalLanguageEntry(
            content=draft.content,
            author=draft.author,
            intent=draft.intent,
            metadata=dict(draft.metadata),
            parent_refs=list(draft.parent_refs),
            derivative_type=draft.derivative_type,
        )
        result = self._add_entry(entry)
        record.submitted += 1

        cls = self.class_outcomes.setdefault(
            draft.traffic_class, {"submitted": 0, "accepted": 0, "rejected": 0}
        )
        cls["submitted"] += 1

        if result.get("status") == "pending":
            record.accepted += 1
            cls["accepted"] += 1
            self._accepted_this_day.append((entry, draft.kind))
            if draft.kind == "asset_transfer":
                asset_id = draft.metadata.get("asset_id")
                recipient = draft.metadata.get("recipient")
                if asset_id and recipient:
                    self.gen.assets[asset_id] = recipient
        else:
            record.rejected += 1
            cls["rejected"] += 1
            decision = result.get("validation_decision")
            reason = result.get("reason") or (
                f"validation:{decision}" if decision else result.get("status", "unknown")
            )
            if decision:
                self.validation_decisions[decision] = (
                    self.validation_decisions.get(decision, 0) + 1
                )
            record.rejections[reason] = record.rejections.get(reason, 0) + 1
            self.rejection_totals[reason] = self.rejection_totals.get(reason, 0) + 1
        return result

    def _mine_day(self, day: int, record: DayRecord) -> None:
        pending_count = len(self.chain.pending_entries)
        if pending_count == 0:
            return
        start = real_time.perf_counter()
        block = self.chain.mine_pending_entries(difficulty=self.cfg.difficulty)
        record.mine_seconds = real_time.perf_counter() - start
        if block is None:
            return
        record.block_index = block.index
        record.block_entries = len(block.entries)
        record.nonce = block.nonce

        # Remember where each accepted entry landed so later entries can cite it.
        for idx, entry in enumerate(block.entries):
            kind = "unknown"
            for cand, cand_kind in self._accepted_this_day:
                if cand is entry:
                    kind = cand_kind
                    break
            self.mined_refs.append(
                MinedRef(
                    block_index=block.index,
                    entry_index=idx,
                    author=entry.author,
                    intent=entry.intent,
                    kind=kind,
                    day=day,
                )
            )

    # -- operations --------------------------------------------------------
    def _snapshot(self, day: int) -> None:
        data = self.chain.to_dict()
        raw_bytes = len(json.dumps(data).encode("utf-8"))
        start = real_time.perf_counter()
        self.storage.save_chain(data)
        save_seconds = real_time.perf_counter() - start
        size = os.path.getsize(self.storage.file_path)
        self.snapshots.append(
            {
                "day": day,
                "blocks": len(self.chain.chain),
                "entries": sum(len(b.entries) for b in self.chain.chain),
                "bytes": size,
                "raw_json_bytes": raw_bytes,
                "save_seconds": round(save_seconds, 4),
            }
        )

    def _restart_node(self, day: int) -> None:
        """Simulate an operator restarting the node from persisted state."""
        pre_head = self.chain.get_latest_block().hash
        pre_blocks = len(self.chain.chain)
        pre_entries = sum(len(b.entries) for b in self.chain.chain)
        pre_owners = dict(self.chain._asset_registry._ownership)
        pre_pending_transfers = dict(self.chain._asset_registry._pending_transfers)
        pre_derivative_parents = len(self.chain._derivative_registry._parents)
        pre_fingerprints = len(self.chain._entry_fingerprints)

        self.storage.save_chain(self.chain.to_dict())
        loaded = self.storage.load_chain()

        start = real_time.perf_counter()
        restored = NatLangChain.from_dict(
            loaded,
            require_validation=True,
            validator=self.validator,
        )
        load_seconds = real_time.perf_counter() - start

        valid = restored.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        head_match = restored.get_latest_block().hash == pre_head
        owners_match = restored._asset_registry._ownership == pre_owners
        pending_match = set(restored._asset_registry._pending_transfers) == set(
            pre_pending_transfers
        )
        derivatives_match = len(restored._derivative_registry._parents) == pre_derivative_parents
        fingerprints_match = len(restored._entry_fingerprints) == pre_fingerprints
        history_preserved = len(restored._asset_registry.get_transfer_history()) == len(
            self.chain._asset_registry.get_transfer_history()
        )

        self.restarts.append(
            {
                "day": day,
                "blocks": pre_blocks,
                "entries": pre_entries,
                "load_seconds": round(load_seconds, 4),
                "chain_valid": valid,
                "head_hash_match": head_match,
                "ownership_match": owners_match,
                "pending_transfers_match": pending_match,
                "derivatives_match": derivatives_match,
                "fingerprints_match": fingerprints_match,
                "transfer_history_preserved": history_preserved,
                "quality_config_preserved": restored.max_entry_size == self.chain.max_entry_size,
            }
        )

        if not history_preserved:
            self._record(
                day,
                "restart_transfer_history",
                "asset transfer history survives a restart",
                f"history lost: {len(self.chain._asset_registry.get_transfer_history())} entries "
                f"before restart, {len(restored._asset_registry.get_transfer_history())} after",
                passed=False,
            )

        # The restored node becomes the live node, exactly as in a real restart.
        self.chain = restored

    def _quarterly_audit(self, day: int) -> None:
        start = real_time.perf_counter()
        valid = self.chain.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        validate_seconds = real_time.perf_counter() - start

        start = real_time.perf_counter()
        narrative = self.chain.get_full_narrative()
        narrative_seconds = real_time.perf_counter() - start

        sample_author = self.mined_refs[-1].author if self.mined_refs else "system"
        start = real_time.perf_counter()
        by_author = self.chain.get_entries_by_author(sample_author)
        author_seconds = real_time.perf_counter() - start

        start = real_time.perf_counter()
        by_intent = self.chain.get_entries_by_intent("delivery")
        intent_seconds = real_time.perf_counter() - start

        entries = sum(len(b.entries) for b in self.chain.chain)
        self.audits.append(
            {
                "day": day,
                "blocks": len(self.chain.chain),
                "entries": entries,
                "chain_valid": valid,
                "validate_seconds": round(validate_seconds, 4),
                "narrative_seconds": round(narrative_seconds, 4),
                "narrative_chars": len(narrative),
                "author_query_seconds": round(author_seconds, 4),
                "author_query_hits": len(by_author),
                "intent_query_seconds": round(intent_seconds, 4),
                "intent_query_hits": len(by_intent),
                "fingerprints_held": len(self.chain._entry_fingerprints),
                "assets_tracked": len(self.chain._asset_registry._ownership),
                "transfers_pending": len(self.chain._asset_registry._pending_transfers),
                "derivative_links": len(self.chain._derivative_registry._parents),
            }
        )

    # ------------------------------------------------------------------
    # Adversarial and operational probes
    # ------------------------------------------------------------------
    def _probe_schedule(self) -> dict[int, Any]:
        """Probe calendar, rescaled if the run is shorter than a full year.

        A short run still exercises every probe, in the same order, spread across
        whatever horizon was requested.
        """
        if self._schedule_cache is not None:
            return self._schedule_cache

        calendar = self._probe_calendar()
        if self.cfg.days >= 365:
            self._schedule_cache = calendar
            return calendar

        scale = self.cfg.days / 365
        scaled: dict[int, Any] = {}
        for canonical_day in sorted(calendar):
            target = max(1, min(self.cfg.days, round(canonical_day * scale)))
            while target in scaled and target < self.cfg.days:
                target += 1
            while target in scaled and target > 1:
                target -= 1
            scaled[target] = calendar[canonical_day]
        self._schedule_cache = scaled
        return scaled

    def _run_scheduled_probes(self, day: int) -> None:
        probe = self._probe_schedule().get(day)
        if probe is not None:
            probe(day)

    def _probe_calendar(self) -> dict[int, Any]:
        return {
            23: self._probe_replay_immediate,
            24: self._probe_replay_after_window,
            47: self._probe_backdating,
            48: self._probe_future_dating,
            61: self._probe_metadata_spoofing,
            90: self._probe_sybil_flood,
            91: self._probe_global_flood,
            118: self._probe_double_spend,
            119: self._probe_transfer_not_owned,
            150: self._probe_bloat,
            151: self._probe_undersized,
            181: self._probe_tamper_detection,
            182: self._probe_tamper_with_rehash,
            210: self._probe_action_intent_mismatch,
            211: self._probe_punctuation_evasion,
            240: self._probe_adversarial_language,
            255: self._probe_asset_lock_leak,
            270: self._probe_history_rewrite,
            300: self._probe_encrypted_persistence,
            330: self._probe_concurrent_mining,
            345: self._probe_fingerprint_growth,
        }

    def _record(
        self, day: int, name: str, expectation: str, outcome: str, passed: bool, **data
    ) -> None:
        self.incidents.append(
            Incident(
                day=day,
                name=name,
                expectation=expectation,
                outcome=outcome,
                passed=passed,
                data=data,
            )
        )

    def _note(self, text: str) -> None:
        self.notes.append(text)

    # -- replay ------------------------------------------------------------
    def _probe_replay_immediate(self, day: int) -> None:
        entry = NaturalLanguageEntry(
            content=(
                "harbor_plastics agreed to supply 1200 injection-molded housings to "
                "atlas_transit under purchase order PO-REPLAY-01. Delivery is due at the "
                "Portland depot with payment on receipt."
            ),
            author="harbor_plastics",
            intent="Supply agreement signed for purchase order PO-REPLAY-01",
        )
        first = self._add_entry(entry)
        replay = NaturalLanguageEntry(
            content=entry.content, author=entry.author, intent=entry.intent
        )
        second = self._add_entry(replay)
        blocked = second.get("status") == "rejected" and second.get("reason") == "duplicate"
        self._record(
            day,
            "replay_within_dedup_window",
            "an identical resubmission inside the 1h window is rejected as a duplicate",
            f"first={first.get('status')}, replay={second.get('status')}/{second.get('reason')}",
            passed=blocked and first.get("status") == "pending",
        )

    def _probe_replay_after_window(self, day: int) -> None:
        content = (
            "granite_tooling agreed to supply 640 precision bearings to lumen_medical "
            "under purchase order PO-REPLAY-02. Delivery is due at the Ashford yard "
            "with payment on receipt."
        )
        intent = "Supply agreement signed for purchase order PO-REPLAY-02"
        first = self._add_entry(
            NaturalLanguageEntry(content=content, author="granite_tooling", intent=intent)
        )
        # Wait out the deduplication window, then replay the exact same prose.
        # The original entry is still sitting in the pending queue, because this
        # node mines once a day and the dedup window is one hour.
        self.clock.advance(self.chain.dedup_window_seconds + 120)
        second = self._add_entry(
            NaturalLanguageEntry(content=content, author="granite_tooling", intent=intent)
        )
        crashed = second.get("status") == "engine_fault"
        rejected = second.get("status") == "rejected"
        self._record(
            day,
            "replay_of_still_pending_entry",
            "replaying an entry that is still in the pending queue is rejected cleanly",
            f"first={first.get('status')}; replay one hour later="
            f"{second.get('status')}"
            + (f" ({second.get('error')})" if crashed else f"/{second.get('reason')}"),
            passed=rejected and not crashed,
            crashed=crashed,
            error=second.get("error"),
            fault=second.get("fault"),
        )
        if crashed:
            self._note(
                "NatLangChain._get_duplicate_rejection reads duplicate_check"
                "['original_timestamp'] unconditionally, but _check_duplicate's "
                "pending-queue branch returns a dict without that key. Once the "
                "deduplication window (3600s) expires while an entry is still "
                "unmined — the normal state of affairs on a node that mines less "
                "often than hourly — resubmitting that entry raises KeyError out of "
                "add_entry(). Through the REST API that is an unhandled 500."
            )

    # -- clock attacks -----------------------------------------------------
    def _probe_backdating(self, day: int) -> None:
        entry = NaturalLanguageEntry(
            content=(
                "meridian_castings agreed to supply 300 steel weldments to "
                "pinnacle_aerospace at a price fixed before the tariff change took effect."
            ),
            author="meridian_castings",
            intent="Supply agreement signed at the pre-tariff price",
        )
        backdated = self.clock.utcnow() - timedelta(days=45)
        entry.timestamp = backdated.isoformat()
        result = self._add_entry(entry)
        rejected = result.get("status") == "rejected" and result.get("reason") == "invalid_timestamp"
        self._record(
            day,
            "backdating_45_days",
            "an entry stamped 45 days in the past is rejected",
            f"{result.get('status')}/{result.get('reason')}",
            passed=rejected,
            drift_seconds=result.get("timestamp_details", {}).get("drift_seconds"),
        )

    def _probe_future_dating(self, day: int) -> None:
        entry = NaturalLanguageEntry(
            content=(
                "quarry_composites agreed to supply 900 carbon fiber panels to "
                "nimbus_drones with the delivery window opening next quarter."
            ),
            author="quarry_composites",
            intent="Supply agreement signed for next quarter delivery",
        )
        entry.timestamp = (self.clock.utcnow() + timedelta(hours=6)).isoformat()
        result = self._add_entry(entry)
        rejected = result.get("status") == "rejected" and result.get("reason") == "invalid_timestamp"
        self._record(
            day,
            "future_dating_6_hours",
            "an entry stamped 6 hours in the future is rejected",
            f"{result.get('status')}/{result.get('reason')}",
            passed=rejected,
        )

    # -- metadata ----------------------------------------------------------
    def _probe_metadata_spoofing(self, day: int) -> None:
        entry = NaturalLanguageEntry(
            content=(
                "kestrel_optics registered equipment EQ-SPOOF-01, a coating line "
                "commissioned this quarter and held at the Riverbend hub with a full "
                "service plan."
            ),
            author="kestrel_optics",
            intent="Register new equipment asset EQ-SPOOF-01",
            metadata={
                "validation_status": "validated",
                "trust_score": 1.0,
                "__admin__": True,
                "block_index": 0,
                "legitimate_field": "keep me",
            },
        )
        result = self._add_entry(entry)
        stored = result.get("entry", {}).get("metadata", {})
        stripped = [
            f
            for f in ("validation_status", "trust_score", "__admin__", "block_index")
            if f not in stored
        ]
        self._record(
            day,
            "metadata_spoofing",
            "reserved metadata fields are stripped, legitimate fields survive",
            f"stripped {len(stripped)}/4 reserved fields; legitimate_field kept="
            f"{stored.get('legitimate_field') == 'keep me'}",
            passed=len(stripped) == 4 and stored.get("legitimate_field") == "keep me",
            remaining_metadata=stored,
        )

    # -- flooding ----------------------------------------------------------
    def _probe_sybil_flood(self, day: int) -> None:
        accepted = 0
        rejected = 0
        reasons: dict[str, int] = {}
        for i in range(120):
            entry = NaturalLanguageEntry(
                content=(
                    f"delta_bearings registered permit PMT-FLOOD-{i:03d} granting site "
                    f"access for freight movement through the end of the month at the "
                    f"Northgate receiving dock."
                ),
                author="delta_bearings",
                intent=f"Register new permit PMT-FLOOD-{i:03d} for freight movement",
            )
            result = self._add_entry(entry)
            if result.get("status") == "pending":
                accepted += 1
            else:
                rejected += 1
                reason = result.get("reason", "unknown")
                reasons[reason] = reasons.get(reason, 0) + 1
        limiter = self.chain._rate_limiter
        self._record(
            day,
            "sybil_flood_120_entries",
            "a 120-entry burst from one author in one instant is rate limited",
            f"{accepted} accepted, {rejected} rejected ({reasons})",
            passed=accepted <= limiter.max_per_author and rejected > 0,
            accepted=accepted,
            rejected=rejected,
            max_per_author=limiter.max_per_author,
            reasons=reasons,
        )

    def _probe_global_flood(self, day: int) -> None:
        """Many authors at once — tests the global cap, not the per-author cap."""
        from simulations.workload import BUYERS, SUPPLIERS

        authors = (SUPPLIERS + BUYERS) * 4
        accepted = 0
        rejected = 0
        reasons: dict[str, int] = {}
        for i, author in enumerate(authors[:200]):
            result = self._add_entry(
                NaturalLanguageEntry(
                    content=(
                        f"{author} registered permit PMT-GLOBAL-{i:03d} covering site "
                        f"access for the coordinated freight window at the Dockside "
                        f"terminal this month."
                    ),
                    author=author,
                    intent=f"Register new permit PMT-GLOBAL-{i:03d} for freight access",
                )
            )
            if result.get("status") == "pending":
                accepted += 1
            else:
                rejected += 1
                reason = result.get("reason", "unknown")
                reasons[reason] = reasons.get(reason, 0) + 1
        limiter = self.chain._rate_limiter
        self._record(
            day,
            "global_flood_200_entries_80_authors",
            "a coordinated 200-entry burst is capped by the global rate limit",
            f"{accepted} accepted, {rejected} rejected ({reasons}); "
            f"global cap is {limiter.max_global} per {limiter.window_seconds}s",
            passed=accepted <= limiter.max_global and rejected > 0,
            accepted=accepted,
            rejected=rejected,
            max_global=limiter.max_global,
        )

    # -- assets ------------------------------------------------------------
    def _probe_double_spend(self, day: int) -> None:
        asset_id = "EQ-DOUBLESPEND-01"
        owner = "ironwood_millwork"
        self.chain._asset_registry.register_asset(asset_id, owner)
        first = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    f"{owner} transferred title in equipment {asset_id} to "
                    f"juniper_furniture following the sale agreed this week. The unit "
                    f"ships from the Ashford yard after final inspection."
                ),
                author=owner,
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "juniper_furniture"},
            )
        )
        second = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    f"{owner} transferred title in equipment {asset_id} to "
                    f"coastal_energy following a separate sale agreed the same week. "
                    f"The unit ships from the Ashford yard after final inspection."
                ),
                author=owner,
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "coastal_energy"},
            )
        )
        blocked = second.get("status") == "rejected" and second.get("reason") == "double_transfer"
        self._record(
            day,
            "double_spend_same_queue",
            "selling the same asset twice before mining is rejected",
            f"first={first.get('status')}, second={second.get('status')}/{second.get('reason')}",
            passed=blocked and first.get("status") == "pending",
        )
        if first.get("status") == "pending":
            self.gen.assets[asset_id] = "juniper_furniture"

    def _probe_transfer_not_owned(self, day: int) -> None:
        asset_id = "EQ-NOTOWNED-01"
        self.chain._asset_registry.register_asset(asset_id, "solstice_electronics")
        result = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    f"blue_ridge_fabrication transferred title in equipment {asset_id} to "
                    f"seabright_marine under a bill of sale dated this week, shipping "
                    f"from the Calloway pier."
                ),
                author="blue_ridge_fabrication",
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "seabright_marine"},
            )
        )
        blocked = result.get("status") == "rejected" and result.get("reason") == "double_transfer"
        owner_intact = self.chain._asset_registry.get_owner(asset_id) == "solstice_electronics"
        self._record(
            day,
            "transfer_by_non_owner",
            "a non-owner cannot transfer a registered asset",
            f"{result.get('status')}/{result.get('reason')}; owner still "
            f"{self.chain._asset_registry.get_owner(asset_id)}",
            passed=blocked and owner_intact,
        )

    def _probe_asset_lock_leak(self, day: int) -> None:
        """A transfer that clears the asset check but fails validation.

        The reservation is taken before validation runs. If validation then
        rejects the entry, nothing releases the reservation.
        """
        asset_id = "EQ-LOCKLEAK-01"
        owner = "tallgrass_textiles"
        self.chain._asset_registry.register_asset(asset_id, owner)

        # Legitimate commercial language ("irrevocable letter of credit") that the
        # validator's adversarial-pattern list rejects.
        rejected = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    f"{owner} transferred title in equipment {asset_id} to "
                    f"silverpine_packaging against an irrevocable letter of credit "
                    f"issued by the buyer's bank this week."
                ),
                author=owner,
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "silverpine_packaging"},
            )
        )
        still_reserved = self.chain._asset_registry.has_pending_transfer(asset_id)

        # Now the owner retries with clean prose. It should succeed.
        retry = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    f"{owner} transferred title in equipment {asset_id} to "
                    f"silverpine_packaging under a bill of sale countersigned at the "
                    f"quarterly review, shipping from the Riverbend hub."
                ),
                author=owner,
                intent=f"Transfer of ownership in asset {asset_id}",
                metadata={"asset_id": asset_id, "recipient": "silverpine_packaging"},
            )
        )
        retry_blocked = retry.get("status") == "rejected"
        self._record(
            day,
            "asset_lock_leak_after_validation_failure",
            "a rejected transfer releases its asset reservation so the owner can retry",
            f"rejected={rejected.get('status')}/{rejected.get('validation_decision')}; "
            f"reservation still held={still_reserved}; clean retry={retry.get('status')}"
            f"/{retry.get('reason')}",
            passed=not still_reserved and not retry_blocked,
            reservation_leaked=still_reserved,
            retry_blocked=retry_blocked,
            pending_transfer=self.chain._asset_registry.get_pending_transfer(asset_id),
        )
        if still_reserved and retry_blocked:
            self._note(
                "Asset reservations are taken before Proof of Understanding runs and are "
                "never released when validation rejects the entry. The asset is left "
                "permanently 'in transit' and the rightful owner can no longer transfer it. "
                "The stuck reservation is serialized into chain.json and survives restarts."
            )

    # -- bloat -------------------------------------------------------------
    def _probe_bloat(self, day: int) -> None:
        filler = (
            "The parties confirm the schedule attached to the master terms and "
            "reaffirm the delivery obligations recorded for this quarter. "
        )
        content = (
            "orchard_appliance agreed to supply parts under the annual framework. "
            + filler * 400
        )
        result = self._add_entry(
            NaturalLanguageEntry(
                content=content,
                author="orchard_appliance",
                intent="Supply agreement signed under the annual framework",
            )
        )
        rejected = result.get("status") in ("rejected", "needs_revision")
        self._record(
            day,
            "chain_bloat_oversized_entry",
            f"an entry of {len(content):,} characters is refused",
            f"{result.get('status')}/{result.get('reason')} "
            f"(quality score {result.get('quality_score')})",
            passed=rejected,
            size=len(content),
        )

    def _probe_undersized(self, day: int) -> None:
        result = self._add_entry(
            NaturalLanguageEntry(content="ok", author="foxglove_labs", intent="Note")
        )
        rejected = result.get("status") in ("rejected", "needs_revision")
        self._record(
            day,
            "undersized_entry",
            "a two-character entry is refused",
            f"{result.get('status')}/{result.get('reason')}",
            passed=rejected,
        )

    # -- tampering ---------------------------------------------------------
    def _clone_chain(self) -> NatLangChain:
        return NatLangChain.from_dict(
            copy.deepcopy(self.chain.to_dict()),
            require_validation=False,
            validator=self.validator,
        )

    def _probe_tamper_detection(self, day: int) -> None:
        clone = self._clone_chain()
        baseline = clone.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        target_block = len(clone.chain) // 2
        entry = clone.chain[target_block].entries[0]
        original = entry.content
        entry.content = original.replace("agreed", "never agreed", 1) + " Amount doubled."
        detected = not clone.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        entry.content = original
        restored = clone.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        self._record(
            day,
            "silent_content_tamper",
            "editing mined prose breaks the block hash and is detected",
            f"clone valid before={baseline}, tamper detected={detected}, "
            f"valid after restore={restored}",
            passed=baseline and detected and restored,
            tampered_block=target_block,
        )

    def _probe_tamper_with_rehash(self, day: int) -> None:
        """Attacker edits an entry and recomputes that block's own hash."""
        clone = self._clone_chain()
        target_block = len(clone.chain) // 2
        block = clone.chain[target_block]
        block.entries[0].content += " The balance is settled in full."
        block.hash = block.calculate_hash()
        detected = not clone.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        # Which check caught it: linkage, or proof-of-work?
        next_block = clone.chain[target_block + 1]
        linkage_broken = next_block.previous_hash != block.hash
        pow_broken = not block.hash.startswith("0" * self.cfg.difficulty)
        self._record(
            day,
            "tamper_with_self_rehash",
            "rehashing the tampered block still fails linkage and proof-of-work",
            f"detected={detected}; linkage broken={linkage_broken}; "
            f"proof-of-work broken={pow_broken}",
            passed=detected,
            tampered_block=target_block,
        )

    def _probe_history_rewrite(self, day: int) -> None:
        """Measure how expensive it is to rewrite the tail of the ledger."""
        clone = self._clone_chain()
        depth = min(self.cfg.rewrite_probe_blocks, max(1, len(clone.chain) - 2))
        start_index = len(clone.chain) - depth
        clone.chain[start_index].entries[0].content += (
            " The recorded quantity is amended to 10,000 units."
        )

        start = real_time.perf_counter()
        target = "0" * self.cfg.difficulty
        for i in range(start_index, len(clone.chain)):
            blk = clone.chain[i]
            if i > 0:
                blk.previous_hash = clone.chain[i - 1].hash
            blk.nonce = 0
            blk.hash = blk.calculate_hash()
            while not blk.hash.startswith(target):
                blk.nonce += 1
                blk.hash = blk.calculate_hash()
        rewrite_seconds = real_time.perf_counter() - start

        now_valid = clone.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        per_block = rewrite_seconds / depth
        full_chain_estimate = per_block * len(self.chain.chain)
        self._record(
            day,
            "history_rewrite_cost",
            "rewriting mined history should be computationally prohibitive",
            f"rewrote {depth} blocks in {rewrite_seconds:.2f}s "
            f"({per_block * 1000:.0f} ms/block); rewritten chain passes validate_chain="
            f"{now_valid}; whole-chain rewrite would take about "
            f"{full_chain_estimate:.1f}s on one core",
            # A rewritten chain that still validates means proof-of-work bought
            # nothing at this difficulty.
            passed=not now_valid,
            depth=depth,
            rewrite_seconds=round(rewrite_seconds, 3),
            seconds_per_block=round(per_block, 5),
            full_chain_estimate_seconds=round(full_chain_estimate, 2),
            difficulty=self.cfg.difficulty,
            rewritten_chain_validates=now_valid,
        )
        if now_valid:
            self._note(
                f"Proof-of-work at difficulty {self.cfg.difficulty} provides no meaningful "
                f"rewrite resistance. A tampered copy of a full year of history re-mines "
                f"and passes validate_chain() in roughly {full_chain_estimate:.1f} seconds "
                f"on a single core. With no peer network or fork-choice rule in the core "
                f"engine, nothing else distinguishes the rewritten chain from the original."
            )

    # -- validator behaviour -----------------------------------------------
    def _probe_action_intent_mismatch(self, day: int) -> None:
        result = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    "verdant_agritech banned the supplier from the vendor portal and "
                    "removed all open purchase orders from the account."
                ),
                author="verdant_agritech",
                intent="Update supplier profile record",
            )
        )
        blocked = result.get("status") == "rejected"
        self._record(
            day,
            "action_intent_mismatch",
            "a restriction action filed under a profile-update intent is rejected",
            f"{result.get('status')}/{result.get('validation_decision')}",
            passed=blocked,
        )

    def _probe_punctuation_evasion(self, day: int) -> None:
        """The same restriction, with the action verb ending the sentence."""
        result = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    "verdant_agritech reviewed the vendor portal account and the "
                    "supplier was banned."
                ),
                author="verdant_agritech",
                intent="Update supplier profile record",
            )
        )
        evaded = result.get("status") == "pending"
        self._record(
            day,
            "action_mismatch_punctuation_evasion",
            "the same restriction action is still caught when the verb ends a sentence",
            f"{result.get('status')}/{result.get('validation_decision')}",
            passed=not evaded,
            accepted=evaded,
        )
        if evaded:
            self._note(
                "MockValidator._detect_action_mismatch tokenises with str.split() and never "
                "strips punctuation, so the token 'banned.' never matches the action word "
                "'banned'. Ending the sentence on the high-impact verb bypasses the "
                "intent-mismatch check entirely: 'the supplier was banned.' filed under a "
                "'Update supplier profile record' intent is accepted, while the identical "
                "action mid-sentence is rejected."
            )

    def _probe_adversarial_language(self, day: int) -> None:
        result = self._add_entry(
            NaturalLanguageEntry(
                content=(
                    "wavelength_audio agreed that the counterparty waives all rights to "
                    "dispute the charges recorded under this account."
                ),
                author="wavelength_audio",
                intent="Supply agreement signed covering dispute handling",
            )
        )
        blocked = result.get("status") == "rejected"
        self._record(
            day,
            "adversarial_language",
            "a rights-waiver clause is rejected by Proof of Understanding",
            f"{result.get('status')}/{result.get('validation_decision')}",
            passed=blocked,
        )

    # -- persistence -------------------------------------------------------
    def _probe_encrypted_persistence(self, day: int) -> None:
        # An operator turning on encryption at rest supplies a key by environment.
        key_var = "NATLANGCHAIN_ENCRYPTION_KEY"
        previous_key = os.environ.get(key_var)
        os.environ[key_var] = "simulation-year-key-0123456789abcdef"

        data = self.chain.to_dict()
        outcomes: dict[str, str] = {}
        recovered: dict[str, bool] = {}
        try:
            for compression in (True, False):
                label = "compressed" if compression else "uncompressed"
                enc_path = os.path.join(self.cfg.workdir, f"chain_encrypted_{label}.json")
                try:
                    store = JSONFileStorage(
                        file_path=enc_path,
                        encryption_enabled=True,
                        compression_enabled=compression,
                    )
                    if not store.encryption_enabled:
                        outcomes[label] = "storage silently disabled encryption"
                        recovered[label] = False
                        continue
                    store.save_chain(data)
                    with open(enc_path, "rb") as fh:
                        head = fh.read(64)
                    if not head.startswith(b"ENC:"):
                        outcomes[label] = f"file is not ciphertext (starts {head[:8]!r})"
                        recovered[label] = False
                        continue
                    loaded = store.load_chain()
                    restored = NatLangChain.from_dict(loaded, require_validation=False)
                    ok = (
                        restored.validate_chain(
                            verify_pow=True, difficulty=self.cfg.difficulty
                        )
                        and restored.get_latest_block().hash
                        == self.chain.get_latest_block().hash
                    )
                    outcomes[label] = "round-trip ok" if ok else "reloaded chain does not match"
                    recovered[label] = ok
                except Exception as exc:
                    outcomes[label] = f"{type(exc).__name__}: {exc}"
                    recovered[label] = False
        finally:
            if previous_key is None:
                os.environ.pop(key_var, None)
            else:
                os.environ[key_var] = previous_key

        all_ok = all(recovered.values())
        self._record(
            day,
            "encrypted_persistence",
            "a chain written with encryption at rest can be read back",
            "; ".join(f"{label}: {msg}" for label, msg in outcomes.items()),
            passed=all_ok,
            recovered=recovered,
        )
        if not all_ok:
            self._note(
                "Encryption at rest is write-only. JSONFileStorage.save_chain() hands the "
                "serialized bytes to encrypt_chain_data(), which is declared to take the "
                "chain dict; load_chain() then treats decrypt_chain_data()'s dict return "
                "value as bytes. With compression on, decryption fails outright on the gzip "
                "payload; with compression off, the load path slices a dict and raises. A "
                "node configured for encrypted storage writes a year of ledger it can never "
                "load back. tests/test_encryption.py passes because it exercises the "
                "encryption module directly and never crosses the storage seam."
            )

    # -- concurrency -------------------------------------------------------
    def _probe_concurrent_mining(self, day: int) -> None:
        """Submit entries while a block is being mined, on an isolated chain."""
        probe_chain = NatLangChain(
            require_validation=False,
            validator=self.validator,
            enable_deduplication=False,
            enable_rate_limiting=False,
            enable_timestamp_validation=False,
            enable_quality_checks=False,
            enable_asset_tracking=False,
            enable_derivative_tracking=False,
        )

        def make_entry(tag: str, i: int) -> NaturalLanguageEntry:
            return NaturalLanguageEntry(
                content=(
                    f"pelican_logistics recorded shipment leg {tag}-{i} moving freight "
                    f"between the Portland depot and the Calloway pier this week."
                ),
                author="pelican_logistics",
                intent=f"Shipment leg {tag}-{i} recorded",
            )

        # Pre-load a block's worth of work so proof-of-work takes real time, and
        # raise difficulty so the mining window is wide enough for a submission
        # to land inside it — the situation any multi-worker API server is in.
        preloaded = 150
        for i in range(preloaded):
            probe_chain.add_entry(make_entry("pre", i))

        errors: list[str] = []
        accepted_during_mining = 0
        mining_started = threading.Event()
        mining_done = threading.Event()
        pow_difficulty = self.cfg.difficulty + 2

        def miner():
            mining_started.set()
            try:
                probe_chain.mine_pending_entries(difficulty=pow_difficulty)
            except Exception as exc:  # pragma: no cover
                errors.append(f"miner {type(exc).__name__}: {exc}")
            finally:
                mining_done.set()

        thread = threading.Thread(target=miner)
        thread.start()
        mining_started.wait()
        real_time.sleep(0.02)  # let proof-of-work get under way

        during = 40
        for i in range(during):
            if mining_done.is_set():
                break
            try:
                res = probe_chain.add_entry(make_entry("during", i))
                if res.get("status") == "pending":
                    accepted_during_mining += 1
            except Exception as exc:  # pragma: no cover
                errors.append(f"submitter {type(exc).__name__}: {exc}")
            real_time.sleep(0.002)
        thread.join()

        submitted_total = preloaded + accepted_during_mining
        on_chain = sum(len(b.entries) for b in probe_chain.chain) - 1  # exclude genesis
        still_pending = len(probe_chain.pending_entries)
        lost = submitted_total - on_chain - still_pending
        chain_valid = probe_chain.validate_chain(verify_pow=True, difficulty=pow_difficulty)
        self._record(
            day,
            "concurrent_submit_and_mine",
            "every entry accepted while a block is being mined is still on the chain "
            "or still pending",
            f"{submitted_total} accepted overall ({accepted_during_mining} of them during "
            f"proof-of-work), {on_chain} on chain, {still_pending} pending, {lost} "
            f"unaccounted for; chain valid={chain_valid}",
            passed=lost == 0 and chain_valid and not errors,
            accepted=submitted_total,
            accepted_during_mining=accepted_during_mining,
            on_chain=on_chain,
            pending=still_pending,
            lost=lost,
            errors=errors[:5],
        )
        if lost > 0:
            self._note(
                f"mine_pending_entries() copies the pending queue, runs proof-of-work, then "
                f"assigns pending_entries = [] — while add_entry() appends to that same list "
                f"without holding the mining lock. Entries accepted during the proof-of-work "
                f"loop are discarded: {lost} of the {accepted_during_mining} entries "
                f"submitted during proof-of-work vanished in this probe. Each submitter "
                f"received status 'pending' and each entry's fingerprint was registered, "
                f"so an immediate resubmission is rejected as a duplicate."
            )

    # -- resource growth ---------------------------------------------------
    def _probe_fingerprint_growth(self, day: int) -> None:
        held = len(self.chain._entry_fingerprints)
        window = self.chain.dedup_window_seconds
        entries_total = sum(len(b.entries) for b in self.chain.chain)
        bounded = held < entries_total
        self._record(
            day,
            "dedup_fingerprint_growth",
            "the fingerprint registry stays bounded rather than growing with the chain",
            f"{held} fingerprints held against {entries_total} chain entries "
            f"(window {window}s)",
            passed=bounded,
            fingerprints=held,
            entries=entries_total,
        )

    # ------------------------------------------------------------------
    # Final audit
    # ------------------------------------------------------------------
    def _final_audit(self) -> dict:
        chain = self.chain
        entries_total = sum(len(b.entries) for b in chain.chain)

        start = real_time.perf_counter()
        chain_valid = chain.validate_chain(verify_pow=True, difficulty=self.cfg.difficulty)
        validate_seconds = real_time.perf_counter() - start

        # Independent linkage and hash verification, not trusting validate_chain.
        linkage_ok = True
        hash_ok = True
        pow_ok = True
        target = "0" * self.cfg.difficulty
        for i, block in enumerate(chain.chain):
            if block.hash != block.calculate_hash():
                hash_ok = False
            if i > 0:
                if block.previous_hash != chain.chain[i - 1].hash:
                    linkage_ok = False
                if block.entries and not block.hash.startswith(target):
                    pow_ok = False

        # Serialization round-trip must be exact.
        exported = chain.to_dict()
        reimported = NatLangChain.from_dict(copy.deepcopy(exported), require_validation=False)
        roundtrip_identical = reimported.to_dict()["chain"] == exported["chain"]

        # Asset ownership reconciliation against the workload's own book.
        registry_owners = chain._asset_registry._ownership
        mismatches = []
        for asset_id, expected_owner in self.gen.assets.items():
            actual = registry_owners.get(asset_id)
            if actual != expected_owner:
                mismatches.append(
                    {"asset_id": asset_id, "expected": expected_owner, "registry": actual}
                )

        # Every registered derivative must point at an entry that really exists.
        dangling = []
        for child_key, parents in chain._derivative_registry._parents.items():
            for parent in parents:
                if chain._get_entry_at(parent["block_index"], parent["entry_index"]) is None:
                    dangling.append({"child": child_key, "parent": parent})

        # Fingerprint uniqueness: no two chain entries share a fingerprint.
        seen: dict[str, int] = {}
        duplicate_entries = 0
        for block in chain.chain:
            for entry in block.entries:
                fp = compute_entry_fingerprint(entry.content, entry.author, entry.intent)
                seen[fp] = seen.get(fp, 0) + 1
                if seen[fp] > 1:
                    duplicate_entries += 1

        # Every mined entry must carry a validation status.
        unvalidated = sum(
            1
            for block in chain.chain[1:]
            for entry in block.entries
            if entry.validation_status != "validated"
        )

        narrative = chain.get_full_narrative()

        return {
            "blocks": len(chain.chain),
            "entries": entries_total,
            "chain_valid": chain_valid,
            "validate_seconds": round(validate_seconds, 4),
            "hashes_consistent": hash_ok,
            "linkage_consistent": linkage_ok,
            "proof_of_work_consistent": pow_ok,
            "roundtrip_identical": roundtrip_identical,
            "asset_ownership_mismatches": mismatches,
            "assets_tracked": len(registry_owners),
            "transfers_completed": len(chain._asset_registry.get_transfer_history()),
            "transfers_stuck_pending": len(chain._asset_registry._pending_transfers),
            "derivative_links": len(chain._derivative_registry._parents),
            "dangling_derivatives": dangling,
            "duplicate_entries_on_chain": duplicate_entries,
            "entries_missing_validation": unvalidated,
            "narrative_chars": len(narrative),
            "head_hash": chain.get_latest_block().hash,
        }

    # ------------------------------------------------------------------
    def _assemble_results(self, final: dict, wall_seconds: float) -> dict:
        submitted = sum(d.submitted for d in self.days)
        accepted = sum(d.accepted for d in self.days)
        rejected = sum(d.rejected for d in self.days)
        mine_times = [d.mine_seconds for d in self.days if d.mine_seconds > 0]
        nonces = [d.nonce for d in self.days if d.block_index is not None]

        return {
            "config": asdict(self.cfg),
            "wall_clock_seconds": round(wall_seconds, 2),
            "simulated_span": {
                "days": self.cfg.days,
                "start": datetime.fromtimestamp(
                    YEAR_START, tz=timezone.utc  # noqa: UP017
                ).strftime("%Y-%m-%d"),
                "end": self.clock.date_str(),
            },
            "throughput": {
                "submitted": submitted,
                "accepted": accepted,
                "rejected": rejected,
                "acceptance_rate": round(accepted / submitted, 4) if submitted else 0.0,
                "entries_on_chain": final["entries"],
                "blocks": final["blocks"],
                "mean_entries_per_block": round(final["entries"] / max(1, final["blocks"]), 1),
                "peak_day_submitted": max((d.submitted for d in self.days), default=0),
                "peak_pending_queue": max(self.pending_by_day, default=0),
            },
            "mining": {
                "mean_seconds": round(statistics.mean(mine_times), 4) if mine_times else 0.0,
                "median_seconds": round(statistics.median(mine_times), 4) if mine_times else 0.0,
                "max_seconds": round(max(mine_times), 4) if mine_times else 0.0,
                "total_seconds": round(sum(mine_times), 2),
                "mean_nonce": round(statistics.mean(nonces), 1) if nonces else 0.0,
                "max_nonce": max(nonces, default=0),
                "difficulty": self.cfg.difficulty,
            },
            "rejections": dict(
                sorted(self.rejection_totals.items(), key=lambda kv: -kv[1])
            ),
            "validation_decisions": dict(
                sorted(self.validation_decisions.items(), key=lambda kv: -kv[1])
            ),
            "traffic_classes": self.class_outcomes,
            "audits": self.audits,
            "snapshots": self.snapshots,
            "restarts": self.restarts,
            "incidents": [asdict(i) for i in self.incidents],
            "engine_faults": {
                "count": len(self.engine_faults),
                "distinct": sorted(
                    {(f["exception"], f["location"], f["message"]) for f in self.engine_faults}
                ),
                "samples": self.engine_faults[:10],
            },
            "final_audit": final,
            "notes": self.notes,
            "days": [asdict(d) for d in self.days],
        }


# ==========================================================================
# Reporting
# ==========================================================================


def render_report(results: dict) -> str:
    cfg = results["config"]
    thr = results["throughput"]
    mining = results["mining"]
    final = results["final_audit"]
    incidents = results["incidents"]

    passed = [i for i in incidents if i["passed"]]
    failed = [i for i in incidents if not i["passed"]]

    lines: list[str] = []
    add = lines.append

    add("# NatLangChain — One Year of Simulated Operation")
    add("")
    add(
        f"A single node ran for **{cfg['days']} simulated days** "
        f"({results['simulated_span']['start']} to {results['simulated_span']['end']}) "
        f"in {results['wall_clock_seconds']}s of wall clock time. The blockchain engine, "
        f"validation pipeline, registries, proof-of-work, and JSON persistence are the "
        f"real implementations from `src/`. Only the clock is simulated, so rate-limit "
        f"windows, deduplication expiry, and timestamp-drift checks experience a full year."
    )
    add("")
    add(
        "Proof of Understanding ran against `MockValidator`, the deterministic validator "
        "shipped in `src/blockchain.py`. No `ANTHROPIC_API_KEY` is available in this "
        "environment, so the LLM validator itself was not exercised; every other "
        "component was."
    )
    add("")

    add("## Ledger at year end")
    add("")
    add("| Measure | Value |")
    add("| --- | --- |")
    add(f"| Blocks mined | {final['blocks']:,} |")
    add(f"| Entries on chain | {final['entries']:,} |")
    add(f"| Entries submitted | {thr['submitted']:,} |")
    add(f"| Entries accepted | {thr['accepted']:,} ({thr['acceptance_rate'] * 100:.1f}%) |")
    add(f"| Entries rejected | {thr['rejected']:,} |")
    add(f"| Mean entries per block | {thr['mean_entries_per_block']} |")
    add(f"| Busiest day | {thr['peak_day_submitted']:,} submissions |")
    add(f"| Deepest pending queue | {thr['peak_pending_queue']:,} entries |")
    add(f"| Head block hash | `{final['head_hash'][:32]}…` |")
    add("")

    add("## Integrity")
    add("")
    add("| Check | Result |")
    add("| --- | --- |")
    add(f"| `validate_chain()` at difficulty {cfg['difficulty']} | {_yn(final['chain_valid'])} |")
    add(f"| Every block hash recomputes | {_yn(final['hashes_consistent'])} |")
    add(f"| Every `previous_hash` links | {_yn(final['linkage_consistent'])} |")
    add(f"| Every mined block meets difficulty | {_yn(final['proof_of_work_consistent'])} |")
    add(f"| Serialization round-trip identical | {_yn(final['roundtrip_identical'])} |")
    add(f"| Entries missing validation status | {final['entries_missing_validation']} |")
    add(f"| Duplicate entries on chain | {final['duplicate_entries_on_chain']} |")
    add(f"| Dangling derivative links | {len(final['dangling_derivatives'])} |")
    add(f"| Asset ownership mismatches | {len(final['asset_ownership_mismatches'])} |")
    add(f"| Full-chain validation time | {final['validate_seconds']}s |")
    add("")

    add("## Growth over the year")
    add("")
    add("| Day | Blocks | Entries | Validate (s) | Narrative (chars) | Dedup fingerprints held |")
    add("| --- | --- | --- | --- | --- | --- |")
    for audit in results["audits"]:
        add(
            f"| {audit['day']} | {audit['blocks']:,} | {audit['entries']:,} | "
            f"{audit['validate_seconds']} | {audit['narrative_chars']:,} | "
            f"{audit['fingerprints_held']} |"
        )
    add("")

    if results["snapshots"]:
        first_snap = results["snapshots"][0]
        last_snap = results["snapshots"][-1]
        add(
            f"Persisted `chain.json` grew from {first_snap['bytes']:,} bytes on day "
            f"{first_snap['day']} to {last_snap['bytes']:,} bytes on day {last_snap['day']} "
            f"({last_snap['bytes'] / max(1, last_snap['entries']):.0f} bytes per entry). "
            f"The final snapshot write took {last_snap['save_seconds']}s."
        )
        add("")

    add("## Mining")
    add("")
    add(
        f"At difficulty {mining['difficulty']}, block production averaged "
        f"{mining['mean_seconds']}s (median {mining['median_seconds']}s, worst "
        f"{mining['max_seconds']}s) with a mean nonce of {mining['mean_nonce']:,.0f} "
        f"and a worst case of {mining['max_nonce']:,}. The whole year of mining cost "
        f"{mining['total_seconds']}s of CPU."
    )
    add("")

    add("## Rejections")
    add("")
    add("| Reason | Count |")
    add("| --- | --- |")
    for reason, count in results["rejections"].items():
        add(f"| `{reason}` | {count:,} |")
    add("")
    if results.get("validation_decisions"):
        add("Proof of Understanding decisions on rejected entries:")
        add("")
        add("| Decision | Count |")
        add("| --- | --- |")
        for decision, count in results["validation_decisions"].items():
            add(f"| `{decision}` | {count:,} |")
        add("")

    add("Outcome by traffic class:")
    add("")
    add("| Traffic class | Submitted | Accepted | Rejected |")
    add("| --- | --- | --- | --- |")
    for name, counts in sorted(results["traffic_classes"].items()):
        add(
            f"| {name} | {counts['submitted']:,} | {counts['accepted']:,} | "
            f"{counts['rejected']:,} |"
        )
    add("")

    add("## Restart recovery")
    add("")
    add("| Day | Blocks | Load (s) | Chain valid | Head hash | Ownership | Derivatives | Transfer history |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results["restarts"]:
        add(
            f"| {r['day']} | {r['blocks']:,} | {r['load_seconds']} | "
            f"{_yn(r['chain_valid'])} | {_yn(r['head_hash_match'])} | "
            f"{_yn(r['ownership_match'])} | {_yn(r['derivatives_match'])} | "
            f"{_yn(r['transfer_history_preserved'])} |"
        )
    add("")

    faults = results.get("engine_faults", {"count": 0, "distinct": []})
    add("## Engine faults")
    add("")
    if faults["count"] == 0:
        add("No uncaught exception escaped `add_entry()` during the year.")
    else:
        add(
            f"`add_entry()` raised an uncaught exception {faults['count']} time(s) during the "
            f"year. Through the REST API each of these is an unhandled 500."
        )
        add("")
        add("| Exception | Raised at | Message |")
        add("| --- | --- | --- |")
        for exc, location, message in faults["distinct"]:
            add(f"| `{exc}` | `{location}` | {message} |")
    add("")

    add("## Adversarial campaign")
    add("")
    add(f"{len(passed)} of {len(incidents)} probes behaved as expected.")
    add("")
    add("| Day | Probe | Expected | Observed | Result |")
    add("| --- | --- | --- | --- | --- |")
    for i in incidents:
        add(
            f"| {i['day']} | `{i['name']}` | {i['expectation']} | {i['outcome']} | "
            f"{'PASS' if i['passed'] else 'FAIL'} |"
        )
    add("")

    if failed:
        add("## Findings")
        add("")
        for idx, i in enumerate(failed, 1):
            add(f"### {idx}. {i['name']} (day {i['day']})")
            add("")
            add(f"**Expected:** {i['expectation']}")
            add("")
            add(f"**Observed:** {i['outcome']}")
            add("")
        add("")

    if results["notes"]:
        add("## Notes from the run")
        add("")
        for note in results["notes"]:
            add(f"- {note}")
        add("")

    return "\n".join(lines)


def _yn(value: bool) -> str:
    return "yes" if value else "**no**"


# ==========================================================================
# Entry point
# ==========================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--seed", type=int, default=20260101)
    parser.add_argument("--difficulty", type=int, default=2)
    parser.add_argument("--entries-per-day", type=int, default=38)
    parser.add_argument(
        "--workdir",
        default=os.path.join(SIM_DIR, "run"),
        help="Directory for chain.json snapshots produced by the run",
    )
    parser.add_argument("--json", default=os.path.join(SIM_DIR, "results", "year_results.json"))
    parser.add_argument("--report", default=os.path.join(SIM_DIR, "results", "YEAR_REPORT.md"))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    cfg = SimConfig(
        days=args.days,
        seed=args.seed,
        difficulty=args.difficulty,
        base_entries_per_day=args.entries_per_day,
        workdir=args.workdir,
    )

    sim = YearSimulation(cfg)
    results = sim.run()

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)

    report = render_report(results)
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(report)

    if not args.quiet:
        print(report)
        print(f"\nJSON results: {args.json}")
        print(f"Report:       {args.report}")

    failures = [i for i in results["incidents"] if not i["passed"]]
    integrity_ok = (
        results["final_audit"]["chain_valid"]
        and results["final_audit"]["linkage_consistent"]
        and results["final_audit"]["roundtrip_identical"]
    )
    return 0 if integrity_ok and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
