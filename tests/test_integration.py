"""
Tests for integrated features (semantic search, drift detection, dialectic consensus)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry
from semantic_search import SemanticSearchEngine


def test_semantic_search():
    """Test semantic search functionality."""
    print("Testing semantic search...")

    # Create a blockchain with some entries
    chain = NatLangChain()

    entries = [
        NaturalLanguageEntry(
            content="The board of directors voted to approve the merger with TechCorp.",
            author="board",
            intent="Record merger decision"
        ),
        NaturalLanguageEntry(
            content="Alice transfers ownership of the vintage car to Bob for $25,000.",
            author="alice",
            intent="Transfer vehicle ownership"
        ),
        NaturalLanguageEntry(
            content="The company acquired new office space in downtown Manhattan.",
            author="realestate",
            intent="Real estate acquisition"
        ),
        NaturalLanguageEntry(
            content="Bob sells his classic automobile to Charlie for thirty thousand dollars.",
            author="bob",
            intent="Vehicle sale"
        )
    ]

    for entry in entries:
        chain.add_entry(entry)

    chain.mine_pending_entries(difficulty=1)

    # Create search engine
    search_engine = SemanticSearchEngine()

    # Search for vehicle-related entries
    # Should match both "vintage car" and "classic automobile" even though words differ
    results = search_engine.search(chain, "car sales and transfers", top_k=3)

    print(f"Found {len(results)} results for 'car sales and transfers'")

    # Verify we got results
    assert len(results) > 0, "Should find at least one result"

    # The top results should be vehicle-related
    top_result = results[0]
    assert top_result["score"] > 0.3, "Top result should have decent similarity score"

    print(f"✓ Semantic search test passed - found {len(results)} relevant entries")

    return True


def test_semantic_search_by_field():
    """Test semantic search on specific fields."""
    print("Testing field-specific semantic search...")

    chain = NatLangChain()

    entry = NaturalLanguageEntry(
        content="The financial transaction was completed successfully with all parties in agreement.",
        author="finance",
        intent="Record successful payment"
    )

    chain.add_entry(entry)
    chain.mine_pending_entries(difficulty=1)

    search_engine = SemanticSearchEngine()

    # Search in intent field for "payment"
    results = search_engine.search_by_field(
        chain, "payment processing", field="intent", top_k=5
    )

    print(f"Found {len(results)} results when searching intent field")

    assert len(results) > 0, "Should find results in intent field"

    print("✓ Field-specific search test passed")

    return True


def test_find_similar_entries():
    """Test finding similar entries."""
    print("Testing similar entry detection...")

    chain = NatLangChain()

    # Add similar entries
    similar_entries = [
        NaturalLanguageEntry(
            content="The stock price increased by 5% today.",
            author="market",
            intent="Price update"
        ),
        NaturalLanguageEntry(
            content="Equity values rose approximately five percent during trading.",
            author="market",
            intent="Market movement"
        ),
        NaturalLanguageEntry(
            content="The company hired three new engineers.",
            author="hr",
            intent="Hiring update"
        )
    ]

    for entry in similar_entries:
        chain.add_entry(entry)

    chain.mine_pending_entries(difficulty=1)

    search_engine = SemanticSearchEngine()

    # Find entries similar to the first stock price entry
    similar = search_engine.find_similar_entries(
        chain,
        "Stock market prices went up by 5 percent",
        top_k=3
    )

    print(f"Found {len(similar)} similar entries")

    # Should find the similar stock entries but not the hiring entry
    assert len(similar) >= 1, "Should find at least one similar entry"

    # Top similar should be stock-related, not hiring
    if len(similar) > 0:
        top_similar = similar[0]["entry"]
        assert "stock" in top_similar["content"].lower() or "equity" in top_similar["content"].lower(), \
            "Top similar entry should be stock-related"

    print("✓ Similar entry detection test passed")

    return True


def run_all_tests():
    """Run all integration tests."""
    print("\nRunning NatLangChain Integration Tests")
    print("=" * 50)

    try:
        test_semantic_search()
        test_semantic_search_by_field()
        test_find_similar_entries()

        print("=" * 50)
        print("All integration tests passed! ✓")
        print("\nNote: Drift detection and dialectic consensus require ANTHROPIC_API_KEY")
        print("These features will be tested via the API endpoints.")
        return True

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error during tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
