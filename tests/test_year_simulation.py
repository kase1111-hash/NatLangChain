"""Smoke test for the long-horizon operational simulation.

Runs a compressed version of ``simulations/year_simulation.py`` — a few weeks
instead of a year, with the full probe campaign rescaled onto that horizon — and
asserts that the ledger stays intact and no probe regresses.

The full 365-day run is not part of the test suite; it takes minutes. Run it
directly when you want the whole picture::

    python -m simulations.year_simulation
"""

import os
import sys

import pytest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
sys.path.insert(0, REPO_ROOT)

from simulations.year_simulation import SimConfig, YearSimulation

# Probes that assert a security or correctness property the engine is expected
# to hold. Characterization probes (e.g. proof-of-work rewrite cost, which
# reports a difficulty tradeoff rather than a defect) are deliberately absent.
MUST_PASS_PROBES = {
    "replay_within_dedup_window",
    "replay_of_still_pending_entry",
    "backdating_45_days",
    "future_dating_6_hours",
    "metadata_spoofing",
    "sybil_flood_120_entries",
    "global_flood_200_entries_80_authors",
    "double_spend_same_queue",
    "transfer_by_non_owner",
    "asset_lock_leak_after_validation_failure",
    "chain_bloat_oversized_entry",
    "undersized_entry",
    "silent_content_tamper",
    "tamper_with_self_rehash",
    "action_intent_mismatch",
    "action_mismatch_punctuation_evasion",
    "adversarial_language",
    "encrypted_persistence",
    "concurrent_submit_and_mine",
    "dedup_fingerprint_growth",
}


@pytest.fixture(scope="module")
def simulation_results(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("year_sim")
    config = SimConfig(
        days=28,
        base_entries_per_day=16,
        restart_every=7,
        audit_every=14,
        rewrite_probe_blocks=6,
        workdir=str(workdir),
    )
    return YearSimulation(config).run()


@pytest.mark.slow
class TestSimulatedOperation:
    def test_ledger_stays_intact(self, simulation_results):
        final = simulation_results["final_audit"]
        assert final["chain_valid"]
        assert final["hashes_consistent"]
        assert final["linkage_consistent"]
        assert final["proof_of_work_consistent"]
        assert final["roundtrip_identical"]

    def test_no_entry_is_lost_or_duplicated(self, simulation_results):
        final = simulation_results["final_audit"]
        assert final["duplicate_entries_on_chain"] == 0
        assert final["entries_missing_validation"] == 0
        assert final["dangling_derivatives"] == []

    def test_asset_ownership_reconciles(self, simulation_results):
        final = simulation_results["final_audit"]
        assert final["asset_ownership_mismatches"] == []
        # Reservations released or completed; none left stranded at year end.
        assert final["transfers_stuck_pending"] == 0

    def test_engine_raises_nothing_uncaught(self, simulation_results):
        faults = simulation_results["engine_faults"]
        assert faults["count"] == 0, f"add_entry raised: {faults['distinct']}"

    def test_every_restart_recovers_cleanly(self, simulation_results):
        restarts = simulation_results["restarts"]
        assert restarts, "the run should have restarted the node at least once"
        for restart in restarts:
            assert restart["chain_valid"], restart
            assert restart["head_hash_match"], restart
            assert restart["ownership_match"], restart
            assert restart["transfer_history_preserved"], restart

    def test_traffic_actually_flowed(self, simulation_results):
        throughput = simulation_results["throughput"]
        assert throughput["submitted"] > 200
        assert throughput["accepted"] > 150
        assert throughput["blocks"] >= 28

    @pytest.mark.parametrize("probe_name", sorted(MUST_PASS_PROBES))
    def test_probe_holds(self, simulation_results, probe_name):
        matches = [i for i in simulation_results["incidents"] if i["name"] == probe_name]
        assert matches, f"probe {probe_name} did not run"
        for incident in matches:
            assert incident["passed"], (
                f"{probe_name}: expected {incident['expectation']}; observed {incident['outcome']}"
            )
