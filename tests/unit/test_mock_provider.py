"""Unit tests for MockProvider implementation."""
from __future__ import annotations

import pytest

from backend.models.schemas import Clause, Confidence, RelationshipType
from backend.providers.mock_provider import MockProvider


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


def _make_clause(cid: str, doc_id: str, text: str) -> Clause:
    return Clause(
        clause_id=cid,
        document_id=doc_id,
        page=1,
        text=text,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_termination_keyword_produces_conflict(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "Termination notice is required in 30 days.")
    c2 = _make_clause("c2", "d2", "Termination notice period is 90 days.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.CONFLICT
    assert judgment.confidence == Confidence.STATED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_payment_keyword_produces_consistent(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "Payment fee schedule is monthly.")
    c2 = _make_clause("c2", "d2", "All payment fees are due monthly.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.CONSISTENT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_amendment_override_keyword_produces_override(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "This amendment shall override section 1.")
    c2 = _make_clause("c2", "d2", "Standard terms apply unless amended.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.OVERRIDE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_short_texts_produces_unaddressed(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "Short text.")
    c2 = _make_clause("c2", "d2", "Also short.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.UNADDRESSED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unrelated_text_produces_ambiguous(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "Quantum mechanical properties of silicon chips.")
    c2 = _make_clause("c2", "d2", "Aerodynamic drag coefficients of specialized sports vehicles.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.AMBIGUOUS


@pytest.mark.unit
@pytest.mark.asyncio
async def test_answer_question_returns_valid_raw_answer(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "The contract term is thirty-six months.")
    ans = await provider.answer_question("What is the term?", [c1])
    assert "thirty-six months" in ans.answer
    assert len(ans.evidence) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_evidence_spans_reference_actual_input_clauses(provider: MockProvider) -> None:
    c1 = _make_clause("c1", "d1", "Notice must be in writing via certified mail.")
    c2 = _make_clause("c2", "d2", "Notice may be sent by overnight delivery.")
    judgment = await provider.analyze_consistency(c1, c2, {})
    assert len(judgment.evidence) == 2
    assert judgment.evidence[0].clause_id == "c1"
    assert judgment.evidence[1].clause_id == "c2"
