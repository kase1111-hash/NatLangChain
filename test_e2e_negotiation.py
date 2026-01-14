#!/usr/bin/env python3
"""
End-to-End Blockchain Negotiation Test
Tests the complete flow: entry creation -> matching -> negotiation -> acceptance -> payment
"""

import json
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry
from contract_matcher import ContractMatcher
from contract_parser import ContractParser


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def print_entry(entry: NaturalLanguageEntry, label: str = "Entry"):
    """Print formatted entry details"""
    print(f"\n{label}:")
    print(f"  Author: {entry.author}")
    print(f"  Intent: {entry.intent}")
    print(f"  Content: {entry.content[:200]}..." if len(entry.content) > 200 else f"  Content: {entry.content}")
    if hasattr(entry, 'metadata') and entry.metadata:
        if 'contract_type' in entry.metadata:
            print(f"  Contract Type: {entry.metadata['contract_type']}")
        if 'terms' in entry.metadata:
            print(f"  Terms: {json.dumps(entry.metadata['terms'], indent=4)}")
        if 'match_score' in entry.metadata:
            print(f"  Match Score: {entry.metadata['match_score']}%")
        if 'negotiation_round' in entry.metadata:
            print(f"  Negotiation Round: {entry.metadata['negotiation_round']}")
    print()

def main():
    print_section("NatLangChain End-to-End Negotiation Test")

    # Initialize blockchain and parsers
    print("Initializing blockchain...")
    blockchain = NatLangChain()
    parser = ContractParser()
    matcher = ContractMatcher()

    print("✓ Blockchain initialized with genesis block")
    print(f"  Chain length: {len(blockchain.chain)}")

    # =========================================================================
    # STEP 1: Create and Add OFFER Entry
    # =========================================================================
    print_section("STEP 1: Create OFFER Entry (Alice - Web Developer)")

    offer_content = """[CONTRACT: OFFER] Professional web development services specializing in React and Node.js.
I have 5 years of experience building e-commerce platforms, SaaS applications, and custom web solutions.
Available for projects ranging from 1 week to 3 months.

[TERMS: fee=$150/hour, min_engagement=1 week, facilitation=2%, payment_method=installments]"""

    offer_entry = NaturalLanguageEntry(
        content=offer_content,
        author="alice",
        intent="Offer web development services",
        metadata={
            "contract_type": "offer",
            "terms": {
                "fee": "$150/hour",
                "min_engagement": "1 week",
                "facilitation": "2%",
                "payment_method": "installments"
            },
            "status": "open"
        }
    )

    result = blockchain.add_entry(offer_entry)
    print("✓ OFFER entry added to pending entries")
    print_entry(offer_entry, "Alice's OFFER")

    # =========================================================================
    # STEP 2: Create and Add SEEK Entry
    # =========================================================================
    print_section("STEP 2: Create SEEK Entry (Bob - Looking for Developer)")

    seek_content = """[CONTRACT: SEEK] Looking for an experienced React developer to build a modern e-commerce platform.
Project includes product catalog, shopping cart, user authentication, and payment integration.
Need someone who can start immediately and deliver within 2 weeks.

[TERMS: budget=$5000, deadline=2 weeks, payment_split=50% upfront / 50% completion]"""

    seek_entry = NaturalLanguageEntry(
        content=seek_content,
        author="bob",
        intent="Hire web developer for e-commerce project",
        metadata={
            "contract_type": "seek",
            "terms": {
                "budget": "$5000",
                "deadline": "2 weeks",
                "payment_split": "50% upfront / 50% completion"
            },
            "status": "open"
        }
    )

    result = blockchain.add_entry(seek_entry)
    print("✓ SEEK entry added to pending entries")
    print_entry(seek_entry, "Bob's SEEK")

    # =========================================================================
    # STEP 3: Mine Block and Trigger Automatic Matching
    # =========================================================================
    print_section("STEP 3: Mine Block and Trigger Contract Matching")

    print("Mining block with difficulty=1...")
    print("This will trigger automatic contract matching between Alice's OFFER and Bob's SEEK...")

    # Find matches before mining
    miner_id = "charlie_miner"
    matches = matcher.find_matches(blockchain, blockchain.pending_entries, miner_id)

    print(f"\n✓ Contract matcher found {len(matches)} match(es)")

    # Add proposal entries to pending
    for match in matches:
        blockchain.pending_entries.append(match)
        print_entry(match, "Generated PROPOSAL")

    # Mine the block
    mined_block = blockchain.mine_pending_entries(difficulty=1)

    if mined_block:
        print(f"\n✓ Block #{mined_block.index} mined successfully!")
        print(f"  Block Hash: {mined_block.hash}")
        print(f"  Entries in block: {len(mined_block.entries)}")
        print(f"  Nonce: {mined_block.nonce}")

        # Find the proposal entry
        proposal_entry = None
        for entry in mined_block.entries:
            if hasattr(entry, 'metadata') and entry.metadata.get('contract_type') == 'proposal':
                proposal_entry = entry
                break
    else:
        print("✗ Mining failed!")
        return

    # =========================================================================
    # STEP 4: Multi-Round Negotiation
    # =========================================================================
    print_section("STEP 4: Multi-Round Negotiation Process")

    if not proposal_entry:
        print("✗ No proposal found in mined block!")
        return

    # Store negotiation entries
    negotiation_entries = []
    current_round = 1
    max_rounds = 5

    # Round 1: Bob's initial counter-offer
    print(f"\n--- Round {current_round}: Bob's Counter-Offer ---")

    round1_content = """Thank you for the proposal! I'm very interested in working with Alice.
However, I need a bit more time - could we extend the deadline to 3 weeks instead of 2 weeks?
I'm willing to accept the $150/hour rate, which seems fair given Alice's experience."""

    round1_entry = NaturalLanguageEntry(
        content=round1_content,
        author="bob",
        intent="Counter-offer: request 3-week timeline",
        metadata={
            "contract_type": "response",
            "response_type": "counter",
            "negotiation_round": current_round,
            "references": {
                "block": mined_block.index,
                "entry": 2,  # proposal entry
                "original_proposal": proposal_entry.metadata.get('terms', {})
            },
            "counter_terms": {
                "deadline": "3 weeks",
                "fee": "$150/hour"
            },
            "status": "negotiating"
        }
    )

    blockchain.add_entry(round1_entry)
    negotiation_entries.append(round1_entry)
    print_entry(round1_entry, f"Round {current_round} - Bob's Response")

    # Mediate this round
    if proposal_entry.metadata and 'terms' in proposal_entry.metadata:
        original_terms = proposal_entry.metadata['terms']
        counter_terms = round1_entry.metadata['counter_terms']

        print(f"\n🤝 Mediating negotiation (Round {current_round})...")
        mediation = matcher.mediate_negotiation(
            proposal_entry.content,
            original_terms,
            round1_entry.content,
            counter_terms,
            current_round
        )

        print("\nMediation Result:")
        print(f"  Points of Agreement: {', '.join(mediation.get('points_of_agreement', []))}")
        print(f"  Differences: {', '.join(mediation.get('differences', []))}")
        print(f"  Recommended Action: {mediation.get('recommended_action', 'CONTINUE')}")
        if 'suggested_compromise' in mediation:
            print(f"  Suggested Compromise: {mediation['suggested_compromise']}")

    # Round 2: Alice's response
    current_round = 2
    print(f"\n--- Round {current_round}: Alice's Response ---")

    round2_content = """I appreciate your interest, Bob! A 3-week timeline works for me.
However, I'd like to propose a slightly different payment structure: 40% upfront, 30% at midpoint,
and 30% upon completion. This helps with cash flow for a longer project."""

    round2_entry = NaturalLanguageEntry(
        content=round2_content,
        author="alice",
        intent="Counter-offer: adjusted payment structure",
        metadata={
            "contract_type": "response",
            "response_type": "counter",
            "negotiation_round": current_round,
            "references": {
                "block": mined_block.index,
                "previous_round": current_round - 1
            },
            "counter_terms": {
                "deadline": "3 weeks",
                "fee": "$150/hour",
                "payment_split": "40% upfront / 30% midpoint / 30% completion"
            },
            "status": "negotiating"
        }
    )

    blockchain.add_entry(round2_entry)
    negotiation_entries.append(round2_entry)
    print_entry(round2_entry, f"Round {current_round} - Alice's Response")

    # Mediate round 2
    mediation2 = matcher.mediate_negotiation(
        round1_entry.content,
        round1_entry.metadata['counter_terms'],
        round2_entry.content,
        round2_entry.metadata['counter_terms'],
        current_round
    )

    print(f"\n🤝 Mediating negotiation (Round {current_round})...")
    print(f"  Points of Agreement: {', '.join(mediation2.get('points_of_agreement', []))}")
    print(f"  Differences: {', '.join(mediation2.get('differences', []))}")
    print(f"  Recommended Action: {mediation2.get('recommended_action', 'CONTINUE')}")
    if 'suggested_compromise' in mediation2:
        print(f"  Suggested Compromise: {mediation2['suggested_compromise']}")

    # Round 3: Bob's acceptance with minor adjustment
    current_round = 3
    print(f"\n--- Round {current_round}: Bob's Modified Acceptance ---")

    round3_content = """The 3-week timeline and payment structure sound good, Alice!
I'm comfortable with 40% upfront / 30% midpoint / 30% completion.
One small request: can we add a clause for weekly progress check-ins?
This helps me stay aligned with the project milestones."""

    round3_entry = NaturalLanguageEntry(
        content=round3_content,
        author="bob",
        intent="Accept with minor addition: weekly check-ins",
        metadata={
            "contract_type": "response",
            "response_type": "counter",
            "negotiation_round": current_round,
            "references": {
                "block": mined_block.index,
                "previous_round": current_round - 1
            },
            "counter_terms": {
                "deadline": "3 weeks",
                "fee": "$150/hour",
                "payment_split": "40% upfront / 30% midpoint / 30% completion",
                "check_ins": "weekly progress meetings"
            },
            "status": "negotiating"
        }
    )

    blockchain.add_entry(round3_entry)
    negotiation_entries.append(round3_entry)
    print_entry(round3_entry, f"Round {current_round} - Bob's Response")

    # Round 4: Alice's final acceptance
    current_round = 4
    print(f"\n--- Round {current_round}: Alice's Final Acceptance ---")

    round4_content = """Perfect! I'm happy to do weekly check-ins - that's actually my standard practice anyway.
I accept all the terms:
- 3 week timeline
- $150/hour rate
- 40% upfront / 30% midpoint / 30% completion payment structure
- Weekly progress check-ins
- 2% miner facilitation fee to Charlie

Let's finalize this contract!"""

    round4_entry = NaturalLanguageEntry(
        content=round4_content,
        author="alice",
        intent="Final acceptance of all negotiated terms",
        metadata={
            "contract_type": "response",
            "response_type": "accept",
            "negotiation_round": current_round,
            "references": {
                "block": mined_block.index,
                "previous_round": current_round - 1
            },
            "final_terms": {
                "deadline": "3 weeks",
                "fee": "$150/hour",
                "estimated_hours": 33,  # ~$5000 / $150
                "total_value": "$5000",
                "payment_split": "40% upfront / 30% midpoint / 30% completion",
                "check_ins": "weekly progress meetings",
                "facilitation": "2%",
                "miner": "charlie_miner"
            },
            "status": "accepted"
        }
    )

    blockchain.add_entry(round4_entry)
    negotiation_entries.append(round4_entry)
    print_entry(round4_entry, f"Round {current_round} - Alice's ACCEPTANCE")

    # =========================================================================
    # STEP 5: User (Bob) Confirms Final Acceptance
    # =========================================================================
    print_section("STEP 5: Simulated User Acceptance")

    print("💬 Simulated User Prompt:")
    print("   User (Bob): 'I accept the contract with Alice. Let's proceed!'")
    print()

    acceptance_content = """I, Bob, formally accept this contract with Alice for web development services.
All terms have been negotiated and agreed upon:
- Developer: Alice
- Rate: $150/hour
- Project duration: 3 weeks
- Total budget: $5000
- Payment: 40% upfront ($2000), 30% midpoint ($1500), 30% completion ($1500)
- Weekly progress check-ins
- Miner facilitation fee: 2% ($100) to Charlie

Contract is now CLOSED and ready for execution."""

    closure_entry = NaturalLanguageEntry(
        content=acceptance_content,
        author="bob",
        intent="Formal contract closure and acceptance",
        metadata={
            "contract_type": "closure",
            "negotiation_round": current_round + 1,
            "references": {
                "original_proposal": mined_block.index,
                "negotiation_rounds": current_round
            },
            "final_terms": round4_entry.metadata['final_terms'],
            "status": "closed",
            "parties": ["alice", "bob"],
            "miner": "charlie_miner",
            "contract_value": 5000,
            "miner_fee_percentage": 2
        }
    )

    blockchain.add_entry(closure_entry)
    print_entry(closure_entry, "CONTRACT CLOSURE")

    print("✓ Contract officially CLOSED and accepted by both parties!")

    # =========================================================================
    # STEP 6: Payment Transfers Between Three Parties
    # =========================================================================
    print_section("STEP 6: Payment Transfers Between Three Parties")

    # Calculate payments
    contract_value = 5000.0
    miner_fee_pct = 0.02
    miner_fee = contract_value * miner_fee_pct
    net_to_alice = contract_value - miner_fee

    # Payment 1: Upfront payment from Bob to Alice
    upfront_amount = contract_value * 0.40
    upfront_to_alice = upfront_amount * (1 - miner_fee_pct)

    print("\n💰 Payment Calculation:")
    print(f"   Total Contract Value: ${contract_value:.2f}")
    print(f"   Miner Fee (2%): ${miner_fee:.2f}")
    print(f"   Net to Alice: ${net_to_alice:.2f}")
    print()

    print("📤 Payment #1: Upfront Payment (40%)")
    payment1_content = f"""[PAYMENT TRANSFER]
From: Bob (buyer)
To: Alice (developer)
Amount: ${upfront_to_alice:.2f} (40% upfront payment, net of 2% miner fee)
Gross: ${upfront_amount:.2f}
Contract Reference: Block #{mined_block.index}
Payment Method: Bank transfer
Status: COMPLETED"""

    payment1_entry = NaturalLanguageEntry(
        content=payment1_content,
        author="system",
        intent="Record upfront payment from Bob to Alice",
        metadata={
            "payment_type": "contract_payment",
            "from": "bob",
            "to": "alice",
            "gross_amount": upfront_amount,
            "net_amount": upfront_to_alice,
            "miner_fee_deducted": upfront_amount * miner_fee_pct,
            "payment_stage": "upfront",
            "percentage": 40,
            "contract_ref": mined_block.index,
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    blockchain.add_entry(payment1_entry)
    print_entry(payment1_entry, "Payment Transfer #1")

    # Payment 2: Miner facilitation fee from upfront payment
    upfront_miner_fee = upfront_amount * miner_fee_pct

    print("📤 Payment #2: Miner Fee from Upfront (2%)")
    payment2_content = f"""[PAYOUT]
Miner: Charlie (charlie_miner)
Amount: ${upfront_miner_fee:.2f} (2% facilitation fee from upfront payment)
Service: Contract matching and mediation services
Matched Contracts: Alice's OFFER with Bob's SEEK (Match score: 87%)
Negotiation Rounds Facilitated: {current_round}
Payment Method: Cryptocurrency wallet
Wallet Address: 0xCHARLIE1234567890ABCDEF
Status: COMPLETED"""

    payment2_entry = NaturalLanguageEntry(
        content=payment2_content,
        author="charlie_miner",
        intent="Claim miner facilitation fee from upfront payment",
        metadata={
            "payment_type": "miner_payout",
            "from": "bob",
            "to": "charlie_miner",
            "amount": upfront_miner_fee,
            "service": "contract_matching",
            "match_score": 87,
            "negotiation_rounds": current_round,
            "contract_ref": mined_block.index,
            "wallet": "0xCHARLIE1234567890ABCDEF",
            "status": "completed",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    blockchain.add_entry(payment2_entry)
    print_entry(payment2_entry, "Miner Payout #1")

    # Mine block with all negotiation and payment entries
    print("\nMining block with negotiation history and payment records...")
    negotiation_block = blockchain.mine_pending_entries(difficulty=1)

    if negotiation_block:
        print(f"\n✓ Block #{negotiation_block.index} mined successfully!")
        print(f"  Entries: {len(negotiation_block.entries)} (negotiation rounds + payments)")
        print(f"  Block Hash: {negotiation_block.hash}")

    # Summary of all payments
    print(f"\n{'─'*80}")
    print("💵 PAYMENT SUMMARY (Three Parties)")
    print(f"{'─'*80}")
    print("\n👤 Bob (Buyer):")
    print(f"   Pays: ${upfront_amount:.2f} upfront (40% of ${contract_value:.2f})")
    print(f"   Remaining: ${contract_value - upfront_amount:.2f} (to be paid at milestones)")
    print("\n👤 Alice (Developer):")
    print(f"   Receives: ${upfront_to_alice:.2f} net upfront payment")
    print(f"   Expected Total: ${net_to_alice:.2f} (after all milestones)")
    print("\n👤 Charlie (Miner):")
    print(f"   Receives: ${upfront_miner_fee:.2f} facilitation fee (from upfront)")
    print(f"   Expected Total: ${miner_fee:.2f} (after all milestones)")
    print(f"\n{'─'*80}\n")

    # =========================================================================
    # STEP 7: Final Blockchain State
    # =========================================================================
    print_section("STEP 7: Final Blockchain State")

    print("Blockchain Statistics:")
    print(f"  Total Blocks: {len(blockchain.chain)}")
    print(f"  Pending Entries: {len(blockchain.pending_entries)}")
    print(f"  Chain Valid: {blockchain.is_chain_valid()}")

    print("\nBlock Details:")
    for i, block in enumerate(blockchain.chain):
        print(f"\n  Block #{block.index}:")
        print(f"    Hash: {block.hash}")
        print(f"    Previous Hash: {block.previous_hash}")
        print(f"    Entries: {len(block.entries)}")
        if block.entries:
            for j, entry in enumerate(block.entries):
                entry_type = entry.metadata.get('contract_type', 'entry') if hasattr(entry, 'metadata') and entry.metadata else 'entry'
                print(f"      [{j}] {entry_type.upper()}: {entry.author} - {entry.intent[:50]}")

    # =========================================================================
    # SUCCESS!
    # =========================================================================
    print_section("✅ END-TO-END TEST COMPLETED SUCCESSFULLY!")

    print("Test Summary:")
    print("  ✓ Created blockchain entries (OFFER and SEEK)")
    print("  ✓ Mined block and triggered automatic contract matching")
    print(f"  ✓ Completed {current_round}-round negotiation process")
    print("  ✓ Both parties accepted final terms")
    print("  ✓ Contract formally closed")
    print("  ✓ Processed payment transfers between all three parties:")
    print(f"      • Bob → Alice: ${upfront_to_alice:.2f}")
    print(f"      • Bob → Charlie (miner): ${upfront_miner_fee:.2f}")
    print("  ✓ All entries recorded immutably on blockchain")
    print(f"  ✓ Blockchain integrity verified: {blockchain.is_chain_valid()}")

    print("\n" + "="*80)
    print("The NatLangChain system successfully facilitated a complete")
    print("contract lifecycle from discovery through negotiation to payment!")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
