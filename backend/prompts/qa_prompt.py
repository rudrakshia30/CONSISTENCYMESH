"""
Prompt template for follow-up Q&A over analyzed documents.

Defines the structured prompt for answering user questions grounded
in specific clauses from the analyzed document set.
"""

from __future__ import annotations

from backend.models.schemas import Clause
from backend.security.prompt_guard import (
    build_isolation_instruction,
    generate_nonce,
    wrap_document_content,
)

QA_PROMPT_VERSION = "qa_v1.0"

QA_SYSTEM_PROMPT = """You are a legal document analysis assistant answering follow-up questions about a set of analyzed documents.

CRITICAL RULES:
1. Base your answer ONLY on the provided clause excerpts — never invent information
2. Assign confidence as one of: STATED, INTERPRETED, NOT_ESTABLISHED
3. Provide evidence spans that are EXACT quotes from the provided clauses
4. Use descriptive language: "The documents state...", "Based on the provided clauses..."
5. NEVER claim to be a lawyer or that a provision is legally enforceable
6. If the question cannot be answered from the provided clauses, say so clearly and use NOT_ESTABLISHED confidence
7. NEVER fabricate legal rules or interpretations

{isolation_instruction}

Respond with ONLY a JSON object matching this exact schema:
{{
    "answer": "Your grounded answer to the question",
    "confidence": "STATED|INTERPRETED|NOT_ESTABLISHED",
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

Do NOT include any text outside the JSON object."""


def build_qa_prompt(
    question: str,
    clauses: list[Clause],
    context: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Build the system and user prompts for a follow-up question.

    Wraps all clause content in nonce-delimited blocks and provides
    the question with relevant clause context.

    Args:
        question: The user's follow-up question.
        clauses: Relevant clauses retrieved for grounding the answer.
        context: Optional additional context (document names, etc.).

    Returns:
        Tuple of (system_prompt, user_prompt) strings.
    """
    nonce = generate_nonce()

    system = QA_SYSTEM_PROMPT.format(
        isolation_instruction=build_isolation_instruction(nonce),
    )

    clause_sections: list[str] = []
    for i, clause in enumerate(clauses):
        doc_label = f"DOC_{clause.document_id[:8]}"
        wrapped = wrap_document_content(clause.text, doc_label, nonce)
        clause_section = f"""Clause {i + 1}:
- Document ID: {clause.document_id}
- Clause ID: {clause.clause_id}
- Page: {clause.page}
- Section: {clause.section or 'Not specified'}
- Topics: {', '.join(clause.topics) if clause.topics else 'None detected'}

{wrapped}"""
        clause_sections.append(clause_section)

    clauses_text = "\n\n---\n\n".join(clause_sections)

    user_prompt = f"""Answer the following question based ONLY on the provided clause excerpts:

QUESTION: {question}

RELEVANT CLAUSES:

{clauses_text}

Answer the question using only the information in the clauses above. Respond with the JSON schema specified in your instructions."""

    return system, user_prompt
