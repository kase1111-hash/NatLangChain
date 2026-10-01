"""
Shared LLM configuration and response helpers.

Every module that talks to the Anthropic Messages API (validator, contract
parser/matcher, intent classifier, PoU scorer) resolves its model through
``get_model()`` and reads responses through ``extract_text()`` so the model
can be changed in one place and responses are parsed by block type rather
than by position.
"""

import os
from typing import Any

# Default model for Proof of Understanding validation, contract parsing,
# intent classification and PoU scoring. Override with NATLANGCHAIN_LLM_MODEL.
DEFAULT_MODEL = "claude-sonnet-5-5"

MODEL_ENV_VAR = "NATLANGCHAIN_LLM_MODEL"


def get_model() -> str:
    """Return the configured Anthropic model ID."""
    return os.getenv(MODEL_ENV_VAR, "").strip() or DEFAULT_MODEL


def extract_text(message: Any) -> str:
    """
    Return the concatenated text of a Messages API response.

    Responses are read by content-block type, not position: current models can
    return a ``thinking`` block before the first ``text`` block, so indexing
    ``content[0]`` is not safe. Blocks without a ``type`` attribute but with a
    string ``text`` attribute are accepted for compatibility with older SDK
    objects and test doubles.

    Raises:
        ValueError: If the request was declined, the response is empty, or it
            contains no text block.
    """
    if getattr(message, "stop_reason", None) == "refusal":
        raise ValueError("LLM declined the request (stop_reason=refusal)")

    content = getattr(message, "content", None)
    if not content:
        raise ValueError("Empty response from API: no content returned")

    parts: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None)
        text = getattr(block, "text", None)
        if block_type == "text" and isinstance(text, str):
            parts.append(text)
        elif block_type is None or not isinstance(block_type, str):
            if isinstance(text, str):
                parts.append(text)

    if not parts:
        raise ValueError("Invalid API response format: no text content block")

    return "".join(parts)
