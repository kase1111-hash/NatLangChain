"""
Tests for NatLangChain blockchain functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry, Block


def test_genesis_block():
    """Test that genesis block is created correctly."""
    # Use require_validation=False, enable_deduplication=False, and enable_rate_limiting=False for unit tests
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)
    assert len(chain.chain) == 1
    assert chain.chain[0].index == 0
    assert chain.chain[0].previous_hash == "0"
    print("✓ Genesis block test passed")


def test_add_entry():
    """Test adding a natural language entry."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry = NaturalLanguageEntry(
        content="Alice transfers ownership of the vintage 1967 Mustang to Bob for $25,000.",
        author="alice",
        intent="Transfer vehicle ownership",
        metadata={"vehicle": "1967 Mustang", "price": 25000}
    )

    result = chain.add_entry(entry)
    assert result["status"] == "pending"
    assert len(chain.pending_entries) == 1
    print("✓ Add entry test passed")


def test_mine_block():
    """Test mining a block with pending entries."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry1 = NaturalLanguageEntry(
        content="The quarterly review meeting concluded with approval of three new initiatives.",
        author="board",
        intent="Record meeting outcome"
    )

    entry2 = NaturalLanguageEntry(
        content="Dr. Smith prescribed medication X for patient condition Y, dosage 50mg daily.",
        author="dr_smith",
        intent="Medical prescription"
    )

    chain.add_entry(entry1)
    chain.add_entry(entry2)

    assert len(chain.pending_entries) == 2

    mined_block = chain.mine_pending_entries(difficulty=1)

    assert mined_block is not None
    assert len(chain.chain) == 2
    assert len(chain.pending_entries) == 0
    assert len(mined_block.entries) == 2
    print("✓ Mine block test passed")


def test_chain_validation():
    """Test blockchain integrity validation."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry = NaturalLanguageEntry(
        content="Test entry for validation.",
        author="test",
        intent="Testing"
    )

    chain.add_entry(entry)
    chain.mine_pending_entries(difficulty=1)

    assert chain.validate_chain() is True
    print("✓ Chain validation test passed")


def test_get_entries_by_author():
    """Test retrieving entries by author."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry1 = NaturalLanguageEntry(
        content="Alice's first entry.",
        author="alice",
        intent="Test"
    )

    entry2 = NaturalLanguageEntry(
        content="Bob's entry.",
        author="bob",
        intent="Test"
    )

    entry3 = NaturalLanguageEntry(
        content="Alice's second entry.",
        author="alice",
        intent="Test"
    )

    chain.add_entry(entry1)
    chain.add_entry(entry2)
    chain.add_entry(entry3)
    chain.mine_pending_entries(difficulty=1)

    alice_entries = chain.get_entries_by_author("alice")
    assert len(alice_entries) == 2

    bob_entries = chain.get_entries_by_author("bob")
    assert len(bob_entries) == 1

    print("✓ Get entries by author test passed")


def test_narrative_generation():
    """Test full narrative generation."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry = NaturalLanguageEntry(
        content="This is a test entry for narrative generation.",
        author="test_user",
        intent="Testing narrative"
    )

    chain.add_entry(entry)
    chain.mine_pending_entries(difficulty=1)

    narrative = chain.get_full_narrative()

    assert "NatLangChain Narrative History" in narrative
    assert "test_user" in narrative
    assert "Testing narrative" in narrative
    print("✓ Narrative generation test passed")


def test_serialization():
    """Test blockchain serialization and deserialization."""
    chain = NatLangChain(require_validation=False, enable_deduplication=False, enable_rate_limiting=False, enable_timestamp_validation=False)

    entry = NaturalLanguageEntry(
        content="Serialization test entry.",
        author="test",
        intent="Test serialization"
    )

    chain.add_entry(entry)
    chain.mine_pending_entries(difficulty=1)

    # Serialize
    chain_dict = chain.to_dict()
    assert "chain" in chain_dict
    assert len(chain_dict["chain"]) == 2  # Genesis + 1 mined

    # Deserialize
    restored_chain = NatLangChain.from_dict(chain_dict)
    assert len(restored_chain.chain) == len(chain.chain)
    assert restored_chain.get_latest_block().hash == chain.get_latest_block().hash

    print("✓ Serialization test passed")


def run_all_tests():
    """Run all blockchain tests."""
    print("\nRunning NatLangChain Blockchain Tests")
    print("=" * 50)

    try:
        test_genesis_block()
        test_add_entry()
        test_mine_block()
        test_chain_validation()
        test_get_entries_by_author()
        test_narrative_generation()
        test_serialization()

        print("=" * 50)
        print("All tests passed! ✓")
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
