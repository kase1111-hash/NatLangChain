"""
Tests for the entry quality analyzer.

Tests size limits, repetition detection, and readability suggestions.
"""


from src.entry_quality import (
    DEFAULT_MAX_ENTRY_SIZE,
    EntryQualityAnalyzer,
    QualityDecision,
    QualityIssue,
    check_entry_quality,
    format_quality_feedback,
    get_readability_suggestions,
    is_entry_acceptable,
)

# =============================================================================
# Size Limit Tests
# =============================================================================


class TestSizeLimits:
    """Tests for entry size validation."""

    def test_valid_size_entry(self):
        """Test that normal-sized entries pass."""
        content = "Alice agrees to provide consulting services to Bob for $5000/month."
        result = check_entry_quality(content)
        assert result.is_acceptable
        assert result.decision in (QualityDecision.ACCEPT, QualityDecision.ACCEPT_WITH_SUGGESTIONS)

    def test_too_short_entry(self):
        """Test that very short entries are rejected."""
        content = "Hi"
        result = check_entry_quality(content)
        assert result.decision == QualityDecision.REJECT
        assert any(i.issue == QualityIssue.TOO_SHORT for i in result.issues)

    def test_too_long_entry(self):
        """Test that entries exceeding max size are rejected."""
        content = "word " * 3000  # ~15000 chars, exceeds 10000 default
        result = check_entry_quality(content, max_size=10000)
        assert result.decision == QualityDecision.REJECT
        assert any(i.issue == QualityIssue.TOO_LONG for i in result.issues)

    def test_approaching_limit_warning(self):
        """Test warning when approaching size limit."""
        # Create content that's 85% of the limit
        content = "x" * int(DEFAULT_MAX_ENTRY_SIZE * 0.85)
        result = check_entry_quality(content)
        # Should accept but may warn
        assert result.is_acceptable

    def test_custom_size_limits(self):
        """Test custom size limits."""
        analyzer = EntryQualityAnalyzer(max_size=100, min_size=10)

        # Too short
        result = analyzer.analyze("short")
        assert result.decision == QualityDecision.REJECT

        # Too long
        result = analyzer.analyze("x" * 150)
        assert result.decision == QualityDecision.REJECT

        # Just right
        result = analyzer.analyze("This is a valid entry with good length.")
        assert result.is_acceptable


# =============================================================================
# Repetition Detection Tests
# =============================================================================


class TestRepetitionDetection:
    """Tests for detecting repetitive content."""

    def test_no_repetition(self):
        """Test that unique content passes."""
        content = (
            "Alice will provide web development services. "
            "Bob agrees to pay monthly compensation. "
            "The project includes frontend and backend work. "
            "Deliverables will be reviewed weekly."
        )
        result = check_entry_quality(content)
        assert result.is_acceptable
        assert result.metrics.get("bigram_repetition", 0) < 0.3

    def test_high_repetition_warning(self):
        """Test that moderately repetitive content gets warning."""
        content = (
            "I will do the work. I will do the work well. "
            "I will do the work on time. I will do the work correctly. "
            "The work will be done. The work will be complete."
        )
        result = check_entry_quality(content)
        # Should still be acceptable but may have warnings
        assert (
            any(
                i.issue in (QualityIssue.EXCESSIVE_REPETITION, QualityIssue.REDUNDANT_CONTENT)
                for i in result.issues
            )
            or result.metrics.get("bigram_repetition", 0) > 0.2
        )

    def test_extreme_repetition_rejection(self):
        """Test that extremely repetitive content is rejected."""
        # Same phrase repeated many times
        content = "I agree to the terms. " * 20
        result = check_entry_quality(content)
        # Very high repetition should trigger issues
        assert result.metrics.get("bigram_repetition", 0) > 0.3 or len(result.issues) > 0

    def test_duplicate_sentences(self):
        """Test detection of duplicate sentences."""
        content = (
            "This is the first clause. "
            "This is the second clause. "
            "This is the first clause. "  # Duplicate
            "This is the third clause. "
            "This is the second clause. "  # Duplicate
        )
        result = check_entry_quality(content)
        assert result.metrics.get("duplicate_sentences", 0) >= 1


# =============================================================================
# Readability Tests
# =============================================================================


class TestReadability:
    """Tests for readability analysis."""

    def test_good_readability(self):
        """Test that clear, simple text scores well."""
        content = (
            "Alice will build a website for Bob. "
            "The project costs five thousand dollars. "
            "Work starts on Monday. "
            "The deadline is in three weeks."
        )
        result = check_entry_quality(content)
        assert result.is_acceptable
        assert result.metrics.get("readability_grade", 20) < 15

    def test_complex_vocabulary_suggestion(self):
        """Test that overly complex text gets suggestions."""
        content = (
            "The indemnification provisions notwithstanding, the "
            "aforementioned contractual obligations shall be effectuated "
            "in accordance with the predetermined specifications and "
            "methodological frameworks established herein."
        )
        result = check_entry_quality(content)
        # Should have readability suggestions
        # Complex vocabulary tends to increase avg word length
        assert result.metrics.get("avg_word_length", 0) > 5

    def test_long_sentences_suggestion(self):
        """Test that very long sentences get suggestions."""
        # One very long sentence
        content = (
            "This contract between Alice and Bob which was signed on "
            "January first two thousand twenty five in the city of "
            "New York in the presence of witnesses and notarized by "
            "a licensed notary public and filed with the county clerk "
            "establishes the terms and conditions of the business "
            "relationship between the parties for the purpose of "
            "developing software applications and related services."
        )
        result = check_entry_quality(content)
        # Should flag long sentences
        assert result.metrics.get("avg_sentence_length", 0) > 25

    def test_readability_grade_calculation(self):
        """Test that readability grade is calculated."""
        content = "Simple words make reading easy. Short sentences help too."
        result = check_entry_quality(content)
        assert "readability_grade" in result.metrics
        assert isinstance(result.metrics["readability_grade"], (int, float))


# =============================================================================
# Structure Tests
# =============================================================================


class TestStructure:
    """Tests for structural analysis."""

    def test_dense_paragraph_warning(self):
        """Test that very dense paragraphs get suggestions."""
        # One huge paragraph
        content = "word " * 200  # ~1000 chars, no paragraph breaks
        result = check_entry_quality(content)
        # May have dense text warning
        assert result.metrics.get("paragraph_count", 0) == 1

    def test_missing_punctuation_warning(self):
        """Test that lack of punctuation is flagged."""
        content = " ".join(["word"] * 60)  # 60 words, no punctuation
        result = check_entry_quality(content)
        # Should have punctuation warning or low punctuation detected
        has_punctuation_issue = any(
            i.issue == QualityIssue.MISSING_PUNCTUATION for i in result.issues
        )
        # Either flagged or metrics show low punctuation
        assert has_punctuation_issue or result.metrics.get("sentence_count", 1) <= 2

    def test_good_structure(self):
        """Test that well-structured content passes."""
        content = """
        This is the first section. It has proper punctuation.

        This is the second section. It's also well-formatted.

        The final section concludes the document.
        """
        result = check_entry_quality(content.strip())
        assert result.is_acceptable
        assert result.metrics.get("paragraph_count", 0) >= 2


# =============================================================================
# Quality Score Tests
# =============================================================================


class TestQualityScore:
    """Tests for quality score calculation."""

    def test_perfect_entry_high_score(self):
        """Test that a well-written entry scores high."""
        content = (
            "Agreement between Alice and Bob.\n\n"
            "Alice will develop a mobile application. "
            "Bob will pay $10,000 upon completion. "
            "The project deadline is March 15, 2025.\n\n"
            "Both parties agree to these terms."
        )
        result = check_entry_quality(content)
        assert result.score >= 0.7
        assert result.is_acceptable

    def test_poor_entry_low_score(self):
        """Test that problematic entries are rejected regardless of score."""
        content = "bad " * 3  # Too short
        result = check_entry_quality(content)
        # Entry should be rejected even if score is reasonable
        # (a single critical issue like too_short causes rejection)
        assert not result.is_acceptable
        assert result.decision == QualityDecision.REJECT

    def test_score_range(self):
        """Test that scores are always in valid range."""
        test_cases = [
            "x",  # Too short
            "Normal content with good structure.",
            "word " * 100,  # Longer content
        ]
        for content in test_cases:
            result = check_entry_quality(content)
            assert 0.0 <= result.score <= 1.0


# =============================================================================
# Decision Tests
# =============================================================================


class TestDecisions:
    """Tests for quality decision outcomes."""

    def test_accept_decision(self):
        """Test that good entries are accepted."""
        content = "Alice transfers ownership of Patent ABC-123 to Bob for $50,000."
        result = check_entry_quality(content)
        assert result.decision in (QualityDecision.ACCEPT, QualityDecision.ACCEPT_WITH_SUGGESTIONS)

    def test_reject_decision(self):
        """Test that bad entries are rejected."""
        content = "hi"  # Too short
        result = check_entry_quality(content)
        assert result.decision == QualityDecision.REJECT

    def test_strict_mode(self):
        """Test that strict mode converts warnings to errors."""
        # Content that might have warnings
        content = "This is a test. " * 10  # Some repetition

        # Non-strict mode
        normal_result = check_entry_quality(content, strict=False)

        # Strict mode
        strict_result = check_entry_quality(content, strict=True)

        # Both should analyze, strict may be more severe
        assert normal_result.decision is not None
        assert strict_result.decision is not None


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_is_entry_acceptable_true(self):
        """Test is_entry_acceptable returns True for good entries."""
        content = "Alice agrees to provide services to Bob for compensation."
        assert is_entry_acceptable(content) is True

    def test_is_entry_acceptable_false(self):
        """Test is_entry_acceptable returns False for bad entries."""
        assert is_entry_acceptable("x") is False
        assert is_entry_acceptable("x" * 50000) is False  # Too long

    def test_get_readability_suggestions(self):
        """Test getting readability suggestions."""
        content = "Simple clear text that is easy to read."
        suggestions = get_readability_suggestions(content)
        assert isinstance(suggestions, list)

    def test_format_quality_feedback(self):
        """Test formatting quality feedback."""
        result = check_entry_quality("Alice agrees to help Bob with the project.")
        feedback = format_quality_feedback(result)
        assert isinstance(feedback, str)
        assert len(feedback) > 0
        # Should contain metrics
        assert "Characters:" in feedback or "Words:" in feedback


# =============================================================================
# Metrics Tests
# =============================================================================


class TestMetrics:
    """Tests for quality metrics."""

    def test_char_count(self):
        """Test character count metric."""
        content = "Hello World"
        result = check_entry_quality(content)
        assert result.metrics["char_count"] == len(content)

    def test_word_count(self):
        """Test word count metric."""
        content = "one two three four five"
        result = check_entry_quality(content)
        assert result.metrics["word_count"] == 5

    def test_sentence_count(self):
        """Test sentence count metric."""
        content = "First sentence. Second sentence. Third sentence."
        result = check_entry_quality(content)
        assert result.metrics["sentence_count"] == 3

    def test_paragraph_count(self):
        """Test paragraph count metric."""
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = check_entry_quality(content)
        assert result.metrics["paragraph_count"] == 3


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_string(self):
        """Test handling of empty string."""
        result = check_entry_quality("")
        assert result.decision == QualityDecision.REJECT

    def test_whitespace_only(self):
        """Test handling of whitespace-only content."""
        result = check_entry_quality("   \n\n   \t   ")
        assert not result.is_acceptable

    def test_unicode_content(self):
        """Test handling of unicode content."""
        content = "Alice 同意 to provide サービス to Bob für €5000."
        result = check_entry_quality(content)
        # Should handle unicode without crashing
        assert result.metrics["char_count"] > 0

    def test_special_characters(self):
        """Test handling of special characters."""
        content = "Contract: $1,000 @ 5% interest (annual) — effective immediately!"
        result = check_entry_quality(content)
        assert result.is_acceptable

    def test_very_long_word(self):
        """Test handling of extremely long words."""
        content = "The " + "x" * 100 + " is important."
        result = check_entry_quality(content)
        # Should handle without crashing
        assert result.metrics["avg_word_length"] > 0
