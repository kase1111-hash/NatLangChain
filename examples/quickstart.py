#!/usr/bin/env python3
"""
NatLangChain Quickstart Example

This example demonstrates the core concepts of NatLangChain:
1. Creating a blockchain with natural language entries
2. Adding entries (intents/agreements)
3. Mining blocks
4. Viewing the chain narrative

Run this example:
    python examples/quickstart.py

No API key required - this uses basic mode without LLM validation.
"""

import os
import sys

# Add src to path so we can import the blockchain
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry


def main():
    print("=" * 60)
    print("NatLangChain Quickstart")
    print("=" * 60)
    print()

    # ==========================================================================
    # Step 1: Create a blockchain
    # ==========================================================================
    # We disable validation features for this demo (no API key needed)
    # In production, you'd enable these for security

    print("Step 1: Creating blockchain...")
    chain = NatLangChain(
        require_validation=False,      # Skip LLM validation (no API key needed)
        enable_deduplication=False,    # Allow duplicate entries for demo
        enable_rate_limiting=False,    # No rate limits for demo
        enable_quality_checks=False,   # Skip quality analysis
    )
    print("  Created blockchain with genesis block")
    print(f"  Chain length: {len(chain.chain)} block(s)")
    print()

    # ==========================================================================
    # Step 2: Create and add natural language entries
    # ==========================================================================
    # Entries are the core of NatLangChain - natural language descriptions
    # of intents, agreements, or events

    print("Step 2: Adding entries...")

    # Entry 1: A service offer
    entry1 = NaturalLanguageEntry(
        content="""I, Alice, offer to provide 10 hours of Python tutoring
        to any interested party. Sessions will be conducted remotely via
        video call. I am available weekday evenings after 6 PM EST.""",
        author="alice@example.com",
        intent="Offer Python tutoring services",
        metadata={"category": "education", "hours": 10}
    )

    result1 = chain.add_entry(entry1)
    print(f"  Entry 1: {result1.get('status', 'added')}")

    # Entry 2: A response to the offer
    entry2 = NaturalLanguageEntry(
        content="""I, Bob, accept Alice's offer for Python tutoring.
        I am interested in learning about web development with Flask.
        I prefer Tuesday and Thursday evenings.""",
        author="bob@example.com",
        intent="Accept tutoring offer",
        metadata={"category": "education", "topic": "Flask"}
    )

    result2 = chain.add_entry(entry2)
    print(f"  Entry 2: {result2.get('status', 'added')}")

    # Entry 3: Agreement confirmation
    entry3 = NaturalLanguageEntry(
        content="""Alice and Bob have agreed to begin Python tutoring
        sessions starting next Tuesday at 7 PM EST. The first session
        will cover Flask basics and project setup.""",
        author="alice@example.com",
        intent="Confirm tutoring agreement",
        metadata={"category": "education", "session": 1}
    )

    result3 = chain.add_entry(entry3)
    print(f"  Entry 3: {result3.get('status', 'added')}")

    print(f"\n  Pending entries: {len(chain.pending_entries)}")
    print()

    # ==========================================================================
    # Step 3: Mine the pending entries into a block
    # ==========================================================================
    # Mining bundles pending entries into a block and adds it to the chain

    print("Step 3: Mining pending entries...")
    block = chain.mine_pending_entries(difficulty=2)

    if block:
        print(f"  Mined block #{block.index}")
        print(f"  Hash: {block.hash[:16]}...")
        print(f"  Entries in block: {len(block.entries)}")
        print(f"  Chain length: {len(chain.chain)} blocks")
    else:
        print("  No block mined (no pending entries)")
    print()

    # ==========================================================================
    # Step 4: View the blockchain
    # ==========================================================================

    print("Step 4: Viewing the chain...")
    print()

    for block in chain.chain:
        print(f"  Block #{block.index}")
        print(f"  ├── Hash: {block.hash[:32]}...")
        print(f"  ├── Previous: {block.previous_hash[:32]}...")
        print(f"  ├── Timestamp: {block.timestamp}")
        print(f"  └── Entries: {len(block.entries)}")

        for i, entry in enumerate(block.entries):
            prefix = "      └──" if i == len(block.entries) - 1 else "      ├──"
            # Truncate content for display
            content_preview = entry.content[:50].replace('\n', ' ') + "..."
            print(f"{prefix} [{entry.author}] {content_preview}")
        print()

    # ==========================================================================
    # Step 5: Chain statistics
    # ==========================================================================

    print("Step 5: Chain statistics")
    total_entries = sum(len(block.entries) for block in chain.chain)
    print(f"  Total blocks: {len(chain.chain)}")
    print(f"  Total entries: {total_entries}")
    print(f"  Pending entries: {len(chain.pending_entries)}")
    print()

    print("=" * 60)
    print("Quickstart complete!")
    print()
    print("Next steps:")
    print("  1. Start the API server: python run_server.py")
    print("  2. Visit http://localhost:5000/health")
    print("  3. See README.md for API usage examples")
    print("=" * 60)


if __name__ == "__main__":
    main()
