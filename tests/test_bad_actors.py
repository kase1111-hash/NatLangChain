"""
NatLangChain - Bad Actor Simulation Tests
Tests blockchain resilience against various attack vectors

This module simulates multiple types of malicious actors attempting to
game or exploit the NatLangChain system.
"""

import copy
import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import Block, MockValidator, NatLangChain, NaturalLanguageEntry


class BadActorSimulator:
    """
    Simulates various bad actors attempting to game the blockchain.
    Tests the system's resilience against attacks.
    """

    def __init__(
        self,
        use_validation: bool = False,
        use_deduplication: bool = False,
        use_rate_limiting: bool = False,
        rate_limit_window: int = 60,
        max_entries_per_author: int = 10,
        max_global_entries: int = 100,
        use_timestamp_validation: bool = False,
        max_timestamp_drift: int = 300,
        max_future_drift: int = 60,
        use_metadata_sanitization: bool = False,
        metadata_sanitize_mode: str = "strip",
        use_asset_tracking: bool = False
    ):
        """
        Initialize simulator.

        Args:
            use_validation: If True, use MockValidator to test protection.
                          If False, test unprotected chain (shows vulnerabilities).
            use_deduplication: If True, enable entry deduplication.
                             If False, disable deduplication for baseline testing.
            use_rate_limiting: If True, enable rate limiting to prevent flooding.
                             If False, disable rate limiting for baseline testing.
            rate_limit_window: Time window for rate limiting in seconds.
            max_entries_per_author: Max entries per author within window.
            max_global_entries: Max total entries within window.
            use_timestamp_validation: If True, validate entry timestamps.
                                     If False, allow any timestamp (shows vulnerability).
            max_timestamp_drift: Max seconds an entry can be in the past.
            max_future_drift: Max seconds an entry can be in the future.
            use_metadata_sanitization: If True, sanitize entry metadata.
                                      If False, allow any metadata (shows vulnerability).
            metadata_sanitize_mode: "strip", "reject", or "warn" mode.
            use_asset_tracking: If True, enable asset tracking to prevent double-spending.
                              If False, disable asset tracking (shows vulnerability).
        """
        self.use_validation = use_validation
        self.use_deduplication = use_deduplication
        self.use_rate_limiting = use_rate_limiting
        self.rate_limit_window = rate_limit_window
        self.max_entries_per_author = max_entries_per_author
        self.max_global_entries = max_global_entries
        self.use_timestamp_validation = use_timestamp_validation
        self.max_timestamp_drift = max_timestamp_drift
        self.max_future_drift = max_future_drift
        self.use_metadata_sanitization = use_metadata_sanitization
        self.metadata_sanitize_mode = metadata_sanitize_mode
        self.use_asset_tracking = use_asset_tracking
        self._init_chain()
        self.attack_results: list[dict[str, Any]] = []
        self.successful_attacks = 0
        self.blocked_attacks = 0

    def _init_chain(self):
        """Initialize the blockchain with current settings."""
        self.chain = NatLangChain(
            require_validation=self.use_validation,
            validator=MockValidator() if self.use_validation else None,
            enable_deduplication=self.use_deduplication,
            enable_rate_limiting=self.use_rate_limiting,
            rate_limit_window=self.rate_limit_window,
            max_entries_per_author=self.max_entries_per_author,
            max_global_entries=self.max_global_entries,
            enable_timestamp_validation=self.use_timestamp_validation,
            max_timestamp_drift=self.max_timestamp_drift,
            max_future_drift=self.max_future_drift,
            enable_metadata_sanitization=self.use_metadata_sanitization,
            metadata_sanitize_mode=self.metadata_sanitize_mode,
            enable_asset_tracking=self.use_asset_tracking
        )

    def reset_chain(self):
        """Reset the blockchain for a fresh test."""
        self._init_chain()

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

def test_ambiguity_exploitation(use_validation: bool = False):
    """
    Test: Bad actor submits deliberately vague entries that could be
    interpreted multiple ways, allowing them to claim different meanings later.
    """
    print("\n" + "="*60)
    print("ATTACK 1: AMBIGUITY EXPLOITATION")
    print("="*60)

    sim = BadActorSimulator(use_validation=use_validation)

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

        result = sim.chain.add_entry(entry)

        # Attack succeeds if entry was added (status=pending), fails if rejected
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
            "exploit": entry_data["exploit"],
            "rejection_reason": result.get("validation_decision", None) if not attack_success else None
        })

        status_msg = "[EXPLOITABLE]" if attack_success else f"[BLOCKED: {result.get('validation_decision', 'rejected')}]"
        print(f"  {status_msg} {entry_data['content'][:50]}...")

    # Mine the block to see if ambiguous entries make it to chain
    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} ambiguous entries mined into block #{mined.index}")
        print("  FINDING: System allows ambiguous entries without semantic validation at mining time")
    elif sim.use_validation:
        print("\n  PROTECTED: No ambiguous entries made it to the pending queue")
        print("  FINDING: PoU validation blocked ambiguous entries")

    return sim, results


# =============================================================================
# ATTACK TYPE 2: INTENT MISMATCH ATTACK
# =============================================================================

def test_intent_mismatch(use_validation: bool = False):
    """
    Test: Bad actor claims one intent but content says something else entirely.
    This could be used for social engineering or plausible deniability.
    """
    print("\n" + "="*60)
    print("ATTACK 2: INTENT MISMATCH ATTACK")
    print("="*60)

    sim = BadActorSimulator(use_validation=use_validation)

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

        status_msg = "[EXPLOITABLE]" if attack_success else f"[BLOCKED: {result.get('validation_decision', 'rejected')}]"
        print(f"  {status_msg} Intent: '{entry_data['intent']}' | Content: '{entry_data['content'][:35]}...'")

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} mismatched entries mined into block #{mined.index}")
        print("  FINDING: System does not validate intent-content alignment at add_entry or mine time")
    elif sim.use_validation:
        print("\n  PROTECTED: No mismatched entries made it to the pending queue")
        print("  FINDING: PoU validation blocked intent-content mismatch attacks")

    return sim, results


# =============================================================================
# ATTACK TYPE 3: CHAIN TAMPERING ATTACK
# =============================================================================

def test_chain_tampering(use_validation: bool = False):
    """
    Test: Bad actor attempts to tamper with block contents after mining.
    Tests cryptographic integrity of the chain.
    """
    print("\n" + "="*60)
    print("ATTACK 3: CHAIN TAMPERING ATTACK")
    print("="*60)

    # Chain tampering tests use unprotected chain since we need entries to mine first
    sim = BadActorSimulator(use_validation=False)

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

def test_double_spending_analog(use_validation: bool = False, use_asset_tracking: bool = False):
    """
    Test: Bad actor attempts to submit contradictory entries.
    In NatLangChain this is like claiming to transfer same asset twice.
    """
    print("\n" + "="*60)
    print("ATTACK 4: DOUBLE-SPENDING ANALOG")
    print("="*60)

    sim = BadActorSimulator(use_validation=use_validation, use_asset_tracking=use_asset_tracking)

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

    first_accepted = result1["status"] == "pending"
    second_accepted = result2["status"] == "pending"
    both_accepted = first_accepted and second_accepted
    second_blocked_as_double_transfer = result2.get("reason") == "double_transfer"

    print(f"  Entry 1 (to Bob) accepted: {first_accepted}")
    print(f"  Entry 2 (to Charlie) accepted: {second_accepted}")

    if second_blocked_as_double_transfer:
        print(f"  Entry 2 blocked: {result2.get('message', 'double-transfer detected')}")

    if use_asset_tracking:
        sim.log_attack(
            attack_name="Double-Spending Analog",
            success=both_accepted,
            details="Second transfer blocked by asset tracking" if second_blocked_as_double_transfer else "Both transfers accepted (protection failed)",
            severity="CRITICAL",
            recommendation="N/A - Asset tracking is working" if second_blocked_as_double_transfer else "Check asset tracking implementation"
        )
    else:
        sim.log_attack(
            attack_name="Double-Spending Analog",
            success=both_accepted,
            details="Both contradictory asset transfers were accepted to pending queue",
            severity="CRITICAL",
            recommendation="Enable asset tracking to prevent double-spending attacks"
        )

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        if use_asset_tracking and second_blocked_as_double_transfer:
            print(f"\n  PROTECTED: Only 1 transfer mined into block #{mined.index}")
            print("  FINDING: Asset tracking successfully prevented double-transfer attack")
        elif len(mined.entries) == 2:
            print(f"\n  WARNING: Both contradictory transfers mined into block #{mined.index}")
            print("  FINDING: System has no asset double-transfer prevention")
            print("  NOTE: The system relies on off-chain dispute resolution for this case")

    return sim, [{
        "first_accepted": first_accepted,
        "second_accepted": second_accepted,
        "both_accepted": both_accepted,
        "blocked_by_asset_tracking": second_blocked_as_double_transfer
    }]


# =============================================================================
# ATTACK TYPE 5: ADVERSARIAL PHRASING
# =============================================================================

def test_adversarial_phrasing(use_validation: bool = False):
    """
    Test: Bad actor uses adversarial phrasing with hidden clauses,
    legal loopholes, or deceptive language.
    """
    print("\n" + "="*60)
    print("ATTACK 5: ADVERSARIAL PHRASING")
    print("="*60)

    sim = BadActorSimulator(use_validation=use_validation)

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

        status_msg = "[EXPLOITABLE]" if attack_success else f"[BLOCKED: {result.get('validation_decision', 'rejected')}]"
        print(f"  {status_msg} {entry_data['exploit']}")

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: {len(mined.entries)} adversarial entries mined into block #{mined.index}")
    elif sim.use_validation:
        print("\n  PROTECTED: No adversarial entries made it to the pending queue")
        print("  FINDING: PoU validation blocked adversarial phrasing attacks")

    return sim, results


# =============================================================================
# ATTACK TYPE 6: REPLAY ATTACK
# =============================================================================

def test_replay_attack(use_validation: bool = False, use_deduplication: bool = False):
    """
    Test: Bad actor attempts to replay old valid entries to duplicate actions.
    """
    print("\n" + "="*60)
    print("ATTACK 6: REPLAY ATTACK")
    print("="*60)

    # Test with deduplication when in protected mode
    sim = BadActorSimulator(use_validation=False, use_deduplication=use_deduplication)

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
    rejected_as_duplicate = result.get("reason") == "duplicate"

    if rejected_as_duplicate:
        print(f"  Replay attempt BLOCKED: {result.get('message', 'duplicate detected')}")
    else:
        print(f"  Replay attempt accepted: {replay_accepted}")

    sim.log_attack(
        attack_name="Replay Attack",
        success=replay_accepted,
        details="Same entry accepted twice - could duplicate payments/actions" if replay_accepted else "Replay blocked by deduplication",
        severity="CRITICAL",
        recommendation="Implement entry deduplication based on content hash + author + timestamp window" if replay_accepted else "N/A - Deduplication working"
    )

    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        print(f"\n  WARNING: Replayed entry mined into block #{mined.index}")
        print("  FINDING: No replay protection mechanism exists at entry/mining level")
    elif use_deduplication and rejected_as_duplicate:
        print("\n  PROTECTED: Replay attack blocked by deduplication")
        print("  FINDING: Entry deduplication prevents replay attacks")

    return sim, [{"replay_accepted": replay_accepted, "blocked_by_dedup": rejected_as_duplicate}]


# =============================================================================
# ATTACK TYPE 7: SYBIL ATTACK (ENTRY FLOODING)
# =============================================================================

def test_sybil_flooding(use_validation: bool = False, use_rate_limiting: bool = False):
    """
    Test: Bad actor creates many entries to flood the pending queue
    or dilute legitimate entries.
    """
    print("\n" + "="*60)
    print("ATTACK 7: SYBIL FLOODING ATTACK")
    print("="*60)

    # For rate limiting test, use tight limits to demonstrate protection
    # 5 entries per author in 60s, 20 total entries
    sim = BadActorSimulator(
        use_validation=use_validation,
        use_rate_limiting=use_rate_limiting,
        rate_limit_window=60,
        max_entries_per_author=5,
        max_global_entries=20
    )

    # Submit one legitimate entry
    legitimate = NaturalLanguageEntry(
        content="Important: New safety protocol requires all workers to wear helmets.",
        author="safety_officer",
        intent="Safety announcement"
    )
    result = sim.chain.add_entry(legitimate)
    result["status"] == "pending"

    # Attacker floods with spam entries
    sybil_count = 100
    spam_accepted = 0
    rate_limited = 0
    flood_start = time.time()
    for i in range(sybil_count):
        spam_entry = NaturalLanguageEntry(
            content=f"Spam entry #{i} from sybil attack. This is meaningless content to flood the queue.",
            author=f"sybil_node_{i % 10}",  # 10 fake identities
            intent="Spam"
        )
        result = sim.chain.add_entry(spam_entry)
        if result["status"] == "pending":
            spam_accepted += 1
        elif result.get("reason") == "rate_limit":
            rate_limited += 1
    flood_end = time.time()

    print(f"  Attempted {sybil_count} entries in {flood_end - flood_start:.3f}s")
    print(f"  Spam entries accepted: {spam_accepted}")
    print(f"  Entries rate limited: {rate_limited}")
    print(f"  Pending queue size: {len(sim.chain.pending_entries)}")

    # Attack succeeds if all spam entries were accepted
    attack_success = spam_accepted == sybil_count

    if use_rate_limiting:
        # With rate limiting, the attack should be blocked
        blocked_pct = (rate_limited / sybil_count) * 100 if sybil_count > 0 else 0
        print(f"  Rate limiting blocked: {blocked_pct:.1f}% of spam")

        sim.log_attack(
            attack_name="Sybil Flooding",
            success=attack_success,
            details=f"Rate limiting blocked {rate_limited}/{sybil_count} spam entries ({blocked_pct:.1f}%)",
            severity="HIGH",
            recommendation="N/A - Rate limiting is working" if rate_limited > 0 else "Rate limits may be too permissive"
        )
    else:
        sim.log_attack(
            attack_name="Sybil Flooding",
            success=attack_success,
            details=f"Accepted {spam_accepted} spam entries, diluting legitimate content",
            severity="HIGH",
            recommendation="Implement rate limiting, stake requirements, or reputation-weighted acceptance"
        )

    # Mine and check the result
    mined = sim.chain.mine_pending_entries(difficulty=1)
    if mined:
        if use_rate_limiting and rate_limited > 0:
            print(f"\n  PROTECTED: Only {len(mined.entries)} entries mined (rate limiting blocked {rate_limited})")
            print("  FINDING: Rate limiting successfully prevented flooding attack")
        else:
            print(f"\n  WARNING: All {len(mined.entries)} entries (including spam) mined into block #{mined.index}")
            print("  FINDING: No rate limiting or anti-spam mechanism at entry level")

    return sim, [{
        "spam_attempted": sybil_count,
        "spam_accepted": spam_accepted,
        "rate_limited": rate_limited,
        "attack_success": attack_success
    }]


# =============================================================================
# ATTACK TYPE 8: TIMESTAMP MANIPULATION
# =============================================================================

def test_timestamp_manipulation(use_validation: bool = False, use_timestamp_validation: bool = False):
    """
    Test: Bad actor manipulates timestamps to alter perceived ordering.
    """
    print("\n" + "="*60)
    print("ATTACK 8: TIMESTAMP MANIPULATION")
    print("="*60)

    sim = BadActorSimulator(
        use_validation=use_validation,
        use_timestamp_validation=use_timestamp_validation
    )

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
    rejected_for_timestamp = result.get("reason") == "invalid_timestamp"

    if rejected_for_timestamp:
        print(f"  Rejection reason: {result.get('timestamp_issue', 'timestamp validation failed')}")

    if use_timestamp_validation:
        sim.log_attack(
            attack_name="Timestamp Manipulation",
            success=attack_success,
            details="Backdated timestamp blocked by validation" if rejected_for_timestamp else "Timestamp validation may be too permissive",
            severity="MEDIUM",
            recommendation="N/A - Timestamp validation is working" if rejected_for_timestamp else "Check timestamp drift thresholds"
        )
    else:
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
    elif use_timestamp_validation and rejected_for_timestamp:
        print("\n  PROTECTED: Backdated entry blocked by timestamp validation")
        print("  FINDING: Timestamp validation prevents backdating attacks")

    return sim, [{
        "attack_success": attack_success,
        "blocked_by_timestamp_validation": rejected_for_timestamp
    }]


# =============================================================================
# ATTACK TYPE 9: METADATA INJECTION
# =============================================================================

def test_metadata_injection(use_validation: bool = False, use_metadata_sanitization: bool = False):
    """
    Test: Bad actor injects malicious or misleading metadata.
    """
    print("\n" + "="*60)
    print("ATTACK 9: METADATA INJECTION")
    print("="*60)

    sim = BadActorSimulator(
        use_validation=use_validation,
        use_metadata_sanitization=use_metadata_sanitization,
        metadata_sanitize_mode="strip"  # Use strip mode for simulation
    )

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
                "__override__": True,
                "legitimate_field": "this is ok"  # Non-forbidden field
            }
        },
        {
            "content": "Payment of $100 to vendor.",
            "author": "meta_attacker_2",
            "intent": "Payment",
            "metadata": {
                "amount": 1000000,  # Metadata contradicts content (not forbidden, just deceptive)
                "urgent": True,
                "skip_validation": True,  # Forbidden field
                "notes": "legitimate notes"  # Non-forbidden field
            }
        }
    ]

    results = []
    forbidden_stripped = 0
    total_forbidden = 0

    for entry_data in malicious_metadata_entries:
        original_metadata = copy.deepcopy(entry_data["metadata"])
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"],
            metadata=copy.deepcopy(entry_data["metadata"])
        )

        result = sim.chain.add_entry(entry)

        # Count forbidden fields in original
        forbidden_in_original = sum(
            1 for k in original_metadata
            if k in ["validation_status", "verified_by", "trust_score", "__override__", "skip_validation"]
        )
        total_forbidden += forbidden_in_original

        if result["status"] == "pending":
            # Check if malicious metadata was preserved or stripped
            stored_entry = sim.chain.pending_entries[-1]
            malicious_preserved = stored_entry.metadata == original_metadata

            # Count how many forbidden fields were stripped
            stripped_count = sum(
                1 for k in original_metadata
                if k not in stored_entry.metadata and k in ["validation_status", "verified_by", "trust_score", "__override__", "skip_validation"]
            )
            forbidden_stripped += stripped_count

            attack_success = malicious_preserved
        else:
            # Entry was rejected (reject mode)
            malicious_preserved = False
            attack_success = False
            forbidden_stripped += forbidden_in_original

        if use_metadata_sanitization:
            sim.log_attack(
                attack_name="Metadata Injection",
                success=attack_success,
                details=f"Forbidden fields stripped: {not malicious_preserved}" if not malicious_preserved else "Sanitization may be incomplete",
                severity="MEDIUM",
                recommendation="N/A - Metadata sanitization is working" if not malicious_preserved else "Check sanitization rules"
            )
        else:
            sim.log_attack(
                attack_name="Metadata Injection",
                success=attack_success,
                details=f"Malicious metadata preserved: {original_metadata}",
                severity="MEDIUM",
                recommendation="Sanitize metadata and maintain allowed-field whitelist"
            )

        results.append({
            "metadata_injected": original_metadata,
            "preserved": malicious_preserved,
            "stripped": not malicious_preserved
        })

        print(f"  Malicious metadata accepted: {attack_success}")
        if use_metadata_sanitization and not malicious_preserved:
            print("    Forbidden fields stripped (sanitization working)")
        else:
            print(f"    Injected: {json.dumps(original_metadata, indent=4)[:100]}...")

    if use_metadata_sanitization:
        print(f"\n  PROTECTED: {forbidden_stripped}/{total_forbidden} forbidden metadata fields stripped")
        print("  FINDING: Metadata sanitization removes dangerous fields")

    return sim, results


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_single_simulation(
    use_validation: bool = False,
    use_deduplication: bool = False,
    use_rate_limiting: bool = False,
    use_timestamp_validation: bool = False,
    use_metadata_sanitization: bool = False,
    use_asset_tracking: bool = False
):
    """Run all bad actor simulations for a single mode (protected or unprotected)."""
    all_results = {}
    total_exploitable = 0
    total_blocked = 0

    # Run all attack simulations
    # Note: Special handling for tests that need extra parameters
    # Format: (name, func, extra_params)
    simulations = [
        ("Ambiguity Exploitation", test_ambiguity_exploitation, {}),
        ("Intent Mismatch", test_intent_mismatch, {}),
        ("Chain Tampering", test_chain_tampering, {}),
        ("Double-Spending Analog", test_double_spending_analog, {"use_asset_tracking": use_asset_tracking}),
        ("Adversarial Phrasing", test_adversarial_phrasing, {}),
        ("Replay Attack", test_replay_attack, {"use_deduplication": use_deduplication}),
        ("Sybil Flooding", test_sybil_flooding, {"use_rate_limiting": use_rate_limiting}),
        ("Timestamp Manipulation", test_timestamp_manipulation, {"use_timestamp_validation": use_timestamp_validation}),
        ("Metadata Injection", test_metadata_injection, {"use_metadata_sanitization": use_metadata_sanitization}),
    ]

    for name, test_func, extra_params in simulations:
        try:
            # Build kwargs: always include use_validation, plus any extra params
            kwargs = {"use_validation": use_validation}
            kwargs.update(extra_params)
            sim, results = test_func(**kwargs)
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
            import traceback
            traceback.print_exc()
            all_results[name] = {"error": str(e)}

    return all_results, total_exploitable, total_blocked


def run_bad_actor_simulation():
    """Run all bad actor simulations and generate report."""
    print("\n" + "="*70)
    print("NATLANGCHAIN BAD ACTOR SIMULATION")
    print("Testing Blockchain Resilience Against Adversarial Behavior")
    print("="*70)

    # ==========================================================================
    # PHASE 1: UNPROTECTED MODE (Shows vulnerabilities)
    # ==========================================================================
    print("\n" + "#"*70)
    print("# PHASE 1: UNPROTECTED MODE")
    print("# (All protections disabled)")
    print("# This demonstrates vulnerabilities when protections are disabled")
    print("#"*70)

    unprotected_results, unprotected_exploitable, unprotected_blocked = run_single_simulation(
        use_validation=False,
        use_deduplication=False,
        use_rate_limiting=False,
        use_timestamp_validation=False,
        use_metadata_sanitization=False,
        use_asset_tracking=False
    )

    # ==========================================================================
    # PHASE 2: PROTECTED MODE (Shows fix in action)
    # ==========================================================================
    print("\n" + "#"*70)
    print("# PHASE 2: PROTECTED MODE")
    print("# (All protections enabled)")
    print("# This demonstrates how all protections work together to block attacks")
    print("#"*70)

    protected_results, protected_exploitable, protected_blocked = run_single_simulation(
        use_validation=True,
        use_deduplication=True,
        use_rate_limiting=True,
        use_timestamp_validation=True,
        use_metadata_sanitization=True,
        use_asset_tracking=True
    )

    # Generate Summary Report
    print("\n" + "="*70)
    print("SIMULATION SUMMARY REPORT")
    print("="*70)

    print("\n" + "-"*70)
    print("UNPROTECTED MODE RESULTS (require_validation=False):")
    print("-"*70)
    print(f"  Total attack attempts: {unprotected_exploitable + unprotected_blocked}")
    print(f"  EXPLOITABLE (System Gamed): {unprotected_exploitable}")
    print(f"  BLOCKED (System Defended): {unprotected_blocked}")
    if unprotected_exploitable + unprotected_blocked > 0:
        exploit_rate = (unprotected_exploitable / (unprotected_exploitable + unprotected_blocked)) * 100
        print(f"  Exploit success rate: {exploit_rate:.1f}%")

    print("\n" + "-"*70)
    print("PROTECTED MODE RESULTS (require_validation=True with MockValidator):")
    print("-"*70)
    print(f"  Total attack attempts: {protected_exploitable + protected_blocked}")
    print(f"  EXPLOITABLE (System Gamed): {protected_exploitable}")
    print(f"  BLOCKED (System Defended): {protected_blocked}")
    if protected_exploitable + protected_blocked > 0:
        block_rate = (protected_blocked / (protected_exploitable + protected_blocked)) * 100
        print(f"  Block success rate: {block_rate:.1f}%")

    # Calculate improvement
    if unprotected_exploitable > 0:
        improvement = ((unprotected_exploitable - protected_exploitable) / unprotected_exploitable) * 100
        print(f"\n  IMPROVEMENT: {improvement:.1f}% fewer successful attacks with validation enabled")

    print("\n" + "-"*70)
    print("FINDINGS BY CATEGORY (UNPROTECTED MODE):")
    print("-"*70)

    # Categorize findings from unprotected mode
    cryptographic_findings = []
    semantic_findings = []
    operational_findings = []

    for name, data in unprotected_results.items():
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

    print("\n[SEMANTIC LAYER - UNPROTECTED]")
    sem_vulnerable = sum(1 for f in semantic_findings if f["success"])
    print(f"  Status: {'SECURE' if sem_vulnerable == 0 else 'VULNERABLE without validation'}")
    print(f"  Exploits possible: {sem_vulnerable}/{len(semantic_findings)}")

    # Check protected mode semantic findings
    protected_sem_blocked = 0
    protected_sem_total = 0
    for name, data in protected_results.items():
        if name in ["Ambiguity Exploitation", "Intent Mismatch", "Adversarial Phrasing"]:
            if "attack_log" in data:
                for attack in data["attack_log"]:
                    protected_sem_total += 1
                    if not attack["success"]:
                        protected_sem_blocked += 1

    print("\n[SEMANTIC LAYER - PROTECTED]")
    print(f"  Status: {'SECURE' if protected_sem_blocked == protected_sem_total else 'PARTIALLY PROTECTED'}")
    print(f"  Attacks blocked: {protected_sem_blocked}/{protected_sem_total}")

    print("\n[OPERATIONAL LAYER]")
    op_vulnerable = sum(1 for f in operational_findings if f["success"])
    print(f"  Status: {'SECURE' if op_vulnerable == 0 else 'NEEDS ADDITIONAL HARDENING'}")
    print("  Note: Operational attacks (replay, flooding, timestamps) need separate fixes")

    # Check rate limiting results
    rate_limited_in_protected = 0
    if "Sybil Flooding" in protected_results and "results" in protected_results["Sybil Flooding"]:
        for r in protected_results["Sybil Flooding"]["results"]:
            rate_limited_in_protected = r.get("rate_limited", 0)

    # Check timestamp validation results
    timestamp_blocked = False
    if "Timestamp Manipulation" in protected_results and "results" in protected_results["Timestamp Manipulation"]:
        for r in protected_results["Timestamp Manipulation"]["results"]:
            timestamp_blocked = r.get("blocked_by_timestamp_validation", False)

    # Check metadata sanitization results
    metadata_sanitized = False
    if "Metadata Injection" in protected_results and "results" in protected_results["Metadata Injection"]:
        for r in protected_results["Metadata Injection"]["results"]:
            if r.get("stripped"):
                metadata_sanitized = True
                break

    # Check asset tracking results
    double_spend_blocked = False
    if "Double-Spending Analog" in protected_results and "results" in protected_results["Double-Spending Analog"]:
        for r in protected_results["Double-Spending Analog"]["results"]:
            if r.get("blocked_by_asset_tracking"):
                double_spend_blocked = True
                break

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print(f"""
  The NatLangChain blockchain with full protections enabled shows:

  BEFORE FIX (all protections disabled):
  - Semantic attacks: {sem_vulnerable}/{len(semantic_findings)} exploitable
  - Bad actors could submit ambiguous, mismatched, or adversarial entries
  - Replay attacks: possible (no deduplication)
  - Flooding attacks: possible (no rate limiting)
  - Timestamp manipulation: possible (no validation)
  - Metadata injection: possible (no sanitization)
  - Double-spending: possible (no asset tracking)

  AFTER FIX (all protections enabled):
  - Semantic attacks: {protected_sem_total - protected_sem_blocked}/{protected_sem_total} exploitable
  - PoU validation blocks most semantic layer attacks
  - Replay attacks: BLOCKED by entry deduplication
  - Flooding attacks: BLOCKED by rate limiting ({rate_limited_in_protected} entries blocked)
  - Timestamp manipulation: {'BLOCKED by timestamp validation' if timestamp_blocked else 'NOT BLOCKED'}
  - Metadata injection: {'BLOCKED by metadata sanitization' if metadata_sanitized else 'NOT BLOCKED'}
  - Double-spending: {'BLOCKED by asset tracking' if double_spend_blocked else 'NOT BLOCKED'}

  ALL SECURITY LAYERS IMPLEMENTED:

  The security improvements implemented include:
  1. require_validation=True - Enforces PoU semantic validation
  2. enable_deduplication=True - Prevents replay attacks
  3. enable_rate_limiting=True - Prevents Sybil/flooding attacks
  4. enable_timestamp_validation=True - Prevents backdating attacks
  5. enable_metadata_sanitization=True - Prevents metadata injection attacks
  6. enable_asset_tracking=True - Prevents double-spending attacks
""")

    return {
        "unprotected": unprotected_results,
        "protected": protected_results,
        "improvement_pct": improvement if unprotected_exploitable > 0 else 0
    }


# =============================================================================
# TEST ENTRY POINTS
# =============================================================================

def test_all_bad_actors():
    """Pytest-compatible test runner."""
    results = run_bad_actor_simulation()

    # Count critical failures
    critical_failures = 0
    for _name, data in results.items():
        # Skip non-dict values like improvement_pct
        if not isinstance(data, dict):
            continue
        if "attack_log" in data:
            for attack in data["attack_log"]:
                if attack["severity"] == "CRITICAL" and attack["success"]:
                    critical_failures += 1

    # The chain tampering attacks should be blocked (check in protected results)
    protected = results.get("protected", {})
    if isinstance(protected, dict) and "Chain Tampering" in protected:
        chain_tampering = protected["Chain Tampering"]
        if isinstance(chain_tampering, dict) and "attack_log" in chain_tampering:
            for attack in chain_tampering["attack_log"]:
                assert not attack["success"], f"CRITICAL: Chain tampering attack succeeded: {attack['details']}"

    print(f"\nTest completed with {critical_failures} critical vulnerabilities in non-crypto layer")


if __name__ == "__main__":
    run_bad_actor_simulation()
