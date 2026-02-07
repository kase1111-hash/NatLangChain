#!/usr/bin/env python3
"""
NatLangChain End-to-End Demo

Demonstrates the complete core loop:
1. Start the API (in-process via Flask test client)
2. Submit an "offer" contract entry
3. Submit a "seek" contract entry
4. Mine entries into a block
5. Trigger contract matching (if LLM available)
6. Show the full chain narrative

Usage:
    python demo.py

Works with or without ANTHROPIC_API_KEY:
- With key: Full Proof of Understanding validation + LLM contract matching
- Without key: Entries accepted in basic mode, contract matching unavailable
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from api import create_app


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def pretty(data):
    print(json.dumps(data, indent=2, default=str))


def main():
    print("NatLangChain — End-to-End Core Loop Demo")
    print("=" * 60)

    # ──────────────────────────────────────────────────────────
    # Step 0: Create the app and test client
    # ──────────────────────────────────────────────────────────
    section("Step 0: Initialize")

    os.environ.setdefault("NATLANGCHAIN_REQUIRE_AUTH", "false")
    os.environ.setdefault("STORAGE_BACKEND", "memory")

    has_api_key = bool(os.getenv("ANTHROPIC_API_KEY"))

    app = create_app(testing=True)
    client = app.test_client()

    # Initialize managers (LLM features) if API key is available
    if has_api_key:
        from api import init_managers
        init_managers(os.getenv("ANTHROPIC_API_KEY"))

    # Configure blockchain for demo mode:
    # Accept entries without LLM validation when no API key is present
    from api import state
    from blockchain import NatLangChain

    state.blockchain = NatLangChain(
        require_validation=has_api_key,
        enable_deduplication=True,
        enable_quality_checks=False,
    )

    # Check health
    resp = client.get("/health")
    health = resp.get_json()
    print(f"Health: {health.get('status', 'ok')}")

    # Check feature availability
    resp = client.get("/stats")
    stats = resp.get_json()
    features = stats.get("features", {})
    print(f"LLM validation: {'enabled' if features.get('llm_validation') else 'disabled (no API key)'}")
    print(f"Contract management: {'enabled' if features.get('contract_management') else 'disabled'}")
    print(f"Semantic search: {'enabled' if features.get('semantic_search') else 'disabled'}")

    # ──────────────────────────────────────────────────────────
    # Step 1: Submit an "offer" entry
    # ──────────────────────────────────────────────────────────
    section("Step 1: Submit Offer Entry")

    offer_payload = {
        "content": (
            "I am a freelance illustrator offering character design services "
            "for indie games. $500-1000 per character sheet, 2-week turnaround. "
            "Portfolio includes 50+ published game characters across mobile and "
            "PC titles. Specializing in stylized anime and western cartoon styles."
        ),
        "author": "illustrator@example.com",
        "intent": "Offer character design services for indie game developers",
        "validate": True,
    }

    resp = client.post("/entry", json=offer_payload)
    offer_result = resp.get_json()
    print(f"Status: {resp.status_code}")
    print(f"Entry status: {offer_result.get('entry', {}).get('status', 'unknown')}")

    validation = offer_result.get("validation", {})
    if validation:
        mode = validation.get("validation_mode", "none")
        decision = validation.get("overall_decision", "N/A")
        print(f"Validation mode: {mode}")
        print(f"Validation decision: {decision}")

    # ──────────────────────────────────────────────────────────
    # Step 2: Submit a "seek" entry
    # ──────────────────────────────────────────────────────────
    section("Step 2: Submit Seek Entry")

    seek_payload = {
        "content": (
            "Small indie studio looking for character artist for our RPG project. "
            "Budget $800 per character, need 5 characters over 3 months. "
            "Art style: stylized anime with fantasy elements. "
            "Must have experience with game-ready asset delivery."
        ),
        "author": "studio@indiegames.com",
        "intent": "Seeking character artist for RPG project",
        "validate": True,
    }

    resp = client.post("/entry", json=seek_payload)
    seek_result = resp.get_json()
    print(f"Status: {resp.status_code}")
    print(f"Entry status: {seek_result.get('entry', {}).get('status', 'unknown')}")

    validation = seek_result.get("validation", {})
    if validation:
        mode = validation.get("validation_mode", "none")
        decision = validation.get("overall_decision", "N/A")
        print(f"Validation mode: {mode}")
        print(f"Validation decision: {decision}")

    # Check pending
    resp = client.get("/pending")
    pending = resp.get_json()
    print(f"\nPending entries: {pending.get('count', 0)}")

    # ──────────────────────────────────────────────────────────
    # Step 3: Mine pending entries into a block
    # ──────────────────────────────────────────────────────────
    section("Step 3: Mine Block")

    resp = client.post("/mine", json={"difficulty": 2})
    mine_result = resp.get_json()
    print(f"Status: {resp.status_code}")

    if "block" in mine_result:
        block = mine_result["block"]
        print(f"Mined block #{block.get('index')}")
        print(f"Hash: {block.get('hash', '')[:32]}...")
        print(f"Entries in block: {block.get('entries_count', 0)}")
    else:
        print(f"Result: {mine_result}")

    # ──────────────────────────────────────────────────────────
    # Step 4: Contract matching (requires LLM)
    # ──────────────────────────────────────────────────────────
    section("Step 4: Contract Matching")

    if features.get("contract_management"):
        # Parse the offer
        resp = client.post("/contract/parse", json={"content": offer_payload["content"]})
        parse_result = resp.get_json()
        print("Offer parsed:")
        if "parsed" in parse_result:
            parsed = parse_result["parsed"]
            print(f"  Is contract: {parsed.get('is_contract')}")
            print(f"  Type: {parsed.get('contract_type')}")
            print(f"  Terms: {parsed.get('terms', {})}")

        # Try matching
        resp = client.post("/contract/match", json={"miner_id": "demo-miner"})
        match_result = resp.get_json()
        print(f"\nContract matching:")
        print(f"  Matches found: {match_result.get('count', 0)}")
        if match_result.get("matches"):
            for m in match_result["matches"][:3]:
                print(f"  - {m}")
    else:
        print("Contract matching requires ANTHROPIC_API_KEY.")
        print("Set the key in .env to enable LLM features.")
        print("\nWithout LLM, entries are still recorded immutably on the chain.")

    # ──────────────────────────────────────────────────────────
    # Step 5: Verify chain integrity
    # ──────────────────────────────────────────────────────────
    section("Step 5: Verify Chain")

    resp = client.get("/validate/chain")
    chain_valid = resp.get_json()
    print(f"Chain valid: {chain_valid.get('valid')}")
    print(f"Total blocks: {chain_valid.get('blocks')}")
    print(f"Pending entries: {chain_valid.get('pending_entries')}")

    # ──────────────────────────────────────────────────────────
    # Step 6: Full narrative
    # ──────────────────────────────────────────────────────────
    section("Step 6: Full Chain Narrative")

    resp = client.get("/chain/narrative")
    narrative = resp.data.decode("utf-8")
    # Print first 1000 chars to keep demo output manageable
    if len(narrative) > 1000:
        print(narrative[:1000])
        print(f"\n... ({len(narrative)} total characters)")
    else:
        print(narrative)

    # ──────────────────────────────────────────────────────────
    # Summary
    # ──────────────────────────────────────────────────────────
    section("Demo Complete")

    resp = client.get("/stats")
    final_stats = resp.get_json()
    print(f"Blocks:          {final_stats.get('blocks')}")
    print(f"Total entries:   {final_stats.get('total_entries')}")
    print(f"Unique authors:  {final_stats.get('unique_authors')}")
    print(f"Chain valid:     {final_stats.get('chain_valid')}")
    print()
    print("The core loop works: post intent -> validate -> mine -> query.")
    print()
    if not features.get("llm_validation"):
        print("To enable full LLM validation and contract matching:")
        print("  export ANTHROPIC_API_KEY=your_key_here")
        print("  python demo.py")


if __name__ == "__main__":
    main()
