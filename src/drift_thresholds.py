"""
NatLangChain - Semantic Drift Thresholds & Validator Responses
Implements NCIP-002: Normative drift classification and mandatory responses

Drift Levels:
- D0 (0.00-0.10): Stable - meaning preserved
- D1 (0.10-0.25): Soft Drift - minor variation, proceed with warning
- D2 (0.25-0.45): Ambiguous Drift - pause execution, request clarification
- D3 (0.45-0.70): Hard Drift - reject, require human ratification
- D4 (0.70-1.00): Semantic Break - reject, escalate to dispute
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Configure drift logging
logger = logging.getLogger("natlangchain.drift")


class DriftLevel(Enum):
    """
    Semantic drift classification levels per NCIP-002.

    These levels are absolute and normative.
    """
    D0 = "D0"  # Stable: 0.00 - 0.10
    D1 = "D1"  # Soft Drift: 0.10 - 0.25
    D2 = "D2"  # Ambiguous Drift: 0.25 - 0.45
    D3 = "D3"  # Hard Drift: 0.45 - 0.70
    D4 = "D4"  # Semantic Break: 0.70 - 1.00


class ValidatorAction(Enum):
    """Mandatory validator actions per drift level."""
    PROCEED = "proceed"
    WARN = "warn"
    PAUSE = "pause"
    REQUIRE_RATIFICATION = "require_ratification"
    REJECT = "reject"
    ESCALATE_DISPUTE = "escalate_dispute"


@dataclass
class DriftThreshold:
    """Definition of a drift level threshold."""
    level: DriftLevel
    min_score: float
    max_score: float
    classification: str
    description: str
    actions: List[ValidatorAction]
    requires_logging: bool
    requires_human: bool


@dataclass
class DriftClassification:
    """Result of classifying a drift score."""
    score: float
    level: DriftLevel
    classification: str
    description: str
    actions: List[ValidatorAction]
    requires_logging: bool
    requires_human: bool
    message: str


@dataclass
class DriftLogEntry:
    """Log entry for drift events (D2 and above per NCIP-002)."""
    timestamp: str
    drift_score: float
    drift_level: str
    affected_terms: List[str]
    source_of_divergence: str
    temporal_reference: str  # T_n
    registry_version: str
    validator_id: str
    entry_id: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedDrift:
    """Result of aggregating multiple drift scores."""
    max_score: float
    max_level: DriftLevel
    component_scores: Dict[str, float]
    governing_component: str
    classification: DriftClassification


# NCIP-002 Normative Threshold Definitions
DRIFT_THRESHOLDS: Dict[DriftLevel, DriftThreshold] = {
    DriftLevel.D0: DriftThreshold(
        level=DriftLevel.D0,
        min_score=0.00,
        max_score=0.10,
        classification="stable",
        description="Meaning preserved",
        actions=[ValidatorAction.PROCEED],
        requires_logging=False,
        requires_human=False
    ),
    DriftLevel.D1: DriftThreshold(
        level=DriftLevel.D1,
        min_score=0.10,
        max_score=0.25,
        classification="soft_drift",
        description="Minor lexical or stylistic variation",
        actions=[ValidatorAction.PROCEED, ValidatorAction.WARN],
        requires_logging=True,
        requires_human=False
    ),
    DriftLevel.D2: DriftThreshold(
        level=DriftLevel.D2,
        min_score=0.25,
        max_score=0.45,
        classification="ambiguous_drift",
        description="Meaning overlap but execution risk",
        actions=[ValidatorAction.PAUSE, ValidatorAction.WARN],
        requires_logging=True,
        requires_human=False
    ),
    DriftLevel.D3: DriftThreshold(
        level=DriftLevel.D3,
        min_score=0.45,
        max_score=0.70,
        classification="hard_drift",
        description="Substantive semantic deviation",
        actions=[ValidatorAction.REJECT, ValidatorAction.REQUIRE_RATIFICATION],
        requires_logging=True,
        requires_human=True
    ),
    DriftLevel.D4: DriftThreshold(
        level=DriftLevel.D4,
        min_score=0.70,
        max_score=1.00,
        classification="semantic_break",
        description="Meaning no longer aligned",
        actions=[ValidatorAction.REJECT, ValidatorAction.ESCALATE_DISPUTE],
        requires_logging=True,
        requires_human=True
    )
}

# Response messages per NCIP-002
DRIFT_MESSAGES = {
    DriftLevel.D0: "Semantic validation passed; meaning preserved.",
    DriftLevel.D1: "Minor semantic variation detected; meaning remains aligned.",
    DriftLevel.D2: "Intent meaning partially ambiguous; clarification required before execution.",
    DriftLevel.D3: "Semantic deviation exceeds safe threshold; human ratification required.",
    DriftLevel.D4: "Semantic break detected; interpretation rejected as unsafe."
}


class SemanticDriftClassifier:
    """
    Classifies drift scores according to NCIP-002 thresholds.

    This class provides:
    - Score-to-level classification
    - Mandatory validator response determination
    - Drift aggregation rules
    - Temporal Fixity context handling
    - Logging for D2+ events
    """

    def __init__(self, validator_id: str = "default", registry_version: str = "1.0"):
        """
        Initialize the drift classifier.

        Args:
            validator_id: Identifier for this validator instance
            registry_version: Version of the canonical term registry
        """
        self.validator_id = validator_id
        self.registry_version = registry_version
        self._drift_log: List[DriftLogEntry] = []

    def classify(self, score: float) -> DriftClassification:
        """
        Classify a drift score into NCIP-002 levels.

        Args:
            score: Drift score in range [0.0, 1.0]
                   0.0 = identical meaning
                   1.0 = completely different meaning

        Returns:
            DriftClassification with level and required actions

        Raises:
            ValueError: If score is outside [0.0, 1.0]
        """
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Drift score must be between 0.0 and 1.0, got {score}")

        # Find matching threshold
        for level in [DriftLevel.D0, DriftLevel.D1, DriftLevel.D2, DriftLevel.D3, DriftLevel.D4]:
            threshold = DRIFT_THRESHOLDS[level]
            if threshold.min_score <= score < threshold.max_score or \
               (level == DriftLevel.D4 and score == 1.0):
                return DriftClassification(
                    score=score,
                    level=level,
                    classification=threshold.classification,
                    description=threshold.description,
                    actions=threshold.actions.copy(),
                    requires_logging=threshold.requires_logging,
                    requires_human=threshold.requires_human,
                    message=DRIFT_MESSAGES[level]
                )

        # Default to D4 for edge cases
        threshold = DRIFT_THRESHOLDS[DriftLevel.D4]
        return DriftClassification(
            score=score,
            level=DriftLevel.D4,
            classification=threshold.classification,
            description=threshold.description,
            actions=threshold.actions.copy(),
            requires_logging=threshold.requires_logging,
            requires_human=threshold.requires_human,
            message=DRIFT_MESSAGES[DriftLevel.D4]
        )

    def aggregate_drift(
        self,
        component_scores: Dict[str, float]
    ) -> AggregatedDrift:
        """
        Aggregate multiple drift scores per NCIP-002 rules.

        Per NCIP-002 Section 6: "The maximum drift score governs response."

        Args:
            component_scores: Dict mapping component names to drift scores
                            e.g., {"term_a": 0.2, "clause_b": 0.5}

        Returns:
            AggregatedDrift with max score and governing component
        """
        if not component_scores:
            # No components = no drift
            return AggregatedDrift(
                max_score=0.0,
                max_level=DriftLevel.D0,
                component_scores={},
                governing_component="none",
                classification=self.classify(0.0)
            )

        # Find maximum score and its component
        max_component = max(component_scores, key=component_scores.get)
        max_score = component_scores[max_component]

        # Classify based on max score
        classification = self.classify(max_score)

        return AggregatedDrift(
            max_score=max_score,
            max_level=classification.level,
            component_scores=component_scores.copy(),
            governing_component=max_component,
            classification=classification
        )

    def should_proceed(self, classification: DriftClassification) -> bool:
        """
        Determine if execution should proceed based on classification.

        Args:
            classification: The drift classification result

        Returns:
            True if PROCEED is in actions, False otherwise
        """
        return ValidatorAction.PROCEED in classification.actions

    def should_warn(self, classification: DriftClassification) -> bool:
        """
        Determine if a warning should be emitted.

        Args:
            classification: The drift classification result

        Returns:
            True if WARN is in actions
        """
        return ValidatorAction.WARN in classification.actions

    def should_pause(self, classification: DriftClassification) -> bool:
        """
        Determine if execution should pause for clarification.

        Args:
            classification: The drift classification result

        Returns:
            True if PAUSE is in actions
        """
        return ValidatorAction.PAUSE in classification.actions

    def should_require_ratification(self, classification: DriftClassification) -> bool:
        """
        Determine if human ratification is required.

        Args:
            classification: The drift classification result

        Returns:
            True if REQUIRE_RATIFICATION is in actions
        """
        return ValidatorAction.REQUIRE_RATIFICATION in classification.actions

    def should_reject(self, classification: DriftClassification) -> bool:
        """
        Determine if the interpretation should be rejected.

        Args:
            classification: The drift classification result

        Returns:
            True if REJECT is in actions
        """
        return ValidatorAction.REJECT in classification.actions

    def should_escalate(self, classification: DriftClassification) -> bool:
        """
        Determine if a dispute should be escalated.

        Args:
            classification: The drift classification result

        Returns:
            True if ESCALATE_DISPUTE is in actions
        """
        return ValidatorAction.ESCALATE_DISPUTE in classification.actions

    def log_drift_event(
        self,
        classification: DriftClassification,
        affected_terms: List[str],
        source_of_divergence: str,
        temporal_reference: Optional[str] = None,
        entry_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[DriftLogEntry]:
        """
        Log a drift event if required per NCIP-002.

        Per NCIP-002 Section 9: Logging is required for D2 and above.

        Args:
            classification: The drift classification
            affected_terms: List of affected canonical terms
            source_of_divergence: Description of what caused the drift
            temporal_reference: Time reference (T_n) for the evaluation
            entry_id: Optional entry ID being evaluated
            additional_context: Additional context data

        Returns:
            DriftLogEntry if logging was required, None otherwise
        """
        if not classification.requires_logging:
            return None

        timestamp = datetime.utcnow().isoformat() + "Z"
        temporal_ref = temporal_reference or timestamp

        log_entry = DriftLogEntry(
            timestamp=timestamp,
            drift_score=classification.score,
            drift_level=classification.level.value,
            affected_terms=affected_terms.copy(),
            source_of_divergence=source_of_divergence,
            temporal_reference=temporal_ref,
            registry_version=self.registry_version,
            validator_id=self.validator_id,
            entry_id=entry_id,
            additional_context=additional_context or {}
        )

        # Store in internal log
        self._drift_log.append(log_entry)

        # Log to Python logger
        log_level = logging.WARNING if classification.level in [DriftLevel.D2, DriftLevel.D3] else logging.ERROR
        logger.log(
            log_level,
            f"Drift {classification.level.value}: score={classification.score:.3f}, "
            f"terms={affected_terms}, source={source_of_divergence}"
        )

        return log_entry

    def get_drift_log(self) -> List[DriftLogEntry]:
        """Get all logged drift events."""
        return self._drift_log.copy()

    def clear_drift_log(self) -> None:
        """Clear the drift log."""
        self._drift_log.clear()

    def get_validator_response(
        self,
        score: float,
        affected_terms: Optional[List[str]] = None,
        source: Optional[str] = None,
        entry_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the complete validator response for a drift score.

        This is the main entry point for validators to process drift.

        Args:
            score: The drift score [0.0, 1.0]
            affected_terms: Optional list of affected terms
            source: Optional description of divergence source
            entry_id: Optional entry ID

        Returns:
            Complete validator response dict with classification and actions
        """
        classification = self.classify(score)

        # Log if required
        if classification.requires_logging:
            self.log_drift_event(
                classification=classification,
                affected_terms=affected_terms or [],
                source_of_divergence=source or "unspecified",
                entry_id=entry_id
            )

        response = {
            "drift_score": score,
            "drift_level": classification.level.value,
            "classification": classification.classification,
            "description": classification.description,
            "message": classification.message,
            "actions": {
                "proceed": self.should_proceed(classification),
                "warn": self.should_warn(classification),
                "pause": self.should_pause(classification),
                "require_ratification": self.should_require_ratification(classification),
                "reject": self.should_reject(classification),
                "escalate_dispute": self.should_escalate(classification)
            },
            "requires_human": classification.requires_human,
            "logged": classification.requires_logging
        }

        if affected_terms:
            response["affected_terms"] = affected_terms

        return response


class TemporalFixityContext:
    """
    Manages Temporal Fixity (T₀) context for drift evaluation.

    Per NCIP-002 Section 7: Drift MUST be evaluated against T₀ context.
    Validators MUST NOT reinterpret older contracts using newer semantics
    without explicit upgrade.
    """

    def __init__(
        self,
        ratification_time: str,
        registry_version: str,
        specification_version: str
    ):
        """
        Initialize temporal context.

        Args:
            ratification_time: ISO timestamp of original ratification (T₀)
            registry_version: Canonical Term Registry version at T₀
            specification_version: NatLangChain spec version at T₀
        """
        self.ratification_time = ratification_time
        self.registry_version = registry_version
        self.specification_version = specification_version
        self._locked = False

    def lock(self) -> None:
        """Lock this context to prevent modifications."""
        self._locked = True

    @property
    def is_locked(self) -> bool:
        """Check if context is locked."""
        return self._locked

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "t0_ratification_time": self.ratification_time,
            "registry_version": self.registry_version,
            "specification_version": self.specification_version,
            "locked": self._locked
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalFixityContext":
        """Create from dictionary representation."""
        context = cls(
            ratification_time=data["t0_ratification_time"],
            registry_version=data["registry_version"],
            specification_version=data["specification_version"]
        )
        if data.get("locked", False):
            context.lock()
        return context


class HumanOverrideRecord:
    """
    Records human overrides of drift classifications.

    Per NCIP-002 Section 8:
    - Humans MAY override D2 (Ambiguous) and D3 (Hard Drift)
    - Humans MUST NOT override D4 (Semantic Break) without formal dispute
    - All overrides must be explicit and logged
    """

    def __init__(
        self,
        original_level: DriftLevel,
        override_decision: str,
        human_id: str,
        rationale: str,
        timestamp: Optional[str] = None
    ):
        """
        Record a human override.

        Args:
            original_level: The original drift level
            override_decision: The human's decision (accept/reject)
            human_id: Identifier of the human making the override
            rationale: Explanation for the override
            timestamp: Optional timestamp (defaults to now)
        """
        if original_level == DriftLevel.D4:
            raise ValueError(
                "D4 (Semantic Break) cannot be overridden without formal dispute resolution. "
                "Per NCIP-002 Section 8."
            )

        if original_level not in [DriftLevel.D2, DriftLevel.D3]:
            raise ValueError(
                f"Human override only applies to D2 and D3 levels, not {original_level.value}"
            )

        self.original_level = original_level
        self.override_decision = override_decision
        self.human_id = human_id
        self.rationale = rationale
        self.timestamp = timestamp or (datetime.utcnow().isoformat() + "Z")
        self.binds_future = True  # Per NCIP-002: Overrides bind future interpretations

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_level": self.original_level.value,
            "override_decision": self.override_decision,
            "human_id": self.human_id,
            "rationale": self.rationale,
            "timestamp": self.timestamp,
            "binds_future_interpretations": self.binds_future
        }


# Machine-readable threshold configuration per NCIP-002 Section 10
NCIP_002_CONFIG = {
    "semantic_drift": {
        "version": "1.0",
        "thresholds": {
            "D0": {
                "min": 0.00,
                "max": 0.10,
                "classification": "stable",
                "action": {"proceed": True, "log": False}
            },
            "D1": {
                "min": 0.10,
                "max": 0.25,
                "classification": "soft_drift",
                "action": {"proceed": True, "warn": True, "log": True}
            },
            "D2": {
                "min": 0.25,
                "max": 0.45,
                "classification": "ambiguous_drift",
                "action": {"proceed": False, "request_clarification": True, "log_uncertainty": True}
            },
            "D3": {
                "min": 0.45,
                "max": 0.70,
                "classification": "hard_drift",
                "action": {"proceed": False, "require_human_ratification": True, "mediator_review": True, "log": True}
            },
            "D4": {
                "min": 0.70,
                "max": 1.00,
                "classification": "semantic_break",
                "action": {"proceed": False, "invalidate_interpretation": True, "escalate_dispute": True, "lock_autoretry": True, "log": True}
            }
        }
    }
}


def get_drift_config() -> Dict[str, Any]:
    """Get the NCIP-002 drift configuration."""
    return NCIP_002_CONFIG.copy()


def classify_drift_score(score: float) -> DriftClassification:
    """
    Convenience function to classify a drift score.

    Args:
        score: Drift score [0.0, 1.0]

    Returns:
        DriftClassification
    """
    classifier = SemanticDriftClassifier()
    return classifier.classify(score)


def get_mandatory_response(score: float) -> Dict[str, Any]:
    """
    Get the mandatory validator response for a drift score.

    Convenience function for quick lookups.

    Args:
        score: Drift score [0.0, 1.0]

    Returns:
        Validator response dict
    """
    classifier = SemanticDriftClassifier()
    return classifier.get_validator_response(score)
