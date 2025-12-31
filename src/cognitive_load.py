"""
NCIP-012: Human Ratification UX & Cognitive Load Limits

This module implements cognitive load budgets, rate limits, cooling periods,
and UI safeguards to ensure human ratification remains informed, deliberate,
and meaningful.

Core Principle: If a human cannot reasonably understand the decision surface,
ratification is invalid.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class RatificationContext(Enum):
    """Context types for ratification with different cognitive load limits."""
    SIMPLE = "simple"           # Simple agreement
    FINANCIAL = "financial"     # Financial settlement
    LICENSING = "licensing"     # License grants & delegation
    DISPUTE = "dispute"         # Dispute escalation
    EMERGENCY = "emergency"     # Emergency / time-bound


class ActionType(Enum):
    """Types of actions subject to rate limits and cooling periods."""
    RATIFICATION = "ratification"
    DISPUTE_ESCALATION = "dispute_escalation"
    LICENSE_GRANT = "license_grant"
    AGREEMENT = "agreement"
    SETTLEMENT = "settlement"


class InformationLevel(Enum):
    """Mandatory information hierarchy levels (must be presented in order)."""
    INTENT_SUMMARY = 1          # 1-2 sentences, PoU-derived
    CONSEQUENCES = 2            # What changes if accepted
    IRREVERSIBILITY_FLAGS = 3   # Flags for irreversible actions
    RISKS_UNKNOWNS = 4          # Risks and unknowns
    ALTERNATIVES = 5            # Including "do nothing"
    CANONICAL_REFERENCES = 6    # Canonical term references
    FULL_TEXT = 7               # Optional, expandable


class UIViolationType(Enum):
    """Types of UI safeguard violations."""
    DARK_PATTERN = "dark_pattern"
    DEFAULT_ACCEPT = "default_accept"
    COUNTDOWN_PRESSURE = "countdown_pressure"
    BUNDLED_DECISIONS = "bundled_decisions"
    SKIPPED_HIERARCHY = "skipped_hierarchy"
    MISSING_LOCK_VISIBILITY = "missing_lock_visibility"
    AUTO_ACCEPT_FINAL = "auto_accept_final"


@dataclass
class SemanticUnit:
    """A single independently meaningful decision concept."""
    id: str
    description: str
    complexity_weight: float = 1.0  # Some units may be more complex
    category: str = "general"


@dataclass
class CognitiveBudget:
    """Tracks cognitive load for a ratification event."""
    context: RatificationContext
    max_units: int
    current_units: list[SemanticUnit] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        """Calculate remaining semantic units."""
        used = sum(u.complexity_weight for u in self.current_units)
        return max(0, self.max_units - math.ceil(used))

    @property
    def is_exceeded(self) -> bool:
        """Check if cognitive load budget is exceeded."""
        used = sum(u.complexity_weight for u in self.current_units)
        return used > self.max_units

    @property
    def utilization(self) -> float:
        """Calculate budget utilization as percentage."""
        used = sum(u.complexity_weight for u in self.current_units)
        return min(1.0, used / self.max_units) if self.max_units > 0 else 0.0


@dataclass
class RateLimitState:
    """Tracks rate limit state for a user."""
    user_id: str
    ratifications_this_hour: int = 0
    disputes_today: int = 0
    license_grants_today: int = 0
    hour_window_start: datetime = field(default_factory=datetime.utcnow)
    day_window_start: datetime = field(default_factory=datetime.utcnow)

    def reset_if_needed(self, now: datetime | None = None) -> None:
        """Reset counters if time windows have elapsed."""
        now = now or datetime.utcnow()

        # Reset hourly counter
        if now - self.hour_window_start >= timedelta(hours=1):
            self.ratifications_this_hour = 0
            self.hour_window_start = now

        # Reset daily counters
        if now - self.day_window_start >= timedelta(days=1):
            self.disputes_today = 0
            self.license_grants_today = 0
            self.day_window_start = now


@dataclass
class CoolingPeriod:
    """Represents an active cooling period."""
    action_type: ActionType
    started_at: datetime
    duration: timedelta
    can_be_waived: bool = False
    waiver_reason: str | None = None
    validator_confidence: float | None = None

    @property
    def ends_at(self) -> datetime:
        """Calculate when cooling period ends."""
        return self.started_at + self.duration

    @property
    def is_active(self) -> bool:
        """Check if cooling period is still active."""
        return datetime.utcnow() < self.ends_at

    @property
    def remaining_time(self) -> timedelta:
        """Calculate remaining cooling time."""
        remaining = self.ends_at - datetime.utcnow()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)


@dataclass
class InformationPresentation:
    """Tracks which information levels have been presented."""
    levels_presented: dict[InformationLevel, bool] = field(default_factory=dict)
    presentation_order: list[InformationLevel] = field(default_factory=list)

    def __post_init__(self):
        # Initialize all levels as not presented
        for level in InformationLevel:
            if level not in self.levels_presented:
                self.levels_presented[level] = False

    def mark_presented(self, level: InformationLevel) -> bool:
        """Mark a level as presented. Returns False if out of order."""
        expected_next = self._get_next_required_level()

        # Full text is optional and can be presented at any time after others
        if level == InformationLevel.FULL_TEXT:
            if expected_next is not None and expected_next != InformationLevel.FULL_TEXT:
                return False  # Must present other levels first
            self.levels_presented[level] = True
            self.presentation_order.append(level)
            return True

        # Other levels must be in order
        if expected_next is None or level != expected_next:
            return False

        self.levels_presented[level] = True
        self.presentation_order.append(level)
        return True

    def _get_next_required_level(self) -> InformationLevel | None:
        """Get the next level that must be presented."""
        for level in InformationLevel:
            if level == InformationLevel.FULL_TEXT:
                continue  # Skip optional level
            if not self.levels_presented.get(level, False):
                return level
        return InformationLevel.FULL_TEXT  # All required done, only optional left

    @property
    def is_hierarchy_complete(self) -> bool:
        """Check if all required levels have been presented."""
        for level in InformationLevel:
            if level == InformationLevel.FULL_TEXT:
                continue  # Optional
            if not self.levels_presented.get(level, False):
                return False
        return True


@dataclass
class PoUConfirmation:
    """Tracks Proof of Understanding confirmation state."""
    paraphrase_viewed: bool = False
    user_confirmed: bool = False
    user_correction: str | None = None
    correction_drift: float | None = None
    max_allowed_drift: float = 0.20

    @property
    def is_valid(self) -> bool:
        """Check if PoU confirmation is valid."""
        if not self.paraphrase_viewed:
            return False
        if not self.user_confirmed:
            return False
        if self.user_correction and self.correction_drift:
            # User correction diverges beyond D2 (drift threshold)
            if self.correction_drift > self.max_allowed_drift:
                return False
        return True

    @property
    def requires_clarification(self) -> bool:
        """Check if semantic clarification is required."""
        return (self.user_correction is not None and
                self.correction_drift is not None and
                self.correction_drift > self.max_allowed_drift)


@dataclass
class UIValidation:
    """Validates UI compliance with NCIP-012 safeguards."""
    violations: list[UIViolationType] = field(default_factory=list)
    violation_details: dict[UIViolationType, str] = field(default_factory=dict)

    def add_violation(self, violation_type: UIViolationType, detail: str = "") -> None:
        """Record a UI violation."""
        if violation_type not in self.violations:
            self.violations.append(violation_type)
        self.violation_details[violation_type] = detail

    @property
    def is_compliant(self) -> bool:
        """Check if UI is compliant with all safeguards."""
        return len(self.violations) == 0

    @property
    def violation_count(self) -> int:
        """Count total violations."""
        return len(self.violations)


@dataclass
class RatificationState:
    """Complete state for a ratification event."""
    ratification_id: str
    user_id: str
    context: RatificationContext
    cognitive_budget: CognitiveBudget
    information: InformationPresentation
    pou_confirmation: PoUConfirmation
    ui_validation: UIValidation
    cooling_period: CoolingPeriod | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    ratified_at: datetime | None = None
    semantic_lock_active: bool = False

    @property
    def can_ratify(self) -> tuple[bool, list[str]]:
        """Check if ratification is allowed. Returns (allowed, reasons)."""
        blockers = []

        # Check cognitive budget
        if self.cognitive_budget.is_exceeded:
            blockers.append("Cognitive load budget exceeded - segmentation required")

        # Check information hierarchy
        if not self.information.is_hierarchy_complete:
            blockers.append("Information hierarchy incomplete - all levels must be presented")

        # Check PoU confirmation
        if not self.pou_confirmation.is_valid:
            if not self.pou_confirmation.paraphrase_viewed:
                blockers.append("PoU paraphrase not viewed")
            elif not self.pou_confirmation.user_confirmed:
                blockers.append("PoU not confirmed by user")
            elif self.pou_confirmation.requires_clarification:
                blockers.append("PoU correction exceeds drift threshold - clarification required")

        # Check UI compliance
        if not self.ui_validation.is_compliant:
            violations_str = ", ".join(v.value for v in self.ui_validation.violations)
            blockers.append(f"UI violations detected: {violations_str}")

        # Check cooling period
        if self.cooling_period and self.cooling_period.is_active:
            remaining = self.cooling_period.remaining_time
            blockers.append(f"Cooling period active - {remaining} remaining")

        return (len(blockers) == 0, blockers)


class CognitiveLoadManager:
    """
    Manages cognitive load budgets, rate limits, cooling periods,
    and UI safeguards for human ratification.
    """

    # Cognitive Load Budget limits (semantic units)
    CLB_LIMITS = {
        RatificationContext.SIMPLE: 7,
        RatificationContext.FINANCIAL: 9,
        RatificationContext.LICENSING: 9,
        RatificationContext.DISPUTE: 5,
        RatificationContext.EMERGENCY: 3,
    }

    # Rate limits
    RATE_LIMITS = {
        ActionType.RATIFICATION: 5,      # per hour
        ActionType.DISPUTE_ESCALATION: 2, # per day
        ActionType.LICENSE_GRANT: 3,      # per day
    }

    # Cooling periods
    COOLING_PERIODS = {
        ActionType.AGREEMENT: timedelta(hours=12),
        ActionType.SETTLEMENT: timedelta(hours=24),
        ActionType.LICENSE_GRANT: timedelta(hours=24),
        ActionType.DISPUTE_ESCALATION: timedelta(hours=6),
    }

    # Validator confidence threshold for cooling waiver
    WAIVER_CONFIDENCE_THRESHOLD = 0.85

    def __init__(self):
        self.rate_limit_states: dict[str, RateLimitState] = {}
        self.ratification_states: dict[str, RatificationState] = {}
        self.active_cooling_periods: dict[str, list[CoolingPeriod]] = {}

    # -------------------------------------------------------------------------
    # Cognitive Load Budget Management
    # -------------------------------------------------------------------------

    def create_cognitive_budget(self, context: RatificationContext) -> CognitiveBudget:
        """Create a new cognitive budget for the given context."""
        max_units = self.CLB_LIMITS.get(context, 7)
        return CognitiveBudget(context=context, max_units=max_units)

    def add_semantic_unit(
        self,
        budget: CognitiveBudget,
        unit: SemanticUnit
    ) -> tuple[bool, str]:
        """
        Add a semantic unit to the budget.
        Returns (success, message).
        """
        budget.current_units.append(unit)

        if budget.is_exceeded:
            return (False, f"Cognitive load budget exceeded. "
                          f"Max: {budget.max_units}, Current: {len(budget.current_units)}")

        return (True, f"Unit added. Remaining budget: {budget.remaining}")

    def check_budget_compliance(self, budget: CognitiveBudget) -> tuple[bool, str]:
        """Check if a cognitive budget is within limits."""
        if budget.is_exceeded:
            return (False, f"Budget exceeded: {len(budget.current_units)} units "
                          f"exceed limit of {budget.max_units}")
        return (True, f"Budget compliant: {budget.utilization:.1%} utilized")

    def request_segmentation(self, budget: CognitiveBudget) -> list[list[SemanticUnit]]:
        """
        Request segmentation of an exceeded budget.
        Returns segments that each fit within the limit.
        """
        if not budget.is_exceeded:
            return [budget.current_units]

        segments = []
        current_segment = []
        current_weight = 0.0

        for unit in budget.current_units:
            if current_weight + unit.complexity_weight <= budget.max_units:
                current_segment.append(unit)
                current_weight += unit.complexity_weight
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = [unit]
                current_weight = unit.complexity_weight

        if current_segment:
            segments.append(current_segment)

        return segments

    # -------------------------------------------------------------------------
    # Rate Limit Management
    # -------------------------------------------------------------------------

    def get_rate_limit_state(self, user_id: str) -> RateLimitState:
        """Get or create rate limit state for a user."""
        if user_id not in self.rate_limit_states:
            self.rate_limit_states[user_id] = RateLimitState(user_id=user_id)

        state = self.rate_limit_states[user_id]
        state.reset_if_needed()
        return state

    def check_rate_limit(
        self,
        user_id: str,
        action_type: ActionType
    ) -> tuple[bool, str]:
        """
        Check if an action is within rate limits.
        Returns (allowed, message).
        """
        state = self.get_rate_limit_state(user_id)

        if action_type == ActionType.RATIFICATION:
            limit = self.RATE_LIMITS[ActionType.RATIFICATION]
            if state.ratifications_this_hour >= limit:
                return (False, f"Rate limit exceeded: {limit} ratifications per hour")
            return (True, f"Rate limit OK: {state.ratifications_this_hour}/{limit} this hour")

        elif action_type == ActionType.DISPUTE_ESCALATION:
            limit = self.RATE_LIMITS[ActionType.DISPUTE_ESCALATION]
            if state.disputes_today >= limit:
                return (False, f"Rate limit exceeded: {limit} dispute escalations per day")
            return (True, f"Rate limit OK: {state.disputes_today}/{limit} today")

        elif action_type == ActionType.LICENSE_GRANT:
            limit = self.RATE_LIMITS[ActionType.LICENSE_GRANT]
            if state.license_grants_today >= limit:
                return (False, f"Rate limit exceeded: {limit} license grants per day")
            return (True, f"Rate limit OK: {state.license_grants_today}/{limit} today")

        return (True, "No rate limit for this action type")

    def record_action(self, user_id: str, action_type: ActionType) -> None:
        """Record that an action was taken (increment counters)."""
        state = self.get_rate_limit_state(user_id)

        if action_type == ActionType.RATIFICATION:
            state.ratifications_this_hour += 1
        elif action_type == ActionType.DISPUTE_ESCALATION:
            state.disputes_today += 1
        elif action_type == ActionType.LICENSE_GRANT:
            state.license_grants_today += 1

    def get_remaining_actions(self, user_id: str) -> dict[ActionType, int]:
        """Get remaining allowed actions for a user."""
        state = self.get_rate_limit_state(user_id)

        return {
            ActionType.RATIFICATION: max(0,
                self.RATE_LIMITS[ActionType.RATIFICATION] - state.ratifications_this_hour),
            ActionType.DISPUTE_ESCALATION: max(0,
                self.RATE_LIMITS[ActionType.DISPUTE_ESCALATION] - state.disputes_today),
            ActionType.LICENSE_GRANT: max(0,
                self.RATE_LIMITS[ActionType.LICENSE_GRANT] - state.license_grants_today),
        }

    # -------------------------------------------------------------------------
    # Cooling Period Management
    # -------------------------------------------------------------------------

    def start_cooling_period(
        self,
        user_id: str,
        action_type: ActionType
    ) -> CoolingPeriod:
        """Start a cooling period for the given action type."""
        duration = self.COOLING_PERIODS.get(action_type, timedelta(hours=12))

        cooling = CoolingPeriod(
            action_type=action_type,
            started_at=datetime.utcnow(),
            duration=duration
        )

        if user_id not in self.active_cooling_periods:
            self.active_cooling_periods[user_id] = []

        self.active_cooling_periods[user_id].append(cooling)
        return cooling

    def check_cooling_period(
        self,
        user_id: str,
        action_type: ActionType
    ) -> tuple[bool, CoolingPeriod | None]:
        """
        Check if a cooling period is active for this action type.
        Returns (is_blocked, active_cooling_period).
        """
        if user_id not in self.active_cooling_periods:
            return (False, None)

        for cooling in self.active_cooling_periods[user_id]:
            if cooling.action_type == action_type and cooling.is_active:
                return (True, cooling)

        return (False, None)

    def waive_cooling_period(
        self,
        cooling: CoolingPeriod,
        reason: str,
        validator_confidence: float
    ) -> tuple[bool, str]:
        """
        Attempt to waive a cooling period.
        Returns (success, message).
        """
        if validator_confidence < self.WAIVER_CONFIDENCE_THRESHOLD:
            return (False, f"Validator confidence {validator_confidence:.2f} below "
                          f"threshold {self.WAIVER_CONFIDENCE_THRESHOLD}")

        cooling.can_be_waived = True
        cooling.waiver_reason = reason
        cooling.validator_confidence = validator_confidence

        # Reduce duration to zero (effectively waiving)
        cooling.duration = timedelta(0)

        return (True, f"Cooling period waived. Reason: {reason}")

    def cleanup_expired_cooling_periods(self, user_id: str) -> int:
        """Remove expired cooling periods. Returns count removed."""
        if user_id not in self.active_cooling_periods:
            return 0

        before = len(self.active_cooling_periods[user_id])
        self.active_cooling_periods[user_id] = [
            c for c in self.active_cooling_periods[user_id] if c.is_active
        ]
        return before - len(self.active_cooling_periods[user_id])

    # -------------------------------------------------------------------------
    # Information Hierarchy Management
    # -------------------------------------------------------------------------

    def create_information_presentation(self) -> InformationPresentation:
        """Create a new information presentation tracker."""
        return InformationPresentation()

    def present_information_level(
        self,
        presentation: InformationPresentation,
        level: InformationLevel
    ) -> tuple[bool, str]:
        """
        Mark an information level as presented.
        Returns (success, message).
        """
        if presentation.mark_presented(level):
            return (True, f"Level {level.name} presented successfully")
        else:
            expected = presentation._get_next_required_level()
            return (False, f"Out of order: expected {expected.name if expected else 'none'}, "
                          f"got {level.name}")

    def validate_hierarchy_complete(
        self,
        presentation: InformationPresentation
    ) -> tuple[bool, list[InformationLevel]]:
        """
        Validate that all required hierarchy levels are complete.
        Returns (complete, missing_levels).
        """
        missing = []
        for level in InformationLevel:
            if level == InformationLevel.FULL_TEXT:
                continue  # Optional
            if not presentation.levels_presented.get(level, False):
                missing.append(level)

        return (len(missing) == 0, missing)

    # -------------------------------------------------------------------------
    # Proof of Understanding Gate
    # -------------------------------------------------------------------------

    def create_pou_confirmation(self) -> PoUConfirmation:
        """Create a new PoU confirmation tracker."""
        return PoUConfirmation()

    def view_pou_paraphrase(self, pou: PoUConfirmation) -> None:
        """Mark that the user has viewed the PoU paraphrase."""
        pou.paraphrase_viewed = True

    def confirm_pou(
        self,
        pou: PoUConfirmation,
        user_correction: str | None = None,
        correction_drift: float | None = None
    ) -> tuple[bool, str]:
        """
        Confirm PoU, optionally with user correction.
        Returns (valid, message).
        """
        if not pou.paraphrase_viewed:
            return (False, "Must view PoU paraphrase before confirming")

        pou.user_confirmed = True
        pou.user_correction = user_correction
        pou.correction_drift = correction_drift

        if pou.requires_clarification:
            return (False, f"User correction drift {correction_drift:.2f} exceeds "
                          f"max allowed {pou.max_allowed_drift}. "
                          "Semantic clarification required.")

        return (True, "PoU confirmed successfully")

    # -------------------------------------------------------------------------
    # UI Safeguard Validation
    # -------------------------------------------------------------------------

    def create_ui_validation(self) -> UIValidation:
        """Create a new UI validation tracker."""
        return UIValidation()

    def validate_ui_element(
        self,
        validation: UIValidation,
        element_type: str,
        properties: dict
    ) -> tuple[bool, list[str]]:
        """
        Validate a UI element against NCIP-012 safeguards.
        Returns (compliant, violations).
        """
        violations_found = []

        # Check for default accept
        if element_type == "button" and properties.get("is_accept_button"):
            if properties.get("is_default", False):
                validation.add_violation(
                    UIViolationType.DEFAULT_ACCEPT,
                    "Accept button cannot be default"
                )
                violations_found.append("Default accept button detected")

        # Check for countdown pressure (only allowed for emergency)
        if element_type == "countdown" and not properties.get("is_emergency", False):
            validation.add_violation(
                UIViolationType.COUNTDOWN_PRESSURE,
                "Countdown pressure not allowed for non-emergency"
            )
            violations_found.append("Countdown pressure in non-emergency context")

        # Check for bundled decisions
        if element_type == "decision_bundle" and properties.get("decision_count", 1) > 1:
            if not properties.get("decisions_related", True):
                validation.add_violation(
                    UIViolationType.BUNDLED_DECISIONS,
                    "Unrelated decisions cannot be bundled"
                )
                violations_found.append("Bundled unrelated decisions")

        # Check for dark patterns
        if properties.get("has_confusing_language", False):
            validation.add_violation(
                UIViolationType.DARK_PATTERN,
                "Confusing language detected"
            )
            violations_found.append("Dark pattern: confusing language")

        if properties.get("has_hidden_options", False):
            validation.add_violation(
                UIViolationType.DARK_PATTERN,
                "Hidden options detected"
            )
            violations_found.append("Dark pattern: hidden options")

        # Check lock visibility
        if element_type == "ratification_complete":
            if not properties.get("lock_status_visible", False):
                validation.add_violation(
                    UIViolationType.MISSING_LOCK_VISIBILITY,
                    "Lock status must be visible after ratification"
                )
                violations_found.append("Missing lock visibility")

        # Check for auto-accept on final ratification
        if element_type == "auto_accept" and properties.get("is_final_ratification", False):
            validation.add_violation(
                UIViolationType.AUTO_ACCEPT_FINAL,
                "Auto-accept not allowed for final ratification"
            )
            violations_found.append("Auto-accept on final ratification")

        return (len(violations_found) == 0, violations_found)

    def detect_dark_patterns(self, ui_properties: dict) -> list[str]:
        """Detect dark patterns in UI properties."""
        patterns = []

        if ui_properties.get("confirm_shame", False):
            patterns.append("Confirm-shaming detected")

        if ui_properties.get("hidden_costs", False):
            patterns.append("Hidden costs detected")

        if ui_properties.get("trick_questions", False):
            patterns.append("Trick questions detected")

        if ui_properties.get("forced_continuity", False):
            patterns.append("Forced continuity detected")

        if ui_properties.get("misdirection", False):
            patterns.append("Visual misdirection detected")

        if ui_properties.get("roach_motel", False):
            patterns.append("Roach motel pattern detected (easy in, hard out)")

        return patterns

    # -------------------------------------------------------------------------
    # Complete Ratification Flow
    # -------------------------------------------------------------------------

    def create_ratification(
        self,
        ratification_id: str,
        user_id: str,
        context: RatificationContext
    ) -> RatificationState:
        """Create a new ratification state with all required components."""
        state = RatificationState(
            ratification_id=ratification_id,
            user_id=user_id,
            context=context,
            cognitive_budget=self.create_cognitive_budget(context),
            information=self.create_information_presentation(),
            pou_confirmation=self.create_pou_confirmation(),
            ui_validation=self.create_ui_validation()
        )

        self.ratification_states[ratification_id] = state
        return state

    def get_ratification(self, ratification_id: str) -> RatificationState | None:
        """Get an existing ratification state."""
        return self.ratification_states.get(ratification_id)

    def attempt_ratification(
        self,
        ratification_id: str,
        action_type: ActionType
    ) -> tuple[bool, list[str]]:
        """
        Attempt to complete a ratification.
        Returns (success, blockers).
        """
        state = self.get_ratification(ratification_id)
        if not state:
            return (False, ["Ratification not found"])

        blockers = []

        # Check rate limits
        rate_ok, rate_msg = self.check_rate_limit(state.user_id, action_type)
        if not rate_ok:
            blockers.append(rate_msg)

        # Check cooling period
        cooling_blocked, cooling = self.check_cooling_period(state.user_id, action_type)
        if cooling_blocked and cooling:
            blockers.append(f"Cooling period active: {cooling.remaining_time} remaining")

        # Check ratification state
        _can_ratify, state_blockers = state.can_ratify
        blockers.extend(state_blockers)

        if blockers:
            return (False, blockers)

        # Complete ratification
        state.ratified_at = datetime.utcnow()
        state.semantic_lock_active = True

        # Record action for rate limiting
        self.record_action(state.user_id, action_type)

        # Start cooling period for next action
        self.start_cooling_period(state.user_id, action_type)

        return (True, [])

    # -------------------------------------------------------------------------
    # Validator Integration
    # -------------------------------------------------------------------------

    def validator_measure_semantic_units(
        self,
        content: str,
        context: RatificationContext
    ) -> tuple[int, list[SemanticUnit]]:
        """
        Validator function to measure semantic units in content.
        Returns (count, units).

        Note: In production, this would use NLP/semantic analysis.
        This is a simplified implementation.
        """
        # Simplified: count independent concepts based on structure
        # Real implementation would use semantic parsing

        units = []
        sentences = content.split('.')

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if len(sentence) > 10:  # Non-trivial sentence
                complexity = 1.0
                # Increase complexity for conditional language
                if any(word in sentence.lower() for word in ['if', 'unless', 'except', 'provided']):
                    complexity = 1.5
                # Increase complexity for financial terms
                if any(word in sentence.lower() for word in ['payment', 'fee', 'penalty', 'liability']):
                    complexity = 1.3

                units.append(SemanticUnit(
                    id=f"unit_{i}",
                    description=sentence[:50] + "..." if len(sentence) > 50 else sentence,
                    complexity_weight=complexity
                ))

        return (len(units), units)

    def validator_detect_ux_violations(
        self,
        ui_snapshot: dict
    ) -> list[UIViolationType]:
        """
        Validator function to detect UX violations.
        Returns list of violations found.
        """
        violations = []

        if ui_snapshot.get("has_default_accept"):
            violations.append(UIViolationType.DEFAULT_ACCEPT)

        if ui_snapshot.get("has_countdown") and not ui_snapshot.get("is_emergency"):
            violations.append(UIViolationType.COUNTDOWN_PRESSURE)

        if ui_snapshot.get("bundled_unrelated"):
            violations.append(UIViolationType.BUNDLED_DECISIONS)

        dark_patterns = ui_snapshot.get("dark_patterns", [])
        if dark_patterns:
            violations.append(UIViolationType.DARK_PATTERN)

        hierarchy_levels = ui_snapshot.get("hierarchy_levels_shown", [])
        required_levels = [l for l in InformationLevel if l != InformationLevel.FULL_TEXT]
        if len(hierarchy_levels) < len(required_levels):
            violations.append(UIViolationType.SKIPPED_HIERARCHY)

        if ui_snapshot.get("is_post_ratification") and not ui_snapshot.get("lock_visible"):
            violations.append(UIViolationType.MISSING_LOCK_VISIBILITY)

        return violations

    def validator_downgrade_confidence(
        self,
        base_confidence: float,
        ratification_state: RatificationState
    ) -> tuple[float, list[str]]:
        """
        Downgrade validator confidence for rushed or problematic ratifications.
        Returns (adjusted_confidence, reasons).
        """
        confidence = base_confidence
        reasons = []

        # Downgrade for high cognitive load utilization
        if ratification_state.cognitive_budget.utilization > 0.9:
            confidence *= 0.9
            reasons.append("High cognitive load utilization")

        # Downgrade for PoU correction
        if ratification_state.pou_confirmation.user_correction:
            drift = ratification_state.pou_confirmation.correction_drift or 0
            if drift > 0.1:
                confidence *= (1 - drift)
                reasons.append(f"PoU correction with drift {drift:.2f}")

        # Downgrade for any UI violations
        violation_count = ratification_state.ui_validation.violation_count
        if violation_count > 0:
            confidence *= (1 - 0.1 * violation_count)
            reasons.append(f"{violation_count} UI violations")

        return (max(0.0, min(1.0, confidence)), reasons)
