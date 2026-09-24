"""Output sanitization utilities."""

from __future__ import annotations

import re


def sanitize_llm_output(text: str) -> str:
    """Sanitize LLM output text.

    Strips HTML tags, script schemes, normalizes line whitespace, and truncates
    to maximum 10,000 characters.

    Args:
        text: Raw output string from LLM.

    Returns:
        Sanitized, safe string.
    """
    if not text:
        return ""

    # Strip HTML tags
    clean = re.sub(r"<[^>]*>", "", text)

    # Remove inline script schemes
    clean = re.sub(r"(?i)(javascript|vbscript|data):", "", clean)

    # Normalize whitespace per line, preserving line breaks
    lines = clean.splitlines()
    normalized_lines = [" ".join(line.split()) for line in lines if line.strip()]
    clean = "\n".join(normalized_lines)

    # Truncate
    if len(clean) > 10000:
        clean = clean[:10000]

    return clean


def sanitize_finding_text(finding_explanation: str) -> str:
    """Sanitize finding explanation text and strip prompt leak markers.

    Args:
        finding_explanation: Explanation text from LLM.

    Returns:
        Sanitized explanation string.
    """
    text = sanitize_llm_output(finding_explanation)

    # Remove prompt leak markers at start of line
    leak_pattern = re.compile(r"^\s*(System|Instructions|Prompt|User):", re.IGNORECASE)
    lines = text.splitlines()
    safe_lines = [line for line in lines if not leak_pattern.match(line)]

    return "\n".join(safe_lines)
