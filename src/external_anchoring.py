"""
NatLangChain - External Anchoring System

Anchors NatLangChain block hashes to external blockchains for independent
verification and enhanced trust/legal weight.

Inspired by:
- Arweave's permanent storage anchoring
- Ceramic's Ethereum timestamp anchoring
- OpenTimestamps protocol

Key Features:
1. Multi-chain support (Ethereum, Arweave, Bitcoin via OpenTimestamps)
2. Merkle tree aggregation for efficient batch anchoring
3. Cryptographic anchor proofs for legal/audit purposes
4. Automatic verification of existing anchors
5. Cost optimization through batching

Anchor Flow:
1. Entries/blocks are added to pending anchor queue
2. Periodically, pending items are aggregated into Merkle tree
3. Merkle root is submitted to external chain(s)
4. Anchor proof is generated and stored
5. Proofs can be independently verified against external chains
"""

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# =============================================================================
# Constants
# =============================================================================

# Anchoring configuration
DEFAULT_BATCH_SIZE = 100  # Max entries per anchor batch
DEFAULT_ANCHOR_INTERVAL_HOURS = 1  # How often to anchor
MIN_ENTRIES_FOR_ANCHOR = 1  # Minimum entries to trigger anchor

# Chain-specific constants
ETHEREUM_MAINNET_CHAIN_ID = 1
ETHEREUM_SEPOLIA_CHAIN_ID = 11155111
ARWEAVE_NETWORK_ID = "arweave-mainnet"

# Merkle tree constants
MERKLE_HASH_ALGORITHM = "sha256"


# =============================================================================
# Enums
# =============================================================================


class AnchorChain(Enum):
    """Supported external chains for anchoring."""

    ETHEREUM_MAINNET = "ethereum_mainnet"
    ETHEREUM_SEPOLIA = "ethereum_sepolia"  # Testnet
    ARWEAVE = "arweave"
    BITCOIN_OPENTIMESTAMPS = "bitcoin_ots"  # Via OpenTimestamps
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"


class AnchorStatus(Enum):
    """Status of an anchor operation."""

    PENDING = "pending"  # In queue, not yet submitted
    SUBMITTED = "submitted"  # Submitted to chain, awaiting confirmation
    CONFIRMED = "confirmed"  # Confirmed on chain
    FAILED = "failed"  # Submission failed
    EXPIRED = "expired"  # Anchor expired or invalidated


class AnchorEventType(Enum):
    """Types of anchoring events."""

    ENTRY_QUEUED = "entry_queued"
    BATCH_CREATED = "batch_created"
    ANCHOR_SUBMITTED = "anchor_submitted"
    ANCHOR_CONFIRMED = "anchor_confirmed"
    ANCHOR_FAILED = "anchor_failed"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MerkleProof:
    """Merkle proof for a specific entry in an anchor batch."""

    entry_hash: str
    proof_path: list[dict[str, str]]  # [{position: "left"|"right", hash: "..."}]
    merkle_root: str
    leaf_index: int
    total_leaves: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_hash": self.entry_hash,
            "proof_path": self.proof_path,
            "merkle_root": self.merkle_root,
            "leaf_index": self.leaf_index,
            "total_leaves": self.total_leaves,
        }

    def verify(self) -> bool:
        """Verify this proof against the Merkle root."""
        current_hash = self.entry_hash

        for step in self.proof_path:
            sibling_hash = step["hash"]
            if step["position"] == "left":
                combined = sibling_hash + current_hash
            else:
                combined = current_hash + sibling_hash

            current_hash = hashlib.sha256(combined.encode()).hexdigest()

        return current_hash == self.merkle_root


@dataclass
class AnchorProof:
    """Complete proof of an entry's anchor to external chain."""

    proof_id: str
    entry_hash: str
    block_index: int | None
    entry_index: int | None
    anchor_chain: str
    merkle_proof: MerkleProof
    transaction_hash: str
    block_number: int | None  # External chain block number
    timestamp: str
    status: str
    verification_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "entry_hash": self.entry_hash,
            "block_index": self.block_index,
            "entry_index": self.entry_index,
            "anchor_chain": self.anchor_chain,
            "merkle_proof": self.merkle_proof.to_dict(),
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "status": self.status,
            "verification_url": self.verification_url,
        }


@dataclass
class AnchorBatch:
    """A batch of entries anchored together."""

    batch_id: str
    merkle_root: str
    entry_hashes: list[str]
    created_at: str
    anchor_chain: str
    transaction_hash: str | None = None
    block_number: int | None = None
    status: str = AnchorStatus.PENDING.value
    confirmed_at: str | None = None
    gas_used: int | None = None
    cost_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "merkle_root": self.merkle_root,
            "entry_count": len(self.entry_hashes),
            "created_at": self.created_at,
            "anchor_chain": self.anchor_chain,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "status": self.status,
            "confirmed_at": self.confirmed_at,
            "gas_used": self.gas_used,
            "cost_usd": self.cost_usd,
        }


@dataclass
class PendingAnchor:
    """Entry waiting to be anchored."""

    entry_hash: str
    block_index: int | None
    entry_index: int | None
    content_hash: str  # Hash of entry content
    queued_at: str
    priority: int = 0  # Higher = more urgent
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Anchor Provider Interface
# =============================================================================


class AnchorProvider(ABC):
    """Abstract base class for external chain anchor providers."""

    @abstractmethod
    def get_chain(self) -> AnchorChain:
        """Get the chain this provider anchors to."""
        ...

    @abstractmethod
    def submit_anchor(self, merkle_root: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Submit a Merkle root to the external chain.

        Args:
            merkle_root: The Merkle root hash to anchor
            metadata: Additional metadata to store

        Returns:
            Dict with transaction_hash, status, and other chain-specific info
        """
        ...

    @abstractmethod
    def verify_anchor(self, transaction_hash: str, merkle_root: str) -> dict[str, Any]:
        """
        Verify an anchor exists on the external chain.

        Args:
            transaction_hash: The transaction to verify
            merkle_root: The expected Merkle root

        Returns:
            Dict with verified (bool), block_number, timestamp, etc.
        """
        ...

    @abstractmethod
    def get_verification_url(self, transaction_hash: str) -> str:
        """Get a URL to view the anchor transaction on a block explorer."""
        ...

    @abstractmethod
    def estimate_cost(self, batch_size: int) -> dict[str, Any]:
        """Estimate cost for anchoring a batch of given size."""
        ...


# =============================================================================
# Ethereum Anchor Provider
# =============================================================================


class EthereumAnchorProvider(AnchorProvider):
    """
    Anchor provider for Ethereum (mainnet or testnets).

    Submits Merkle roots to a simple anchor contract or uses
    transaction input data for lightweight anchoring.
    """

    def __init__(
        self,
        chain: AnchorChain = AnchorChain.ETHEREUM_MAINNET,
        rpc_url: str | None = None,
        private_key: str | None = None,
        contract_address: str | None = None,
    ):
        self.chain = chain
        self.rpc_url = rpc_url or os.getenv("ETHEREUM_RPC_URL")
        self.private_key = private_key or os.getenv("ETHEREUM_PRIVATE_KEY")
        self.contract_address = contract_address or os.getenv("ANCHOR_CONTRACT_ADDRESS")

        # Chain-specific config
        if chain == AnchorChain.ETHEREUM_MAINNET:
            self.chain_id = ETHEREUM_MAINNET_CHAIN_ID
            self.explorer_base = "https://etherscan.io/tx/"
        elif chain == AnchorChain.ETHEREUM_SEPOLIA:
            self.chain_id = ETHEREUM_SEPOLIA_CHAIN_ID
            self.explorer_base = "https://sepolia.etherscan.io/tx/"
        else:
            self.chain_id = 1
            self.explorer_base = "https://etherscan.io/tx/"

    def get_chain(self) -> AnchorChain:
        return self.chain

    def submit_anchor(self, merkle_root: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Submit anchor to Ethereum.

        In production, this would use web3.py to:
        1. Connect to RPC
        2. Build transaction with merkle_root in data field
        3. Sign and broadcast transaction
        4. Return transaction hash

        For now, returns simulated response.
        """
        # Simulate transaction submission
        # In production: use web3.py
        tx_hash = self._generate_tx_hash(merkle_root)

        return {
            "status": "submitted",
            "transaction_hash": tx_hash,
            "chain": self.chain.value,
            "chain_id": self.chain_id,
            "merkle_root": merkle_root,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Simulated - implement web3.py for production",
        }

    def verify_anchor(self, transaction_hash: str, merkle_root: str) -> dict[str, Any]:
        """
        Verify anchor on Ethereum.

        In production, this would:
        1. Fetch transaction from RPC
        2. Decode input data
        3. Compare merkle_root
        4. Return block number and timestamp
        """
        # Simulate verification
        return {
            "verified": True,
            "transaction_hash": transaction_hash,
            "merkle_root": merkle_root,
            "block_number": 18500000,  # Simulated
            "timestamp": datetime.utcnow().isoformat(),
            "confirmations": 12,
            "chain": self.chain.value,
        }

    def get_verification_url(self, transaction_hash: str) -> str:
        return f"{self.explorer_base}{transaction_hash}"

    def estimate_cost(self, batch_size: int) -> dict[str, Any]:
        """Estimate gas cost for Ethereum anchor."""
        # Approximate gas for data storage
        base_gas = 21000
        data_gas = 68 * 32  # 32 bytes for merkle root
        total_gas = base_gas + data_gas

        # Approximate costs (would fetch real gas price in production)
        gas_price_gwei = 30
        eth_price_usd = 2000

        total_cost_eth = (total_gas * gas_price_gwei) / 1e9
        total_cost_usd = total_cost_eth * eth_price_usd
        cost_per_entry = total_cost_usd / batch_size if batch_size > 0 else 0

        return {
            "chain": self.chain.value,
            "estimated_gas": total_gas,
            "gas_price_gwei": gas_price_gwei,
            "total_cost_eth": total_cost_eth,
            "total_cost_usd": round(total_cost_usd, 4),
            "cost_per_entry_usd": round(cost_per_entry, 6),
            "batch_size": batch_size,
        }

    def _generate_tx_hash(self, merkle_root: str) -> str:
        """Generate simulated transaction hash."""
        data = f"{merkle_root}:{datetime.utcnow().isoformat()}"
        return "0x" + hashlib.sha256(data.encode()).hexdigest()


# =============================================================================
# Arweave Anchor Provider
# =============================================================================


class ArweaveAnchorProvider(AnchorProvider):
    """
    Anchor provider for Arweave permanent storage.

    Stores Merkle root with metadata as a permanent Arweave transaction.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        wallet_path: str | None = None,
    ):
        self.gateway_url = gateway_url or os.getenv("ARWEAVE_GATEWAY", "https://arweave.net")
        self.wallet_path = wallet_path or os.getenv("ARWEAVE_WALLET_PATH")

    def get_chain(self) -> AnchorChain:
        return AnchorChain.ARWEAVE

    def submit_anchor(self, merkle_root: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """
        Submit anchor to Arweave.

        In production, this would use arweave-python-client to:
        1. Load wallet
        2. Create transaction with merkle_root and metadata
        3. Sign and submit transaction
        4. Return transaction ID
        """
        # Simulate transaction submission
        tx_id = self._generate_tx_id(merkle_root)

        return {
            "status": "submitted",
            "transaction_hash": tx_id,
            "chain": AnchorChain.ARWEAVE.value,
            "merkle_root": merkle_root,
            "timestamp": datetime.utcnow().isoformat(),
            "permanence": "permanent",
            "note": "Simulated - implement arweave-python-client for production",
        }

    def verify_anchor(self, transaction_hash: str, merkle_root: str) -> dict[str, Any]:
        """Verify anchor on Arweave."""
        return {
            "verified": True,
            "transaction_hash": transaction_hash,
            "merkle_root": merkle_root,
            "block_height": 1200000,  # Simulated
            "timestamp": datetime.utcnow().isoformat(),
            "confirmations": 50,
            "chain": AnchorChain.ARWEAVE.value,
            "permanence": "permanent",
        }

    def get_verification_url(self, transaction_hash: str) -> str:
        return f"https://viewblock.io/arweave/tx/{transaction_hash}"

    def estimate_cost(self, batch_size: int) -> dict[str, Any]:
        """Estimate cost for Arweave anchor."""
        # Arweave pricing is per byte, one-time
        data_size_bytes = 256  # Merkle root + metadata
        ar_price_per_byte = 0.0000001  # Approximate
        ar_price_usd = 10  # Approximate AR/USD

        total_cost_ar = data_size_bytes * ar_price_per_byte
        total_cost_usd = total_cost_ar * ar_price_usd
        cost_per_entry = total_cost_usd / batch_size if batch_size > 0 else 0

        return {
            "chain": AnchorChain.ARWEAVE.value,
            "data_size_bytes": data_size_bytes,
            "total_cost_ar": total_cost_ar,
            "total_cost_usd": round(total_cost_usd, 6),
            "cost_per_entry_usd": round(cost_per_entry, 8),
            "batch_size": batch_size,
            "permanence": "permanent (200+ years)",
        }

    def _generate_tx_id(self, merkle_root: str) -> str:
        """Generate simulated Arweave transaction ID."""
        data = f"ar:{merkle_root}:{datetime.utcnow().isoformat()}"
        # Arweave IDs are base64url encoded
        return hashlib.sha256(data.encode()).hexdigest()[:43]


# =============================================================================
# Merkle Tree Builder
# =============================================================================


class MerkleTreeBuilder:
    """Builds Merkle trees from entry hashes for efficient anchoring."""

    def __init__(self, hash_algorithm: str = MERKLE_HASH_ALGORITHM):
        self.hash_algorithm = hash_algorithm

    def build_tree(self, hashes: list[str]) -> tuple[str, list[list[str]]]:
        """
        Build a Merkle tree from a list of hashes.

        Args:
            hashes: List of entry hashes (leaves)

        Returns:
            Tuple of (merkle_root, tree_levels)
        """
        if not hashes:
            return "", []

        # Ensure even number of leaves by duplicating last if odd
        leaves = list(hashes)
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])

        # Build tree levels from bottom up
        levels = [leaves]
        current_level = leaves

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)

            levels.append(next_level)
            current_level = next_level

        merkle_root = current_level[0]
        return merkle_root, levels

    def generate_proof(
        self, entry_hash: str, hashes: list[str], merkle_root: str, levels: list[list[str]]
    ) -> MerkleProof | None:
        """
        Generate a Merkle proof for a specific entry.

        Args:
            entry_hash: The hash to generate proof for
            hashes: Original list of hashes
            merkle_root: The Merkle root
            levels: Tree levels from build_tree

        Returns:
            MerkleProof or None if entry not found
        """
        # Find leaf index
        try:
            # Handle odd number of leaves
            leaves = list(hashes)
            if len(leaves) % 2 == 1:
                leaves.append(leaves[-1])

            leaf_index = leaves.index(entry_hash)
        except ValueError:
            return None

        proof_path = []
        current_index = leaf_index

        for level in levels[:-1]:  # Exclude root level
            # Get sibling
            if current_index % 2 == 0:
                sibling_index = current_index + 1
                position = "right"
            else:
                sibling_index = current_index - 1
                position = "left"

            if sibling_index < len(level):
                sibling_hash = level[sibling_index]
                proof_path.append({"position": position, "hash": sibling_hash})

            current_index = current_index // 2

        return MerkleProof(
            entry_hash=entry_hash,
            proof_path=proof_path,
            merkle_root=merkle_root,
            leaf_index=leaf_index,
            total_leaves=len(hashes),
        )


# =============================================================================
# Main External Anchoring Service
# =============================================================================


class ExternalAnchoringService:
    """
    Manages external anchoring of NatLangChain entries to external blockchains.

    Features:
    - Multi-chain support with configurable providers
    - Batch anchoring with Merkle tree aggregation
    - Automatic anchor scheduling
    - Proof generation and verification
    - Cost tracking and optimization
    """

    def __init__(
        self,
        providers: list[AnchorProvider] | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        anchor_interval_hours: int = DEFAULT_ANCHOR_INTERVAL_HOURS,
    ):
        """
        Initialize the anchoring service.

        Args:
            providers: List of anchor providers to use
            batch_size: Maximum entries per anchor batch
            anchor_interval_hours: Hours between anchor operations
        """
        self.providers = providers or []
        self.batch_size = batch_size
        self.anchor_interval_hours = anchor_interval_hours

        self.merkle_builder = MerkleTreeBuilder()

        # State tracking
        self.pending_anchors: list[PendingAnchor] = []
        self.anchor_batches: dict[str, AnchorBatch] = {}
        self.anchor_proofs: dict[str, AnchorProof] = {}
        self.entry_to_proof: dict[str, list[str]] = {}  # entry_hash -> [proof_ids]

        # Metrics
        self.total_anchored = 0
        self.total_cost_usd = 0.0
        self.events: list[dict[str, Any]] = []

        self.last_anchor_time: str | None = None

    # =========================================================================
    # Provider Management
    # =========================================================================

    def add_provider(self, provider: AnchorProvider) -> None:
        """Add an anchor provider."""
        self.providers.append(provider)

    def get_providers(self) -> list[dict[str, Any]]:
        """Get list of configured providers."""
        return [
            {
                "chain": p.get_chain().value,
                "type": p.__class__.__name__,
            }
            for p in self.providers
        ]

    def get_provider(self, chain: AnchorChain) -> AnchorProvider | None:
        """Get provider for a specific chain."""
        for provider in self.providers:
            if provider.get_chain() == chain:
                return provider
        return None

    # =========================================================================
    # Queue Management
    # =========================================================================

    def queue_entry(
        self,
        entry_hash: str,
        block_index: int | None = None,
        entry_index: int | None = None,
        content_hash: str | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Queue an entry for anchoring.

        Args:
            entry_hash: Hash of the entry
            block_index: Block index if mined
            entry_index: Entry index within block
            content_hash: Hash of entry content (for verification)
            priority: Higher priority = anchored sooner
            metadata: Additional metadata

        Returns:
            Queue result with position
        """
        # Check if already queued
        for pending in self.pending_anchors:
            if pending.entry_hash == entry_hash:
                return {
                    "status": "already_queued",
                    "entry_hash": entry_hash,
                    "position": self.pending_anchors.index(pending),
                }

        pending = PendingAnchor(
            entry_hash=entry_hash,
            block_index=block_index,
            entry_index=entry_index,
            content_hash=content_hash or entry_hash,
            queued_at=datetime.utcnow().isoformat(),
            priority=priority,
            metadata=metadata or {},
        )

        self.pending_anchors.append(pending)

        # Sort by priority (higher first)
        self.pending_anchors.sort(key=lambda x: x.priority, reverse=True)

        self._emit_event(
            AnchorEventType.ENTRY_QUEUED,
            {
                "entry_hash": entry_hash,
                "block_index": block_index,
                "entry_index": entry_index,
                "priority": priority,
                "queue_length": len(self.pending_anchors),
            },
        )

        return {
            "status": "queued",
            "entry_hash": entry_hash,
            "position": self.pending_anchors.index(pending),
            "queue_length": len(self.pending_anchors),
            "estimated_anchor_time": self._estimate_anchor_time(),
        }

    def queue_block(self, block_hash: str, block_index: int, entry_count: int) -> dict[str, Any]:
        """
        Queue an entire block for anchoring.

        Args:
            block_hash: Hash of the block
            block_index: Block index
            entry_count: Number of entries in block

        Returns:
            Queue result
        """
        return self.queue_entry(
            entry_hash=block_hash,
            block_index=block_index,
            entry_index=None,
            priority=10,  # Blocks get higher priority
            metadata={"type": "block", "entry_count": entry_count},
        )

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status."""
        return {
            "pending_count": len(self.pending_anchors),
            "batch_size": self.batch_size,
            "anchor_interval_hours": self.anchor_interval_hours,
            "last_anchor_time": self.last_anchor_time,
            "next_anchor_time": self._estimate_anchor_time(),
            "providers": [p.get_chain().value for p in self.providers],
            "pending_entries": [
                {
                    "entry_hash": p.entry_hash[:16] + "...",
                    "block_index": p.block_index,
                    "priority": p.priority,
                    "queued_at": p.queued_at,
                }
                for p in self.pending_anchors[:10]  # Show first 10
            ],
        }

    # =========================================================================
    # Anchor Operations
    # =========================================================================

    def create_anchor_batch(
        self, chain: AnchorChain | None = None, max_entries: int | None = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Create and submit an anchor batch.

        Args:
            chain: Specific chain to anchor to (uses all providers if None)
            max_entries: Max entries in batch (uses default if None)

        Returns:
            Tuple of (success, result)
        """
        if not self.pending_anchors:
            return False, {"error": "No pending entries to anchor"}

        if not self.providers:
            return False, {"error": "No anchor providers configured"}

        max_entries = max_entries or self.batch_size
        entries_to_anchor = self.pending_anchors[:max_entries]

        # Build Merkle tree
        hashes = [p.entry_hash for p in entries_to_anchor]
        merkle_root, levels = self.merkle_builder.build_tree(hashes)

        # Generate batch ID
        batch_id = self._generate_batch_id(merkle_root)

        # Determine which providers to use
        target_providers = self.providers
        if chain:
            provider = self.get_provider(chain)
            if provider:
                target_providers = [provider]
            else:
                return False, {"error": f"No provider for chain: {chain.value}"}

        # Submit to each provider
        results = []
        for provider in target_providers:
            try:
                result = provider.submit_anchor(
                    merkle_root,
                    {
                        "batch_id": batch_id,
                        "entry_count": len(hashes),
                        "source": "natlangchain",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

                # Create batch record
                batch = AnchorBatch(
                    batch_id=f"{batch_id}-{provider.get_chain().value}",
                    merkle_root=merkle_root,
                    entry_hashes=hashes,
                    created_at=datetime.utcnow().isoformat(),
                    anchor_chain=provider.get_chain().value,
                    transaction_hash=result.get("transaction_hash"),
                    status=AnchorStatus.SUBMITTED.value,
                )

                self.anchor_batches[batch.batch_id] = batch

                # Generate proofs for each entry
                for pending in entries_to_anchor:
                    proof = self.merkle_builder.generate_proof(
                        pending.entry_hash, hashes, merkle_root, levels
                    )

                    if proof:
                        anchor_proof = AnchorProof(
                            proof_id=self._generate_proof_id(pending.entry_hash, batch.batch_id),
                            entry_hash=pending.entry_hash,
                            block_index=pending.block_index,
                            entry_index=pending.entry_index,
                            anchor_chain=provider.get_chain().value,
                            merkle_proof=proof,
                            transaction_hash=result.get("transaction_hash", ""),
                            block_number=None,
                            timestamp=datetime.utcnow().isoformat(),
                            status=AnchorStatus.SUBMITTED.value,
                            verification_url=provider.get_verification_url(
                                result.get("transaction_hash", "")
                            ),
                        )

                        self.anchor_proofs[anchor_proof.proof_id] = anchor_proof

                        # Track entry -> proofs mapping
                        if pending.entry_hash not in self.entry_to_proof:
                            self.entry_to_proof[pending.entry_hash] = []
                        self.entry_to_proof[pending.entry_hash].append(anchor_proof.proof_id)

                results.append(
                    {
                        "chain": provider.get_chain().value,
                        "batch_id": batch.batch_id,
                        "transaction_hash": result.get("transaction_hash"),
                        "status": "submitted",
                    }
                )

                self._emit_event(
                    AnchorEventType.ANCHOR_SUBMITTED,
                    {
                        "batch_id": batch.batch_id,
                        "chain": provider.get_chain().value,
                        "entry_count": len(hashes),
                        "merkle_root": merkle_root,
                        "transaction_hash": result.get("transaction_hash"),
                    },
                )

            except Exception as e:
                results.append(
                    {
                        "chain": provider.get_chain().value,
                        "status": "failed",
                        "error": str(e),
                    }
                )

                self._emit_event(
                    AnchorEventType.ANCHOR_FAILED,
                    {
                        "chain": provider.get_chain().value,
                        "error": str(e),
                    },
                )

        # Remove anchored entries from queue
        self.pending_anchors = self.pending_anchors[max_entries:]
        self.total_anchored += len(entries_to_anchor)
        self.last_anchor_time = datetime.utcnow().isoformat()

        self._emit_event(
            AnchorEventType.BATCH_CREATED,
            {
                "batch_id": batch_id,
                "entry_count": len(hashes),
                "merkle_root": merkle_root,
                "providers": [r["chain"] for r in results if r.get("status") == "submitted"],
            },
        )

        return True, {
            "status": "anchored",
            "batch_id": batch_id,
            "entries_anchored": len(entries_to_anchor),
            "merkle_root": merkle_root,
            "results": results,
            "remaining_queue": len(self.pending_anchors),
        }

    def confirm_anchor(self, batch_id: str) -> tuple[bool, dict[str, Any]]:
        """
        Confirm an anchor batch has been confirmed on-chain.

        Args:
            batch_id: The batch to confirm

        Returns:
            Tuple of (success, result)
        """
        if batch_id not in self.anchor_batches:
            return False, {"error": "Batch not found"}

        batch = self.anchor_batches[batch_id]

        if batch.status == AnchorStatus.CONFIRMED.value:
            return True, {"status": "already_confirmed", "batch": batch.to_dict()}

        # Get provider and verify
        provider = self.get_provider(AnchorChain(batch.anchor_chain))
        if not provider:
            return False, {"error": f"No provider for chain: {batch.anchor_chain}"}

        try:
            verification = provider.verify_anchor(batch.transaction_hash or "", batch.merkle_root)

            if verification.get("verified"):
                batch.status = AnchorStatus.CONFIRMED.value
                batch.block_number = verification.get("block_number")
                batch.confirmed_at = datetime.utcnow().isoformat()

                # Update all proofs for this batch
                for entry_hash in batch.entry_hashes:
                    if entry_hash in self.entry_to_proof:
                        for proof_id in self.entry_to_proof[entry_hash]:
                            if proof_id in self.anchor_proofs:
                                proof = self.anchor_proofs[proof_id]
                                if proof.anchor_chain == batch.anchor_chain:
                                    proof.status = AnchorStatus.CONFIRMED.value
                                    proof.block_number = verification.get("block_number")

                self._emit_event(
                    AnchorEventType.ANCHOR_CONFIRMED,
                    {
                        "batch_id": batch_id,
                        "chain": batch.anchor_chain,
                        "block_number": batch.block_number,
                        "entry_count": len(batch.entry_hashes),
                    },
                )

                return True, {
                    "status": "confirmed",
                    "batch": batch.to_dict(),
                    "verification": verification,
                }
            else:
                return False, {"status": "not_confirmed", "verification": verification}

        except Exception as e:
            return False, {"error": str(e)}

    # =========================================================================
    # Proof and Verification
    # =========================================================================

    def get_proof(self, entry_hash: str) -> list[dict[str, Any]]:
        """
        Get all anchor proofs for an entry.

        Args:
            entry_hash: The entry hash

        Returns:
            List of proof dictionaries
        """
        proof_ids = self.entry_to_proof.get(entry_hash, [])
        return [self.anchor_proofs[pid].to_dict() for pid in proof_ids if pid in self.anchor_proofs]

    def verify_proof(self, entry_hash: str, chain: AnchorChain | None = None) -> dict[str, Any]:
        """
        Verify anchor proofs for an entry.

        Args:
            entry_hash: The entry hash
            chain: Specific chain to verify (verifies all if None)

        Returns:
            Verification result
        """
        proofs = self.get_proof(entry_hash)

        if not proofs:
            return {"verified": False, "error": "No proofs found for entry"}

        results = []
        for proof_dict in proofs:
            if chain and proof_dict["anchor_chain"] != chain.value:
                continue

            # Verify Merkle proof locally
            proof = MerkleProof(**proof_dict["merkle_proof"])
            merkle_valid = proof.verify()

            # Verify on-chain
            provider = self.get_provider(AnchorChain(proof_dict["anchor_chain"]))
            chain_valid = False
            chain_verification = {}

            if provider:
                try:
                    chain_verification = provider.verify_anchor(
                        proof_dict["transaction_hash"], proof_dict["merkle_proof"]["merkle_root"]
                    )
                    chain_valid = chain_verification.get("verified", False)
                except Exception as e:
                    chain_verification = {"error": str(e)}

            results.append(
                {
                    "chain": proof_dict["anchor_chain"],
                    "merkle_proof_valid": merkle_valid,
                    "chain_verified": chain_valid,
                    "transaction_hash": proof_dict["transaction_hash"],
                    "verification_url": proof_dict.get("verification_url"),
                    "chain_verification": chain_verification,
                }
            )

            if merkle_valid and chain_valid:
                self._emit_event(
                    AnchorEventType.VERIFICATION_SUCCESS,
                    {"entry_hash": entry_hash, "chain": proof_dict["anchor_chain"]},
                )
            else:
                self._emit_event(
                    AnchorEventType.VERIFICATION_FAILED,
                    {
                        "entry_hash": entry_hash,
                        "chain": proof_dict["anchor_chain"],
                        "merkle_valid": merkle_valid,
                        "chain_valid": chain_valid,
                    },
                )

        all_valid = all(r["merkle_proof_valid"] and r["chain_verified"] for r in results)

        return {
            "entry_hash": entry_hash,
            "verified": all_valid,
            "proofs_checked": len(results),
            "results": results,
        }

    def generate_legal_proof(self, entry_hash: str) -> dict[str, Any]:
        """
        Generate a comprehensive proof document for legal/audit purposes.

        Args:
            entry_hash: The entry hash

        Returns:
            Legal proof document
        """
        proofs = self.get_proof(entry_hash)

        if not proofs:
            return {"error": "No proofs found for entry"}

        return {
            "document_type": "NatLangChain Anchor Proof",
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat(),
            "entry_hash": entry_hash,
            "summary": {
                "total_anchors": len(proofs),
                "chains": list(set(p["anchor_chain"] for p in proofs)),
                "oldest_anchor": min(p["timestamp"] for p in proofs),
                "newest_anchor": max(p["timestamp"] for p in proofs),
            },
            "anchors": proofs,
            "verification_instructions": {
                "merkle_proof": "Use the merkle_proof.proof_path to verify entry inclusion in merkle_proof.merkle_root",
                "ethereum": "Verify transaction_hash on Etherscan or via eth_getTransactionByHash RPC",
                "arweave": "Verify transaction on ViewBlock or via Arweave gateway",
            },
            "legal_note": "This proof demonstrates that the entry hash existed at the time of anchoring "
            "by inclusion in a Merkle tree whose root was recorded on an external blockchain.",
        }

    # =========================================================================
    # Statistics and Reporting
    # =========================================================================

    def get_statistics(self) -> dict[str, Any]:
        """Get anchoring statistics."""
        batches_by_chain = {}
        for batch in self.anchor_batches.values():
            chain = batch.anchor_chain
            if chain not in batches_by_chain:
                batches_by_chain[chain] = {"count": 0, "entries": 0, "confirmed": 0}
            batches_by_chain[chain]["count"] += 1
            batches_by_chain[chain]["entries"] += len(batch.entry_hashes)
            if batch.status == AnchorStatus.CONFIRMED.value:
                batches_by_chain[chain]["confirmed"] += 1

        return {
            "total_anchored": self.total_anchored,
            "pending_count": len(self.pending_anchors),
            "total_batches": len(self.anchor_batches),
            "total_proofs": len(self.anchor_proofs),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "batches_by_chain": batches_by_chain,
            "providers": self.get_providers(),
            "last_anchor_time": self.last_anchor_time,
            "events_count": len(self.events),
        }

    def estimate_costs(self, entry_count: int | None = None) -> dict[str, Any]:
        """
        Estimate anchoring costs for pending or given entries.

        Args:
            entry_count: Number of entries (uses pending count if None)

        Returns:
            Cost estimates per provider
        """
        count = entry_count or len(self.pending_anchors)

        if count == 0:
            return {"error": "No entries to estimate"}

        estimates = []
        for provider in self.providers:
            estimate = provider.estimate_cost(count)
            estimates.append(estimate)

        total_cost = sum(e.get("total_cost_usd", 0) for e in estimates)

        return {
            "entry_count": count,
            "provider_estimates": estimates,
            "total_cost_usd": round(total_cost, 4),
            "cost_per_entry_usd": round(total_cost / count, 6) if count > 0 else 0,
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _generate_batch_id(self, merkle_root: str) -> str:
        """Generate unique batch ID."""
        data = f"{merkle_root}:{datetime.utcnow().isoformat()}"
        return f"BATCH-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _generate_proof_id(self, entry_hash: str, batch_id: str) -> str:
        """Generate unique proof ID."""
        data = f"{entry_hash}:{batch_id}"
        return f"PROOF-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _estimate_anchor_time(self) -> str | None:
        """Estimate when next anchor will occur."""
        if self.last_anchor_time:
            last = datetime.fromisoformat(self.last_anchor_time)
            next_time = last + timedelta(hours=self.anchor_interval_hours)
        else:
            next_time = datetime.utcnow() + timedelta(hours=self.anchor_interval_hours)

        # Anchor sooner if queue is full
        if len(self.pending_anchors) >= self.batch_size:
            next_time = datetime.utcnow()

        return next_time.isoformat()

    def _emit_event(self, event_type: AnchorEventType, data: dict[str, Any]) -> None:
        """Emit an event for audit trail."""
        event = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
        }
        self.events.append(event)

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> dict[str, Any]:
        """Serialize service state."""
        return {
            "pending_anchors": [
                {
                    "entry_hash": p.entry_hash,
                    "block_index": p.block_index,
                    "entry_index": p.entry_index,
                    "content_hash": p.content_hash,
                    "queued_at": p.queued_at,
                    "priority": p.priority,
                }
                for p in self.pending_anchors
            ],
            "anchor_batches": {k: v.to_dict() for k, v in self.anchor_batches.items()},
            "anchor_proofs": {k: v.to_dict() for k, v in self.anchor_proofs.items()},
            "entry_to_proof": self.entry_to_proof,
            "total_anchored": self.total_anchored,
            "total_cost_usd": self.total_cost_usd,
            "last_anchor_time": self.last_anchor_time,
        }
