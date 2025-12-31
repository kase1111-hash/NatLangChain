"""
Tests for NCIP-012: Human Ratification UX & Cognitive Load Limits
"""

from datetime import datetime, timedelta

from src.cognitive_load import (
    ActionType,
    CognitiveBudget,
    CognitiveLoadManager,
    CoolingPeriod,
    InformationLevel,
    InformationPresentation,
    PoUConfirmation,
    RateLimitState,
    RatificationContext,
    SemanticUnit,
    UIViolationType,
)


class TestCognitiveBudget:
    """Tests for Cognitive Load Budget management."""

    def test_clb_limits_by_context(self):
        """Test that CLB limits are correct for each context."""
        manager = CognitiveLoadManager()

        assert manager.CLB_LIMITS[RatificationContext.SIMPLE] == 7
        assert manager.CLB_LIMITS[RatificationContext.FINANCIAL] == 9
        assert manager.CLB_LIMITS[RatificationContext.LICENSING] == 9
        assert manager.CLB_LIMITS[RatificationContext.DISPUTE] == 5
        assert manager.CLB_LIMITS[RatificationContext.EMERGENCY] == 3

    def test_create_cognitive_budget(self):
        """Test creating cognitive budgets for different contexts."""
        manager = CognitiveLoadManager()

        simple_budget = manager.create_cognitive_budget(RatificationContext.SIMPLE)
        assert simple_budget.max_units == 7
        assert simple_budget.remaining == 7
        assert not simple_budget.is_exceeded

        emergency_budget = manager.create_cognitive_budget(RatificationContext.EMERGENCY)
        assert emergency_budget.max_units == 3

    def test_add_semantic_units(self):
        """Test adding semantic units to budget."""
        manager = CognitiveLoadManager()
        budget = manager.create_cognitive_budget(RatificationContext.SIMPLE)

        # Add units within budget
        for i in range(5):
            unit = SemanticUnit(id=f"unit_{i}", description=f"Concept {i}")
            success, _msg = manager.add_semantic_unit(budget, unit)
            assert success

        assert budget.remaining == 2
        assert not budget.is_exceeded

    def test_budget_exceeded(self):
        """Test that budget exceeded is detected."""
        manager = CognitiveLoadManager()
        budget = manager.create_cognitive_budget(RatificationContext.EMERGENCY)  # 3 max

        # Add 4 units to exceed budget
        for i in range(4):
            unit = SemanticUnit(id=f"unit_{i}", description=f"Concept {i}")
            manager.add_semantic_unit(budget, unit)

        assert budget.is_exceeded
        assert budget.remaining == 0

    def test_complexity_weighted_units(self):
        """Test that complexity weights affect budget correctly."""
        manager = CognitiveLoadManager()
        budget = manager.create_cognitive_budget(RatificationContext.DISPUTE)  # 5 max

        # Add 3 units with higher complexity
        for i in range(3):
            unit = SemanticUnit(id=f"unit_{i}", description=f"Complex concept {i}",
                              complexity_weight=2.0)
            manager.add_semantic_unit(budget, unit)

        assert budget.is_exceeded  # 3 * 2.0 = 6 > 5

    def test_request_segmentation(self):
        """Test segmentation of exceeded budget."""
        manager = CognitiveLoadManager()
        budget = manager.create_cognitive_budget(RatificationContext.DISPUTE)  # 5 max

        # Add 10 units
        for i in range(10):
            unit = SemanticUnit(id=f"unit_{i}", description=f"Concept {i}")
            budget.current_units.append(unit)

        segments = manager.request_segmentation(budget)

        # Should be segmented into at least 2 parts
        assert len(segments) >= 2
        # Each segment should be within budget
        for segment in segments:
            total_weight = sum(u.complexity_weight for u in segment)
            assert total_weight <= 5


class TestRateLimits:
    """Tests for rate limit management."""

    def test_rate_limit_values(self):
        """Test rate limit configuration values."""
        manager = CognitiveLoadManager()

        assert manager.RATE_LIMITS[ActionType.RATIFICATION] == 5  # per hour
        assert manager.RATE_LIMITS[ActionType.DISPUTE_ESCALATION] == 2  # per day
        assert manager.RATE_LIMITS[ActionType.LICENSE_GRANT] == 3  # per day

    def test_check_rate_limit_initial(self):
        """Test rate limit check for new user."""
        manager = CognitiveLoadManager()

        allowed, msg = manager.check_rate_limit("user1", ActionType.RATIFICATION)
        assert allowed
        assert "0/5" in msg

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded detection."""
        manager = CognitiveLoadManager()

        # Exhaust ratification limit
        for _ in range(5):
            manager.record_action("user1", ActionType.RATIFICATION)

        allowed, msg = manager.check_rate_limit("user1", ActionType.RATIFICATION)
        assert not allowed
        assert "exceeded" in msg.lower()

    def test_rate_limit_per_action_type(self):
        """Test that rate limits are tracked per action type."""
        manager = CognitiveLoadManager()

        # Exhaust dispute limit
        for _ in range(2):
            manager.record_action("user1", ActionType.DISPUTE_ESCALATION)

        # Disputes should be blocked
        allowed, _ = manager.check_rate_limit("user1", ActionType.DISPUTE_ESCALATION)
        assert not allowed

        # Ratifications should still be allowed
        allowed, _ = manager.check_rate_limit("user1", ActionType.RATIFICATION)
        assert allowed

    def test_get_remaining_actions(self):
        """Test getting remaining action counts."""
        manager = CognitiveLoadManager()

        manager.record_action("user1", ActionType.RATIFICATION)
        manager.record_action("user1", ActionType.RATIFICATION)

        remaining = manager.get_remaining_actions("user1")

        assert remaining[ActionType.RATIFICATION] == 3
        assert remaining[ActionType.DISPUTE_ESCALATION] == 2
        assert remaining[ActionType.LICENSE_GRANT] == 3

    def test_rate_limit_window_reset(self):
        """Test rate limit counter reset after window."""
        state = RateLimitState(user_id="user1")
        state.ratifications_this_hour = 5
        state.hour_window_start = datetime.utcnow() - timedelta(hours=2)

        state.reset_if_needed()

        assert state.ratifications_this_hour == 0


class TestCoolingPeriods:
    """Tests for cooling period management."""

    def test_cooling_period_durations(self):
        """Test cooling period configuration."""
        manager = CognitiveLoadManager()

        assert manager.COOLING_PERIODS[ActionType.AGREEMENT] == timedelta(hours=12)
        assert manager.COOLING_PERIODS[ActionType.SETTLEMENT] == timedelta(hours=24)
        assert manager.COOLING_PERIODS[ActionType.LICENSE_GRANT] == timedelta(hours=24)
        assert manager.COOLING_PERIODS[ActionType.DISPUTE_ESCALATION] == timedelta(hours=6)

    def test_start_cooling_period(self):
        """Test starting a cooling period."""
        manager = CognitiveLoadManager()

        cooling = manager.start_cooling_period("user1", ActionType.AGREEMENT)

        assert cooling.action_type == ActionType.AGREEMENT
        assert cooling.duration == timedelta(hours=12)
        assert cooling.is_active

    def test_check_cooling_period_active(self):
        """Test checking for active cooling period."""
        manager = CognitiveLoadManager()

        manager.start_cooling_period("user1", ActionType.AGREEMENT)

        blocked, cooling = manager.check_cooling_period("user1", ActionType.AGREEMENT)

        assert blocked
        assert cooling is not None
        assert cooling.remaining_time.total_seconds() > 0

    def test_cooling_period_different_action(self):
        """Test that cooling periods are per action type."""
        manager = CognitiveLoadManager()

        manager.start_cooling_period("user1", ActionType.AGREEMENT)

        # Different action type should not be blocked
        blocked, _ = manager.check_cooling_period("user1", ActionType.DISPUTE_ESCALATION)
        assert not blocked

    def test_waive_cooling_period(self):
        """Test waiving cooling period with sufficient confidence."""
        manager = CognitiveLoadManager()

        cooling = manager.start_cooling_period("user1", ActionType.AGREEMENT)

        # Waive with high validator confidence
        success, _msg = manager.waive_cooling_period(
            cooling,
            reason="Emergency: time-critical transaction",
            validator_confidence=0.90
        )

        assert success
        assert not cooling.is_active

    def test_waive_cooling_period_insufficient_confidence(self):
        """Test that waiver fails with low confidence."""
        manager = CognitiveLoadManager()

        cooling = manager.start_cooling_period("user1", ActionType.AGREEMENT)

        success, msg = manager.waive_cooling_period(
            cooling,
            reason="Just want to hurry",
            validator_confidence=0.70
        )

        assert not success
        assert "below threshold" in msg.lower()


class TestInformationHierarchy:
    """Tests for information hierarchy management."""

    def test_all_required_levels(self):
        """Test that all required hierarchy levels are tracked."""
        required = [
            InformationLevel.INTENT_SUMMARY,
            InformationLevel.CONSEQUENCES,
            InformationLevel.IRREVERSIBILITY_FLAGS,
            InformationLevel.RISKS_UNKNOWNS,
            InformationLevel.ALTERNATIVES,
            InformationLevel.CANONICAL_REFERENCES,
        ]

        presentation = InformationPresentation()

        for level in required:
            assert level in presentation.levels_presented
            assert not presentation.levels_presented[level]

    def test_present_in_order(self):
        """Test presenting information levels in correct order."""
        manager = CognitiveLoadManager()
        presentation = manager.create_information_presentation()

        # Present in correct order
        success, _ = manager.present_information_level(
            presentation, InformationLevel.INTENT_SUMMARY)
        assert success

        success, _ = manager.present_information_level(
            presentation, InformationLevel.CONSEQUENCES)
        assert success

    def test_present_out_of_order(self):
        """Test that out-of-order presentation fails."""
        manager = CognitiveLoadManager()
        presentation = manager.create_information_presentation()

        # Try to skip to consequences without intent summary
        success, msg = manager.present_information_level(
            presentation, InformationLevel.CONSEQUENCES)

        assert not success
        assert "out of order" in msg.lower()

    def test_hierarchy_complete(self):
        """Test completing the full hierarchy."""
        manager = CognitiveLoadManager()
        presentation = manager.create_information_presentation()

        levels = [
            InformationLevel.INTENT_SUMMARY,
            InformationLevel.CONSEQUENCES,
            InformationLevel.IRREVERSIBILITY_FLAGS,
            InformationLevel.RISKS_UNKNOWNS,
            InformationLevel.ALTERNATIVES,
            InformationLevel.CANONICAL_REFERENCES,
        ]

        for level in levels:
            manager.present_information_level(presentation, level)

        assert presentation.is_hierarchy_complete

    def test_full_text_optional(self):
        """Test that full text level is optional."""
        presentation = InformationPresentation()

        # Mark all required as presented
        for level in InformationLevel:
            if level != InformationLevel.FULL_TEXT:
                presentation.levels_presented[level] = True

        # Should be complete without full text
        assert presentation.is_hierarchy_complete


class TestPoUConfirmation:
    """Tests for Proof of Understanding gate."""

    def test_pou_max_drift(self):
        """Test PoU max allowed drift."""
        pou = PoUConfirmation()
        assert pou.max_allowed_drift == 0.20

    def test_pou_requires_view_first(self):
        """Test that PoU paraphrase must be viewed first."""
        manager = CognitiveLoadManager()
        pou = manager.create_pou_confirmation()

        success, msg = manager.confirm_pou(pou)

        assert not success
        assert "view" in msg.lower()

    def test_pou_valid_confirmation(self):
        """Test valid PoU confirmation."""
        manager = CognitiveLoadManager()
        pou = manager.create_pou_confirmation()

        manager.view_pou_paraphrase(pou)
        success, _msg = manager.confirm_pou(pou)

        assert success
        assert pou.is_valid

    def test_pou_correction_within_drift(self):
        """Test PoU correction within drift threshold."""
        manager = CognitiveLoadManager()
        pou = manager.create_pou_confirmation()

        manager.view_pou_paraphrase(pou)
        success, _msg = manager.confirm_pou(
            pou,
            user_correction="Minor clarification",
            correction_drift=0.15
        )

        assert success
        assert pou.is_valid

    def test_pou_correction_exceeds_drift(self):
        """Test PoU correction exceeding drift threshold."""
        manager = CognitiveLoadManager()
        pou = manager.create_pou_confirmation()

        manager.view_pou_paraphrase(pou)
        success, msg = manager.confirm_pou(
            pou,
            user_correction="Major disagreement",
            correction_drift=0.30
        )

        assert not success
        assert pou.requires_clarification
        assert "clarification required" in msg.lower()


class TestUIValidation:
    """Tests for UI safeguard validation."""

    def test_detect_default_accept(self):
        """Test detection of default accept button."""
        manager = CognitiveLoadManager()
        validation = manager.create_ui_validation()

        success, violations = manager.validate_ui_element(
            validation,
            element_type="button",
            properties={"is_accept_button": True, "is_default": True}
        )

        assert not success
        assert "Default accept" in violations[0]
        assert UIViolationType.DEFAULT_ACCEPT in validation.violations

    def test_detect_countdown_pressure(self):
        """Test detection of countdown pressure."""
        manager = CognitiveLoadManager()
        validation = manager.create_ui_validation()

        success, _violations = manager.validate_ui_element(
            validation,
            element_type="countdown",
            properties={"is_emergency": False}
        )

        assert not success
        assert UIViolationType.COUNTDOWN_PRESSURE in validation.violations

    def test_countdown_allowed_for_emergency(self):
        """Test countdown is allowed for emergency context."""
        manager = CognitiveLoadManager()
        validation = manager.create_ui_validation()

        success, violations = manager.validate_ui_element(
            validation,
            element_type="countdown",
            properties={"is_emergency": True}
        )

        assert success
        assert len(violations) == 0

    def test_detect_bundled_decisions(self):
        """Test detection of bundled unrelated decisions."""
        manager = CognitiveLoadManager()
        validation = manager.create_ui_validation()

        success, _ = manager.validate_ui_element(
            validation,
            element_type="decision_bundle",
            properties={"decision_count": 3, "decisions_related": False}
        )

        assert not success
        assert UIViolationType.BUNDLED_DECISIONS in validation.violations

    def test_detect_dark_patterns(self):
        """Test dark pattern detection."""
        manager = CognitiveLoadManager()

        patterns = manager.detect_dark_patterns({
            "confirm_shame": True,
            "hidden_costs": True,
            "misdirection": True,
        })

        assert len(patterns) == 3
        assert any("shame" in p.lower() for p in patterns)

    def test_missing_lock_visibility(self):
        """Test detection of missing lock visibility post-ratification."""
        manager = CognitiveLoadManager()
        validation = manager.create_ui_validation()

        success, _ = manager.validate_ui_element(
            validation,
            element_type="ratification_complete",
            properties={"lock_status_visible": False}
        )

        assert not success
        assert UIViolationType.MISSING_LOCK_VISIBILITY in validation.violations


class TestRatificationFlow:
    """Tests for complete ratification flow."""

    def test_create_ratification_state(self):
        """Test creating a complete ratification state."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_001",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        assert state.ratification_id == "rat_001"
        assert state.user_id == "user1"
        assert state.context == RatificationContext.SIMPLE
        assert state.cognitive_budget.max_units == 7
        assert not state.semantic_lock_active

    def test_ratification_blocked_incomplete_hierarchy(self):
        """Test ratification blocked when hierarchy incomplete."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_002",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        can_ratify, blockers = state.can_ratify

        assert not can_ratify
        assert any("hierarchy" in b.lower() for b in blockers)

    def test_ratification_blocked_no_pou(self):
        """Test ratification blocked without PoU confirmation."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_003",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        can_ratify, blockers = state.can_ratify

        assert not can_ratify
        assert any("pou" in b.lower() for b in blockers)

    def test_successful_ratification(self):
        """Test successful ratification with all requirements met."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_004",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        # Complete information hierarchy
        for level in InformationLevel:
            if level != InformationLevel.FULL_TEXT:
                state.information.mark_presented(level)

        # Complete PoU
        state.pou_confirmation.paraphrase_viewed = True
        state.pou_confirmation.user_confirmed = True

        # Attempt ratification
        success, blockers = manager.attempt_ratification(
            "rat_004", ActionType.RATIFICATION)

        assert success
        assert len(blockers) == 0
        assert state.semantic_lock_active
        assert state.ratified_at is not None

    def test_ratification_triggers_cooling_period(self):
        """Test that ratification triggers cooling period."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_005",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        # Complete requirements
        for level in InformationLevel:
            if level != InformationLevel.FULL_TEXT:
                state.information.mark_presented(level)
        state.pou_confirmation.paraphrase_viewed = True
        state.pou_confirmation.user_confirmed = True

        manager.attempt_ratification("rat_005", ActionType.RATIFICATION)

        # Check cooling period started
        blocked, cooling = manager.check_cooling_period(
            "user1", ActionType.RATIFICATION)

        assert blocked
        assert cooling is not None


class TestValidatorIntegration:
    """Tests for validator integration functions."""

    def test_measure_semantic_units(self):
        """Test validator semantic unit measurement."""
        manager = CognitiveLoadManager()

        content = ("This agreement grants a license. "
                   "If payment is not received, the license terminates. "
                   "Except in cases of emergency.")

        count, units = manager.validator_measure_semantic_units(
            content, RatificationContext.LICENSING)

        assert count == 3
        # Conditional units should have higher weight
        conditional_unit = next(u for u in units if u.complexity_weight > 1.0)
        assert conditional_unit is not None

    def test_detect_ux_violations(self):
        """Test validator UX violation detection."""
        manager = CognitiveLoadManager()

        ui_snapshot = {
            "has_default_accept": True,
            "has_countdown": True,
            "is_emergency": False,
            "bundled_unrelated": True,
        }

        violations = manager.validator_detect_ux_violations(ui_snapshot)

        assert UIViolationType.DEFAULT_ACCEPT in violations
        assert UIViolationType.COUNTDOWN_PRESSURE in violations
        assert UIViolationType.BUNDLED_DECISIONS in violations

    def test_downgrade_confidence_for_issues(self):
        """Test validator confidence downgrade for issues."""
        manager = CognitiveLoadManager()

        state = manager.create_ratification(
            ratification_id="rat_006",
            user_id="user1",
            context=RatificationContext.SIMPLE
        )

        # Add some issues
        for i in range(7):  # Max out budget
            state.cognitive_budget.current_units.append(
                SemanticUnit(id=f"u_{i}", description=f"Unit {i}")
            )

        state.pou_confirmation.user_correction = "Disagreement"
        state.pou_confirmation.correction_drift = 0.15

        state.ui_validation.add_violation(UIViolationType.DARK_PATTERN)

        adjusted, reasons = manager.validator_downgrade_confidence(0.95, state)

        assert adjusted < 0.95
        assert len(reasons) >= 2


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_user_state(self):
        """Test handling of new user with no state."""
        manager = CognitiveLoadManager()

        remaining = manager.get_remaining_actions("new_user")

        assert remaining[ActionType.RATIFICATION] == 5
        assert remaining[ActionType.DISPUTE_ESCALATION] == 2
        assert remaining[ActionType.LICENSE_GRANT] == 3

    def test_multiple_cooling_periods(self):
        """Test multiple simultaneous cooling periods."""
        manager = CognitiveLoadManager()

        manager.start_cooling_period("user1", ActionType.AGREEMENT)
        manager.start_cooling_period("user1", ActionType.DISPUTE_ESCALATION)

        # Both should be active
        blocked1, _ = manager.check_cooling_period("user1", ActionType.AGREEMENT)
        blocked2, _ = manager.check_cooling_period("user1", ActionType.DISPUTE_ESCALATION)

        assert blocked1
        assert blocked2

    def test_cleanup_expired_cooling_periods(self):
        """Test cleanup of expired cooling periods."""
        manager = CognitiveLoadManager()

        # Create expired cooling period
        cooling = CoolingPeriod(
            action_type=ActionType.AGREEMENT,
            started_at=datetime.utcnow() - timedelta(hours=24),
            duration=timedelta(hours=12)
        )

        manager.active_cooling_periods["user1"] = [cooling]

        removed = manager.cleanup_expired_cooling_periods("user1")

        assert removed == 1
        assert len(manager.active_cooling_periods["user1"]) == 0

    def test_budget_utilization_percentage(self):
        """Test budget utilization calculation."""
        budget = CognitiveBudget(
            context=RatificationContext.SIMPLE,
            max_units=10
        )

        for i in range(5):
            budget.current_units.append(
                SemanticUnit(id=f"u_{i}", description=f"Unit {i}")
            )

        assert budget.utilization == 0.5
