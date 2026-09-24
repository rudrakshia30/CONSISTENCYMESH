"""Unit tests for candidate pair scoring."""
from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.matching.scoring import CandidateScorer
from backend.models.schemas import Clause


def _make_clause(cid: str, doc_id: str, text: str, topics: list[str] = None) -> Clause:
    return Clause(
        clause_id=cid,
        document_id=doc_id,
        page=1,
        text=text,
        topics=topics or [],
    )


@pytest.mark.unit
def test_scorer_init() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    assert scorer is not None


@pytest.mark.unit
def test_build_index() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    c1 = _make_clause("c1", "d1", "Termination notice required")
    c2 = _make_clause("c2", "d2", "Payment due within thirty days")
    scorer.build_index([c1, c2])


@pytest.mark.unit
def test_score_pair() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    c1 = _make_clause("c1", "d1", "Termination of agreement upon 30 days notice", ["termination"])
    c2 = _make_clause("c2", "d2", "Either party may terminate upon 60 days notice", ["termination"])
    scorer.build_index([c1, c2])

    score = scorer.score_pair(c1, c2)
    assert isinstance(score, float)
    assert score >= 0.0


@pytest.mark.unit
def test_high_similarity() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    c1 = _make_clause("c1", "d1", "Termination for convenience with ninety days notice", ["termination", "notice"])
    c2 = _make_clause("c2", "d2", "Termination for convenience upon thirty days notice", ["termination", "notice"])
    scorer.build_index([c1, c2])

    score = scorer.score_pair(c1, c2)
    assert score > 0.2


@pytest.mark.unit
def test_filter_candidates() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    c1 = _make_clause("c1", "d1", "Termination notice required for agreement", ["termination"])
    c2 = _make_clause("c2", "d2", "Termination notice period is thirty days", ["termination"])
    c3 = _make_clause("c3", "d2", "Unrelated quantum computing hardware details", ["hardware"])

    scorer.build_index([c1, c2, c3])
    pairs = [(c1, c2), (c1, c3)]
    filtered = scorer.filter_candidates(pairs)

    # c1 and c2 should score higher than c1 and c3
    assert len(filtered) <= 2
    if len(filtered) > 0:
        assert filtered[0][0].clause_id == "c1"
        assert filtered[0][1].clause_id == "c2"


@pytest.mark.unit
def test_jaccard() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    set_a = {"a", "b", "c"}
    set_b = {"b", "c", "d"}
    # Intersection = {b, c} = 2, Union = {a, b, c, d} = 4 => 0.5
    j = scorer._jaccard(set_a, set_b)
    assert j == 0.5


@pytest.mark.unit
def test_empty_overlap() -> None:
    settings = Settings()
    scorer = CandidateScorer(settings)
    set_a = {"a"}
    set_b = {"b"}
    assert scorer._jaccard(set_a, set_b) == 0.0
    assert scorer._jaccard(set(), set()) == 0.0
