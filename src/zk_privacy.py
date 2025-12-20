"""
NatLangChain - ZK Privacy Infrastructure
Zero-knowledge proof and privacy-preserving features for dispute resolution.

"Privacy is not secrecy. Privacy is the power to selectively reveal oneself."
- The Cypherpunk Manifesto

This module implements:
- Phase 14A: Dispute Membership Circuit (ZK proof verification)
- Phase 14B: Viewing Key Infrastructure (Pedersen, ECIES, Shamir)
- Phase 14C: Inference Attack Mitigations (batching, dummies)
- Phase 14D: Threshold Decryption (BLS/FROST simulation)
"""

import json
import hashlib
import secrets
import base64
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# Phase 14A: Dispute Membership Circuit
# ============================================================

class ProofStatus(Enum):
    """Status of a ZK proof."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class IdentityProof:
    """
    Represents a ZK identity proof.

    In production, this would contain actual Groth16/PLONK proof data.
    Here we simulate the structure for API integration.
    """
    proof_id: str
    dispute_id: str
    prover: str  # Address of prover (not revealed on-chain)
    identity_hash: str  # Public: hash that must match on-chain
    proof_a: List[str]  # [2] elements
    proof_b: List[List[str]]  # [2][2] elements
    proof_c: List[str]  # [2] elements
    public_signals: List[str]  # Public inputs to circuit
    status: ProofStatus = ProofStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    verified_at: Optional[str] = None
    gas_estimate: int = 100000  # Estimated verification gas


class PoseidonHasher:
    """
    Simulates Poseidon hash function used in ZK circuits.

    Poseidon is chosen for Ethereum ZK compatibility due to:
    - Low constraint count in R1CS/PLONK
    - Native field arithmetic on BN254/BLS12-381
    - Standard in circomlib

    This is a simulation - production would use actual Poseidon.
    """

    # Simulated round constants (in production, use proper Poseidon constants)
    ROUND_CONSTANTS = [
        0x0ee9a592ba9a9518d05986d656f40c2114c4993c11bb29938d21d47304cd8e6e,
        0x00f1445235f2148c5986587169fc1bcd887b08d4d00868df5696fff40956e864,
    ]

    @staticmethod
    def hash(inputs: List[int]) -> str:
        """
        Compute Poseidon hash of inputs.

        Args:
            inputs: List of field elements (integers)

        Returns:
            Hash as hex string (simulated Poseidon output)
        """
        # Simulation: combine inputs with constants
        combined = sum(inputs) + sum(PoseidonHasher.ROUND_CONSTANTS[:len(inputs)])

        # Use SHA256 as a stand-in for Poseidon (for simulation only)
        hash_input = json.dumps({"inputs": inputs, "combined": combined})
        hash_bytes = hashlib.sha256(hash_input.encode()).digest()

        # Return as field element (256-bit hex)
        return "0x" + hash_bytes.hex()

    @staticmethod
    def hash_identity(secret: str) -> str:
        """
        Hash an identity secret for on-chain commitment.

        Args:
            secret: User's identity secret (salt + address)

        Returns:
            Identity hash for on-chain storage
        """
        # Convert secret to field element
        secret_bytes = hashlib.sha256(secret.encode()).digest()
        secret_int = int.from_bytes(secret_bytes, 'big')

        return PoseidonHasher.hash([secret_int])


class DisputeMembershipCircuit:
    """
    Manages ZK proofs for dispute membership.

    Circuit Logic (prove_identity.circom):
    - Private input: identitySecret
    - Public input: identityManager (on-chain hash)
    - Constraint: Poseidon(identitySecret) === identityManager

    This proves "I know a secret that hashes to the on-chain identity"
    without revealing the secret or the prover's address.
    """

    # Proof expiration time
    PROOF_EXPIRY_MINUTES = 30

    def __init__(self):
        """Initialize the circuit manager."""
        self.proofs: Dict[str, IdentityProof] = {}
        self.verified_proofs: Dict[str, List[str]] = {}  # dispute_id -> [proof_ids]
        self.hasher = PoseidonHasher()
        self.audit_trail: List[Dict[str, Any]] = []

    def generate_identity_commitment(
        self,
        user_address: str,
        salt: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Generate identity commitment for on-chain registration.

        Args:
            user_address: User's address
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (identity_secret, identity_hash)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        # Create identity secret
        identity_secret = f"{salt}:{user_address}"

        # Compute on-chain hash
        identity_hash = self.hasher.hash_identity(identity_secret)

        self._log_audit("identity_commitment_generated", {
            "user_address": user_address,
            "identity_hash": identity_hash
        })

        return identity_secret, identity_hash

    def generate_proof(
        self,
        dispute_id: str,
        prover_address: str,
        identity_secret: str,
        identity_manager: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate a ZK proof of dispute membership.

        In production, this would call snarkjs to generate actual proof.
        Here we simulate the proof structure.

        Args:
            dispute_id: ID of the dispute
            prover_address: Address generating the proof
            identity_secret: Private identity secret
            identity_manager: Public on-chain hash to match

        Returns:
            Tuple of (success, proof_data or error)
        """
        # Verify the secret hashes to the identity_manager
        computed_hash = self.hasher.hash_identity(identity_secret)

        if computed_hash != identity_manager:
            return False, {
                "error": "Identity verification failed",
                "reason": "Secret does not hash to identity_manager"
            }

        # Generate proof ID
        proof_id = f"PROOF-{secrets.token_hex(8).upper()}"

        # Simulate Groth16 proof components
        # In production, these would be actual curve points
        proof_a = [
            "0x" + secrets.token_hex(32),
            "0x" + secrets.token_hex(32)
        ]
        proof_b = [
            ["0x" + secrets.token_hex(32), "0x" + secrets.token_hex(32)],
            ["0x" + secrets.token_hex(32), "0x" + secrets.token_hex(32)]
        ]
        proof_c = [
            "0x" + secrets.token_hex(32),
            "0x" + secrets.token_hex(32)
        ]

        # Public signals (only identity_manager is public)
        public_signals = [identity_manager]

        # Create proof record
        proof = IdentityProof(
            proof_id=proof_id,
            dispute_id=dispute_id,
            prover=prover_address,
            identity_hash=identity_manager,
            proof_a=proof_a,
            proof_b=proof_b,
            proof_c=proof_c,
            public_signals=public_signals
        )

        self.proofs[proof_id] = proof

        self._log_audit("proof_generated", {
            "proof_id": proof_id,
            "dispute_id": dispute_id,
            "identity_hash": identity_manager
        })

        return True, {
            "proof_id": proof_id,
            "dispute_id": dispute_id,
            "proof": {
                "a": proof_a,
                "b": proof_b,
                "c": proof_c
            },
            "public_signals": public_signals,
            "expires_at": (datetime.utcnow() + timedelta(minutes=self.PROOF_EXPIRY_MINUTES)).isoformat(),
            "gas_estimate": proof.gas_estimate
        }

    def verify_proof(
        self,
        proof_id: str,
        expected_identity_hash: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a ZK proof on-chain (simulated).

        In production, this would call the verifier contract.

        Args:
            proof_id: ID of the proof to verify
            expected_identity_hash: Expected identity hash from dispute struct

        Returns:
            Tuple of (is_valid, result)
        """
        if proof_id not in self.proofs:
            return False, {"error": "Proof not found"}

        proof = self.proofs[proof_id]

        # Check expiration
        created = datetime.fromisoformat(proof.created_at)
        if datetime.utcnow() - created > timedelta(minutes=self.PROOF_EXPIRY_MINUTES):
            proof.status = ProofStatus.EXPIRED
            return False, {"error": "Proof expired"}

        # Check already verified
        if proof.status == ProofStatus.VERIFIED:
            return False, {"error": "Proof already used"}

        # Verify public signal matches expected
        if proof.public_signals[0] != expected_identity_hash:
            proof.status = ProofStatus.REJECTED
            return False, {
                "error": "Proof verification failed",
                "reason": "Public signal does not match expected identity"
            }

        # In production: call verifier.verifyProof(a, b, c, publicSignals)
        # Here we simulate successful verification
        proof.status = ProofStatus.VERIFIED
        proof.verified_at = datetime.utcnow().isoformat()

        # Track verified proofs per dispute
        if proof.dispute_id not in self.verified_proofs:
            self.verified_proofs[proof.dispute_id] = []
        self.verified_proofs[proof.dispute_id].append(proof_id)

        self._log_audit("proof_verified", {
            "proof_id": proof_id,
            "dispute_id": proof.dispute_id,
            "identity_hash": expected_identity_hash
        })

        return True, {
            "status": "verified",
            "proof_id": proof_id,
            "dispute_id": proof.dispute_id,
            "verified_at": proof.verified_at,
            "gas_used": proof.gas_estimate
        }

    def get_proof(self, proof_id: str) -> Optional[Dict[str, Any]]:
        """Get proof details."""
        if proof_id not in self.proofs:
            return None

        proof = self.proofs[proof_id]
        return {
            "proof_id": proof.proof_id,
            "dispute_id": proof.dispute_id,
            "identity_hash": proof.identity_hash,
            "status": proof.status.value,
            "created_at": proof.created_at,
            "verified_at": proof.verified_at
        }

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================
# Phase 14B: Viewing Key Infrastructure
# ============================================================

@dataclass
class ViewingKey:
    """Represents an ECIES viewing key for a dispute."""
    key_id: str
    dispute_id: str
    public_key: str  # ECIES public key
    commitment: str  # Pedersen commitment hash
    encrypted_metadata_cid: Optional[str] = None  # IPFS/Arweave CID
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    shares_distributed: bool = False
    share_holders: List[str] = field(default_factory=list)
    threshold: int = 3  # m-of-n threshold
    total_shares: int = 5


@dataclass
class KeyShare:
    """A share of a viewing key (Shamir's Secret Sharing)."""
    share_id: str
    key_id: str
    holder: str
    share_index: int
    share_data: str  # Encrypted share
    submitted_at: Optional[str] = None


class PedersenCommitment:
    """
    Pedersen commitment scheme for hiding values on-chain.

    Commitment = g^value * h^blinding_factor

    Properties:
    - Hiding: Cannot determine value from commitment
    - Binding: Cannot open to different value
    """

    # Simulated generator points (in production, use curve generators)
    G = "0x" + "01" * 32  # Generator g
    H = "0x" + "02" * 32  # Generator h (nothing-up-my-sleeve)

    @staticmethod
    def commit(value: str, blinding_factor: Optional[str] = None) -> Tuple[str, str]:
        """
        Create a Pedersen commitment.

        Args:
            value: Value to commit to
            blinding_factor: Random blinding factor (generated if not provided)

        Returns:
            Tuple of (commitment, blinding_factor)
        """
        if blinding_factor is None:
            blinding_factor = secrets.token_hex(32)

        # Simulate commitment: hash(value || blinding_factor)
        commitment_input = f"{value}:{blinding_factor}"
        commitment = "0x" + hashlib.sha256(commitment_input.encode()).hexdigest()

        return commitment, blinding_factor

    @staticmethod
    def verify(commitment: str, value: str, blinding_factor: str) -> bool:
        """
        Verify a Pedersen commitment opening.

        Args:
            commitment: The commitment to verify
            value: Claimed value
            blinding_factor: Blinding factor used

        Returns:
            True if commitment opens to value
        """
        expected, _ = PedersenCommitment.commit(value, blinding_factor)
        return commitment == expected


class ShamirSecretSharing:
    """
    Shamir's Secret Sharing for m-of-n key escrow.

    Splits a secret into n shares such that any m shares
    can reconstruct the secret, but m-1 shares reveal nothing.
    """

    # Prime for finite field arithmetic (simulated)
    PRIME = 2**256 - 189  # Large prime

    @staticmethod
    def split(secret: str, threshold: int, total_shares: int) -> List[Dict[str, Any]]:
        """
        Split a secret into shares.

        Args:
            secret: Secret to split
            threshold: Minimum shares needed (m)
            total_shares: Total shares to create (n)

        Returns:
            List of share dictionaries
        """
        if threshold > total_shares:
            raise ValueError("Threshold cannot exceed total shares")

        # Convert secret to integer
        secret_bytes = hashlib.sha256(secret.encode()).digest()
        secret_int = int.from_bytes(secret_bytes, 'big')

        # Generate random polynomial coefficients
        coefficients = [secret_int]
        for _ in range(threshold - 1):
            coefficients.append(secrets.randbelow(ShamirSecretSharing.PRIME))

        # Evaluate polynomial at points 1, 2, ..., n
        shares = []
        for x in range(1, total_shares + 1):
            # Evaluate polynomial
            y = 0
            for i, coef in enumerate(coefficients):
                y = (y + coef * pow(x, i, ShamirSecretSharing.PRIME)) % ShamirSecretSharing.PRIME

            shares.append({
                "index": x,
                "share": hex(y),
                "share_hash": "0x" + hashlib.sha256(hex(y).encode()).hexdigest()[:16]
            })

        return shares

    @staticmethod
    def reconstruct(shares: List[Dict[str, Any]]) -> str:
        """
        Reconstruct secret from shares using Lagrange interpolation.

        Args:
            shares: List of shares with index and share value

        Returns:
            Reconstructed secret (as hex)
        """
        if len(shares) < 2:
            raise ValueError("Need at least 2 shares")

        # Lagrange interpolation at x=0
        secret = 0

        for i, share_i in enumerate(shares):
            xi = share_i["index"]
            yi = int(share_i["share"], 16)

            # Calculate Lagrange basis polynomial
            numerator = 1
            denominator = 1

            for j, share_j in enumerate(shares):
                if i != j:
                    xj = share_j["index"]
                    numerator = (numerator * (-xj)) % ShamirSecretSharing.PRIME
                    denominator = (denominator * (xi - xj)) % ShamirSecretSharing.PRIME

            # Modular inverse
            denominator_inv = pow(denominator, ShamirSecretSharing.PRIME - 2, ShamirSecretSharing.PRIME)

            # Add contribution
            lagrange = (numerator * denominator_inv) % ShamirSecretSharing.PRIME
            secret = (secret + yi * lagrange) % ShamirSecretSharing.PRIME

        return hex(secret)


class ECIESEncryption:
    """
    ECIES (Elliptic Curve Integrated Encryption Scheme).

    Used for viewing key generation and encryption.
    Simulated for API demonstration.
    """

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """
        Generate ECIES keypair.

        Returns:
            Tuple of (private_key, public_key)
        """
        private_key = "0x" + secrets.token_hex(32)

        # Simulate public key derivation
        pub_hash = hashlib.sha256(private_key.encode()).hexdigest()
        public_key = "0x04" + pub_hash + secrets.token_hex(32)  # Uncompressed point

        return private_key, public_key

    @staticmethod
    def encrypt(public_key: str, plaintext: str) -> Dict[str, str]:
        """
        Encrypt data with ECIES.

        Args:
            public_key: Recipient's public key
            plaintext: Data to encrypt

        Returns:
            Encrypted data with ephemeral public key
        """
        # Generate ephemeral keypair
        ephemeral_private, ephemeral_public = ECIESEncryption.generate_keypair()

        # Derive shared secret (simulated ECDH)
        shared_input = f"{ephemeral_private}:{public_key}"
        shared_secret = hashlib.sha256(shared_input.encode()).digest()

        # Encrypt with AES (simulated)
        plaintext_bytes = plaintext.encode()
        ciphertext = bytes(a ^ b for a, b in zip(
            plaintext_bytes,
            (shared_secret * ((len(plaintext_bytes) // 32) + 1))[:len(plaintext_bytes)]
        ))

        return {
            "ephemeral_public_key": ephemeral_public,
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "mac": "0x" + hashlib.sha256(ciphertext + shared_secret).hexdigest()[:32]
        }

    @staticmethod
    def decrypt(private_key: str, encrypted: Dict[str, str]) -> str:
        """
        Decrypt ECIES encrypted data.

        Args:
            private_key: Recipient's private key
            encrypted: Encrypted data from encrypt()

        Returns:
            Decrypted plaintext
        """
        # Derive shared secret
        shared_input = f"{private_key}:{encrypted['ephemeral_public_key']}"
        shared_secret = hashlib.sha256(shared_input.encode()).digest()

        # Decrypt
        ciphertext = base64.b64decode(encrypted["ciphertext"])
        plaintext_bytes = bytes(a ^ b for a, b in zip(
            ciphertext,
            (shared_secret * ((len(ciphertext) // 32) + 1))[:len(ciphertext)]
        ))

        return plaintext_bytes.decode()


class ViewingKeyManager:
    """
    Manages viewing keys for selective de-anonymization.

    Workflow:
    1. User creates viewing key for dispute
    2. Metadata encrypted and stored off-chain (IPFS/Arweave)
    3. Key split into shares via Shamir
    4. Shares distributed to escrow holders
    5. On legal request, shares reconstructed to decrypt
    """

    def __init__(self):
        """Initialize viewing key manager."""
        self.keys: Dict[str, ViewingKey] = {}
        self.shares: Dict[str, List[KeyShare]] = {}  # key_id -> shares
        self.submitted_shares: Dict[str, Dict[str, str]] = {}  # key_id -> {holder: share}
        self.audit_trail: List[Dict[str, Any]] = []

    def create_viewing_key(
        self,
        dispute_id: str,
        metadata: Dict[str, Any],
        share_holders: List[str],
        threshold: int = 3
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a viewing key for a dispute.

        Args:
            dispute_id: ID of the dispute
            metadata: Metadata to encrypt
            share_holders: List of share holder addresses
            threshold: Minimum shares for reconstruction

        Returns:
            Tuple of (success, result)
        """
        if len(share_holders) < threshold:
            return False, {"error": "Not enough share holders for threshold"}

        # Generate ECIES keypair
        private_key, public_key = ECIESEncryption.generate_keypair()

        # Encrypt metadata
        metadata_json = json.dumps(metadata)
        encrypted = ECIESEncryption.encrypt(public_key, metadata_json)

        # Create Pedersen commitment to the key
        commitment, blinding = PedersenCommitment.commit(private_key)

        # Generate key ID
        key_id = f"VKEY-{secrets.token_hex(8).upper()}"

        # Split private key into shares
        shares = ShamirSecretSharing.split(
            private_key,
            threshold,
            len(share_holders)
        )

        # Create viewing key record
        viewing_key = ViewingKey(
            key_id=key_id,
            dispute_id=dispute_id,
            public_key=public_key,
            commitment=commitment,
            share_holders=share_holders,
            threshold=threshold,
            total_shares=len(share_holders)
        )

        self.keys[key_id] = viewing_key

        # Create share records
        self.shares[key_id] = []
        for i, (holder, share_data) in enumerate(zip(share_holders, shares)):
            share = KeyShare(
                share_id=f"SHARE-{secrets.token_hex(4).upper()}",
                key_id=key_id,
                holder=holder,
                share_index=share_data["index"],
                share_data=share_data["share"]
            )
            self.shares[key_id].append(share)

        self._log_audit("viewing_key_created", {
            "key_id": key_id,
            "dispute_id": dispute_id,
            "threshold": threshold,
            "total_shares": len(share_holders)
        })

        return True, {
            "key_id": key_id,
            "dispute_id": dispute_id,
            "public_key": public_key,
            "commitment": commitment,
            "encrypted_metadata": encrypted,
            "shares_created": len(shares),
            "threshold": threshold,
            "share_holders": share_holders
        }

    def submit_share(
        self,
        key_id: str,
        holder: str,
        share_data: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a share for key reconstruction.

        Args:
            key_id: ID of the viewing key
            holder: Share holder address
            share_data: The share value

        Returns:
            Tuple of (success, result)
        """
        if key_id not in self.keys:
            return False, {"error": "Viewing key not found"}

        viewing_key = self.keys[key_id]

        # Verify holder is authorized
        if holder not in viewing_key.share_holders:
            return False, {"error": "Holder not authorized for this key"}

        # Store submitted share
        if key_id not in self.submitted_shares:
            self.submitted_shares[key_id] = {}

        # Find the share for this holder
        holder_share = None
        for share in self.shares[key_id]:
            if share.holder == holder:
                holder_share = share
                break

        if not holder_share:
            return False, {"error": "Share not found for holder"}

        # Verify share matches
        if share_data != holder_share.share_data:
            return False, {"error": "Share verification failed"}

        self.submitted_shares[key_id][holder] = share_data
        holder_share.submitted_at = datetime.utcnow().isoformat()

        shares_submitted = len(self.submitted_shares[key_id])
        can_reconstruct = shares_submitted >= viewing_key.threshold

        self._log_audit("share_submitted", {
            "key_id": key_id,
            "holder": holder,
            "shares_submitted": shares_submitted,
            "threshold": viewing_key.threshold
        })

        return True, {
            "status": "share_accepted",
            "key_id": key_id,
            "shares_submitted": shares_submitted,
            "threshold": viewing_key.threshold,
            "can_reconstruct": can_reconstruct
        }

    def reconstruct_key(
        self,
        key_id: str,
        authorization: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Reconstruct viewing key from submitted shares.

        Args:
            key_id: ID of the viewing key
            authorization: Authorization proof (legal warrant hash)

        Returns:
            Tuple of (success, result with decrypted key)
        """
        if key_id not in self.keys:
            return False, {"error": "Viewing key not found"}

        viewing_key = self.keys[key_id]

        if key_id not in self.submitted_shares:
            return False, {"error": "No shares submitted"}

        submitted = self.submitted_shares[key_id]

        if len(submitted) < viewing_key.threshold:
            return False, {
                "error": "Insufficient shares",
                "submitted": len(submitted),
                "required": viewing_key.threshold
            }

        # Prepare shares for reconstruction
        shares_for_reconstruction = []
        for holder, share_data in list(submitted.items())[:viewing_key.threshold]:
            # Find the index for this share
            for share in self.shares[key_id]:
                if share.holder == holder:
                    shares_for_reconstruction.append({
                        "index": share.share_index,
                        "share": share_data
                    })
                    break

        # Reconstruct the key
        try:
            reconstructed = ShamirSecretSharing.reconstruct(shares_for_reconstruction)
        except Exception as e:
            return False, {"error": f"Reconstruction failed: {str(e)}"}

        self._log_audit("key_reconstructed", {
            "key_id": key_id,
            "dispute_id": viewing_key.dispute_id,
            "authorization": authorization,
            "shares_used": len(shares_for_reconstruction)
        })

        return True, {
            "status": "key_reconstructed",
            "key_id": key_id,
            "dispute_id": viewing_key.dispute_id,
            "private_key": reconstructed,
            "authorization": authorization,
            "reconstructed_at": datetime.utcnow().isoformat()
        }

    def get_key_status(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get viewing key status."""
        if key_id not in self.keys:
            return None

        key = self.keys[key_id]
        submitted = len(self.submitted_shares.get(key_id, {}))

        return {
            "key_id": key.key_id,
            "dispute_id": key.dispute_id,
            "commitment": key.commitment,
            "threshold": key.threshold,
            "total_shares": key.total_shares,
            "shares_submitted": submitted,
            "can_reconstruct": submitted >= key.threshold,
            "created_at": key.created_at
        }

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================
# Phase 14C: Inference Attack Mitigations
# ============================================================

class BatchStatus(Enum):
    """Status of a batch."""
    COLLECTING = "collecting"
    READY = "ready"
    RELEASED = "released"


@dataclass
class TransactionBatch:
    """A batch of transactions for privacy."""
    batch_id: str
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    status: BatchStatus = BatchStatus.COLLECTING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    release_block: Optional[int] = None
    released_at: Optional[str] = None


class BatchingQueue:
    """
    Batching queue for transaction privacy.

    Aggregates transactions and releases them in batches
    to prevent timing correlation attacks.
    """

    # Configuration
    BATCH_SIZE = 10  # Transactions per batch
    BATCH_INTERVAL_BLOCKS = 100  # Blocks between releases

    def __init__(self):
        """Initialize batching queue."""
        self.current_batch: Optional[TransactionBatch] = None
        self.released_batches: List[TransactionBatch] = []
        self.current_block = 0
        self.audit_trail: List[Dict[str, Any]] = []

        # Start new batch
        self._new_batch()

    def _new_batch(self):
        """Create a new batch."""
        batch_id = f"BATCH-{secrets.token_hex(6).upper()}"
        self.current_batch = TransactionBatch(
            batch_id=batch_id,
            release_block=self.current_block + self.BATCH_INTERVAL_BLOCKS
        )

    def submit_transaction(
        self,
        tx_type: str,
        tx_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a transaction to the batching queue.

        Args:
            tx_type: Type of transaction
            tx_data: Transaction data

        Returns:
            Tuple of (success, result)
        """
        if self.current_batch.status != BatchStatus.COLLECTING:
            self._new_batch()

        tx_id = f"TX-{secrets.token_hex(6).upper()}"

        transaction = {
            "tx_id": tx_id,
            "tx_type": tx_type,
            "tx_data": tx_data,
            "submitted_at": datetime.utcnow().isoformat(),
            "batch_id": self.current_batch.batch_id
        }

        self.current_batch.transactions.append(transaction)

        # Check if batch is ready
        if len(self.current_batch.transactions) >= self.BATCH_SIZE:
            self.current_batch.status = BatchStatus.READY

        self._log_audit("transaction_batched", {
            "tx_id": tx_id,
            "batch_id": self.current_batch.batch_id,
            "batch_size": len(self.current_batch.transactions)
        })

        return True, {
            "tx_id": tx_id,
            "batch_id": self.current_batch.batch_id,
            "position_in_batch": len(self.current_batch.transactions),
            "batch_status": self.current_batch.status.value,
            "release_block": self.current_batch.release_block
        }

    def advance_block(self, new_block: int) -> List[Dict[str, Any]]:
        """
        Advance to a new block and release ready batches.

        Args:
            new_block: New block number

        Returns:
            List of released transactions
        """
        self.current_block = new_block
        released = []

        # Check if current batch should be released
        if (self.current_batch and
            self.current_batch.release_block <= new_block and
            len(self.current_batch.transactions) > 0):

            self.current_batch.status = BatchStatus.RELEASED
            self.current_batch.released_at = datetime.utcnow().isoformat()

            released = self.current_batch.transactions.copy()
            self.released_batches.append(self.current_batch)

            self._log_audit("batch_released", {
                "batch_id": self.current_batch.batch_id,
                "transaction_count": len(released),
                "block": new_block
            })

            # Start new batch
            self._new_batch()

        return released

    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get batch status."""
        if self.current_batch and self.current_batch.batch_id == batch_id:
            batch = self.current_batch
        else:
            batch = next(
                (b for b in self.released_batches if b.batch_id == batch_id),
                None
            )

        if not batch:
            return None

        return {
            "batch_id": batch.batch_id,
            "status": batch.status.value,
            "transaction_count": len(batch.transactions),
            "created_at": batch.created_at,
            "release_block": batch.release_block,
            "released_at": batch.released_at
        }

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


class DummyTransactionGenerator:
    """
    Generates dummy transactions to obscure real activity patterns.

    Funded by treasury; executed via Chainlink Automation.
    """

    # Configuration
    DUMMY_PROBABILITY = 0.3  # 30% chance per interval
    DUMMY_TYPES = [
        "voluntary_request",
        "identity_proof",
        "viewing_key_check"
    ]

    def __init__(self):
        """Initialize dummy generator."""
        self.generated_dummies: List[Dict[str, Any]] = []
        self.total_generated = 0
        self.audit_trail: List[Dict[str, Any]] = []

    def should_generate(self) -> bool:
        """
        Determine if a dummy transaction should be generated.

        Returns:
            True if dummy should be generated
        """
        return secrets.randbelow(100) < (self.DUMMY_PROBABILITY * 100)

    def generate_dummy(self) -> Dict[str, Any]:
        """
        Generate a dummy transaction.

        Returns:
            Dummy transaction data
        """
        dummy_id = f"DUMMY-{secrets.token_hex(6).upper()}"
        dummy_type = secrets.choice(self.DUMMY_TYPES)

        # Generate plausible dummy data
        dummy_data = {
            "dummy_id": dummy_id,
            "tx_type": dummy_type,
            "is_dummy": True,  # Marked internally, not revealed on-chain
            "created_at": datetime.utcnow().isoformat()
        }

        if dummy_type == "voluntary_request":
            dummy_data["initiator"] = f"0x{secrets.token_hex(20)}"
            dummy_data["recipient"] = f"0x{secrets.token_hex(20)}"
        elif dummy_type == "identity_proof":
            dummy_data["identity_hash"] = f"0x{secrets.token_hex(32)}"
        elif dummy_type == "viewing_key_check":
            dummy_data["key_commitment"] = f"0x{secrets.token_hex(32)}"

        self.generated_dummies.append(dummy_data)
        self.total_generated += 1

        self._log_audit("dummy_generated", {
            "dummy_id": dummy_id,
            "dummy_type": dummy_type
        })

        return dummy_data

    def get_statistics(self) -> Dict[str, Any]:
        """Get dummy generation statistics."""
        return {
            "total_generated": self.total_generated,
            "probability": self.DUMMY_PROBABILITY,
            "dummy_types": self.DUMMY_TYPES,
            "recent_dummies": len(self.generated_dummies)
        }

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================
# Phase 14D: Threshold Decryption
# ============================================================

class VoteStatus(Enum):
    """Status of a compliance vote."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ComplianceVote:
    """A vote in the compliance council."""
    vote_id: str
    voter: str
    key_id: str
    vote: bool  # True = approve, False = reject
    signature: str
    voted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ComplianceRequest:
    """A request for key disclosure."""
    request_id: str
    key_id: str
    requester: str
    warrant_hash: str
    justification: str
    votes: List[ComplianceVote] = field(default_factory=list)
    status: VoteStatus = VoteStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    threshold: int = 3  # Votes needed


class ThresholdDecryption:
    """
    Threshold decryption with BLS/FROST signatures.

    Implements compliance council governance for legal warrants.
    """

    # Configuration
    VOTE_EXPIRY_HOURS = 72
    DEFAULT_THRESHOLD = 3

    def __init__(self, council_members: List[str]):
        """
        Initialize threshold decryption.

        Args:
            council_members: List of compliance council member addresses
        """
        self.council_members = council_members
        self.requests: Dict[str, ComplianceRequest] = {}
        self.member_public_keys: Dict[str, str] = {}
        self.audit_trail: List[Dict[str, Any]] = []

        # Generate public keys for council members
        for member in council_members:
            _, public_key = ECIESEncryption.generate_keypair()
            self.member_public_keys[member] = public_key

    def submit_compliance_request(
        self,
        key_id: str,
        requester: str,
        warrant_hash: str,
        justification: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a compliance request for key disclosure.

        Args:
            key_id: ID of the viewing key
            requester: Authority submitting the request
            warrant_hash: Hash of legal warrant
            justification: Reason for request

        Returns:
            Tuple of (success, result)
        """
        request_id = f"CREQ-{secrets.token_hex(6).upper()}"

        request = ComplianceRequest(
            request_id=request_id,
            key_id=key_id,
            requester=requester,
            warrant_hash=warrant_hash,
            justification=justification,
            threshold=min(self.DEFAULT_THRESHOLD, len(self.council_members))
        )

        self.requests[request_id] = request

        self._log_audit("compliance_request_submitted", {
            "request_id": request_id,
            "key_id": key_id,
            "requester": requester,
            "warrant_hash": warrant_hash
        })

        return True, {
            "request_id": request_id,
            "key_id": key_id,
            "status": request.status.value,
            "threshold": request.threshold,
            "council_size": len(self.council_members),
            "expires_at": (datetime.utcnow() + timedelta(hours=self.VOTE_EXPIRY_HOURS)).isoformat()
        }

    def submit_vote(
        self,
        request_id: str,
        voter: str,
        approve: bool,
        signature: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Submit a vote on a compliance request.

        Args:
            request_id: ID of the request
            voter: Council member voting
            approve: True to approve, False to reject
            signature: BLS signature on vote

        Returns:
            Tuple of (success, result)
        """
        if request_id not in self.requests:
            return False, {"error": "Request not found"}

        request = self.requests[request_id]

        if request.status != VoteStatus.PENDING:
            return False, {"error": "Request already resolved"}

        # Check voter is council member
        if voter not in self.council_members:
            return False, {"error": "Voter not a council member"}

        # Check for duplicate vote
        if any(v.voter == voter for v in request.votes):
            return False, {"error": "Already voted"}

        # Check expiry
        created = datetime.fromisoformat(request.created_at)
        if datetime.utcnow() - created > timedelta(hours=self.VOTE_EXPIRY_HOURS):
            request.status = VoteStatus.EXPIRED
            return False, {"error": "Request expired"}

        # Create vote
        vote_id = f"VOTE-{secrets.token_hex(4).upper()}"
        vote = ComplianceVote(
            vote_id=vote_id,
            voter=voter,
            key_id=request.key_id,
            vote=approve,
            signature=signature
        )

        request.votes.append(vote)

        # Check if threshold reached
        approve_count = sum(1 for v in request.votes if v.vote)
        reject_count = sum(1 for v in request.votes if not v.vote)

        if approve_count >= request.threshold:
            request.status = VoteStatus.APPROVED
            request.resolved_at = datetime.utcnow().isoformat()
        elif reject_count > len(self.council_members) - request.threshold:
            request.status = VoteStatus.REJECTED
            request.resolved_at = datetime.utcnow().isoformat()

        self._log_audit("compliance_vote_submitted", {
            "request_id": request_id,
            "voter": voter,
            "vote": "approve" if approve else "reject",
            "approve_count": approve_count,
            "reject_count": reject_count,
            "status": request.status.value
        })

        return True, {
            "vote_id": vote_id,
            "request_id": request_id,
            "status": request.status.value,
            "approve_count": approve_count,
            "reject_count": reject_count,
            "threshold": request.threshold
        }

    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get compliance request status."""
        if request_id not in self.requests:
            return None

        request = self.requests[request_id]

        return {
            "request_id": request.request_id,
            "key_id": request.key_id,
            "requester": request.requester,
            "status": request.status.value,
            "votes": [
                {
                    "voter": v.voter,
                    "vote": "approve" if v.vote else "reject",
                    "voted_at": v.voted_at
                }
                for v in request.votes
            ],
            "approve_count": sum(1 for v in request.votes if v.vote),
            "reject_count": sum(1 for v in request.votes if not v.vote),
            "threshold": request.threshold,
            "created_at": request.created_at,
            "resolved_at": request.resolved_at
        }

    def generate_threshold_signature(
        self,
        request_id: str,
        message: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate threshold signature for approved request.

        Args:
            request_id: ID of the approved request
            message: Message to sign

        Returns:
            Tuple of (success, signature data)
        """
        if request_id not in self.requests:
            return False, {"error": "Request not found"}

        request = self.requests[request_id]

        if request.status != VoteStatus.APPROVED:
            return False, {"error": "Request not approved"}

        # Collect partial signatures from approving voters
        partial_signatures = []
        for vote in request.votes:
            if vote.vote:
                partial_signatures.append({
                    "voter": vote.voter,
                    "partial_signature": vote.signature
                })

        # Aggregate signatures (simulated BLS aggregation)
        aggregated_input = json.dumps({
            "message": message,
            "partials": [p["partial_signature"] for p in partial_signatures]
        })
        aggregated_signature = "0x" + hashlib.sha256(aggregated_input.encode()).hexdigest()

        self._log_audit("threshold_signature_generated", {
            "request_id": request_id,
            "signers": len(partial_signatures)
        })

        return True, {
            "request_id": request_id,
            "message": message,
            "aggregated_signature": aggregated_signature,
            "signers": len(partial_signatures),
            "threshold": request.threshold
        }

    def _log_audit(self, action: str, details: Dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })


# ============================================================
# Main ZK Privacy Manager
# ============================================================

class ZKPrivacyManager:
    """
    Main manager for ZK Privacy Infrastructure.

    Coordinates all privacy-preserving features.
    """

    def __init__(self, council_members: Optional[List[str]] = None):
        """
        Initialize ZK Privacy Manager.

        Args:
            council_members: Optional list of compliance council members
        """
        # Phase 14A
        self.membership_circuit = DisputeMembershipCircuit()

        # Phase 14B
        self.viewing_keys = ViewingKeyManager()

        # Phase 14C
        self.batching_queue = BatchingQueue()
        self.dummy_generator = DummyTransactionGenerator()

        # Phase 14D
        default_council = council_members or [
            "user_representative",
            "protocol_governance",
            "independent_auditor_1",
            "independent_auditor_2",
            "legal_counsel"
        ]
        self.threshold_decryption = ThresholdDecryption(default_council)

        self.audit_trail: List[Dict[str, Any]] = []

    # ===== Phase 14A: Dispute Membership =====

    def generate_identity_commitment(
        self,
        user_address: str,
        salt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate identity commitment for on-chain registration."""
        secret, hash_value = self.membership_circuit.generate_identity_commitment(
            user_address, salt
        )
        return {
            "identity_secret": secret,
            "identity_hash": hash_value,
            "user_address": user_address
        }

    def generate_identity_proof(
        self,
        dispute_id: str,
        prover_address: str,
        identity_secret: str,
        identity_manager: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Generate ZK proof of dispute membership."""
        return self.membership_circuit.generate_proof(
            dispute_id, prover_address, identity_secret, identity_manager
        )

    def verify_identity_proof(
        self,
        proof_id: str,
        expected_identity_hash: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify ZK identity proof."""
        return self.membership_circuit.verify_proof(proof_id, expected_identity_hash)

    # ===== Phase 14B: Viewing Keys =====

    def create_viewing_key(
        self,
        dispute_id: str,
        metadata: Dict[str, Any],
        share_holders: Optional[List[str]] = None,
        threshold: int = 3
    ) -> Tuple[bool, Dict[str, Any]]:
        """Create viewing key for dispute."""
        if share_holders is None:
            share_holders = self.threshold_decryption.council_members

        return self.viewing_keys.create_viewing_key(
            dispute_id, metadata, share_holders, threshold
        )

    def submit_key_share(
        self,
        key_id: str,
        holder: str,
        share_data: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Submit a share for key reconstruction."""
        return self.viewing_keys.submit_share(key_id, holder, share_data)

    def reconstruct_viewing_key(
        self,
        key_id: str,
        authorization: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Reconstruct viewing key from shares."""
        return self.viewing_keys.reconstruct_key(key_id, authorization)

    # ===== Phase 14C: Inference Mitigations =====

    def submit_to_batch(
        self,
        tx_type: str,
        tx_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Submit transaction to batching queue."""
        return self.batching_queue.submit_transaction(tx_type, tx_data)

    def advance_block(self, new_block: int) -> List[Dict[str, Any]]:
        """Advance block and release batches."""
        released = self.batching_queue.advance_block(new_block)

        # Maybe generate dummy
        if self.dummy_generator.should_generate():
            dummy = self.dummy_generator.generate_dummy()
            released.append(dummy)

        return released

    # ===== Phase 14D: Compliance =====

    def submit_compliance_request(
        self,
        key_id: str,
        requester: str,
        warrant_hash: str,
        justification: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Submit compliance request for key disclosure."""
        return self.threshold_decryption.submit_compliance_request(
            key_id, requester, warrant_hash, justification
        )

    def submit_compliance_vote(
        self,
        request_id: str,
        voter: str,
        approve: bool,
        signature: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Submit vote on compliance request."""
        return self.threshold_decryption.submit_vote(
            request_id, voter, approve, signature
        )

    def get_compliance_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get compliance request status."""
        return self.threshold_decryption.get_request_status(request_id)

    # ===== Statistics & Audit =====

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "identity_proofs": {
                "total": len(self.membership_circuit.proofs),
                "verified": len([p for p in self.membership_circuit.proofs.values()
                               if p.status == ProofStatus.VERIFIED])
            },
            "viewing_keys": {
                "total": len(self.viewing_keys.keys),
                "with_shares_submitted": len(self.viewing_keys.submitted_shares)
            },
            "batching": {
                "current_batch_size": len(self.batching_queue.current_batch.transactions)
                if self.batching_queue.current_batch else 0,
                "released_batches": len(self.batching_queue.released_batches)
            },
            "dummies": self.dummy_generator.get_statistics(),
            "compliance": {
                "pending_requests": len([r for r in self.threshold_decryption.requests.values()
                                        if r.status == VoteStatus.PENDING]),
                "approved_requests": len([r for r in self.threshold_decryption.requests.values()
                                         if r.status == VoteStatus.APPROVED]),
                "council_size": len(self.threshold_decryption.council_members)
            }
        }

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get combined audit trail from all components."""
        trails = (
            self.membership_circuit.audit_trail +
            self.viewing_keys.audit_trail +
            self.batching_queue.audit_trail +
            self.dummy_generator.audit_trail +
            self.threshold_decryption.audit_trail
        )

        # Sort by timestamp
        trails.sort(key=lambda x: x["timestamp"], reverse=True)

        return trails[:limit]
