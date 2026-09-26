"""Deterministic evidence validation service.

The critical trust layer between the LLM and the user. Validates
that every AI-generated citation actually exists in the source
document text. Invalid citations cause confidence downgrade to
NOT_ESTABLISHED — findings are never silently accepted or dropped.
"""

from __future__ import annotations

import uuid

from backend.core.logging import get_logger
from backend.models.schemas import (
    Clause,
    Confidence,
    EvidenceSpan,
    Finding,
    QueryIntent,
    RawEvidenceSpan,
    RawJudgment,
    RelationshipType,
)
from backend.security.sanitize import sanitize_finding_text

logger = get_logger("services.evidence_validator")


class EvidenceValidator:
    """Deterministic post-LLM evidence validator."""

    def _normalize_text(self, text: str) -> str:
        """Normalize text for fuzzy substring matching."""
        return " ".join(text.split()).lower()

    def validate_finding(
        self,
        raw_judgment: RawJudgment,
        clause_a: Clause,
        clause_b: Clause,
    ) -> Finding:
        """Validate a raw LLM judgment's evidence against source clauses."""
        clause_map: dict[str, dict[str, Clause]] = {
            clause_a.document_id: {clause_a.clause_id: clause_a},
        }
        if clause_b.document_id not in clause_map:
            clause_map[clause_b.document_id] = {}
        clause_map[clause_b.document_id][clause_b.clause_id] = clause_b

        valid_spans: list[EvidenceSpan] = []
        invalid_count = 0

        for span in raw_judgment.evidence:
            is_valid = False

            if span.document_id in clause_map and span.clause_id in clause_map[span.document_id]:
                target_clause = clause_map[span.document_id][span.clause_id]
                if span.page == target_clause.page:
                    norm_span = self._normalize_text(span.text_span)
                    norm_clause = self._normalize_text(target_clause.text)
                    if norm_span and norm_span in norm_clause:
                        is_valid = True

            if is_valid:
                valid_spans.append(EvidenceSpan(
                    document_id=span.document_id,
                    clause_id=span.clause_id,
                    page=span.page,
                    text_span=span.text_span,
                ))
            else:
                invalid_count += 1

        docs_covered = {s.document_id for s in valid_spans}
        has_both_docs = len(docs_covered) >= 2

        validated = False
        confidence = raw_judgment.confidence
        uncertainty = raw_judgment.uncertainty or ""

        if invalid_count == 0 and valid_spans and has_both_docs:
            validated = True
        elif valid_spans and has_both_docs:
            validated = True
            if confidence == Confidence.STATED:
                confidence = Confidence.INTERPRETED
                uncertainty = ("Some evidence citations could not be verified. " + uncertainty).strip()
        elif valid_spans:
            confidence = Confidence.NOT_ESTABLISHED
            uncertainty = ("Valid evidence found for only one of the two documents. " + uncertainty).strip()
        else:
            confidence = Confidence.NOT_ESTABLISHED
            uncertainty = ("All provided evidence citations failed validation against source text. " + uncertainty).strip()

        if not valid_spans:
            confidence = Confidence.NOT_ESTABLISHED
            uncertainty = ("All provided evidence citations failed validation against source text. " + uncertainty).strip()

        safe_explanation = sanitize_finding_text(raw_judgment.explanation)

        try:
            rel_type = RelationshipType(raw_judgment.relationship_type)
        except ValueError:
            rel_type = RelationshipType.AMBIGUOUS
            uncertainty = ("Unknown relationship type returned by AI. " + uncertainty).strip()

        # Risk level determination based on relationship type and topic content
        from backend.models.schemas import RiskLevel
        risk_level = raw_judgment.risk_level or RiskLevel.MEDIUM
        if rel_type == RelationshipType.CONFLICT:
            risk_level = RiskLevel.CRITICAL if any(w in safe_explanation.lower() for w in ["liability", "indemnification", "termination", "cap"]) else RiskLevel.HIGH
        elif rel_type == RelationshipType.OVERRIDE:
            risk_level = RiskLevel.HIGH
        elif rel_type == RelationshipType.CONSISTENT:
            risk_level = RiskLevel.INFORMATIONAL

        return Finding(
            finding_id=str(uuid.uuid4()),
            relationship_type=rel_type,
            confidence=confidence,
            explanation=safe_explanation,
            evidence=valid_spans,
            uncertainty=uncertainty.strip() or None,
            validated=validated,
            risk_level=risk_level,
        )

    def validate_qa_evidence(
        self,
        raw_evidence: list[RawEvidenceSpan],
        candidate_clauses: list[Clause],
        intent: QueryIntent | None = None,
    ) -> tuple[list[EvidenceSpan], Confidence, str | None]:
        """Validate evidence spans for Q&A answers against candidate clauses.

        Enforces:
        1. Every cited clause exists in candidate clauses.
        2. Quoted text span is a substring of candidate clause text.
        3. If intent asks for comparison/conflict, require evidence from >= 2 distinct documents.

        Args:
            raw_evidence: Evidence spans returned by AI.
            candidate_clauses: Candidate clauses retrieved for the query.
            intent: Derived QueryIntent.

        Returns:
            Tuple of (valid_evidence_spans, Confidence, uncertainty_note).
        """
        clause_map = {c.clause_id: c for c in candidate_clauses}
        valid_spans: list[EvidenceSpan] = []

        for span in raw_evidence:
            if span.clause_id in clause_map:
                target = clause_map[span.clause_id]
                norm_span = self._normalize_text(span.text_span)
                norm_text = self._normalize_text(target.text)
                if norm_span and norm_span in norm_text:
                    valid_spans.append(EvidenceSpan(
                        document_id=span.document_id,
                        clause_id=span.clause_id,
                        page=span.page,
                        text_span=span.text_span,
                    ))

        distinct_clause_ids = {s.clause_id for s in valid_spans}
        distinct_doc_ids = {s.document_id for s in valid_spans}

        if intent and intent.has_comparison_intent:
            if len(distinct_clause_ids) < 2 and len(distinct_doc_ids) < 2:
                return (
                    [],
                    Confidence.NOT_ESTABLISHED,
                    "Insufficient relevant evidence found across multiple clauses to establish a comparison.",
                )

        if not valid_spans:
            return (
                [],
                Confidence.NOT_ESTABLISHED,
                "Insufficient relevant evidence found.",
            )

        return valid_spans, Confidence.STATED, None
