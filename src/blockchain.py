"""
NatLangChain - Natural Language Blockchain Implementation
Core blockchain data structures and logic
"""

import hashlib
import json
import time
from typing import List, Dict, Optional, Any
from datetime import datetime


class NaturalLanguageEntry:
    """
    A natural language entry in the blockchain.
    The core innovation: prose as the primary substrate.
    """

    def __init__(
        self,
        content: str,
        author: str,
        intent: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create a natural language entry.

        Args:
            content: The natural language prose describing the transaction/event
            author: Identifier of the entry creator
            intent: Brief summary of the entry's purpose
            metadata: Optional additional structured data
        """
        self.content = content
        self.author = author
        self.intent = intent
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.validation_status = "pending"
        self.validation_paraphrases = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary for serialization."""
        return {
            "content": self.content,
            "author": self.author,
            "intent": self.intent,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "validation_status": self.validation_status,
            "validation_paraphrases": self.validation_paraphrases
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NaturalLanguageEntry':
        """Create entry from dictionary."""
        entry = cls(
            content=data["content"],
            author=data["author"],
            intent=data["intent"],
            metadata=data.get("metadata", {})
        )
        entry.timestamp = data.get("timestamp", entry.timestamp)
        entry.validation_status = data.get("validation_status", "pending")
        entry.validation_paraphrases = data.get("validation_paraphrases", [])
        return entry


class Block:
    """
    A block in the NatLangChain.
    Contains natural language entries and maintains chain integrity.
    """

    def __init__(
        self,
        index: int,
        entries: List[NaturalLanguageEntry],
        previous_hash: str,
        nonce: int = 0
    ):
        """
        Create a new block.

        Args:
            index: Block position in chain
            entries: List of natural language entries
            previous_hash: Hash of the previous block
            nonce: Proof of work nonce
        """
        self.index = index
        self.timestamp = time.time()
        self.entries = entries
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """
        Calculate the cryptographic hash of this block.
        Combines traditional cryptographic security with linguistic content.
        """
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "entries": [entry.to_dict() for entry in self.entries],
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create block from dictionary."""
        entries = [NaturalLanguageEntry.from_dict(e) for e in data["entries"]]
        block = cls(
            index=data["index"],
            entries=entries,
            previous_hash=data["previous_hash"],
            nonce=data.get("nonce", 0)
        )
        block.timestamp = data["timestamp"]
        block.hash = data.get("hash", block.calculate_hash())
        return block


class NatLangChain:
    """
    The NatLangChain blockchain.
    A distributed ledger where natural language prose is the primary substrate.
    """

    def __init__(self):
        """Initialize the blockchain with genesis block."""
        self.chain: List[Block] = []
        self.pending_entries: List[NaturalLanguageEntry] = []
        self.create_genesis_block()

    def create_genesis_block(self):
        """Create the first block in the chain."""
        genesis_entry = NaturalLanguageEntry(
            content="This is the genesis block of the NatLangChain, a distributed ledger "
                   "paradigm where natural language prose is the primary substrate for "
                   "immutable entries. This chain enables linguistic consensus, validation, "
                   "and execution, preserving intent and enhancing auditability.",
            author="system",
            intent="Initialize the NatLangChain",
            metadata={"type": "genesis"}
        )
        genesis_entry.validation_status = "validated"

        genesis_block = Block(
            index=0,
            entries=[genesis_entry],
            previous_hash="0"
        )
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain."""
        return self.chain[-1]

    def add_entry(self, entry: NaturalLanguageEntry) -> Dict[str, Any]:
        """
        Add a new natural language entry to pending entries.

        Args:
            entry: The natural language entry to add

        Returns:
            Dict with entry information
        """
        self.pending_entries.append(entry)
        return {
            "status": "pending",
            "message": "Entry added to pending queue",
            "entry": entry.to_dict()
        }

    def mine_pending_entries(self, difficulty: int = 2) -> Optional[Block]:
        """
        Mine pending entries into a new block.
        Implements a simple proof-of-work for demonstration.

        Args:
            difficulty: Number of leading zeros required in hash

        Returns:
            The newly mined block or None if no pending entries
        """
        if not self.pending_entries:
            return None

        new_block = Block(
            index=len(self.chain),
            entries=self.pending_entries.copy(),
            previous_hash=self.get_latest_block().hash
        )

        # Simple proof of work
        target = "0" * difficulty
        while not new_block.hash.startswith(target):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()

        self.chain.append(new_block)
        self.pending_entries = []

        return new_block

    def validate_chain(self) -> bool:
        """
        Validate the entire blockchain for integrity.

        Returns:
            True if chain is valid, False otherwise
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check hash integrity
            if current_block.hash != current_block.calculate_hash():
                return False

            # Check chain linkage
            if current_block.previous_hash != previous_block.hash:
                return False

        return True

    def get_entries_by_author(self, author: str) -> List[Dict[str, Any]]:
        """
        Retrieve all entries by a specific author.

        Args:
            author: The author identifier

        Returns:
            List of entry dictionaries
        """
        entries = []
        for block in self.chain:
            for entry in block.entries:
                if entry.author == author:
                    entries.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "entry": entry.to_dict()
                    })
        return entries

    def get_entries_by_intent(self, intent_keyword: str) -> List[Dict[str, Any]]:
        """
        Search for entries by intent keyword.

        Args:
            intent_keyword: Keyword to search for in intent

        Returns:
            List of matching entry dictionaries
        """
        entries = []
        for block in self.chain:
            for entry in block.entries:
                if intent_keyword.lower() in entry.intent.lower():
                    entries.append({
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "entry": entry.to_dict()
                    })
        return entries

    def get_full_narrative(self) -> str:
        """
        Get the full narrative of the blockchain as readable text.
        This is the key innovation: the entire ledger as human-readable prose.

        Returns:
            The complete narrative history
        """
        narrative = []
        narrative.append("=== NatLangChain Narrative History ===\n")

        for block in self.chain:
            narrative.append(f"\n--- Block {block.index} ---")
            narrative.append(f"Hash: {block.hash}")
            narrative.append(f"Timestamp: {datetime.fromtimestamp(block.timestamp).isoformat()}")
            narrative.append(f"Previous Hash: {block.previous_hash}\n")

            for i, entry in enumerate(block.entries, 1):
                narrative.append(f"Entry {i}:")
                narrative.append(f"  Author: {entry.author}")
                narrative.append(f"  Intent: {entry.intent}")
                narrative.append(f"  Time: {entry.timestamp}")
                narrative.append(f"  Status: {entry.validation_status}")
                narrative.append(f"  Content:\n    {entry.content}")
                if entry.validation_paraphrases:
                    narrative.append(f"  Validation Paraphrases:")
                    for paraphrase in entry.validation_paraphrases:
                        narrative.append(f"    - {paraphrase}")
                narrative.append("")

        return "\n".join(narrative)

    def to_dict(self) -> Dict[str, Any]:
        """Export the entire chain as dictionary."""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_entries": [entry.to_dict() for entry in self.pending_entries]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NatLangChain':
        """Import chain from dictionary."""
        chain = cls.__new__(cls)
        chain.chain = [Block.from_dict(b) for b in data["chain"]]
        chain.pending_entries = [
            NaturalLanguageEntry.from_dict(e)
            for e in data.get("pending_entries", [])
        ]
        return chain
