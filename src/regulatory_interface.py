"""
NCIP-009: Regulatory Interface Modules & Compliance Proofs

This module implements regulatory compliance proving without exposing private data
or surrendering semantic authority:
- Regulatory Interface Modules (RIMs) for specific regimes
- Compliance proof generation (immutability, retention, consent, access, privacy)
- Zero-knowledge proof mechanisms for privacy preservation
- Proof package structure with scope minimality
- Validator verification of proof correctness

Core Principle: Compliance is proven cryptographically, not narratively.

Final Guarantee: Regulators can verify that rules were followed
without being able to decide what was meant.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import secrets


class RegulatoryRegime(Enum):
    """
    Supported regulatory regimes per NCIP-009 Section 3.
    """
    SEC_17A_4 = "SEC-17a-4"      # SEC Rule 17a-4 (broker-dealer records)
    GDPR = "GDPR"                 # EU General Data Protection Regulation
    HIPAA = "HIPAA"               # Health Insurance Portability and Accountability Act
    SOX = "SOX"                   # Sarbanes-Oxley Act
    CCPA = "CCPA"                 # California Consumer Privacy Act
    PCI_DSS = "PCI-DSS"           # Payment Card Industry Data Security Standard
    FINRA = "FINRA"               # Financial Industry Regulatory Authority
    MiFID_II = "MiFID-II"         # Markets in Financial Instruments Directive II


class ComplianceClaimType(Enum):
    """
    Compliance proof claim types per NCIP-009 Section 4.
    """
    IMMUTABILITY = "immutability"      # Record Immutability (Temporal Fixity + hash chains)
    RETENTION = "retention"            # Retention (WORM export certificates)
    CONSENT = "consent"                # Consent (Ratified PoUs)
    ACCESS_CONTROL = "access_control"  # Access Control (Boundary Daemon logs)
    PRIVACY = "privacy"                # Privacy (ZK proofs)
    AUTHORSHIP = "authorship"          # Authorship verification
    INTEGRITY = "integrity"            # Data integrity
    AUDIT_TRAIL = "audit_trail"        # Complete audit trail


class ProofMechanism(Enum):
    """Mechanisms used to generate proofs."""
    HASH_CHAIN = "hash_chain"                # Temporal fixity via hash chains
    WORM_CERTIFICATE = "worm_certificate"    # Write-Once-Read-Many export
    RATIFIED_POU = "ratified_pou"            # Proof of Understanding ratification
    BOUNDARY_LOG = "boundary_log"            # Boundary Daemon access logs
    ZERO_KNOWLEDGE = "zero_knowledge"        # ZK proofs for privacy
    MERKLE_PROOF = "merkle_proof"            # Merkle tree inclusion proof
    SIGNATURE = "signature"                   # Digital signature


class DisclosureScope(Enum):
    """Scope of proof disclosure."""
    REGULATOR_ONLY = "regulator_only"    # Only to specific regulator
    AUDITOR_ONLY = "auditor_only"        # Only to authorized auditor
    COURT_ORDER = "court_order"          # Only under court order
    PUBLIC = "public"                    # Publicly verifiable (privacy-preserving)


class ProofStatus(Enum):
    """Status of a compliance proof."""
    PENDING = "pending"
    GENERATED = "generated"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class ZKProof:
    """
    Zero-Knowledge Proof per NCIP-009 Section 4.

    Proves compliance claims without revealing underlying data.
    """
    proof_id: str
    claim_type: ComplianceClaimType
    commitment: str         # Cryptographic commitment
    challenge: str          # Challenge value
    response: str           # Response (proof)
    public_inputs: List[str] = field(default_factory=list)

    # Verification
    verified: bool = False
    verified_at: Optional[datetime] = None
    verifier_id: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if proof has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proof_id": self.proof_id,
            "claim_type": self.claim_type.value,
            "commitment": self.commitment,
            "verified": self.verified,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class ComplianceArtifact:
    """
    An artifact included in a compliance proof package.
    """
    artifact_id: str
    artifact_type: str      # e.g., "t0_snapshot_hash", "chain_segment_hash", "pou_hash"
    hash_value: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WORMCertificate:
    """
    Write-Once-Read-Many export certificate for retention proof.
    """
    certificate_id: str
    entry_ids: List[str]
    export_hash: str
    retention_start: datetime
    retention_period_years: int
    storage_location: str
    immutable: bool = True

    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def retention_end(self) -> datetime:
        """Calculate retention end date."""
        return self.retention_start + timedelta(days=self.retention_period_years * 365)

    @property
    def is_within_retention(self) -> bool:
        """Check if within retention period."""
        now = datetime.utcnow()
        return self.retention_start <= now <= self.retention_end


@dataclass
class AccessLogEntry:
    """
    Boundary Daemon access log entry for access control proof.
    """
    log_id: str
    entry_id: str
    accessor_id: str
    access_type: str        # read, write, delete, etc.
    timestamp: datetime
    authorized: bool
    authorization_proof: Optional[str] = None
    boundary_daemon_signature: Optional[str] = None


@dataclass
class ComplianceProof:
    """
    Compliance Proof Package per NCIP-009 Section 6.

    Proofs MUST be: Minimal, Purpose-bound, Non-semantic
    Proofs MUST NOT: Reveal unrelated intents, Introduce reinterpretation, Persist beyond scope
    """
    proof_id: str
    regime: RegulatoryRegime
    claims: List[ComplianceClaimType]

    # Artifacts
    artifacts: List[ComplianceArtifact] = field(default_factory=list)

    # Privacy mechanism
    privacy_method: ProofMechanism = ProofMechanism.ZERO_KNOWLEDGE
    disclosure_scope: DisclosureScope = DisclosureScope.REGULATOR_ONLY

    # ZK proofs for privacy claims
    zk_proofs: List[ZKProof] = field(default_factory=list)

    # WORM certificate for retention
    worm_certificate: Optional[WORMCertificate] = None

    # Status
    status: ProofStatus = ProofStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None

    # Scope control
    entry_ids_covered: List[str] = field(default_factory=list)
    scope_hash: Optional[str] = None  # Hash of covered scope for minimality verification

    # Validator verification
    validator_signatures: List[Dict[str, str]] = field(default_factory=list)

    def is_minimal(self) -> bool:
        """Check if proof covers only necessary scope."""
        # Proof is minimal if it only includes artifacts for claimed purposes
        artifact_types = {a.artifact_type for a in self.artifacts}
        required_types = self._get_required_artifact_types()
        return artifact_types.issubset(required_types)

    def _get_required_artifact_types(self) -> Set[str]:
        """Get required artifact types for claims."""
        type_map = {
            ComplianceClaimType.IMMUTABILITY: {"t0_snapshot_hash", "chain_segment_hash"},
            ComplianceClaimType.RETENTION: {"worm_certificate", "retention_hash"},
            ComplianceClaimType.CONSENT: {"pou_hash", "ratification_hash"},
            ComplianceClaimType.ACCESS_CONTROL: {"access_log_hash", "boundary_log_hash"},
            ComplianceClaimType.PRIVACY: {"zk_proof", "commitment_hash"},
            ComplianceClaimType.AUTHORSHIP: {"author_signature_hash", "identity_proof"},
            ComplianceClaimType.INTEGRITY: {"merkle_root", "chain_segment_hash"},
            ComplianceClaimType.AUDIT_TRAIL: {"audit_log_hash", "event_chain_hash"},
        }
        required = set()
        for claim in self.claims:
            required.update(type_map.get(claim, set()))
        return required

    def is_purpose_bound(self) -> bool:
        """Check if proof is bound to specific regulatory purpose."""
        return self.regime is not None and len(self.claims) > 0

    def is_non_semantic(self) -> bool:
        """Check if proof does not reveal semantic content."""
        # All artifacts should be hashes, not raw content
        for artifact in self.artifacts:
            if not artifact.hash_value:
                return False
        return True

    def to_package(self) -> Dict[str, Any]:
        """Generate compliance proof package per NCIP-009 Section 6."""
        return {
            "compliance_proof": {
                "regime": self.regime.value,
                "proof_id": self.proof_id,
                "claims": [c.value for c in self.claims],
                "artifacts": [
                    {
                        "type": a.artifact_type,
                        "hash": a.hash_value,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in self.artifacts
                ],
                "privacy": {
                    "method": self.privacy_method.value,
                    "disclosure_scope": self.disclosure_scope.value
                },
                "status": self.status.value,
                "created_at": self.created_at.isoformat(),
                "expires_at": self.expires_at.isoformat() if self.expires_at else None,
                "validator_signatures": self.validator_signatures
            }
        }


@dataclass
class RegulatoryInterfaceModule:
    """
    Regulatory Interface Module (RIM) per NCIP-009 Section 3.

    A RIM is a scoped adapter that generates compliance proofs for a specific regime.
    """
    rim_id: str
    regime: RegulatoryRegime
    description: str

    # Supported claims for this regime
    supported_claims: List[ComplianceClaimType] = field(default_factory=list)

    # Retention requirements
    retention_years: int = 7  # Default SEC 17a-4 requirement

    # Configuration
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Statistics
    proofs_generated: int = 0
    proofs_verified: int = 0


class RegulatoryInterfaceManager:
    """
    Manages Regulatory Interface Modules and Compliance Proofs per NCIP-009.

    Responsibilities:
    - RIM registration and management
    - Compliance proof generation
    - ZK proof creation for privacy
    - Proof verification
    - Scope minimality enforcement
    - Abuse prevention
    """

    # Default retention periods by regime
    RETENTION_PERIODS = {
        RegulatoryRegime.SEC_17A_4: 7,   # 7 years
        RegulatoryRegime.GDPR: 6,        # Variable, using 6 as default
        RegulatoryRegime.HIPAA: 6,       # 6 years
        RegulatoryRegime.SOX: 7,         # 7 years
        RegulatoryRegime.CCPA: 2,        # 2 years
        RegulatoryRegime.PCI_DSS: 1,     # 1 year minimum
        RegulatoryRegime.FINRA: 6,       # 6 years
        RegulatoryRegime.MiFID_II: 5,    # 5 years
    }

    # Proof validity period (days)
    DEFAULT_PROOF_VALIDITY_DAYS = 90

    def __init__(self):
        self.rims: Dict[str, RegulatoryInterfaceModule] = {}
        self.proofs: Dict[str, ComplianceProof] = {}
        self.zk_proofs: Dict[str, ZKProof] = {}
        self.worm_certificates: Dict[str, WORMCertificate] = {}
        self.access_logs: Dict[str, List[AccessLogEntry]] = {}

        self.rim_counter = 0
        self.proof_counter = 0
        self.zk_counter = 0

        # Initialize default RIMs
        self._initialize_default_rims()

    def _initialize_default_rims(self):
        """Initialize RIMs for common regulatory regimes."""
        default_rims = [
            (RegulatoryRegime.SEC_17A_4, "SEC Rule 17a-4 Broker-Dealer Records",
             [ComplianceClaimType.IMMUTABILITY, ComplianceClaimType.RETENTION,
              ComplianceClaimType.AUTHORSHIP, ComplianceClaimType.AUDIT_TRAIL]),
            (RegulatoryRegime.GDPR, "EU General Data Protection Regulation",
             [ComplianceClaimType.CONSENT, ComplianceClaimType.PRIVACY,
              ComplianceClaimType.ACCESS_CONTROL, ComplianceClaimType.RETENTION]),
            (RegulatoryRegime.HIPAA, "Health Insurance Portability and Accountability Act",
             [ComplianceClaimType.PRIVACY, ComplianceClaimType.ACCESS_CONTROL,
              ComplianceClaimType.INTEGRITY, ComplianceClaimType.AUDIT_TRAIL]),
            (RegulatoryRegime.SOX, "Sarbanes-Oxley Act",
             [ComplianceClaimType.IMMUTABILITY, ComplianceClaimType.INTEGRITY,
              ComplianceClaimType.AUTHORSHIP, ComplianceClaimType.AUDIT_TRAIL]),
        ]

        for regime, description, claims in default_rims:
            self.register_rim(regime, description, claims)

    # -------------------------------------------------------------------------
    # RIM Management
    # -------------------------------------------------------------------------

    def register_rim(
        self,
        regime: RegulatoryRegime,
        description: str,
        supported_claims: List[ComplianceClaimType]
    ) -> RegulatoryInterfaceModule:
        """Register a new Regulatory Interface Module."""
        self.rim_counter += 1
        rim_id = f"RIM-{regime.value}-{self.rim_counter:04d}"

        retention_years = self.RETENTION_PERIODS.get(regime, 7)

        rim = RegulatoryInterfaceModule(
            rim_id=rim_id,
            regime=regime,
            description=description,
            supported_claims=supported_claims,
            retention_years=retention_years
        )

        self.rims[rim_id] = rim
        return rim

    def get_rim(self, regime: RegulatoryRegime) -> Optional[RegulatoryInterfaceModule]:
        """Get RIM for a specific regime."""
        for rim in self.rims.values():
            if rim.regime == regime and rim.enabled:
                return rim
        return None

    def list_rims(self) -> List[RegulatoryInterfaceModule]:
        """List all registered RIMs."""
        return list(self.rims.values())

    # -------------------------------------------------------------------------
    # Compliance Proof Generation
    # -------------------------------------------------------------------------

    def generate_compliance_proof(
        self,
        regime: RegulatoryRegime,
        claims: List[ComplianceClaimType],
        entry_ids: List[str],
        entry_hashes: Dict[str, str],
        pou_hashes: Optional[List[str]] = None,
        disclosure_scope: DisclosureScope = DisclosureScope.REGULATOR_ONLY,
        validity_days: Optional[int] = None
    ) -> Tuple[Optional[ComplianceProof], List[str]]:
        """
        Generate a compliance proof per NCIP-009.

        Proofs MUST be: Minimal, Purpose-bound, Non-semantic
        """
        errors = []

        # Get RIM for regime
        rim = self.get_rim(regime)
        if not rim:
            errors.append(f"No RIM registered for regime: {regime.value}")
            return (None, errors)

        # Validate claims are supported by RIM
        unsupported = [c for c in claims if c not in rim.supported_claims]
        if unsupported:
            errors.append(f"Unsupported claims for {regime.value}: {[c.value for c in unsupported]}")
            return (None, errors)

        if not entry_ids:
            errors.append("At least one entry_id is required")
            return (None, errors)

        self.proof_counter += 1
        proof_id = f"CP-{self.proof_counter:04d}"

        validity = validity_days or self.DEFAULT_PROOF_VALIDITY_DAYS
        expires_at = datetime.utcnow() + timedelta(days=validity)

        proof = ComplianceProof(
            proof_id=proof_id,
            regime=regime,
            claims=claims,
            privacy_method=ProofMechanism.ZERO_KNOWLEDGE,
            disclosure_scope=disclosure_scope,
            expires_at=expires_at,
            entry_ids_covered=entry_ids
        )

        # Generate artifacts based on claims
        artifacts = self._generate_artifacts(claims, entry_ids, entry_hashes, pou_hashes)
        proof.artifacts = artifacts

        # Calculate scope hash for minimality verification
        proof.scope_hash = self._compute_scope_hash(entry_ids)

        # Generate ZK proofs for privacy claims
        if ComplianceClaimType.PRIVACY in claims:
            zk_proof = self._generate_zk_proof(
                ComplianceClaimType.PRIVACY,
                entry_ids,
                entry_hashes
            )
            proof.zk_proofs.append(zk_proof)

        # Generate WORM certificate for retention claims
        if ComplianceClaimType.RETENTION in claims:
            worm_cert = self._generate_worm_certificate(entry_ids, rim.retention_years)
            proof.worm_certificate = worm_cert
            self.worm_certificates[worm_cert.certificate_id] = worm_cert

        # Verify proof constraints
        if not proof.is_minimal():
            errors.append("Proof violates minimality constraint")
        if not proof.is_purpose_bound():
            errors.append("Proof violates purpose-bound constraint")
        if not proof.is_non_semantic():
            errors.append("Proof violates non-semantic constraint")

        if errors:
            return (None, errors)

        proof.status = ProofStatus.GENERATED
        self.proofs[proof_id] = proof
        rim.proofs_generated += 1

        return (proof, [])

    def _generate_artifacts(
        self,
        claims: List[ComplianceClaimType],
        entry_ids: List[str],
        entry_hashes: Dict[str, str],
        pou_hashes: Optional[List[str]]
    ) -> List[ComplianceArtifact]:
        """Generate artifacts for claims."""
        artifacts = []
        artifact_counter = 0

        for claim in claims:
            if claim == ComplianceClaimType.IMMUTABILITY:
                # T0 snapshot hash
                artifact_counter += 1
                t0_hash = self._compute_chain_hash(list(entry_hashes.values()))
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="t0_snapshot_hash",
                    hash_value=t0_hash
                ))

                # Chain segment hash
                artifact_counter += 1
                chain_hash = self._compute_chain_hash(entry_ids)
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="chain_segment_hash",
                    hash_value=chain_hash
                ))

            elif claim == ComplianceClaimType.RETENTION:
                artifact_counter += 1
                retention_hash = self._compute_retention_hash(entry_ids)
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="retention_hash",
                    hash_value=retention_hash
                ))

            elif claim == ComplianceClaimType.CONSENT:
                if pou_hashes:
                    for pou_hash in pou_hashes:
                        artifact_counter += 1
                        artifacts.append(ComplianceArtifact(
                            artifact_id=f"ART-{artifact_counter:04d}",
                            artifact_type="pou_hash",
                            hash_value=pou_hash
                        ))

            elif claim == ComplianceClaimType.ACCESS_CONTROL:
                artifact_counter += 1
                access_hash = self._compute_access_log_hash(entry_ids)
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="access_log_hash",
                    hash_value=access_hash
                ))

            elif claim == ComplianceClaimType.PRIVACY:
                artifact_counter += 1
                commitment = self._generate_commitment(entry_ids)
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="commitment_hash",
                    hash_value=commitment
                ))

            elif claim == ComplianceClaimType.AUTHORSHIP:
                for entry_id in entry_ids:
                    if entry_id in entry_hashes:
                        artifact_counter += 1
                        artifacts.append(ComplianceArtifact(
                            artifact_id=f"ART-{artifact_counter:04d}",
                            artifact_type="author_signature_hash",
                            hash_value=entry_hashes[entry_id],
                            metadata={"entry_id": entry_id}
                        ))

            elif claim == ComplianceClaimType.INTEGRITY:
                artifact_counter += 1
                merkle_root = self._compute_merkle_root(list(entry_hashes.values()))
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="merkle_root",
                    hash_value=merkle_root
                ))

            elif claim == ComplianceClaimType.AUDIT_TRAIL:
                artifact_counter += 1
                audit_hash = self._compute_audit_trail_hash(entry_ids)
                artifacts.append(ComplianceArtifact(
                    artifact_id=f"ART-{artifact_counter:04d}",
                    artifact_type="audit_log_hash",
                    hash_value=audit_hash
                ))

        return artifacts

    def _compute_chain_hash(self, values: List[str]) -> str:
        """Compute hash chain of values."""
        combined = "|".join(sorted(values))
        return hashlib.sha256(combined.encode()).hexdigest()

    def _compute_retention_hash(self, entry_ids: List[str]) -> str:
        """Compute retention proof hash."""
        content = f"RETENTION:{','.join(sorted(entry_ids))}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _compute_access_log_hash(self, entry_ids: List[str]) -> str:
        """Compute access log hash for entries."""
        logs = []
        for entry_id in entry_ids:
            if entry_id in self.access_logs:
                for log in self.access_logs[entry_id]:
                    logs.append(f"{log.log_id}:{log.timestamp.isoformat()}")
        content = "|".join(sorted(logs)) if logs else f"NO_LOGS:{','.join(entry_ids)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _compute_scope_hash(self, entry_ids: List[str]) -> str:
        """Compute hash of proof scope for minimality verification."""
        content = f"SCOPE:{','.join(sorted(entry_ids))}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Compute Merkle root of hashes."""
        if not hashes:
            return hashlib.sha256(b"EMPTY").hexdigest()

        # Simple Merkle tree construction
        current_level = [hashlib.sha256(h.encode()).hexdigest() for h in hashes]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                if i + 1 < len(current_level):
                    combined = current_level[i] + current_level[i + 1]
                else:
                    combined = current_level[i] + current_level[i]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            current_level = next_level

        return current_level[0]

    def _compute_audit_trail_hash(self, entry_ids: List[str]) -> str:
        """Compute audit trail hash."""
        content = f"AUDIT:{','.join(sorted(entry_ids))}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _generate_commitment(self, entry_ids: List[str]) -> str:
        """Generate cryptographic commitment for ZK proof."""
        randomness = secrets.token_hex(32)
        content = f"COMMIT:{','.join(sorted(entry_ids))}:{randomness}"
        return hashlib.sha256(content.encode()).hexdigest()

    # -------------------------------------------------------------------------
    # Zero-Knowledge Proofs
    # -------------------------------------------------------------------------

    def _generate_zk_proof(
        self,
        claim_type: ComplianceClaimType,
        entry_ids: List[str],
        entry_hashes: Dict[str, str]
    ) -> ZKProof:
        """
        Generate a Zero-Knowledge Proof per NCIP-009 Section 4.

        This is a simplified simulation of ZK proof generation.
        In production, this would use actual ZK-SNARK or ZK-STARK circuits.
        """
        self.zk_counter += 1
        proof_id = f"ZKP-{self.zk_counter:04d}"

        # Generate commitment (Pedersen-style)
        randomness = secrets.token_hex(32)
        content = f"{','.join(sorted(entry_ids))}:{randomness}"
        commitment = hashlib.sha256(content.encode()).hexdigest()

        # Generate challenge (Fiat-Shamir)
        challenge_input = f"{commitment}:{claim_type.value}"
        challenge = hashlib.sha256(challenge_input.encode()).hexdigest()[:16]

        # Generate response
        response_input = f"{randomness}:{challenge}"
        response = hashlib.sha256(response_input.encode()).hexdigest()

        # Public inputs (what the verifier sees)
        public_inputs = [
            f"claim:{claim_type.value}",
            f"entry_count:{len(entry_ids)}",
            f"timestamp:{datetime.utcnow().isoformat()}"
        ]

        zk_proof = ZKProof(
            proof_id=proof_id,
            claim_type=claim_type,
            commitment=commitment,
            challenge=challenge,
            response=response,
            public_inputs=public_inputs,
            expires_at=datetime.utcnow() + timedelta(days=self.DEFAULT_PROOF_VALIDITY_DAYS)
        )

        self.zk_proofs[proof_id] = zk_proof
        return zk_proof

    def verify_zk_proof(self, proof_id: str) -> Dict[str, Any]:
        """
        Verify a Zero-Knowledge Proof.

        In production, this would verify the actual ZK circuit.
        """
        zk_proof = self.zk_proofs.get(proof_id)
        if not zk_proof:
            return {
                "valid": False,
                "reason": f"ZK proof {proof_id} not found"
            }

        if zk_proof.is_expired():
            return {
                "valid": False,
                "reason": "ZK proof has expired"
            }

        # Simplified verification (in production: actual ZK verification)
        # Verify challenge was correctly derived
        expected_challenge_input = f"{zk_proof.commitment}:{zk_proof.claim_type.value}"
        expected_challenge = hashlib.sha256(expected_challenge_input.encode()).hexdigest()[:16]

        if zk_proof.challenge != expected_challenge:
            return {
                "valid": False,
                "reason": "Challenge verification failed"
            }

        zk_proof.verified = True
        zk_proof.verified_at = datetime.utcnow()

        return {
            "valid": True,
            "proof_id": proof_id,
            "claim_type": zk_proof.claim_type.value,
            "verified_at": zk_proof.verified_at.isoformat(),
            "message": "ZK proof verified - compliance proven without data disclosure"
        }

    # -------------------------------------------------------------------------
    # WORM Certificates
    # -------------------------------------------------------------------------

    def _generate_worm_certificate(
        self,
        entry_ids: List[str],
        retention_years: int
    ) -> WORMCertificate:
        """Generate WORM (Write-Once-Read-Many) export certificate."""
        cert_id = f"WORM-{secrets.token_hex(8).upper()}"

        export_content = f"WORM:{','.join(sorted(entry_ids))}:{datetime.utcnow().isoformat()}"
        export_hash = hashlib.sha256(export_content.encode()).hexdigest()

        return WORMCertificate(
            certificate_id=cert_id,
            entry_ids=entry_ids,
            export_hash=export_hash,
            retention_start=datetime.utcnow(),
            retention_period_years=retention_years,
            storage_location=f"worm://storage/{cert_id}",
            immutable=True
        )

    # -------------------------------------------------------------------------
    # Access Logging
    # -------------------------------------------------------------------------

    def record_access(
        self,
        entry_id: str,
        accessor_id: str,
        access_type: str,
        authorized: bool,
        authorization_proof: Optional[str] = None
    ) -> AccessLogEntry:
        """Record an access event for compliance proof."""
        log_id = f"LOG-{secrets.token_hex(8).upper()}"

        log_entry = AccessLogEntry(
            log_id=log_id,
            entry_id=entry_id,
            accessor_id=accessor_id,
            access_type=access_type,
            timestamp=datetime.utcnow(),
            authorized=authorized,
            authorization_proof=authorization_proof,
            boundary_daemon_signature=hashlib.sha256(
                f"{log_id}:{entry_id}:{accessor_id}:{access_type}".encode()
            ).hexdigest()[:32]
        )

        if entry_id not in self.access_logs:
            self.access_logs[entry_id] = []
        self.access_logs[entry_id].append(log_entry)

        return log_entry

    # -------------------------------------------------------------------------
    # Proof Verification
    # -------------------------------------------------------------------------

    def verify_compliance_proof(
        self,
        proof_id: str,
        validator_id: str
    ) -> Dict[str, Any]:
        """
        Verify a compliance proof per NCIP-009 Section 7.

        Validators verify:
        - Proof correctness
        - Scope minimality
        - Semantic non-interference

        Validators MUST reject overbroad proofs.
        """
        proof = self.proofs.get(proof_id)
        if not proof:
            return {
                "valid": False,
                "reason": f"Proof {proof_id} not found"
            }

        issues = []

        # Check proof constraints
        if not proof.is_minimal():
            issues.append("Proof violates minimality - overbroad scope")

        if not proof.is_purpose_bound():
            issues.append("Proof not purpose-bound to regulatory regime")

        if not proof.is_non_semantic():
            issues.append("Proof reveals semantic content - privacy violation")

        # Check expiration
        if proof.expires_at and datetime.utcnow() > proof.expires_at:
            issues.append("Proof has expired")

        # Verify ZK proofs
        for zk_proof in proof.zk_proofs:
            zk_result = self.verify_zk_proof(zk_proof.proof_id)
            if not zk_result["valid"]:
                issues.append(f"ZK proof verification failed: {zk_result['reason']}")

        # Verify WORM certificate
        if proof.worm_certificate:
            if not proof.worm_certificate.is_within_retention:
                issues.append("WORM certificate outside retention period")

        if issues:
            proof.status = ProofStatus.REJECTED
            return {
                "valid": False,
                "proof_id": proof_id,
                "issues": issues,
                "validator_id": validator_id,
                "action": "REJECT - overbroad or invalid proof"
            }

        # Add validator signature
        signature = hashlib.sha256(
            f"{proof_id}:{validator_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()

        proof.validator_signatures.append({
            "validator_id": validator_id,
            "signature": signature,
            "timestamp": datetime.utcnow().isoformat()
        })

        proof.status = ProofStatus.VERIFIED
        proof.verified_at = datetime.utcnow()

        # Update RIM stats
        rim = self.get_rim(proof.regime)
        if rim:
            rim.proofs_verified += 1

        return {
            "valid": True,
            "proof_id": proof_id,
            "regime": proof.regime.value,
            "claims": [c.value for c in proof.claims],
            "validator_id": validator_id,
            "verified_at": proof.verified_at.isoformat(),
            "message": "Proof verified - compliance confirmed cryptographically"
        }

    def reject_overbroad_proof(
        self,
        proof_id: str,
        reason: str,
        validator_id: str
    ) -> Dict[str, Any]:
        """
        Reject an overbroad proof per NCIP-009 Section 7.

        Validators MUST reject overbroad proofs.
        """
        proof = self.proofs.get(proof_id)
        if not proof:
            return {
                "status": "error",
                "message": f"Proof {proof_id} not found"
            }

        proof.status = ProofStatus.REJECTED

        return {
            "status": "rejected",
            "proof_id": proof_id,
            "reason": reason,
            "validator_id": validator_id,
            "timestamp": datetime.utcnow().isoformat(),
            "rule": "Validators MUST reject overbroad proofs per NCIP-009 Section 7"
        }

    # -------------------------------------------------------------------------
    # Abuse Prevention
    # -------------------------------------------------------------------------

    def check_abuse_patterns(
        self,
        requester_id: str,
        regime: RegulatoryRegime,
        entry_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Check for abuse patterns per NCIP-009 Section 8.

        Prevents:
        - Compliance laundering
        - Fishing expeditions
        - Semantic leakage
        - Regulator-as-validator escalation
        """
        warnings = []

        # Check for fishing expedition (requesting too many entries)
        if len(entry_ids) > 100:
            warnings.append({
                "type": "fishing_expedition",
                "message": f"Request covers {len(entry_ids)} entries - possible fishing expedition"
            })

        # Check for repeated requests
        requester_proofs = [
            p for p in self.proofs.values()
            if requester_id in str(p.validator_signatures)
        ]
        if len(requester_proofs) > 10:
            warnings.append({
                "type": "excessive_requests",
                "message": "Requester has made many proof requests - monitor for abuse"
            })

        # Check scope overlap with existing proofs
        for proof in self.proofs.values():
            if proof.regime == regime:
                overlap = set(entry_ids) & set(proof.entry_ids_covered)
                if len(overlap) > 0 and proof.status == ProofStatus.VERIFIED:
                    warnings.append({
                        "type": "duplicate_scope",
                        "message": f"Overlapping scope with existing proof {proof.proof_id}"
                    })

        return {
            "requester_id": requester_id,
            "regime": regime.value,
            "entry_count": len(entry_ids),
            "warnings": warnings,
            "allow": len(warnings) == 0,
            "message": "Abuse check complete" if not warnings else "Review warnings before proceeding"
        }

    def prevent_semantic_leakage(
        self,
        proof_id: str
    ) -> Dict[str, Any]:
        """
        Verify proof does not leak semantic content.

        Proofs MUST NOT reveal unrelated intents.
        """
        proof = self.proofs.get(proof_id)
        if not proof:
            return {
                "status": "error",
                "message": f"Proof {proof_id} not found"
            }

        leakage_detected = False
        issues = []

        # Check all artifacts are hashed (not raw content)
        for artifact in proof.artifacts:
            if not artifact.hash_value:
                leakage_detected = True
                issues.append(f"Artifact {artifact.artifact_id} missing hash - potential leakage")

            # Check hash format (should be hex string of proper length)
            if artifact.hash_value and len(artifact.hash_value) < 32:
                leakage_detected = True
                issues.append(f"Artifact {artifact.artifact_id} has short hash - possible raw data")

        # Check ZK proofs hide actual content
        for zk_proof in proof.zk_proofs:
            if any("content:" in pi.lower() for pi in zk_proof.public_inputs):
                leakage_detected = True
                issues.append(f"ZK proof {zk_proof.proof_id} may leak content in public inputs")

        return {
            "proof_id": proof_id,
            "leakage_detected": leakage_detected,
            "issues": issues,
            "status": "BLOCKED" if leakage_detected else "SAFE",
            "rule": "Proofs MUST NOT reveal unrelated intents per NCIP-009 Section 5"
        }

    # -------------------------------------------------------------------------
    # Proof Expiration
    # -------------------------------------------------------------------------

    def check_proof_expiration(self, proof_id: str) -> Dict[str, Any]:
        """
        Check proof expiration.

        Proofs MUST NOT persist beyond scope.
        """
        proof = self.proofs.get(proof_id)
        if not proof:
            return {"status": "error", "message": f"Proof {proof_id} not found"}

        now = datetime.utcnow()

        if proof.expires_at and now > proof.expires_at:
            proof.status = ProofStatus.EXPIRED
            return {
                "proof_id": proof_id,
                "expired": True,
                "expired_at": proof.expires_at.isoformat(),
                "message": "Proof has expired - cannot be used for compliance"
            }

        remaining_days = (proof.expires_at - now).days if proof.expires_at else None

        return {
            "proof_id": proof_id,
            "expired": False,
            "expires_at": proof.expires_at.isoformat() if proof.expires_at else None,
            "remaining_days": remaining_days,
            "status": proof.status.value
        }

    def revoke_proof(
        self,
        proof_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Revoke a compliance proof."""
        proof = self.proofs.get(proof_id)
        if not proof:
            return {"status": "error", "message": f"Proof {proof_id} not found"}

        proof.status = ProofStatus.REVOKED

        return {
            "proof_id": proof_id,
            "status": "revoked",
            "reason": reason,
            "revoked_at": datetime.utcnow().isoformat()
        }

    # -------------------------------------------------------------------------
    # Reporting
    # -------------------------------------------------------------------------

    def get_proof(self, proof_id: str) -> Optional[ComplianceProof]:
        """Get a compliance proof by ID."""
        return self.proofs.get(proof_id)

    def get_proofs_by_regime(self, regime: RegulatoryRegime) -> List[ComplianceProof]:
        """Get all proofs for a specific regime."""
        return [p for p in self.proofs.values() if p.regime == regime]

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of regulatory interface status."""
        status_counts = {}
        for proof in self.proofs.values():
            status = proof.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        regime_counts = {}
        for proof in self.proofs.values():
            regime = proof.regime.value
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        return {
            "total_rims": len(self.rims),
            "total_proofs": len(self.proofs),
            "total_zk_proofs": len(self.zk_proofs),
            "total_worm_certificates": len(self.worm_certificates),
            "status_counts": status_counts,
            "regime_counts": regime_counts,
            "principle": "Compliance is proven cryptographically, not narratively."
        }

    def generate_compliance_report(
        self,
        regime: RegulatoryRegime,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Generate compliance report for a regime."""
        proofs = self.get_proofs_by_regime(regime)

        if date_range:
            start_date, end_date = date_range
            proofs = [
                p for p in proofs
                if start_date <= p.created_at <= end_date
            ]

        verified = [p for p in proofs if p.status == ProofStatus.VERIFIED]
        rejected = [p for p in proofs if p.status == ProofStatus.REJECTED]

        return {
            "regime": regime.value,
            "report_generated_at": datetime.utcnow().isoformat(),
            "date_range": {
                "start": date_range[0].isoformat() if date_range else None,
                "end": date_range[1].isoformat() if date_range else None
            } if date_range else None,
            "summary": {
                "total_proofs": len(proofs),
                "verified": len(verified),
                "rejected": len(rejected),
                "verification_rate": len(verified) / len(proofs) if proofs else 0
            },
            "guarantee": "Regulators can verify that rules were followed without being able to decide what was meant."
        }
