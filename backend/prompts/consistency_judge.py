"""
Prompt template for pairwise consistency judgment.

Defines the structured prompt sent to the LLM for analyzing the
relationship between two clauses from different documents. Includes
nonce-based document isolation and strict JSON output schema.
"""

from __future__ import annotations

from backend.models.schemas import Clause
from backend.security.prompt_guard import (
    build_isolation_instruction,
    generate_nonce,
    wrap_document_content,
)

PROMPT_VERSION = "consistency_judge_v1.0"

SYSTEM_PROMPT = """You are a legal document consistency analyzer. Your task is to compare two clauses from different documents and determine their relationship.

CRITICAL RULES:
1. You may ONLY classify the relationship using one of these exact types: CONSISTENT, CONFLICT, OVERRIDE, AMBIGUOUS, UNADDRESSED
2. You may ONLY assign confidence as one of: STATED, INTERPRETED, NOT_ESTABLISHED
3. You must provide evidence spans that are EXACT quotes from the provided clause texts
4. You must NEVER decide which document "wins" legally unless the text explicitly states it
5. Use descriptive language: "The documents state...", "The documents appear inconsistent because..."
6. NEVER claim to be a lawyer or that a provision is legally enforceable
7. If you cannot determine the relationship with confidence, use AMBIGUOUS or NOT_ESTABLISHED

{isolation_instruction}

Respond with ONLY a JSON object matching this exact schema:
{{
    "relationship_type": "CONSISTENT|CONFLICT|OVERRIDE|AMBIGUOUS|UNADDRESSED",
    "confidence": "STATED|INTERPRETED|NOT_ESTABLISHED",
    "explanation": "Clear explanation of the relationship found",
    "evidence": [
        {{
            "document_id": "id of the source document",
            "clause_id": "id of the source clause",
            "page": 1,
            "text_span": "exact quote from the clause text"
        }}
    ],
    "uncertainty": "null or explanation of any uncertainty"
}}

You MUST include at least one evidence span from EACH of the two clauses being compared.
Do NOT include any text outside the JSON object."""


def build_consistency_prompt(
    clause_a: Clause,
    clause_b: Clause,
    context: dict[str, str],
) -> tuple[str, str]:
    """Build the system prompt and user prompt for a pairwise consistency judgment.

    Wraps clause content in nonce-delimited blocks for injection isolation.
    Returns only the two candidate clauses plus minimal metadata — never
    full documents.

    Args:
        clause_a: First clause for comparison.
        clause_b: Second clause for comparison.
        context: Additional context (document filenames, etc.).

    Returns:
        Tuple of (system_prompt, user_prompt) strings.
    """
    nonce = generate_nonce()

    system = SYSTEM_PROMPT.format(
        isolation_instruction=build_isolation_instruction(nonce),
    )

    doc_a_label = context.get("doc_a_name", "A")
    doc_b_label = context.get("doc_b_name", "B")

    wrapped_a = wrap_document_content(clause_a.text, doc_a_label, nonce)
    wrapped_b = wrap_document_content(clause_b.text, doc_b_label, nonce)

    user_prompt = f"""Compare these two clauses for consistency:

CLAUSE A:
- Document: {doc_a_label} (ID: {clause_a.document_id})
- Clause ID: {clause_a.clause_id}
- Page: {clause_a.page}
- Section: {clause_a.section or 'Not specified'}
- Topics: {', '.join(clause_a.topics) if clause_a.topics else 'None detected'}

{wrapped_a}

CLAUSE B:
- Document: {doc_b_label} (ID: {clause_b.document_id})
- Clause ID: {clause_b.clause_id}
- Page: {clause_b.page}
- Section: {clause_b.section or 'Not specified'}
- Topics: {', '.join(clause_b.topics) if clause_b.topics else 'None detected'}

{wrapped_b}

Analyze the relationship between these two clauses and respond with the JSON schema specified in your instructions."""

    return system, user_prompt


def estimate_prompt_tokens(system_prompt: str, user_prompt: str) -> int:
    """Estimate token count for a prompt using character-based approximation.

    Uses the rough heuristic of 1 token ≈ 4 characters, which is
    a reasonable approximation for English text with the Gemini tokenizer.

    Args:
        system_prompt: The system prompt text.
        user_prompt: The user prompt text.

    Returns:
        Estimated token count.
    """
    total_chars = len(system_prompt) + len(user_prompt)
    return total_chars // 4
