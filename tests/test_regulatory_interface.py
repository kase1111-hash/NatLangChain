"""
Tests for NCIP-009: Regulatory Interface Modules & Compliance Proofs

Tests cover:
- RIM registration and management
- Compliance proof generation
- ZK proof creation and verification
- Proof constraints (minimal, purpose-bound, non-semantic)
- WORM certificates for retention
- Access logging
- Proof verification
- Abuse prevention
- Semantic leakage prevention
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regulatory_interface import (
    ComplianceClaimType,
    DisclosureScope,
    ProofMechanism,
    ProofStatus,
    RegulatoryInterfaceManager,
    RegulatoryRegime,
)


class TestRegulatoryRegimes:
    """Test regulatory regime support."""

    def test_all_regimes_defined(self):
        """Test all expected regulatory regimes are defined."""
        assert RegulatoryRegime.SEC_17A_4.value == "SEC-17a-4"
        assert RegulatoryRegime.GDPR.value == "GDPR"
        assert RegulatoryRegime.HIPAA.value == "HIPAA"
        assert RegulatoryRegime.SOX.value == "SOX"
        assert RegulatoryRegime.CCPA.value == "CCPA"
        assert RegulatoryRegime.PCI_DSS.value == "PCI-DSS"

    def test_default_rims_initialized(self):
        """Test default RIMs are initialized."""
        manager = RegulatoryInterfaceManager()

        # Should have RIMs for major regimes
        sec_rim = manager.get_rim(RegulatoryRegime.SEC_17A_4)
        gdpr_rim = manager.get_rim(RegulatoryRegime.GDPR)
        hipaa_rim = manager.get_rim(RegulatoryRegime.HIPAA)
        sox_rim = manager.get_rim(RegulatoryRegime.SOX)

        assert sec_rim is not None
        assert gdpr_rim is not None
        assert hipaa_rim is not None
        assert sox_rim is not None


class TestRIMManagement:
    """Test Regulatory Interface Module management."""

    def test_register_rim(self):
        """Test registering a new RIM."""
        manager = RegulatoryInterfaceManager()

        rim = manager.register_rim(
            regime=RegulatoryRegime.PCI_DSS,
            description="Payment Card Industry Data Security Standard",
            supported_claims=[
                ComplianceClaimType.ACCESS_CONTROL,
                ComplianceClaimType.AUDIT_TRAIL
            ]
        )

        assert rim is not None
        assert rim.regime == RegulatoryRegime.PCI_DSS
        assert ComplianceClaimType.ACCESS_CONTROL in rim.supported_claims

    def test_rim_has_retention_period(self):
        """Test RIM has correct retention period."""
        manager = RegulatoryInterfaceManager()

        sec_rim = manager.get_rim(RegulatoryRegime.SEC_17A_4)
        assert sec_rim.retention_years == 7  # SEC requires 7 years

    def test_list_rims(self):
        """Test listing all registered RIMs."""
        manager = RegulatoryInterfaceManager()
        rims = manager.list_rims()

        assert len(rims) >= 4  # At least the 4 default RIMs


class TestComplianceClaimTypes:
    """Test compliance claim types per NCIP-009 Section 4."""

    def test_all_claim_types_exist(self):
        """Test all claim types are defined."""
        assert ComplianceClaimType.IMMUTABILITY.value == "immutability"
        assert ComplianceClaimType.RETENTION.value == "retention"
        assert ComplianceClaimType.CONSENT.value == "consent"
        assert ComplianceClaimType.ACCESS_CONTROL.value == "access_control"
        assert ComplianceClaimType.PRIVACY.value == "privacy"
        assert ComplianceClaimType.AUTHORSHIP.value == "authorship"
        assert ComplianceClaimType.INTEGRITY.value == "integrity"
        assert ComplianceClaimType.AUDIT_TRAIL.value == "audit_trail"

    def test_proof_mechanisms_defined(self):
        """Test proof mechanisms are defined."""
        assert ProofMechanism.HASH_CHAIN.value == "hash_chain"
        assert ProofMechanism.WORM_CERTIFICATE.value == "worm_certificate"
        assert ProofMechanism.RATIFIED_POU.value == "ratified_pou"
        assert ProofMechanism.ZERO_KNOWLEDGE.value == "zero_knowledge"
        assert ProofMechanism.MERKLE_PROOF.value == "merkle_proof"


class TestComplianceProofGeneration:
    """Test compliance proof generation."""

    def test_generate_basic_proof(self):
        """Test generating a basic compliance proof."""
        manager = RegulatoryInterfaceManager()

        proof, errors = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY, ComplianceClaimType.RETENTION],
            entry_ids=["ENTRY-001", "ENTRY-002"],
            entry_hashes={
                "ENTRY-001": "abc123def456",
                "ENTRY-002": "789xyz012abc"
            }
        )

        assert proof is not None
        assert len(errors) == 0
        assert proof.regime == RegulatoryRegime.SEC_17A_4
        assert proof.status == ProofStatus.GENERATED

    def test_proof_has_artifacts(self):
        """Test proof contains appropriate artifacts."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert len(proof.artifacts) > 0
        artifact_types = [a.artifact_type for a in proof.artifacts]
        assert "t0_snapshot_hash" in artifact_types or "chain_segment_hash" in artifact_types

    def test_proof_includes_pou_hashes(self):
        """Test proof includes PoU hashes for consent claims."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.CONSENT],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"},
            pou_hashes=["pou_hash_1", "pou_hash_2"]
        )

        artifact_types = [a.artifact_type for a in proof.artifacts]
        assert "pou_hash" in artifact_types

    def test_unsupported_claims_rejected(self):
        """Test unsupported claims for regime are rejected."""
        manager = RegulatoryInterfaceManager()

        # SEC 17a-4 doesn't support PRIVACY claim by default
        proof, errors = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert proof is None
        assert any("unsupported" in e.lower() for e in errors)


class TestProofConstraints:
    """Test proof constraints per NCIP-009 Section 5."""

    def test_proof_is_minimal(self):
        """Test proof contains only necessary artifacts."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert proof.is_minimal() is True

    def test_proof_is_purpose_bound(self):
        """Test proof is bound to specific regulatory purpose."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert proof.is_purpose_bound() is True
        assert proof.regime is not None
        assert len(proof.claims) > 0

    def test_proof_is_non_semantic(self):
        """Test proof does not reveal semantic content."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert proof.is_non_semantic() is True
        # All artifacts should have hashes, not raw content
        for artifact in proof.artifacts:
            assert artifact.hash_value is not None


class TestZeroKnowledgeProofs:
    """Test ZK proof generation and verification per NCIP-009 Section 4."""

    def test_zk_proof_generated_for_privacy(self):
        """Test ZK proof is generated for privacy claims."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert len(proof.zk_proofs) > 0
        assert proof.zk_proofs[0].claim_type == ComplianceClaimType.PRIVACY

    def test_zk_proof_structure(self):
        """Test ZK proof has correct structure."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        zk_proof = proof.zk_proofs[0]
        assert zk_proof.commitment is not None
        assert zk_proof.challenge is not None
        assert zk_proof.response is not None
        assert len(zk_proof.public_inputs) > 0

    def test_verify_zk_proof(self):
        """Test ZK proof verification."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        zk_proof = proof.zk_proofs[0]
        result = manager.verify_zk_proof(zk_proof.proof_id)

        assert result["valid"] is True
        assert "without data disclosure" in result["message"]

    def test_zk_proof_not_found(self):
        """Test ZK proof verification for non-existent proof."""
        manager = RegulatoryInterfaceManager()
        result = manager.verify_zk_proof("ZKP-NONEXISTENT")

        assert result["valid"] is False
        assert "not found" in result["reason"]


class TestWORMCertificates:
    """Test WORM certificate generation for retention claims."""

    def test_worm_certificate_generated(self):
        """Test WORM certificate is generated for retention claims."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.RETENTION],
            entry_ids=["ENTRY-001", "ENTRY-002"],
            entry_hashes={
                "ENTRY-001": "abc123",
                "ENTRY-002": "def456"
            }
        )

        assert proof.worm_certificate is not None
        assert proof.worm_certificate.immutable is True

    def test_worm_certificate_retention_period(self):
        """Test WORM certificate has correct retention period."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.RETENTION],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        # SEC 17a-4 requires 7 years
        assert proof.worm_certificate.retention_period_years == 7

    def test_worm_certificate_within_retention(self):
        """Test WORM certificate is within retention period."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.RETENTION],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        assert proof.worm_certificate.is_within_retention is True


class TestAccessLogging:
    """Test access logging for access control claims."""

    def test_record_access(self):
        """Test recording an access event."""
        manager = RegulatoryInterfaceManager()

        log_entry = manager.record_access(
            entry_id="ENTRY-001",
            accessor_id="USER-001",
            access_type="read",
            authorized=True,
            authorization_proof="AUTH-001"
        )

        assert log_entry is not None
        assert log_entry.entry_id == "ENTRY-001"
        assert log_entry.authorized is True
        assert log_entry.boundary_daemon_signature is not None

    def test_access_log_included_in_proof(self):
        """Test access logs are included in access control proofs."""
        manager = RegulatoryInterfaceManager()

        # Record some access
        manager.record_access("ENTRY-001", "USER-001", "read", True)
        manager.record_access("ENTRY-001", "USER-002", "write", True)

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.ACCESS_CONTROL],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        artifact_types = [a.artifact_type for a in proof.artifacts]
        assert "access_log_hash" in artifact_types


class TestProofVerification:
    """Test proof verification per NCIP-009 Section 7."""

    def test_verify_valid_proof(self):
        """Test verifying a valid compliance proof."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        result = manager.verify_compliance_proof(proof.proof_id, "VALIDATOR-001")

        assert result["valid"] is True
        assert result["validator_id"] == "VALIDATOR-001"
        assert "cryptographically" in result["message"]

    def test_verified_proof_has_signature(self):
        """Test verified proof has validator signature."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        manager.verify_compliance_proof(proof.proof_id, "VALIDATOR-001")

        assert len(proof.validator_signatures) > 0
        assert proof.validator_signatures[0]["validator_id"] == "VALIDATOR-001"

    def test_reject_overbroad_proof(self):
        """Test validators reject overbroad proofs."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        result = manager.reject_overbroad_proof(
            proof.proof_id,
            "Scope exceeds necessary coverage",
            "VALIDATOR-001"
        )

        assert result["status"] == "rejected"
        assert proof.status == ProofStatus.REJECTED


class TestAbuseResistance:
    """Test abuse resistance per NCIP-009 Section 8."""

    def test_detect_fishing_expedition(self):
        """Test detection of fishing expedition (too many entries)."""
        manager = RegulatoryInterfaceManager()

        # Request with many entries
        many_entries = [f"ENTRY-{i:04d}" for i in range(150)]

        result = manager.check_abuse_patterns(
            requester_id="REQUESTER-001",
            regime=RegulatoryRegime.SEC_17A_4,
            entry_ids=many_entries
        )

        assert len(result["warnings"]) > 0
        assert any(w["type"] == "fishing_expedition" for w in result["warnings"])

    def test_normal_request_allowed(self):
        """Test normal request is allowed."""
        manager = RegulatoryInterfaceManager()

        result = manager.check_abuse_patterns(
            requester_id="REQUESTER-001",
            regime=RegulatoryRegime.SEC_17A_4,
            entry_ids=["ENTRY-001", "ENTRY-002"]
        )

        assert result["allow"] is True
        assert len(result["warnings"]) == 0


class TestSemanticLeakagePrevention:
    """Test semantic leakage prevention per NCIP-009 Section 5."""

    def test_prevent_semantic_leakage(self):
        """Test checking proof for semantic leakage."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123def456789012345678901234567890"}
        )

        result = manager.prevent_semantic_leakage(proof.proof_id)

        assert result["leakage_detected"] is False
        assert result["status"] == "SAFE"


class TestProofExpiration:
    """Test proof expiration handling."""

    def test_proof_has_expiration(self):
        """Test proof has expiration date."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"},
            validity_days=30
        )

        assert proof.expires_at is not None
        # Should expire in approximately 30 days
        days_until_expiry = (proof.expires_at - datetime.utcnow()).days
        assert 29 <= days_until_expiry <= 31

    def test_check_proof_expiration(self):
        """Test checking proof expiration status."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        result = manager.check_proof_expiration(proof.proof_id)

        assert result["expired"] is False
        assert result["remaining_days"] is not None

    def test_revoke_proof(self):
        """Test revoking a compliance proof."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        result = manager.revoke_proof(proof.proof_id, "No longer valid")

        assert result["status"] == "revoked"
        assert proof.status == ProofStatus.REVOKED


class TestProofPackage:
    """Test proof package structure per NCIP-009 Section 6."""

    def test_proof_package_structure(self):
        """Test proof package has correct structure."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY, ComplianceClaimType.AUTHORSHIP],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        package = proof.to_package()

        assert "compliance_proof" in package
        assert package["compliance_proof"]["regime"] == "SEC-17a-4"
        assert "claims" in package["compliance_proof"]
        assert "artifacts" in package["compliance_proof"]
        assert "privacy" in package["compliance_proof"]

    def test_proof_package_privacy_section(self):
        """Test proof package has privacy section."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"},
            disclosure_scope=DisclosureScope.REGULATOR_ONLY
        )

        package = proof.to_package()

        assert package["compliance_proof"]["privacy"]["method"] == "zero_knowledge"
        assert package["compliance_proof"]["privacy"]["disclosure_scope"] == "regulator_only"


class TestDisclosureScopes:
    """Test disclosure scope handling."""

    def test_all_disclosure_scopes(self):
        """Test all disclosure scopes are supported."""
        assert DisclosureScope.REGULATOR_ONLY.value == "regulator_only"
        assert DisclosureScope.AUDITOR_ONLY.value == "auditor_only"
        assert DisclosureScope.COURT_ORDER.value == "court_order"
        assert DisclosureScope.PUBLIC.value == "public"

    def test_proof_respects_disclosure_scope(self):
        """Test proof respects specified disclosure scope."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"},
            disclosure_scope=DisclosureScope.AUDITOR_ONLY
        )

        assert proof.disclosure_scope == DisclosureScope.AUDITOR_ONLY


class TestReporting:
    """Test reporting and status functions."""

    def test_get_status_summary(self):
        """Test getting status summary."""
        manager = RegulatoryInterfaceManager()

        manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        summary = manager.get_status_summary()

        assert summary["total_rims"] >= 4
        assert summary["total_proofs"] >= 1
        assert "principle" in summary
        assert "cryptographically" in summary["principle"]

    def test_generate_compliance_report(self):
        """Test generating compliance report."""
        manager = RegulatoryInterfaceManager()

        manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        report = manager.generate_compliance_report(RegulatoryRegime.SEC_17A_4)

        assert report["regime"] == "SEC-17a-4"
        assert "summary" in report
        assert "guarantee" in report
        assert "verify that rules were followed" in report["guarantee"]

    def test_get_proofs_by_regime(self):
        """Test getting proofs by regime."""
        manager = RegulatoryInterfaceManager()

        manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        manager.generate_compliance_proof(
            regime=RegulatoryRegime.GDPR,
            claims=[ComplianceClaimType.PRIVACY],
            entry_ids=["ENTRY-002"],
            entry_hashes={"ENTRY-002": "def456"}
        )

        sec_proofs = manager.get_proofs_by_regime(RegulatoryRegime.SEC_17A_4)
        gdpr_proofs = manager.get_proofs_by_regime(RegulatoryRegime.GDPR)

        assert len(sec_proofs) >= 1
        assert len(gdpr_proofs) >= 1
        assert all(p.regime == RegulatoryRegime.SEC_17A_4 for p in sec_proofs)


class TestCorePrinciple:
    """Test core principle: Compliance is proven cryptographically, not narratively."""

    def test_proofs_are_cryptographic(self):
        """Test proofs use cryptographic mechanisms."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        # All artifacts should be hashes
        for artifact in proof.artifacts:
            assert len(artifact.hash_value) >= 32  # SHA-256 length

    def test_regulators_cannot_decide_meaning(self):
        """Test proofs don't expose semantic content."""
        manager = RegulatoryInterfaceManager()

        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123"}
        )

        # Proof should not contain any prose or semantic content
        package = proof.to_package()
        package_str = str(package)

        # Should not contain original entry content
        assert "ENTRY-001" not in package_str or "abc123" not in package_str


class TestFinalGuarantee:
    """Test final guarantee: Regulators can verify rules were followed
    without being able to decide what was meant."""

    def test_verification_without_meaning(self):
        """Test regulators can verify compliance without semantic access."""
        manager = RegulatoryInterfaceManager()

        # Generate proof
        proof, _ = manager.generate_compliance_proof(
            regime=RegulatoryRegime.SEC_17A_4,
            claims=[ComplianceClaimType.IMMUTABILITY, ComplianceClaimType.RETENTION],
            entry_ids=["ENTRY-001"],
            entry_hashes={"ENTRY-001": "abc123def456"}
        )

        # Verify proof
        result = manager.verify_compliance_proof(proof.proof_id, "REGULATOR-001")

        # Verification succeeds
        assert result["valid"] is True

        # But regulator only sees hashes, not content
        for artifact in proof.artifacts:
            assert "hash" in artifact.artifact_type.lower() or artifact.hash_value is not None
