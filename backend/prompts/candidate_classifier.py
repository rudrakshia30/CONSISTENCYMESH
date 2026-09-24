"""
Optional candidate classifier prompt template.

This is an optional AI pre-check stage that can be used to further
filter candidate pairs before full consistency analysis. In the current
implementation, deterministic TF-IDF + metadata scoring handles
candidate filtering without an LLM call, which is more efficient.

This module is provided as an extension point if empirical measurement
shows that an AI pre-check further reduces LLM calls cost-effectively.
"""

from __future__ import annotations

CANDIDATE_CLASSIFIER_VERSION = "candidate_classifier_v1.0"

CLASSIFIER_SYSTEM_PROMPT = """You are a document clause classifier. Given two clauses from different documents, determine if they are semantically related enough to warrant a detailed consistency analysis.

Respond with ONLY a JSON object:
{
    "related": true/false,
    "reason": "brief explanation"
}

Be conservative — if in doubt, mark as related (true). It is better to over-include than to miss a potential conflict."""


def build_classifier_prompt(
    clause_a_text: str,
    clause_b_text: str,
) -> tuple[str, str]:
    """Build prompts for the optional candidate classifier.

    Currently unused in the main pipeline — deterministic scoring
    via TF-IDF + metadata overlap handles filtering. This exists
    as a documented extension point.

    Args:
        clause_a_text: Text of the first clause.
        clause_b_text: Text of the second clause.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    user_prompt = f"""Are these two clauses related enough to warrant consistency analysis?

Clause A:
{clause_a_text[:500]}

Clause B:
{clause_b_text[:500]}

Respond with the JSON schema specified in your instructions."""

    return CLASSIFIER_SYSTEM_PROMPT, user_prompt
