"""
Tests for Automated Negotiation Engine (src/negotiation_engine.py)

Tests cover:
- Intent extraction and management
- Proactive alignment layer
- Clause generation
- Negotiation session management
- Offer handling
"""

import pytest
import sys
from datetime import datetime, timedelta

sys.path.insert(0, "src")

from negotiation_engine import (
    NegotiationPhase,
    OfferType,
    ClauseType,
    AlignmentLevel,
    Intent,
    Clause,
    Offer,
    NegotiationSession,
    ProactiveAlignmentLayer,
    ClauseGenerator,
)


# ============================================================
# Data Class Tests
# ============================================================

class TestIntent:
    """Tests for Intent dataclass."""

    def test_create_intent(self):
        """Should create Intent."""
        intent = Intent(
            party="alice",
            objectives=["sell product", "get fair price"],
            constraints=["minimum $1000", "delivery within 30 days"],
            priorities={"price": 10, "timeline": 7},
            flexibility={"price": "rigid", "timeline": "flexible"}
        )

        assert intent.party == "alice"
        assert len(intent.objectives) == 2
        assert intent.priorities["price"] == 10

    def test_intent_with_batna(self):
        """Should support BATNA field."""
        intent = Intent(
            party="bob",
            objectives=["buy product"],
            constraints=[],
            priorities={},
            flexibility={},
            batna="Buy from alternative supplier at $1200"
        )

        assert intent.batna is not None
        assert "alternative" in intent.batna

    def test_intent_with_reservation_point(self):
        """Should support reservation point."""
        intent = Intent(
            party="carol",
            objectives=["consulting services"],
            constraints=[],
            priorities={},
            flexibility={},
            reservation_point={"min_rate": 150, "max_hours": 100}
        )

        assert intent.reservation_point is not None
        assert intent.reservation_point["min_rate"] == 150


class TestClause:
    """Tests for Clause dataclass."""

    def test_create_clause(self):
        """Should create Clause."""
        clause = Clause(
            clause_id="CL-001",
            clause_type=ClauseType.PAYMENT,
            content="Payment of $5000 shall be made within 30 days.",
            proposed_by="mediator"
        )

        assert clause.clause_id == "CL-001"
        assert clause.clause_type == ClauseType.PAYMENT
        assert clause.status == "proposed"

    def test_clause_with_alternatives(self):
        """Should support alternatives."""
        clause = Clause(
            clause_id="CL-002",
            clause_type=ClauseType.TIMELINE,
            content="Project due in 60 days",
            proposed_by="alice",
            alternatives=[
                "Project due in 45 days with rush fee",
                "Project due in 90 days"
            ]
        )

        assert len(clause.alternatives) == 2

    def test_clause_has_timestamp(self):
        """Should have creation timestamp."""
        clause = Clause(
            clause_id="CL-003",
            clause_type=ClauseType.QUALITY,
            content="Quality standards must be met",
            proposed_by="bob"
        )

        assert clause.created_at is not None


class TestOffer:
    """Tests for Offer dataclass."""

    def test_create_offer(self):
        """Should create Offer."""
        offer = Offer(
            offer_id="OFF-001",
            offer_type=OfferType.INITIAL,
            from_party="alice",
            to_party="bob",
            terms={"price": 5000, "quantity": 100},
            clauses=["CL-001", "CL-002"],
            message="Initial offer for widgets"
        )

        assert offer.offer_id == "OFF-001"
        assert offer.offer_type == OfferType.INITIAL
        assert offer.terms["price"] == 5000

    def test_offer_with_expiration(self):
        """Should support expiration."""
        expires = (datetime.utcnow() + timedelta(days=7)).isoformat()
        offer = Offer(
            offer_id="OFF-002",
            offer_type=OfferType.FINAL,
            from_party="bob",
            to_party="alice",
            terms={},
            clauses=[],
            message="Final offer",
            expires_at=expires
        )

        assert offer.expires_at is not None


class TestNegotiationSession:
    """Tests for NegotiationSession dataclass."""

    def test_create_session(self):
        """Should create NegotiationSession."""
        session = NegotiationSession(
            session_id="SESSION-001",
            initiator="alice",
            counterparty="bob",
            subject="Widget purchase agreement",
            phase=NegotiationPhase.INITIATED
        )

        assert session.session_id == "SESSION-001"
        assert session.phase == NegotiationPhase.INITIATED
        assert session.round_count == 0
        assert session.max_rounds == 10

    def test_session_defaults(self):
        """Should have sensible defaults."""
        session = NegotiationSession(
            session_id="S1",
            initiator="a",
            counterparty="b",
            subject="test",
            phase=NegotiationPhase.INITIATED
        )

        assert session.alignment_score == 0.0
        assert session.clauses == {}
        assert session.offers == []
        assert session.agreed_terms is None


# ============================================================
# Enum Tests
# ============================================================

class TestEnums:
    """Tests for negotiation enums."""

    def test_negotiation_phase_values(self):
        """NegotiationPhase should have expected values."""
        assert NegotiationPhase.INITIATED.value == "initiated"
        assert NegotiationPhase.INTENT_ALIGNMENT.value == "alignment"
        assert NegotiationPhase.CLAUSE_DRAFTING.value == "drafting"
        assert NegotiationPhase.NEGOTIATING.value == "negotiating"
        assert NegotiationPhase.AGREED.value == "agreed"
        assert NegotiationPhase.FAILED.value == "failed"

    def test_offer_type_values(self):
        """OfferType should have expected values."""
        assert OfferType.INITIAL.value == "initial"
        assert OfferType.COUNTER.value == "counter"
        assert OfferType.FINAL.value == "final"
        assert OfferType.CONCESSION.value == "concession"
        assert OfferType.PACKAGE.value == "package"

    def test_clause_type_values(self):
        """ClauseType should have expected values."""
        assert ClauseType.PAYMENT.value == "payment"
        assert ClauseType.DELIVERY.value == "delivery"
        assert ClauseType.QUALITY.value == "quality"
        assert ClauseType.TIMELINE.value == "timeline"
        assert ClauseType.LIABILITY.value == "liability"
        assert ClauseType.TERMINATION.value == "termination"
        assert ClauseType.DISPUTE_RESOLUTION.value == "dispute_resolution"
        assert ClauseType.CONFIDENTIALITY.value == "confidentiality"

    def test_alignment_level_values(self):
        """AlignmentLevel should have expected values."""
        assert AlignmentLevel.STRONG.value == "strong"
        assert AlignmentLevel.MODERATE.value == "moderate"
        assert AlignmentLevel.WEAK.value == "weak"
        assert AlignmentLevel.MISALIGNED.value == "misaligned"


# ============================================================
# Proactive Alignment Layer Tests
# ============================================================

class TestProactiveAlignmentLayer:
    """Tests for ProactiveAlignmentLayer."""

    @pytest.fixture
    def alignment_layer(self):
        """Create alignment layer without LLM."""
        return ProactiveAlignmentLayer(client=None)

    def test_extract_intent_fallback(self, alignment_layer):
        """Should extract basic intent without LLM."""
        intent = alignment_layer.extract_intent(
            party="alice",
            statement="I want to sell 100 widgets for at least $10 each"
        )

        assert intent.party == "alice"
        assert len(intent.objectives) >= 1
        assert "I want to sell" in intent.objectives[0]

    def test_extract_intent_with_context(self, alignment_layer):
        """Should handle context parameter."""
        intent = alignment_layer.extract_intent(
            party="bob",
            statement="I need rush delivery",
            context="Previous agreement was for standard delivery"
        )

        assert intent.party == "bob"

    def test_compute_alignment_fallback(self, alignment_layer):
        """Should compute basic alignment without LLM."""
        intent_a = Intent(
            party="alice",
            objectives=["sell widgets"],
            constraints=["min $10 each"],
            priorities={"price": 10},
            flexibility={}
        )
        intent_b = Intent(
            party="bob",
            objectives=["buy widgets"],
            constraints=["max $12 each"],
            priorities={"quality": 10},
            flexibility={}
        )

        score, details = alignment_layer.compute_alignment(intent_a, intent_b)

        assert 0.0 <= score <= 1.0
        assert "alignment_level" in details

    def test_suggest_alignment_strategy_strong(self, alignment_layer):
        """Should suggest fast-track for strong alignment."""
        details = {"alignment_level": "strong", "strategy_suggestions": []}

        strategies = alignment_layer.suggest_alignment_strategy(details, "alice")

        assert len(strategies) >= 1
        assert any("Fast-track" in s["strategy"] for s in strategies)

    def test_suggest_alignment_strategy_moderate(self, alignment_layer):
        """Should suggest focus on complementary needs for moderate alignment."""
        details = {"alignment_level": "moderate", "strategy_suggestions": []}

        strategies = alignment_layer.suggest_alignment_strategy(details, "bob")

        assert len(strategies) >= 1
        assert any("complementary" in s["strategy"].lower() for s in strategies)

    def test_suggest_alignment_strategy_weak(self, alignment_layer):
        """Should suggest building common ground for weak alignment."""
        details = {"alignment_level": "weak", "strategy_suggestions": []}

        strategies = alignment_layer.suggest_alignment_strategy(details, "carol")

        assert len(strategies) >= 1
        assert any("common ground" in s["strategy"].lower() for s in strategies)

    def test_suggest_alignment_strategy_misaligned(self, alignment_layer):
        """Should suggest reassessment for misaligned parties."""
        details = {"alignment_level": "misaligned", "strategy_suggestions": []}

        strategies = alignment_layer.suggest_alignment_strategy(details, "dave")

        assert len(strategies) >= 1
        assert any("Reassess" in s["strategy"] or "BATNA" in s["action"] for s in strategies)

    def test_includes_ai_suggestions(self, alignment_layer):
        """Should include AI strategy suggestions."""
        details = {
            "alignment_level": "moderate",
            "strategy_suggestions": [
                "Consider package deal",
                "Offer timeline flexibility"
            ]
        }

        strategies = alignment_layer.suggest_alignment_strategy(details, "alice")

        # Should include both built-in and AI suggestions
        assert len(strategies) >= 3


# ============================================================
# Clause Generator Tests
# ============================================================

class TestClauseGenerator:
    """Tests for ClauseGenerator."""

    @pytest.fixture
    def generator(self):
        """Create clause generator without LLM."""
        return ClauseGenerator(client=None)

    def test_has_templates(self, generator):
        """Should have clause templates."""
        assert len(generator.TEMPLATES) > 0
        assert ClauseType.PAYMENT in generator.TEMPLATES
        assert ClauseType.DELIVERY in generator.TEMPLATES

    def test_payment_template(self, generator):
        """Payment template should have required placeholders."""
        template = generator.TEMPLATES[ClauseType.PAYMENT]

        assert "{amount}" in template
        assert "{method}" in template

    def test_delivery_template(self, generator):
        """Delivery template should have required placeholders."""
        template = generator.TEMPLATES[ClauseType.DELIVERY]

        assert "{location}" in template
        assert "{date}" in template

    def test_timeline_template(self, generator):
        """Timeline template should have required placeholders."""
        template = generator.TEMPLATES[ClauseType.TIMELINE]

        assert "{start_date}" in template
        assert "{end_date}" in template

    def test_dispute_resolution_template(self, generator):
        """Dispute resolution template should have required placeholders."""
        template = generator.TEMPLATES[ClauseType.DISPUTE_RESOLUTION]

        assert "{method}" in template
        assert "{jurisdiction}" in template


# ============================================================
# Session Management Tests
# ============================================================

class TestSessionManagement:
    """Tests for negotiation session management."""

    def test_session_phase_progression(self):
        """Session phases should follow logical order."""
        phases = [
            NegotiationPhase.INITIATED,
            NegotiationPhase.INTENT_ALIGNMENT,
            NegotiationPhase.CLAUSE_DRAFTING,
            NegotiationPhase.NEGOTIATING,
            NegotiationPhase.PENDING_APPROVAL,
            NegotiationPhase.AGREED
        ]

        # All phases should be distinct
        assert len(phases) == len(set(phases))

    def test_session_with_intents(self):
        """Session should store party intents."""
        intent_a = Intent(
            party="alice",
            objectives=["sell"],
            constraints=[],
            priorities={},
            flexibility={}
        )
        intent_b = Intent(
            party="bob",
            objectives=["buy"],
            constraints=[],
            priorities={},
            flexibility={}
        )

        session = NegotiationSession(
            session_id="S1",
            initiator="alice",
            counterparty="bob",
            subject="test",
            phase=NegotiationPhase.INTENT_ALIGNMENT,
            initiator_intent=intent_a,
            counterparty_intent=intent_b,
            alignment_score=0.7
        )

        assert session.initiator_intent.party == "alice"
        assert session.counterparty_intent.party == "bob"
        assert session.alignment_score == 0.7

    def test_session_with_offers(self):
        """Session should track offers."""
        offer1 = Offer(
            offer_id="O1",
            offer_type=OfferType.INITIAL,
            from_party="alice",
            to_party="bob",
            terms={"price": 100},
            clauses=[],
            message="Initial"
        )
        offer2 = Offer(
            offer_id="O2",
            offer_type=OfferType.COUNTER,
            from_party="bob",
            to_party="alice",
            terms={"price": 90},
            clauses=[],
            message="Counter"
        )

        session = NegotiationSession(
            session_id="S1",
            initiator="alice",
            counterparty="bob",
            subject="test",
            phase=NegotiationPhase.NEGOTIATING,
            offers=[offer1, offer2],
            round_count=2
        )

        assert len(session.offers) == 2
        assert session.round_count == 2

    def test_session_with_clauses(self):
        """Session should store clauses."""
        clause = Clause(
            clause_id="CL1",
            clause_type=ClauseType.PAYMENT,
            content="Payment terms",
            proposed_by="mediator",
            status="accepted"
        )

        session = NegotiationSession(
            session_id="S1",
            initiator="alice",
            counterparty="bob",
            subject="test",
            phase=NegotiationPhase.CLAUSE_DRAFTING,
            clauses={"CL1": clause}
        )

        assert "CL1" in session.clauses
        assert session.clauses["CL1"].status == "accepted"

    def test_session_agreement(self):
        """Session should store agreed terms."""
        session = NegotiationSession(
            session_id="S1",
            initiator="alice",
            counterparty="bob",
            subject="Widget purchase",
            phase=NegotiationPhase.AGREED,
            agreed_terms={
                "price": 95,
                "quantity": 100,
                "delivery": "30 days",
                "payment": "Net 30"
            }
        )

        assert session.phase == NegotiationPhase.AGREED
        assert session.agreed_terms is not None
        assert session.agreed_terms["price"] == 95


# ============================================================
# Integration Tests
# ============================================================

class TestNegotiationIntegration:
    """Integration tests for negotiation components."""

    def test_full_alignment_workflow(self):
        """Test complete alignment analysis workflow."""
        layer = ProactiveAlignmentLayer(client=None)

        # 1. Extract intents from parties
        intent_seller = layer.extract_intent(
            party="seller",
            statement="I want to sell my vintage guitar for at least $2000"
        )

        intent_buyer = layer.extract_intent(
            party="buyer",
            statement="I'm looking to buy a vintage guitar, budget up to $2500"
        )

        # 2. Compute alignment
        score, details = layer.compute_alignment(intent_seller, intent_buyer)

        # 3. Get strategies
        strategies = layer.suggest_alignment_strategy(details, "mediator")

        assert intent_seller.party == "seller"
        assert intent_buyer.party == "buyer"
        assert 0.0 <= score <= 1.0
        assert len(strategies) >= 1

    def test_session_lifecycle(self):
        """Test complete session lifecycle."""
        # 1. Create session
        session = NegotiationSession(
            session_id="LIFECYCLE-001",
            initiator="company_a",
            counterparty="company_b",
            subject="Partnership Agreement",
            phase=NegotiationPhase.INITIATED
        )

        assert session.phase == NegotiationPhase.INITIATED

        # 2. Add intents (phase: alignment)
        session.initiator_intent = Intent(
            party="company_a",
            objectives=["establish partnership"],
            constraints=["maintain IP rights"],
            priorities={"revenue_share": 10},
            flexibility={}
        )
        session.counterparty_intent = Intent(
            party="company_b",
            objectives=["access technology"],
            constraints=["limit liability"],
            priorities={"exclusivity": 8},
            flexibility={}
        )
        session.phase = NegotiationPhase.INTENT_ALIGNMENT
        session.alignment_score = 0.65

        # 3. Add clauses (phase: drafting)
        session.clauses["IP"] = Clause(
            clause_id="IP",
            clause_type=ClauseType.CUSTOM,
            content="IP rights remain with originating party",
            proposed_by="mediator"
        )
        session.phase = NegotiationPhase.CLAUSE_DRAFTING

        # 4. Exchange offers (phase: negotiating)
        session.offers.append(Offer(
            offer_id="OFFER-1",
            offer_type=OfferType.INITIAL,
            from_party="company_a",
            to_party="company_b",
            terms={"revenue_share": 0.6},
            clauses=["IP"],
            message="Initial proposal"
        ))
        session.phase = NegotiationPhase.NEGOTIATING
        session.round_count = 1

        # 5. Reach agreement
        session.agreed_terms = {
            "revenue_share": 0.55,
            "ip_clause": "IP",
            "duration": "3 years"
        }
        session.phase = NegotiationPhase.AGREED

        assert session.phase == NegotiationPhase.AGREED
        assert session.agreed_terms is not None
        assert len(session.offers) == 1
        assert len(session.clauses) == 1

    def test_offer_response_tracking(self):
        """Test tracking offer responses."""
        initial_offer = Offer(
            offer_id="O1",
            offer_type=OfferType.INITIAL,
            from_party="seller",
            to_party="buyer",
            terms={"price": 100},
            clauses=[],
            message="Initial offer at $100"
        )

        # Simulate response
        initial_offer.response = "countered"

        counter_offer = Offer(
            offer_id="O2",
            offer_type=OfferType.COUNTER,
            from_party="buyer",
            to_party="seller",
            terms={"price": 85},
            clauses=[],
            message="Counter at $85"
        )

        assert initial_offer.response == "countered"
        assert counter_offer.offer_type == OfferType.COUNTER
        assert counter_offer.terms["price"] < initial_offer.terms["price"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
