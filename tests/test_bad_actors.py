"""
NatLangChain - Bad Actor Simulation Tests
Tests blockchain resilience against various attack vectors

This module simulates multiple types of malicious actors attempting to
game or exploit the NatLangChain system.
"""

import sys
import os
import json
import copy
import time
import hashlib
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry, Block


class BadActorSimulator:
    """
    Simulates various bad actors attempting to game the blockchain.
    Tests the system's resilience against attacks.
    """

    def __init__(self):
        self.chain = NatLangChain()
        self.attack_results: List[Dict[str, Any]] = []
        self.successful_attacks = 0
        self.blocked_attacks = 0

    def reset_chain(self):
        """Reset the blockchain for a fresh test."""
        self.chain = NatLangChain()

    def log_attack(self, attack_name: str, success: bool, details: str,
                   severity: str = "HIGH", recommendation: str = ""):
        """Log the result of an attack attempt."""
        result = {
            "attack_name": attack_name,
            "success": success,
            "details": details,
            "severity": severity,
            "recommendation": recommendation,
            "timestamp": time.time()
        }
        self.attack_results.append(result)
        if success:
            self.successful_attacks += 1
        else:
            self.blocked_attacks += 1
        return result


# =============================================================================
# ATTACK TYPE 1: AMBIGUITY EXPLOITATION
# =============================================================================

def test_ambiguity_exploitation():
    """
    Test: Bad actor submits deliberately vague entries that could be
    interpreted multiple ways, allowing them to claim different meanings later.
    """
    print("\n" + "="*60)
    print("ATTACK 1: AMBIGUITY EXPLOITATION")
    print("="*60)

    sim = BadActorSimulator()

    # Ambiguous entries that could be interpreted multiple ways
    ambiguous_entries = [
        {
            "content": "I'll pay you soon for the services rendered.",
            "author": "bad_actor_1",
            "intent": "Promise of payment",
            "exploit": "'Soon' is undefined - could claim it means any time"
        },
        {
            "content": "The delivery will be completed in a reasonable timeframe.",
            "author": "bad_actor_2",
            "intent": "Delivery commitment",
            "exploit": "'Reasonable' is subjective - can be disputed indefinitely"
        },
        {
            "content": "We agree to share the profits appropriately.",
            "author": "bad_actor_3",
            "intent": "Profit sharing agreement",
            "exploit": "'Appropriately' could mean 1% or 99%"
        },
        {
            "content": "The work will meet acceptable standards.",
            "author": "bad_actor_4",
            "intent": "Quality commitment",
            "exploit": "'Acceptable' is never defined"
        },
        {
            "content": "Payment is contingent on satisfactory completion.",
            "author": "bad_actor_5",
            "intent": "Conditional payment",
            "exploit": "'Satisfactory' can always be disputed"
        }
    ]

    results = []
    for entry_data in ambiguous_entries:
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"]
        )

        # The blockchain accepts these entries without semantic validation
        result = sim.chain.add_entry(entry)

        attack_success = result["status"] == "pending"

        sim.log_attack(
            attack_name="Ambiguity Exploitation",
            success=attack_success,
            details=f"Entry '{entry_data['content'][:50]}...' - Exploit: {entry_data['exploit']}",
            severity="MEDIUM",
            recommendation="Require PoU validation before accepting entry to pending queue"
        )

        results.append({
            "entry": entry_data["content"][:50],
            "accepted": attack_success,
            "exploit": entry_data["exploit"]
        })

        print(f"  {'[EXPLOITABLE]' if attack_success else '[BLOCKED]'} {entry_data['content'][:50]}...")

    # Mine the block to see if ambiguous entries make it to chain
    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} ambiguous entries mined into block #{mined.index}")
        print("  FINDING: System allows ambiguous entries without semantic validation at mining time")

    return sim, results


# =============================================================================
# ATTACK TYPE 2: INTENT MISMATCH ATTACK
# =============================================================================

def test_intent_mismatch():
    """
    Test: Bad actor claims one intent but content says something else entirely.
    This could be used for social engineering or plausible deniability.
    """
    print("\n" + "="*60)
    print("ATTACK 2: INTENT MISMATCH ATTACK")
    print("="*60)

    sim = BadActorSimulator()

    # Entries where intent doesn't match content
    mismatch_entries = [
        {
            "content": "I hereby transfer all my assets to John Smith effective immediately.",
            "author": "malicious_user",
            "intent": "Birthday greeting",  # Intent is completely different
            "exploit": "Could claim intent was just a joke/greeting if challenged"
        },
        {
            "content": "The company agrees to pay $1,000,000 in damages to the plaintiff.",
            "author": "corporate_fraud",
            "intent": "Meeting notes",  # Downplaying serious commitment
            "exploit": "Could deny the commitment by pointing to benign intent"
        },
        {
            "content": "User X is hereby banned from the platform for life.",
            "author": "rogue_admin",
            "intent": "User profile update",  # Hiding moderation action
            "exploit": "Action hidden under innocuous intent"
        },
        {
            "content": "All previous agreements are null and void.",
            "author": "contract_breaker",
            "intent": "Quarterly summary",
            "exploit": "Major action buried under routine intent"
        }
    ]

    results = []
    for entry_data in mismatch_entries:
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"]
        )

        result = sim.chain.add_entry(entry)
        attack_success = result["status"] == "pending"

        sim.log_attack(
            attack_name="Intent Mismatch",
            success=attack_success,
            details=f"Content: '{entry_data['content'][:40]}...' | Fake Intent: '{entry_data['intent']}'",
            severity="HIGH",
            recommendation="Require mandatory PoU intent-content alignment check before entry acceptance"
        )

        results.append({
            "content": entry_data["content"][:40],
            "fake_intent": entry_data["intent"],
            "accepted": attack_success
        })

        print(f"  {'[EXPLOITABLE]' if attack_success else '[BLOCKED]'} Intent: '{entry_data['intent']}' | Content: '{entry_data['content'][:35]}...'")

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} mismatched entries mined into block #{mined.index}")
        print("  FINDING: System does not validate intent-content alignment at add_entry or mine time")

    return sim, results


# =============================================================================
# ATTACK TYPE 3: CHAIN TAMPERING ATTACK
# =============================================================================

def test_chain_tampering():
    """
    Test: Bad actor attempts to tamper with block contents after mining.
    Tests cryptographic integrity of the chain.
    """
    print("\n" + "="*60)
    print("ATTACK 3: CHAIN TAMPERING ATTACK")
    print("="*60)

    sim = BadActorSimulator()

    # Add legitimate entry first
    legitimate_entry = NaturalLanguageEntry(
        content="Alice pays Bob $1,000 for consulting services.",
        author="alice",
        intent="Payment record"
    )
    sim.chain.add_entry(legitimate_entry)
    sim.chain.mine_pending_entries(difficulty=1)

    original_valid = sim.chain.validate_chain()
    print(f"  Chain valid before tampering: {original_valid}")

    results = []

    # ATTACK 3a: Try to modify entry content after mining
    print("\n  [ATTACK 3a] Attempting to modify entry content...")
    original_content = sim.chain.chain[1].entries[0].content
    sim.chain.chain[1].entries[0].content = "Alice pays Bob $100,000 for consulting services."

    tamper_detected = not sim.chain.validate_chain()

    sim.log_attack(
        attack_name="Content Tampering",
        success=not tamper_detected,
        details="Attempted to change $1,000 to $100,000 after mining",
        severity="CRITICAL",
        recommendation="N/A - Hash validation working correctly" if tamper_detected else "Implement hash validation"
    )

    print(f"    Tampering detected by hash validation: {tamper_detected}")
    results.append({"attack": "content_modification", "detected": tamper_detected})

    # Restore for next test
    sim.chain.chain[1].entries[0].content = original_content

    # ATTACK 3b: Try to recalculate hash after tampering (smarter attack)
    # First, add more blocks so we have a chain with blocks after the tampered one
    print("\n  [ATTACK 3b] Attempting to tamper + recalculate hash...")
    sim.reset_chain()
    entry1 = NaturalLanguageEntry(content="Payment of $1,000.", author="alice", intent="Payment")
    entry2 = NaturalLanguageEntry(content="Delivery confirmed.", author="bob", intent="Delivery")
    sim.chain.add_entry(entry1)
    sim.chain.mine_pending_entries(difficulty=1)
    sim.chain.add_entry(entry2)
    sim.chain.mine_pending_entries(difficulty=1)
    # Now we have: genesis -> block1 -> block2
    # Tamper with block1 and recalculate its hash
    sim.chain.chain[1].entries[0].content = "Payment of $100,000."
    sim.chain.chain[1].hash = sim.chain.chain[1].calculate_hash()

    # Block2's previous_hash still points to old block1 hash, so chain should be invalid
    chain_still_valid = sim.chain.validate_chain()

    sim.log_attack(
        attack_name="Hash Recalculation Attack",
        success=chain_still_valid,
        details="Attempted to tamper and recalculate hash",
        severity="CRITICAL",
        recommendation="N/A - Chain linkage prevents attack" if not chain_still_valid else "Implement previous_hash validation"
    )

    print(f"    Chain linkage broken: {not chain_still_valid}")
    results.append({"attack": "hash_recalculation", "detected": not chain_still_valid})

    # ATTACK 3c: Try to insert a fake block
    print("\n  [ATTACK 3c] Attempting to insert fake block...")
    sim.reset_chain()

    legitimate_entry = NaturalLanguageEntry(
        content="Legitimate transaction.",
        author="real_user",
        intent="Real transaction"
    )
    sim.chain.add_entry(legitimate_entry)
    sim.chain.mine_pending_entries(difficulty=1)

    # Create a fake block with different previous_hash
    fake_entry = NaturalLanguageEntry(
        content="FAKE: I now own everything.",
        author="attacker",
        intent="Fraudulent claim"
    )
    fake_block = Block(
        index=2,
        entries=[fake_entry],
        previous_hash="0000fake_hash_here"  # Wrong previous hash
    )
    sim.chain.chain.append(fake_block)

    fake_detected = not sim.chain.validate_chain()

    sim.log_attack(
        attack_name="Block Insertion Attack",
        success=not fake_detected,
        details="Attempted to insert fake block with wrong previous_hash",
        severity="CRITICAL",
        recommendation="N/A - Chain validation working" if fake_detected else "Implement previous_hash validation"
    )

    print(f"    Fake block detected: {fake_detected}")
    results.append({"attack": "fake_block_insertion", "detected": fake_detected})

    return sim, results


# =============================================================================
# ATTACK TYPE 4: DOUBLE-SPENDING ANALOG
# =============================================================================

def test_double_spending_analog():
    """
    Test: Bad actor attempts to submit contradictory entries.
    In NatLangChain this is like claiming to transfer same asset twice.
    """
    print("\n" + "="*60)
    print("ATTACK 4: DOUBLE-SPENDING ANALOG")
    print("="*60)

    sim = BadActorSimulator()

    # Submit contradictory entries
    entry1 = NaturalLanguageEntry(
        content="I, Alice, hereby transfer ownership of my vintage car (VIN: 12345) to Bob.",
        author="alice",
        intent="Asset transfer to Bob",
        metadata={"asset_id": "car_vin_12345", "recipient": "bob"}
    )

    entry2 = NaturalLanguageEntry(
        content="I, Alice, hereby transfer ownership of my vintage car (VIN: 12345) to Charlie.",
        author="alice",
        intent="Asset transfer to Charlie",
        metadata={"asset_id": "car_vin_12345", "recipient": "charlie"}
    )

    result1 = sim.chain.add_entry(entry1)
    result2 = sim.chain.add_entry(entry2)

    both_accepted = result1["status"] == "pending" and result2["status"] == "pending"

    print(f"  Entry 1 (to Bob) accepted: {result1['status'] == 'pending'}")
    print(f"  Entry 2 (to Charlie) accepted: {result2['status'] == 'pending'}")

    sim.log_attack(
        attack_name="Double-Spending Analog",
        success=both_accepted,
        details="Both contradictory asset transfers were accepted to pending queue",
        severity="CRITICAL",
        recommendation="Implement semantic deduplication and asset tracking layer"
    )

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined and len(mined.entries) == 2:
        print(f"\n  WARNING: Both contradictory transfers mined into block #{mined.index}")
        print("  FINDING: System has no asset double-transfer prevention")
        print("  NOTE: The system relies on off-chain dispute resolution for this case")

    return sim, [{"both_accepted": both_accepted}]


# =============================================================================
# ATTACK TYPE 5: ADVERSARIAL PHRASING
# =============================================================================

def test_adversarial_phrasing():
    """
    Test: Bad actor uses adversarial phrasing with hidden clauses,
    legal loopholes, or deceptive language.
    """
    print("\n" + "="*60)
    print("ATTACK 5: ADVERSARIAL PHRASING")
    print("="*60)

    sim = BadActorSimulator()

    adversarial_entries = [
        {
            "content": "Party A agrees to provide services to Party B. In the event of any dispute, "
                      "Party A shall be the sole arbiter. Party B waives all rights to legal recourse. "
                      "This clause is buried in paragraph 47 subsection C.",
            "author": "predatory_contractor",
            "intent": "Service agreement",
            "exploit": "Hidden one-sided arbitration and rights waiver"
        },
        {
            "content": "The payment of $100 is due upon completion. (Note: 'completion' is defined "
                      "as the heat death of the universe in Appendix Z, not attached hereto.)",
            "author": "payment_evader",
            "intent": "Payment terms",
            "exploit": "Impossible condition hidden in unreferenced appendix"
        },
        {
            "content": "This agreement supersedes all previous agreements including but not limited to "
                      "any protections, warranties, or guarantees previously agreed upon.",
            "author": "warranty_eliminator",
            "intent": "Contract update",
            "exploit": "Retroactively removes protections via supersede clause"
        },
        {
            "content": "User agrees that by using the service they grant Company an irrevocable, "
                      "perpetual, royalty-free license to all user content for any purpose whatsoever.",
            "author": "data_harvester",
            "intent": "Terms of service update",
            "exploit": "Overly broad content license buried in ToS"
        },
        {
            "content": "The price is $50 per unit (minimum order: 1,000,000 units, non-refundable).",
            "author": "hidden_minimum",
            "intent": "Price quote",
            "exploit": "Massive hidden minimum commitment"
        }
    ]

    results = []
    for entry_data in adversarial_entries:
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"]
        )

        result = sim.chain.add_entry(entry)
        attack_success = result["status"] == "pending"

        sim.log_attack(
            attack_name="Adversarial Phrasing",
            success=attack_success,
            details=f"Exploit: {entry_data['exploit']}",
            severity="HIGH",
            recommendation="Require PoU dialectic consensus to detect adversarial patterns"
        )

        results.append({
            "content_preview": entry_data["content"][:50],
            "exploit": entry_data["exploit"],
            "accepted": attack_success
        })

        print(f"  {'[EXPLOITABLE]' if attack_success else '[BLOCKED]'} {entry_data['exploit']}")

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} adversarial entries mined into block #{mined.index}")

    return sim, results


# =============================================================================
# ATTACK TYPE 6: REPLAY ATTACK
# =============================================================================

def test_replay_attack():
    """
    Test: Bad actor attempts to replay old valid entries to duplicate actions.
    """
    print("\n" + "="*60)
    print("ATTACK 6: REPLAY ATTACK")
    print("="*60)

    sim = BadActorSimulator()

    # Create and mine a legitimate payment entry
    original_entry = NaturalLanguageEntry(
        content="Company X pays Employee Y a bonus of $10,000 for Q4 performance.",
        author="finance_dept",
        intent="Bonus payment",
        metadata={"payment_id": "bonus_2024_q4_001"}
    )

    sim.chain.add_entry(original_entry)
    sim.chain.mine_pending_entries(difficulty=1)
    print(f"  Original entry mined in block #{len(sim.chain.chain) - 1}")

    # Attacker copies the entry and tries to submit again
    replayed_entry = NaturalLanguageEntry.from_dict(original_entry.to_dict())

    result = sim.chain.add_entry(replayed_entry)
    replay_accepted = result["status"] == "pending"

    print(f"  Replay attempt accepted: {replay_accepted}")

    sim.log_attack(
        attack_name="Replay Attack",
        success=replay_accepted,
        details="Same entry accepted twice - could duplicate payments/actions",
        severity="CRITICAL",
        recommendation="Implement entry deduplication based on content hash + author + timestamp window"
    )

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: Replayed entry mined into block #{mined.index}")
        print("  FINDING: No replay protection mechanism exists at entry/mining level")

    return sim, [{"replay_accepted": replay_accepted}]


# =============================================================================
# ATTACK TYPE 7: SYBIL ATTACK (ENTRY FLOODING)
# =============================================================================

def test_sybil_flooding():
    """
    Test: Bad actor creates many entries to flood the pending queue
    or dilute legitimate entries.
    """
    print("\n" + "="*60)
    print("ATTACK 7: SYBIL FLOODING ATTACK")
    print("="*60)

    sim = BadActorSimulator()

    # Submit one legitimate entry
    legitimate = NaturalLanguageEntry(
        content="Important: New safety protocol requires all workers to wear helmets.",
        author="safety_officer",
        intent="Safety announcement"
    )
    sim.chain.add_entry(legitimate)

    # Attacker floods with spam entries
    sybil_count = 100
    flood_start = time.time()
    for i in range(sybil_count):
        spam_entry = NaturalLanguageEntry(
            content=f"Spam entry #{i} from sybil attack. This is meaningless content to flood the queue.",
            author=f"sybil_node_{i % 10}",  # 10 fake identities
            intent="Spam"
        )
        sim.chain.add_entry(spam_entry)
    flood_end = time.time()

    print(f"  Flooded {sybil_count} entries in {flood_end - flood_start:.3f}s")
    print(f"  Pending queue size: {len(sim.chain.pending_entries)}")
    print(f"  Legitimate to spam ratio: 1:{sybil_count}")

    attack_success = len(sim.chain.pending_entries) == sybil_count + 1

    sim.log_attack(
        attack_name="Sybil Flooding",
        success=attack_success,
        details=f"Accepted {sybil_count} spam entries, diluting legitimate content",
        severity="HIGH",
        recommendation="Implement rate limiting, stake requirements, or reputation-weighted acceptance"
    )

    # Mine and check the result
    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: All {len(mined.entries)} entries (including spam) mined into block #{mined.index}")
        print("  FINDING: No rate limiting or anti-spam mechanism at entry level")

    return sim, [{"spam_accepted": sybil_count, "attack_success": attack_success}]


# =============================================================================
# ATTACK TYPE 8: TIMESTAMP MANIPULATION
# =============================================================================

def test_timestamp_manipulation():
    """
    Test: Bad actor manipulates timestamps to alter perceived ordering.
    """
    print("\n" + "="*60)
    print("ATTACK 8: TIMESTAMP MANIPULATION")
    print("="*60)

    sim = BadActorSimulator()

    # Create entry then manipulate timestamp
    entry = NaturalLanguageEntry(
        content="This contract was agreed upon.",
        author="timestamp_attacker",
        intent="Contract"
    )

    original_timestamp = entry.timestamp

    # Attacker backdates the entry to claim it was made earlier
    entry.timestamp = "2020-01-01T00:00:00.000000"

    result = sim.chain.add_entry(entry)

    print(f"  Original timestamp: {original_timestamp}")
    print(f"  Backdated timestamp: {entry.timestamp}")
    print(f"  Entry accepted: {result['status'] == 'pending'}")

    attack_success = result["status"] == "pending"

    sim.log_attack(
        attack_name="Timestamp Manipulation",
        success=attack_success,
        details="Entry with backdated timestamp accepted without validation",
        severity="MEDIUM",
        recommendation="Implement server-side timestamp validation or threshold check"
    )

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        # Check if block timestamp differs significantly from entry timestamp
        block_time = mined.timestamp
        entry_claims = "2020-01-01"
        print(f"\n  Block timestamp: {block_time}")
        print(f"  Entry claims: {entry_claims}")
        print("  FINDING: Entry timestamps are not validated against block/system time")

    return sim, [{"attack_success": attack_success}]


# =============================================================================
# ATTACK TYPE 9: METADATA INJECTION
# =============================================================================

def test_metadata_injection():
    """
    Test: Bad actor injects malicious or misleading metadata.
    """
    print("\n" + "="*60)
    print("ATTACK 9: METADATA INJECTION")
    print("="*60)

    sim = BadActorSimulator()

    # Entry with malicious metadata
    malicious_metadata_entries = [
        {
            "content": "Standard contract between parties.",
            "author": "meta_attacker",
            "intent": "Contract",
            "metadata": {
                "validation_status": "validated",  # Trying to self-validate
                "verified_by": "official_validator",
                "trust_score": 100,
                "__override__": True
            }
        },
        {
            "content": "Payment of $100 to vendor.",
            "author": "meta_attacker_2",
            "intent": "Payment",
            "metadata": {
                "amount": 1000000,  # Metadata contradicts content
                "urgent": True,
                "skip_validation": True
            }
        }
    ]

    results = []
    for entry_data in malicious_metadata_entries:
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"],
            metadata=entry_data["metadata"]
        )

        result = sim.chain.add_entry(entry)

        # Check if malicious metadata was preserved
        stored_entry = sim.chain.pending_entries[-1]
        malicious_preserved = stored_entry.metadata == entry_data["metadata"]

        attack_success = result["status"] == "pending" and malicious_preserved

        sim.log_attack(
            attack_name="Metadata Injection",
            success=attack_success,
            details=f"Malicious metadata preserved: {entry_data['metadata']}",
            severity="MEDIUM",
            recommendation="Sanitize metadata and maintain allowed-field whitelist"
        )

        results.append({
            "metadata_injected": entry_data["metadata"],
            "preserved": malicious_preserved
        })

        print(f"  Malicious metadata accepted: {attack_success}")
        print(f"    Injected: {json.dumps(entry_data['metadata'], indent=4)[:100]}...")

    return sim, results


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_bad_actor_simulation():
    """Run all bad actor simulations and generate report."""
    print("\n" + "="*70)
    print("NATLANGCHAIN BAD ACTOR SIMULATION")
    print("Testing Blockchain Resilience Against Adversarial Behavior")
    print("="*70)

    all_results = {}
    total_exploitable = 0
    total_blocked = 0

    # Run all attack simulations
    simulations = [
        ("Ambiguity Exploitation", test_ambiguity_exploitation),
        ("Intent Mismatch", test_intent_mismatch),
        ("Chain Tampering", test_chain_tampering),
        ("Double-Spending Analog", test_double_spending_analog),
        ("Adversarial Phrasing", test_adversarial_phrasing),
        ("Replay Attack", test_replay_attack),
        ("Sybil Flooding", test_sybil_flooding),
        ("Timestamp Manipulation", test_timestamp_manipulation),
        ("Metadata Injection", test_metadata_injection),
    ]

    for name, test_func in simulations:
        try:
            sim, results = test_func()
            all_results[name] = {
                "results": results,
                "successful_attacks": sim.successful_attacks,
                "blocked_attacks": sim.blocked_attacks,
                "attack_log": sim.attack_results
            }
            total_exploitable += sim.successful_attacks
            total_blocked += sim.blocked_attacks
        except Exception as e:
            print(f"  ERROR in {name}: {e}")
            all_results[name] = {"error": str(e)}

    # Generate Summary Report
    print("\n" + "="*70)
    print("SIMULATION SUMMARY REPORT")
    print("="*70)

    print(f"\n  TOTAL ATTACK ATTEMPTS: {total_exploitable + total_blocked}")
    print(f"  EXPLOITABLE (System Gamed): {total_exploitable}")
    print(f"  BLOCKED (System Defended): {total_blocked}")

    if total_exploitable + total_blocked > 0:
        exploit_rate = (total_exploitable / (total_exploitable + total_blocked)) * 100
        print(f"  EXPLOIT SUCCESS RATE: {exploit_rate:.1f}%")

    print("\n" + "-"*70)
    print("FINDINGS BY CATEGORY:")
    print("-"*70)

    # Categorize findings
    cryptographic_findings = []
    semantic_findings = []
    operational_findings = []

    for name, data in all_results.items():
        if "attack_log" in data:
            for attack in data["attack_log"]:
                finding = {
                    "attack": name,
                    "success": attack["success"],
                    "severity": attack["severity"],
                    "recommendation": attack["recommendation"]
                }

                if name == "Chain Tampering":
                    cryptographic_findings.append(finding)
                elif name in ["Ambiguity Exploitation", "Intent Mismatch", "Adversarial Phrasing"]:
                    semantic_findings.append(finding)
                else:
                    operational_findings.append(finding)

    print("\n[CRYPTOGRAPHIC LAYER]")
    crypto_blocked = sum(1 for f in cryptographic_findings if not f["success"])
    print(f"  Status: {'SECURE' if crypto_blocked == len(cryptographic_findings) else 'VULNERABLE'}")
    print(f"  Attacks blocked: {crypto_blocked}/{len(cryptographic_findings)}")

    print("\n[SEMANTIC LAYER]")
    sem_vulnerable = sum(1 for f in semantic_findings if f["success"])
    print(f"  Status: {'SECURE' if sem_vulnerable == 0 else 'VULNERABLE - PoU not enforced at add_entry/mine time'}")
    print(f"  Exploits possible: {sem_vulnerable}/{len(semantic_findings)}")

    print("\n[OPERATIONAL LAYER]")
    op_vulnerable = sum(1 for f in operational_findings if f["success"])
    print(f"  Status: {'SECURE' if op_vulnerable == 0 else 'NEEDS HARDENING'}")
    print(f"  Exploits possible: {op_vulnerable}/{len(operational_findings)}")

    print("\n" + "-"*70)
    print("KEY RECOMMENDATIONS:")
    print("-"*70)
    recommendations = set()
    for name, data in all_results.items():
        if "attack_log" in data:
            for attack in data["attack_log"]:
                if attack["success"] and attack["recommendation"]:
                    recommendations.add(attack["recommendation"])

    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print("""
  The NatLangChain blockchain shows:

  STRENGTHS:
  - Cryptographic integrity (hash chaining) works correctly
  - Block tampering is detected
  - Chain linkage prevents isolated block manipulation

  WEAKNESSES:
  - Semantic validation (PoU) is not enforced at add_entry or mining time
  - No replay protection at blockchain layer
  - No rate limiting / anti-spam mechanisms
  - Metadata is not sanitized
  - Timestamps are not validated
  - Double-spending analogs are not prevented at blockchain layer

  DESIGN NOTE:
  The system appears designed to rely on the Validator layer (PoU, Dialectic
  Consensus, Multi-Model Consensus) for semantic security, but these checks
  are optional and not enforced at the blockchain core layer. A malicious
  actor could bypass validation entirely if submitting directly to the chain.

  RECOMMENDATION:
  Consider making PoU validation mandatory before entries are accepted into
  the pending queue, or implement a validation_required flag that must be
  set to True before mining.
""")

    return all_results


# =============================================================================
# TEST ENTRY POINTS
# =============================================================================

def test_all_bad_actors():
    """Pytest-compatible test runner."""
    results = run_bad_actor_simulation()

    # Count critical failures
    critical_failures = 0
    for name, data in results.items():
        if "attack_log" in data:
            for attack in data["attack_log"]:
                if attack["severity"] == "CRITICAL" and attack["success"]:
                    critical_failures += 1

    # The chain tampering attacks should be blocked
    if "Chain Tampering" in results and "attack_log" in results["Chain Tampering"]:
        for attack in results["Chain Tampering"]["attack_log"]:
            assert not attack["success"], f"CRITICAL: Chain tampering attack succeeded: {attack['details']}"

    print(f"\nTest completed with {critical_failures} critical vulnerabilities in non-crypto layer")


if __name__ == "__main__":
    run_bad_actor_simulation()
