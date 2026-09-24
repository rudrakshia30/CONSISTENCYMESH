"""Integration tests for provider factory and mock provider."""
from __future__ import annotations

import pytest

from backend.models.schemas import Clause, Confidence, RelationshipType
from backend.providers.mock_provider import MockProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_provider_conflict() -> None:
    provider = MockProvider()
    c1 = Clause(
        clause_id="c1", document_id="d1", page=1, text="Termination notice is 30 days."
    )
    c2 = Clause(
        clause_id="c2", document_id="d2", page=1, text="Termination notice is 90 days."
    )

    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.CONFLICT
    assert judgment.confidence == Confidence.STATED
    assert len(judgment.evidence) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_provider_consistent() -> None:
    provider = MockProvider()
    c1 = Clause(
        clause_id="c1", document_id="d1", page=1, text="Payment is due in 30 days."
    )
    c2 = Clause(
        clause_id="c2", document_id="d2", page=1, text="Fee payment terms are net 30."
    )

    judgment = await provider.analyze_consistency(c1, c2, {})
    assert judgment.relationship_type == RelationshipType.CONSISTENT


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mock_provider_qa() -> None:
    provider = MockProvider()
    c1 = Clause(clause_id="c1", document_id="d1", page=1, text="The term is 36 months.")
    answer = await provider.answer_question("What is the term?", [c1])
    assert "36 months" in answer.answer
    assert len(answer.evidence) == 1
