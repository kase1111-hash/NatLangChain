"""
NatLangChain - Standalone Sanitization Module

SECURITY: This module provides prompt injection detection and input sanitization
with ZERO external dependencies (no Flask, no anthropic, no validator imports).
This ensures sanitization is always available, even in degraded deployments.

Created to address Finding 1.1 (fallback sanitization bypasses injection detection)
and Finding 1.2 (Unicode normalization for confusable bypasses).
"""

import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# Maximum allowed lengths for user inputs in prompts
MAX_CONTENT_LENGTH = 10000
MAX_AUTHOR_LENGTH = 200
MAX_INTENT_LENGTH = 1000

# Patterns that could indicate prompt injection attempts
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"forget\s+(everything|all)\s+(above|before)",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"```\s*(system|instruction)",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
]


def sanitize_prompt_input(
    text: str, max_length: int = MAX_CONTENT_LENGTH, field_name: str = "input"
) -> str:
    """
    Sanitize user input before including it in LLM prompts.

    This function:
    1. Normalizes Unicode to prevent confusable bypasses (Finding 1.2)
    2. Truncates input to maximum allowed length
    3. Detects and flags potential injection attempts
    4. Normalizes whitespace

    Args:
        text: The user input to sanitize
        max_length: Maximum allowed length
        field_name: Name of field for error messages

    Returns:
        Sanitized text safe for inclusion in prompts

    Raises:
        ValueError: If input contains detected injection patterns
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""

    # SECURITY: Normalize Unicode to prevent confusable bypasses (Finding 1.2)
    text = unicodedata.normalize("NFKC", text)

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length] + f"... [TRUNCATED - exceeded {max_length} chars]"

    # Check for prompt injection patterns
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            # SECURITY: Log matched pattern server-side only (Finding 9.5)
            logger.warning(
                "Prompt injection detected in %s: pattern=%s",
                field_name, pattern,
            )
            raise ValueError(
                f"Input rejected for security reasons in field '{field_name}'."
            )

    # Escape delimiter-like sequences that could break prompt structure
    text = re.sub(r"```+", "[code-block]", text)
    text = re.sub(r"---+", "[separator]", text)
    text = re.sub(r"===+", "[separator]", text)

    # Normalize excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {3,}", "  ", text)

    return text.strip()


def create_safe_prompt_section(label: str, content: str, max_length: int) -> str:
    """
    Create a safely delimited section for inclusion in prompts.

    Uses clear delimiters that are hard to forge and includes length info.

    Args:
        label: Section label (e.g., "AUTHOR", "CONTENT")
        content: The sanitized content
        max_length: Max length used for sanitization

    Returns:
        Formatted section with clear delimiters
    """
    sanitized = sanitize_prompt_input(content, max_length, label)
    char_count = len(sanitized)

    return f"""[BEGIN {label} - {char_count} characters]
{sanitized}
[END {label}]"""


def validate_composed_sections(
    sections: list[tuple[str, str]],
) -> None:
    """
    Validate that composed prompt sections don't contain cross-boundary
    injection attempts. When multiple user-provided entries are composed
    into a single LLM prompt, a coordinated split-payload attack could
    bypass per-entry sanitization.

    Args:
        sections: List of (label, content) tuples that will be composed
                  into a single prompt.

    Raises:
        ValueError: If cross-entry injection is detected.
    """
    all_labels = {label for label, _ in sections}

    for label, content in sections:
        content_lower = content.lower()
        # Check if any entry references another entry's delimiter labels
        for other_label in all_labels:
            if other_label == label:
                continue
            if other_label.lower() in content_lower:
                logger.warning(
                    "Cross-section reference detected: '%s' found in section '%s'",
                    other_label, label,
                )
                raise ValueError(
                    f"Input rejected: cross-section reference detected in '{label}'"
                )

        # Check for delimiter forgery: [END ...] or [BEGIN ...] patterns
        if re.search(r"\[(BEGIN|END)\s+\w+", content, re.IGNORECASE):
            logger.warning(
                "Delimiter pattern detected in section '%s'", label,
            )
            raise ValueError(
                f"Input rejected: delimiter pattern detected in '{label}'"
            )

    # Run injection detection on concatenated content (catches split payloads)
    combined = " ".join(content for _, content in sections)
    combined_lower = combined.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, combined_lower, re.IGNORECASE):
            logger.warning(
                "Injection pattern detected in composed prompt: pattern=%s", pattern,
            )
            raise ValueError(
                "Input rejected: injection pattern detected in composed prompt"
            )


def sanitize_output(text: str) -> str:
    """
    Sanitize output content to prevent injection payload passthrough.

    Unlike sanitize_prompt_input, this does NOT raise errors — it silently
    replaces dangerous patterns with [FILTERED]. Used for content served
    to downstream consumers (e.g., narrative endpoint).

    Args:
        text: The output text to sanitize

    Returns:
        Sanitized text with injection patterns removed
    """
    if not isinstance(text, str):
        return str(text) if text is not None else ""

    # Normalize Unicode
    text = unicodedata.normalize("NFKC", text)

    # Replace injection patterns silently
    text_lower = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

    return text
