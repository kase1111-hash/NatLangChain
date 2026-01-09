"""
NatLangChain - Entry Quality & Readability

Addresses chain bloat by:
1. Enforcing reasonable entry size limits
2. Detecting repetitive/redundant content
3. Providing readability suggestions (optional, helps matching)

Philosophy: Rejection should happen for genuinely problematic entries,
but suggestions help users write clearer contracts that match better.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Size limits (in characters)
DEFAULT_MAX_ENTRY_SIZE = 10000  # ~2500 words, sufficient for detailed contracts
DEFAULT_MIN_ENTRY_SIZE = 20  # Minimum meaningful content
ABSOLUTE_MAX_ENTRY_SIZE = 50000  # Hard cap for exceptional cases

# Repetition thresholds
REPETITION_THRESHOLD = 0.3  # 30% repeated n-grams triggers warning
REDUNDANCY_THRESHOLD = 0.5  # 50% repeated content triggers rejection

# Readability targets
TARGET_SENTENCE_LENGTH = 25  # Average words per sentence
TARGET_WORD_LENGTH = 6  # Average characters per word
MAX_PARAGRAPH_LENGTH = 500  # Characters before suggesting a break


class QualityDecision(Enum):
    """Quality check decision outcomes."""

    ACCEPT = "accept"  # Entry is acceptable
    ACCEPT_WITH_SUGGESTIONS = "accept_with_suggestions"  # Acceptable but could be improved
    NEEDS_REVISION = "needs_revision"  # Should be revised (soft rejection)
    REJECT = "reject"  # Rejected (hard rejection)


class QualityIssue(Enum):
    """Types of quality issues detected."""

    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    EXCESSIVE_REPETITION = "excessive_repetition"
    REDUNDANT_CONTENT = "redundant_content"
    POOR_READABILITY = "poor_readability"
    DENSE_TEXT = "dense_text"
    AMBIGUOUS_STRUCTURE = "ambiguous_structure"
    MISSING_PUNCTUATION = "missing_punctuation"


@dataclass
class QualitySuggestion:
    """A suggestion for improving entry quality."""

    issue: QualityIssue
    severity: str  # "info", "warning", "error"
    message: str
    suggestion: str
    location: str | None = None  # Optional: where in the text


@dataclass
class QualityResult:
    """Result of entry quality analysis."""

    decision: QualityDecision
    score: float  # 0.0 to 1.0
    issues: list[QualitySuggestion] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    @property
    def is_acceptable(self) -> bool:
        """Whether the entry can be accepted (possibly with suggestions)."""
        return self.decision in (QualityDecision.ACCEPT, QualityDecision.ACCEPT_WITH_SUGGESTIONS)

    @property
    def has_suggestions(self) -> bool:
        """Whether there are suggestions for improvement."""
        return len(self.issues) > 0


# =============================================================================
# Entry Quality Analyzer
# =============================================================================


class EntryQualityAnalyzer:
    """
    Analyzes entry quality for size, repetition, and readability.

    This helps prevent chain bloat while providing helpful feedback
    to users about how to write clearer contracts.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_ENTRY_SIZE,
        min_size: int = DEFAULT_MIN_ENTRY_SIZE,
        repetition_threshold: float = REPETITION_THRESHOLD,
        redundancy_threshold: float = REDUNDANCY_THRESHOLD,
        strict_mode: bool = False,
    ):
        """
        Initialize the quality analyzer.

        Args:
            max_size: Maximum entry size in characters
            min_size: Minimum entry size in characters
            repetition_threshold: Threshold for repetition warnings
            redundancy_threshold: Threshold for redundancy rejection
            strict_mode: If True, treats warnings as errors
        """
        self.max_size = min(max_size, ABSOLUTE_MAX_ENTRY_SIZE)
        self.min_size = min_size
        self.repetition_threshold = repetition_threshold
        self.redundancy_threshold = redundancy_threshold
        self.strict_mode = strict_mode

    def analyze(self, content: str, intent: str = "") -> QualityResult:
        """
        Analyze entry quality comprehensively.

        Args:
            content: The entry content to analyze
            intent: Optional intent for context

        Returns:
            QualityResult with decision, score, and suggestions
        """
        issues = []
        metrics = {}

        # Basic metrics
        metrics["char_count"] = len(content)
        metrics["word_count"] = len(content.split())
        metrics["sentence_count"] = self._count_sentences(content)
        metrics["paragraph_count"] = self._count_paragraphs(content)

        # Size checks
        size_issues = self._check_size(content)
        issues.extend(size_issues)

        # Repetition checks
        rep_issues, rep_metrics = self._check_repetition(content)
        issues.extend(rep_issues)
        metrics.update(rep_metrics)

        # Readability checks
        read_issues, read_metrics = self._check_readability(content)
        issues.extend(read_issues)
        metrics.update(read_metrics)

        # Structure checks
        struct_issues = self._check_structure(content)
        issues.extend(struct_issues)

        # Calculate overall score and decision
        score = self._calculate_score(issues, metrics)
        decision = self._determine_decision(issues, score)
        summary = self._generate_summary(decision, issues, metrics)

        return QualityResult(
            decision=decision,
            score=score,
            issues=issues,
            metrics=metrics,
            summary=summary,
        )

    # =========================================================================
    # Size Checks
    # =========================================================================

    def _check_size(self, content: str) -> list[QualitySuggestion]:
        """Check entry size constraints."""
        issues = []
        char_count = len(content)

        if char_count < self.min_size:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.TOO_SHORT,
                    severity="error",
                    message=f"Entry too short ({char_count} chars, minimum {self.min_size})",
                    suggestion="Provide more detail about your intent. What are the key terms, "
                    "parties involved, and expected outcomes?",
                )
            )

        elif char_count > self.max_size:
            excess = char_count - self.max_size
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.TOO_LONG,
                    severity="error",
                    message=f"Entry exceeds size limit ({char_count} chars, maximum {self.max_size})",
                    suggestion=f"Reduce by ~{excess} characters. Consider:\n"
                    "• Removing redundant explanations\n"
                    "• Using bullet points instead of paragraphs\n"
                    "• Splitting into multiple related entries\n"
                    "• Referencing external documents instead of embedding them",
                )
            )

        elif char_count > self.max_size * 0.8:
            # Warning when approaching limit
            remaining = self.max_size - char_count
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.TOO_LONG,
                    severity="warning",
                    message=f"Entry approaching size limit ({remaining} chars remaining)",
                    suggestion="Consider condensing if possible to leave room for amendments",
                )
            )

        return issues

    # =========================================================================
    # Repetition Detection
    # =========================================================================

    def _check_repetition(self, content: str) -> tuple[list[QualitySuggestion], dict]:
        """Detect repetitive content that bloats entries."""
        issues = []
        metrics = {}

        words = self._tokenize(content)
        if len(words) < 10:
            return issues, metrics

        # Check for repeated phrases (n-grams)
        bigrams = self._get_ngrams(words, 2)
        trigrams = self._get_ngrams(words, 3)

        # Calculate repetition ratios
        bigram_ratio = self._repetition_ratio(bigrams)
        trigram_ratio = self._repetition_ratio(trigrams)

        metrics["bigram_repetition"] = round(bigram_ratio, 3)
        metrics["trigram_repetition"] = round(trigram_ratio, 3)

        # Check for copy-paste redundancy (exact duplicate sentences)
        sentences = self._split_sentences(content)
        duplicate_sentences = self._find_duplicates(sentences)
        metrics["duplicate_sentences"] = len(duplicate_sentences)

        # Evaluate issues
        if bigram_ratio > self.redundancy_threshold:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.REDUNDANT_CONTENT,
                    severity="error",
                    message=f"Excessive repetition detected ({bigram_ratio:.0%} of phrases repeat)",
                    suggestion="This entry contains too much repeated content. "
                    "Remove duplicate phrases and consolidate similar points.",
                )
            )

        elif bigram_ratio > self.repetition_threshold:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.EXCESSIVE_REPETITION,
                    severity="warning",
                    message=f"High repetition detected ({bigram_ratio:.0%} of phrases repeat)",
                    suggestion="Consider consolidating repeated phrases. "
                    "Repetition can make contracts harder to match and interpret.",
                )
            )

        if duplicate_sentences:
            dup_count = len(duplicate_sentences)
            if dup_count > 2:
                issues.append(
                    QualitySuggestion(
                        issue=QualityIssue.REDUNDANT_CONTENT,
                        severity="error" if dup_count > 4 else "warning",
                        message=f"Found {dup_count} duplicate sentences",
                        suggestion=f"Remove duplicated sentences: {duplicate_sentences[:2]}...",
                    )
                )

        return issues, metrics

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r"\b[a-zA-Z]+\b", text.lower())

    def _get_ngrams(self, words: list[str], n: int) -> list[tuple]:
        """Get n-grams from word list."""
        return [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]

    def _repetition_ratio(self, ngrams: list[tuple]) -> float:
        """Calculate what fraction of n-grams are repeated."""
        if not ngrams:
            return 0.0
        counts = Counter(ngrams)
        repeated = sum(count - 1 for count in counts.values() if count > 1)
        return repeated / len(ngrams)

    def _find_duplicates(self, items: list[str]) -> list[str]:
        """Find duplicate items in a list."""
        seen = set()
        duplicates = []
        for item in items:
            normalized = item.strip().lower()
            if normalized in seen and normalized not in duplicates:
                duplicates.append(item.strip()[:50])  # Truncate for display
            seen.add(normalized)
        return duplicates

    # =========================================================================
    # Readability Analysis
    # =========================================================================

    def _check_readability(self, content: str) -> tuple[list[QualitySuggestion], dict]:
        """Analyze readability and provide suggestions."""
        issues = []
        metrics = {}

        words = content.split()
        sentences = self._split_sentences(content)

        if not words or not sentences:
            return issues, metrics

        # Average sentence length
        avg_sentence_length = len(words) / len(sentences)
        metrics["avg_sentence_length"] = round(avg_sentence_length, 1)

        # Average word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        metrics["avg_word_length"] = round(avg_word_length, 1)

        # Flesch-Kincaid approximation (simplified)
        fk_score = self._flesch_kincaid_grade(content, words, sentences)
        metrics["readability_grade"] = round(fk_score, 1)

        # Generate suggestions
        if avg_sentence_length > TARGET_SENTENCE_LENGTH * 1.5:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.POOR_READABILITY,
                    severity="info",
                    message=f"Long sentences detected (avg {avg_sentence_length:.0f} words)",
                    suggestion="Consider breaking long sentences into shorter ones. "
                    "Aim for 15-25 words per sentence for clarity.",
                )
            )

        if avg_word_length > TARGET_WORD_LENGTH * 1.3:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.POOR_READABILITY,
                    severity="info",
                    message="Complex vocabulary detected",
                    suggestion="Consider using simpler words where possible. "
                    "Clearer language improves matching accuracy.",
                )
            )

        if fk_score > 16:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.POOR_READABILITY,
                    severity="warning",
                    message=f"High reading level (grade {fk_score:.0f}+)",
                    suggestion="This text requires advanced reading level. "
                    "Consider simplifying for broader accessibility.",
                )
            )

        return issues, metrics

    def _flesch_kincaid_grade(self, text: str, words: list[str], sentences: list[str]) -> float:
        """Calculate approximate Flesch-Kincaid grade level."""
        if not words or not sentences:
            return 0.0

        # Count syllables (approximation)
        syllables = sum(self._count_syllables(word) for word in words)

        words_per_sentence = len(words) / len(sentences)
        syllables_per_word = syllables / len(words)

        # Flesch-Kincaid formula
        grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
        return max(0, min(20, grade))  # Clamp to reasonable range

    def _count_syllables(self, word: str) -> int:
        """Approximate syllable count for a word."""
        word = word.lower()
        if len(word) <= 3:
            return 1

        # Count vowel groups
        vowels = "aeiouy"
        count = 0
        prev_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                count += 1
            prev_was_vowel = is_vowel

        # Adjust for silent e
        if word.endswith("e"):
            count = max(1, count - 1)

        return max(1, count)

    # =========================================================================
    # Structure Checks
    # =========================================================================

    def _check_structure(self, content: str) -> list[QualitySuggestion]:
        """Check for structural issues."""
        issues = []

        # Check for very long paragraphs
        paragraphs = content.split("\n\n")
        long_paragraphs = [p for p in paragraphs if len(p) > MAX_PARAGRAPH_LENGTH]
        if long_paragraphs:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.DENSE_TEXT,
                    severity="info",
                    message=f"Found {len(long_paragraphs)} dense paragraph(s)",
                    suggestion="Consider breaking long paragraphs into smaller sections "
                    "with clear headings. This improves readability and matching.",
                )
            )

        # Check for missing punctuation (wall of text)
        words = content.split()
        if len(words) > 50:
            punctuation_ratio = sum(1 for c in content if c in ".!?;:") / len(words)
            if punctuation_ratio < 0.02:
                issues.append(
                    QualitySuggestion(
                        issue=QualityIssue.MISSING_PUNCTUATION,
                        severity="warning",
                        message="Low punctuation density (possible run-on text)",
                        suggestion="Add proper punctuation to separate ideas. "
                        "Well-punctuated text is easier to parse and match.",
                    )
                )

        # Check for ambiguous list structures
        bullet_chars = content.count("•") + content.count("-") + content.count("*")
        if bullet_chars > 10 and "\n" not in content:
            issues.append(
                QualitySuggestion(
                    issue=QualityIssue.AMBIGUOUS_STRUCTURE,
                    severity="info",
                    message="Bullet points without line breaks detected",
                    suggestion="Put each bullet point on its own line for clarity.",
                )
            )

        return issues

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        return len(self._split_sentences(text))

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text."""
        paragraphs = text.split("\n\n")
        return len([p for p in paragraphs if p.strip()])

    def _calculate_score(self, issues: list[QualitySuggestion], metrics: dict) -> float:
        """Calculate overall quality score (0-1)."""
        score = 1.0

        # Deduct for issues based on severity
        for issue in issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.1
            elif issue.severity == "info":
                score -= 0.02

        # Bonus for good metrics
        if metrics.get("avg_sentence_length", 30) <= TARGET_SENTENCE_LENGTH:
            score += 0.05
        if metrics.get("readability_grade", 16) <= 12:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _determine_decision(self, issues: list[QualitySuggestion], score: float) -> QualityDecision:
        """Determine the overall decision based on issues and score."""
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        if error_count > 0:
            # Check if it's a hard rejection (size/redundancy) or soft (needs revision)
            hard_reject_issues = {
                QualityIssue.TOO_SHORT,
                QualityIssue.TOO_LONG,
                QualityIssue.REDUNDANT_CONTENT,
            }
            has_hard_reject = any(
                i.issue in hard_reject_issues for i in issues if i.severity == "error"
            )
            if has_hard_reject:
                return QualityDecision.REJECT
            return QualityDecision.NEEDS_REVISION

        if warning_count > 0 or (self.strict_mode and issues):
            return QualityDecision.ACCEPT_WITH_SUGGESTIONS

        if issues:
            return QualityDecision.ACCEPT_WITH_SUGGESTIONS

        return QualityDecision.ACCEPT

    def _generate_summary(
        self,
        decision: QualityDecision,
        issues: list[QualitySuggestion],
        metrics: dict,
    ) -> str:
        """Generate human-readable summary."""
        if decision == QualityDecision.ACCEPT:
            return "Entry meets quality standards."

        if decision == QualityDecision.REJECT:
            error_messages = [i.message for i in issues if i.severity == "error"]
            return f"Entry rejected: {'; '.join(error_messages)}"

        if decision == QualityDecision.NEEDS_REVISION:
            return "Entry needs revision before acceptance. See suggestions."

        # ACCEPT_WITH_SUGGESTIONS
        suggestion_count = len(issues)
        return f"Entry acceptable with {suggestion_count} suggestion(s) for improvement."


# =============================================================================
# Convenience Functions
# =============================================================================


def check_entry_quality(
    content: str,
    intent: str = "",
    max_size: int = DEFAULT_MAX_ENTRY_SIZE,
    strict: bool = False,
) -> QualityResult:
    """
    Quick quality check for an entry.

    Args:
        content: Entry content
        intent: Optional intent
        max_size: Maximum allowed size
        strict: Whether to be strict about warnings

    Returns:
        QualityResult with decision and suggestions
    """
    analyzer = EntryQualityAnalyzer(max_size=max_size, strict_mode=strict)
    return analyzer.analyze(content, intent)


def get_readability_suggestions(content: str) -> list[str]:
    """
    Get readability suggestions for content.

    Args:
        content: Text to analyze

    Returns:
        List of suggestion strings
    """
    result = check_entry_quality(content)
    return [
        f"{issue.message}: {issue.suggestion}"
        for issue in result.issues
        if issue.issue == QualityIssue.POOR_READABILITY
    ]


def is_entry_acceptable(content: str, max_size: int = DEFAULT_MAX_ENTRY_SIZE) -> bool:
    """
    Quick check if entry is acceptable.

    Args:
        content: Entry content
        max_size: Maximum allowed size

    Returns:
        True if entry can be accepted
    """
    result = check_entry_quality(content, max_size=max_size)
    return result.is_acceptable


def format_quality_feedback(result: QualityResult) -> str:
    """
    Format quality result as user-friendly feedback.

    Args:
        result: QualityResult to format

    Returns:
        Formatted feedback string
    """
    lines = [result.summary, ""]

    if result.metrics:
        lines.append("Metrics:")
        lines.append(f"  • Characters: {result.metrics.get('char_count', 'N/A')}")
        lines.append(f"  • Words: {result.metrics.get('word_count', 'N/A')}")
        lines.append(f"  • Readability: Grade {result.metrics.get('readability_grade', 'N/A')}")
        lines.append("")

    if result.issues:
        lines.append("Suggestions:")
        for issue in result.issues:
            icon = {"error": "❌", "warning": "⚠️", "info": "💡"}.get(issue.severity, "•")
            lines.append(f"  {icon} {issue.message}")
            lines.append(f"     → {issue.suggestion}")
        lines.append("")

    return "\n".join(lines)
