"""
Deterministic mock LLM provider for testing.

Returns predictable, deterministic results based on clause content.
No network calls. Used as the default provider in tests and when
no API key is configured.
"""

from __future__ import annotations

from backend.models.schemas import (
    Clause,
    Confidence,
    RawAnswer,
    RawEvidenceSpan,
    RawJudgment,
    RelationshipType,
)
from backend.providers.base import LLMProvider


class MockProvider(LLMProvider):
    """Deterministic mock provider for testing.

    Returns predictable results based on clause text content:
    - Both mention 'termination'/'notice' -> CONFLICT
    - Both mention 'payment'/'fee' -> CONSISTENT
    - One mentions 'amendment'/'supersede'/'override' -> OVERRIDE
    - Both texts < 20 chars -> UNADDRESSED
    - Otherwise -> AMBIGUOUS

    No network calls are ever made.
    """

    async def analyze_consistency(
        self, clause_a: Clause, clause_b: Clause, context: dict[str, str]
    ) -> RawJudgment:
        """Analyze clause pair deterministically based on keyword matching.

        Args:
            clause_a: First clause for comparison.
            clause_b: Second clause for comparison.
            context: Additional context (ignored by mock).

        Returns:
            Deterministic RawJudgment based on clause content.
        """
        text_a = clause_a.text.lower()
        text_b = clause_b.text.lower()

        def has_words(text: str, words: list[str]) -> bool:
            return any(w in text for w in words)

        rel_type = RelationshipType.AMBIGUOUS
        confidence = Confidence.INTERPRETED
        explanation = "The relationship between these clauses is unclear."

        if len(text_a) < 20 and len(text_b) < 20:
            rel_type = RelationshipType.UNADDRESSED
            confidence = Confidence.NOT_ESTABLISHED
            explanation = "Both clause texts are too brief to establish a relationship."
        elif has_words(text_a, ["termination", "notice"]) and has_words(
            text_b, ["termination", "notice"]
        ):
            rel_type = RelationshipType.CONFLICT
            confidence = Confidence.STATED
            explanation = (
                "The documents specify different requirements regarding "
                "termination or notice provisions."
            )
        elif has_words(text_a, ["payment", "fee"]) and has_words(
            text_b, ["payment", "fee"]
        ):
            rel_type = RelationshipType.CONSISTENT
            confidence = Confidence.STATED
            explanation = (
                "Both clauses address payment or fee provisions "
                "and appear consistent with each other."
            )
        elif has_words(text_a, ["amendment", "supersede", "override"]) or has_words(
            text_b, ["amendment", "supersede", "override"]
        ):
            rel_type = RelationshipType.OVERRIDE
            confidence = Confidence.STATED
            explanation = (
                "One clause appears to amend or supersede the other."
            )

        evidence = [
            RawEvidenceSpan(
                document_id=clause_a.document_id,
                clause_id=clause_a.clause_id,
                page=clause_a.page,
                text_span=clause_a.text[:100],
            ),
            RawEvidenceSpan(
                document_id=clause_b.document_id,
                clause_id=clause_b.clause_id,
                page=clause_b.page,
                text_span=clause_b.text[:100],
            ),
        ]

        return RawJudgment(
            relationship_type=rel_type,
            confidence=confidence,
            explanation=explanation,
            evidence=evidence,
            uncertainty=None,
        )

    async def classify_candidate(
        self, clause_a: Clause, clause_b: Clause
    ) -> bool:
        """Always returns True — all candidates pass mock pre-check.

        Args:
            clause_a: First clause.
            clause_b: Second clause.

        Returns:
            Always True.
        """
        return True

    async def answer_question(
        self, question: str, clauses: list[Clause]
    ) -> RawAnswer:
        """Answer a question deterministically using the provided clauses.

        Args:
            question: The user's question.
            clauses: Relevant clauses to ground the answer.

        Returns:
            Deterministic answer referencing the provided clauses.
        """
        if not clauses:
            return RawAnswer(
                answer="No relevant clauses were provided to answer this question.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty="No clauses available.",
            )

        answer_text = (
            f"Based on the provided clauses, regarding '{question}': "
            + " ".join(c.text[:100] for c in clauses[:2])
        )

        evidence = [
            RawEvidenceSpan(
                document_id=c.document_id,
                clause_id=c.clause_id,
                page=c.page,
                text_span=c.text[:100],
            )
            for c in clauses[:2]
        ]

        return RawAnswer(
            answer=answer_text,
            confidence=Confidence.INTERPRETED,
            evidence=evidence,
            uncertainty=None,
        )
