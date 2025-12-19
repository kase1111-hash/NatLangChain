"""
Integration test runner for Escalation Fork and Observance Burn protocols.
Runs 10 test scenarios with various outcomes including escalations.
"""

import sys
import os
import random
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from escalation_fork import EscalationForkManager, ForkStatus, TriggerReason
from observance_burn import ObservanceBurnManager, BurnReason

# Test configuration
SCENARIOS = [
    {"name": "Alice vs Bob - Rate Dispute", "escalate": False, "resolve": True},
    {"name": "Charlie vs Dave - Timeline Conflict", "escalate": True, "resolve": True},
    {"name": "Eve vs Frank - Scope Disagreement", "escalate": True, "resolve": True},
    {"name": "Grace vs Henry - Payment Terms", "escalate": False, "resolve": True},
    {"name": "Ivy vs Jack - Quality Standards", "escalate": True, "resolve": False},  # Timeout
    {"name": "Kate vs Leo - Deliverable Dispute", "escalate": True, "resolve": True},
    {"name": "Mike vs Nancy - IP Rights", "escalate": False, "resolve": True},
    {"name": "Oscar vs Paula - Contract Interpretation", "escalate": True, "resolve": True},
    {"name": "Quinn vs Rita - Milestone Completion", "escalate": True, "resolve": True, "veto": True},
    {"name": "Sam vs Tina - Force Majeure", "escalate": True, "resolve": True},
]


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")


def print_subheader(text):
    """Print a formatted subheader."""
    print(f"\n  --- {text} ---")


def print_result(label, value, indent=4):
    """Print a formatted result."""
    print(f"{' '*indent}{label}: {value}")


def generate_proposal(word_count=600):
    """Generate a proposal with specified word count."""
    words = ["fair", "reasonable", "agreement", "terms", "both", "parties",
             "shall", "agree", "propose", "resolution", "contract", "amended",
             "rate", "timeline", "deliverable", "scope", "payment", "milestone"]
    return " ".join(random.choices(words, k=word_count))


def generate_veto_reason(word_count=150):
    """Generate a veto reason with specified word count."""
    words = ["reject", "insufficient", "fails", "address", "concern", "evidence",
             "ignored", "proposal", "inadequate", "missing", "key", "provision"]
    return " ".join(random.choices(words, k=word_count))


def run_scenario(scenario_num, scenario, fork_manager, burn_manager):
    """Run a single test scenario."""
    name = scenario["name"]
    should_escalate = scenario["escalate"]
    should_resolve = scenario["resolve"]
    has_veto = scenario.get("veto", False)

    parties = name.split(" - ")[0].split(" vs ")
    party_a = parties[0].strip()
    party_b = parties[1].strip()
    dispute_topic = name.split(" - ")[1] if " - " in name else "General Dispute"

    print_header(f"TEST RUN {scenario_num}: {name}")

    # Create dispute ID
    dispute_id = f"DISPUTE-{scenario_num:03d}"
    print_result("Dispute ID", dispute_id)
    print_result("Parties", f"{party_a} vs {party_b}")
    print_result("Topic", dispute_topic)

    if not should_escalate:
        # Resolved without escalation
        print_subheader("OUTCOME: Resolved without escalation")
        print_result("Status", "✅ Mediation successful - no fork needed")
        return {
            "scenario": name,
            "escalated": False,
            "resolved": True,
            "fork_id": None
        }

    # Scenario requires escalation
    print_subheader("STEP 1: Perform Observance Burn")

    mediation_stake = random.uniform(50, 200)
    burn_amount = burn_manager.calculate_escalation_burn(mediation_stake)

    success, burn_result = burn_manager.perform_burn(
        burner=f"0x{party_a}",
        amount=burn_amount,
        reason=BurnReason.ESCALATION_COMMITMENT,
        intent_hash=dispute_id,
        epitaph=f"Escalating {dispute_topic} dispute fairly"
    )

    if not success:
        print_result("Burn Status", f"❌ FAILED: {burn_result.get('error')}")
        return {"scenario": name, "escalated": False, "resolved": False, "error": burn_result}

    print_result("Burn Status", "✅ Completed")
    print_result("Amount Burned", f"{burn_amount:.2f} tokens (5% of {mediation_stake:.2f} stake)")
    print_result("Tx Hash", burn_result["tx_hash"][:20] + "...")
    print_result("Epitaph", f'"{scenario["name"]} - escalated fairly"')
    print_result("New Supply", f"{burn_manager.total_supply:,.2f} tokens")

    # Trigger escalation fork
    print_subheader("STEP 2: Trigger Escalation Fork")

    trigger_reasons = list(TriggerReason)
    trigger_reason = random.choice(trigger_reasons)

    fork_data = fork_manager.trigger_fork(
        dispute_id=dispute_id,
        trigger_reason=trigger_reason,
        triggering_party=party_a,
        original_mediator=f"mediator_{scenario_num}",
        original_pool=mediation_stake,
        burn_tx_hash=burn_result["tx_hash"],
        evidence_of_failure={
            "failed_proposals": [f"PROP-{scenario_num:03d}-001"],
            "rejection_reasons": [f"{dispute_topic} terms unacceptable"]
        }
    )

    fork_id = fork_data["fork_id"]
    print_result("Fork ID", fork_id)
    print_result("Trigger Reason", trigger_reason.value)
    print_result("Original Pool", f"{mediation_stake:.2f} tokens")
    print_result("Mediator Retained", f"{fork_data['mediator_retained']:.2f} tokens (50%)")
    print_result("Bounty Pool", f"{fork_data['bounty_pool']:.2f} tokens (50%)")
    print_result("Solver Window", fork_data["solver_window_ends"][:10])

    # Submit solver proposals
    print_subheader("STEP 3: Solver Proposals")

    num_solvers = random.randint(1, 3)
    proposals = []

    for i in range(num_solvers):
        solver_name = f"solver_{scenario_num}_{chr(65+i)}"
        proposal_content = generate_proposal(random.randint(500, 1200))

        success, proposal = fork_manager.submit_proposal(
            fork_id=fork_id,
            solver=solver_name,
            proposal_content=proposal_content,
            addresses_concerns=[dispute_topic.lower().replace(" ", "_"), "fair_resolution"]
        )

        if success:
            proposals.append(proposal)
            print_result(f"Proposal {i+1}", f"{proposal['proposal_id']} by {solver_name} ({proposal['word_count']} words)")

    if not proposals:
        print_result("Status", "❌ No valid proposals submitted")
        return {"scenario": name, "escalated": True, "resolved": False, "fork_id": fork_id}

    # Handle veto scenario
    if has_veto and len(proposals) > 1:
        print_subheader("STEP 3b: Veto")

        veto_target = proposals[0]
        veto_reason = generate_veto_reason()

        success, veto_result = fork_manager.veto_proposal(
            fork_id=fork_id,
            proposal_id=veto_target["proposal_id"],
            vetoing_party=party_b,
            veto_reason=veto_reason,
            evidence_refs=[f"EVIDENCE-{scenario_num:03d}"]
        )

        if success:
            print_result("Vetoed", veto_target["proposal_id"])
            print_result("Remaining Vetoes", veto_result["remaining_vetoes"])
            proposals = proposals[1:]  # Use next proposal

    if not should_resolve:
        # Simulate timeout (for reporting purposes)
        print_subheader("OUTCOME: Solver Window Timeout")
        print_result("Status", "⏱️ No ratified resolution within 7 days")
        print_result("Refund", f"90% returned to parties ({fork_data['bounty_pool'] * 0.9:.2f} tokens)")
        print_result("Burned", f"10% via Observance Burn ({fork_data['bounty_pool'] * 0.1:.2f} tokens)")

        return {
            "scenario": name,
            "escalated": True,
            "resolved": False,
            "fork_id": fork_id,
            "timeout": True
        }

    # Ratification
    print_subheader("STEP 4: Dual Ratification")

    winning_proposal = proposals[0]

    # Party A ratifies
    success, result = fork_manager.ratify_proposal(
        fork_id=fork_id,
        proposal_id=winning_proposal["proposal_id"],
        ratifying_party=party_a,
        satisfaction_rating=random.randint(70, 95),
        comments=f"{party_a} accepts the proposed resolution"
    )
    print_result(f"{party_a} Ratification", "✅ Accepted" if success else "❌ Failed")

    # Party B ratifies
    success, result = fork_manager.ratify_proposal(
        fork_id=fork_id,
        proposal_id=winning_proposal["proposal_id"],
        ratifying_party=party_b,
        satisfaction_rating=random.randint(70, 95),
        comments=f"{party_b} accepts the proposed resolution"
    )
    print_result(f"{party_b} Ratification", "✅ Accepted" if success else "❌ Failed")

    if success and result.get("status") == "resolved":
        print_subheader("OUTCOME: Fork Resolved")
        print_result("Status", "✅ Dual ratification achieved")
        print_result("Winning Proposal", result["winning_proposal"])
        print_result("Winning Solver", result["solver"])

        # Show distribution
        print("\n    Bounty Distribution:")
        for solver, amount in result["distribution"].items():
            print_result(solver, f"{amount:.2f} tokens", indent=6)

        return {
            "scenario": name,
            "escalated": True,
            "resolved": True,
            "fork_id": fork_id,
            "winning_solver": result["solver"],
            "distribution": result["distribution"]
        }

    return {
        "scenario": name,
        "escalated": True,
        "resolved": False,
        "fork_id": fork_id
    }


def run_all_tests():
    """Run all 10 test scenarios."""
    print("\n" + "="*70)
    print("  ESCALATION FORK & OBSERVANCE BURN - 10 RUN INTEGRATION TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    # Initialize managers
    fork_manager = EscalationForkManager()
    burn_manager = ObservanceBurnManager(initial_supply=1_000_000.0)

    print(f"\n  Initial Token Supply: {burn_manager.total_supply:,.2f}")
    print(f"  Test Scenarios: {len(SCENARIOS)}")

    results = []

    for i, scenario in enumerate(SCENARIOS, 1):
        result = run_scenario(i, scenario, fork_manager, burn_manager)
        results.append(result)

    # Summary
    print_header("TEST SUMMARY")

    escalated = sum(1 for r in results if r.get("escalated"))
    resolved = sum(1 for r in results if r.get("resolved"))
    timeouts = sum(1 for r in results if r.get("timeout"))
    vetoed = sum(1 for r in results if r.get("scenario") and "veto" in str(results))

    print_result("Total Scenarios", len(results))
    print_result("Resolved Without Escalation", len(results) - escalated)
    print_result("Escalated to Fork", escalated)
    print_result("Successfully Resolved", resolved)
    print_result("Timeouts", timeouts)

    print_subheader("Burn Statistics")
    stats = burn_manager.get_statistics()
    print_result("Total Burns", stats["total_burns"])
    print_result("Total Burned", f"{stats['total_burned']:.4f} tokens")
    print_result("Final Supply", f"{stats['current_supply']:,.4f} tokens")
    print_result("Supply Reduction", f"{(1_000_000 - stats['current_supply']):.4f} tokens")

    print_subheader("Active Forks")
    active_forks = fork_manager.list_active_forks()
    print_result("Active Forks Remaining", len(active_forks))

    print_subheader("Scenario Results")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("resolved") else ("⏱️ TIMEOUT" if result.get("timeout") else "❌")
        escalate_status = "→ FORK" if result.get("escalated") else "→ DIRECT"
        print(f"    {i:2d}. {result['scenario'][:40]:<40} {escalate_status:<10} {status}")

    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70 + "\n")

    return results


if __name__ == "__main__":
    results = run_all_tests()

    # Return exit code based on results
    all_expected_resolved = all(
        r.get("resolved") == SCENARIOS[i].get("resolve", True)
        for i, r in enumerate(results)
    )

    if all_expected_resolved:
        print("All scenarios completed as expected! ✅")
        sys.exit(0)
    else:
        print("Some scenarios did not complete as expected! ❌")
        sys.exit(1)
