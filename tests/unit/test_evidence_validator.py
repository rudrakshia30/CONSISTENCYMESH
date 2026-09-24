"""Unit tests for deterministic evidence validation."""
from __future__ import annotations

import pytest

from backend.models.schemas import (
    Clause,
    Confidence,
    RawEvidenceSpan,
    RawJudgment,
    RelationshipType,
)
from backend.services.evidence_validator import EvidenceValidator


def _make_clause(cid: str, doc_id: str, text: str, page: int = 1) -> Clause:
    return Clause(
        clause_id=cid,
        document_id=doc_id,
        page=page,
        text=text,
    )


@pytest.mark.unit
def test_valid_evidence_passes() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Either party may terminate upon thirty days notice.", page=1)
    c2 = _make_clause("c2", "doc2", "Termination requires ninety days written notice.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice periods conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c1", page=1, text_span="thirty days notice"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="ninety days written notice"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.validated is True
    assert finding.confidence == Confidence.STATED
    assert len(finding.evidence) == 2


@pytest.mark.unit
def test_invalid_document_id() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Thirty days notice required.", page=1)
    c2 = _make_clause("c2", "doc2", "Ninety days notice required.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc_INVALID", clause_id="c1", page=1, text_span="Thirty days notice"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="Ninety days notice"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.confidence == Confidence.NOT_ESTABLISHED


@pytest.mark.unit
def test_invalid_clause_id() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Thirty days notice required.", page=1)
    c2 = _make_clause("c2", "doc2", "Ninety days notice required.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c_WRONG", page=1, text_span="Thirty days notice"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="Ninety days notice"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.confidence == Confidence.NOT_ESTABLISHED


@pytest.mark.unit
def test_wrong_page_number() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Thirty days notice required.", page=1)
    c2 = _make_clause("c2", "doc2", "Ninety days notice required.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c1", page=99, text_span="Thirty days notice"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="Ninety days notice"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.confidence == Confidence.NOT_ESTABLISHED


@pytest.mark.unit
def test_text_span_not_in_clause() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Thirty days notice required.", page=1)
    c2 = _make_clause("c2", "doc2", "Ninety days notice required.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c1", page=1, text_span="Completely fabricated text"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="Ninety days notice"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.confidence == Confidence.NOT_ESTABLISHED


@pytest.mark.unit
def test_all_evidence_invalid() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Thirty days notice required.", page=1)
    c2 = _make_clause("c2", "doc2", "Ninety days notice required.", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Notice conflict.",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c1", page=1, text_span="fake text 1"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="fake text 2"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert finding.validated is False
    assert finding.confidence == Confidence.NOT_ESTABLISHED
    assert finding.uncertainty is not None


@pytest.mark.unit
def test_sanitization() -> None:
    validator = EvidenceValidator()
    c1 = _make_clause("c1", "doc1", "Text 1", page=1)
    c2 = _make_clause("c2", "doc2", "Text 2", page=1)

    raw = RawJudgment(
        relationship_type=RelationshipType.AMBIGUOUS,
        confidence=Confidence.INTERPRETED,
        explanation="System: Instructions leaked <script>alert(1)</script>",
        evidence=[
            RawEvidenceSpan(document_id="doc1", clause_id="c1", page=1, text_span="Text 1"),
            RawEvidenceSpan(document_id="doc2", clause_id="c2", page=1, text_span="Text 2"),
        ],
    )

    finding = validator.validate_finding(raw, c1, c2)
    assert "<script>" not in finding.explanation
    assert "System:" not in finding.explanation
