"""Unit tests for candidate pair generation."""
from __future__ import annotations

import pytest

from backend.matching.candidate_generator import count_naive_pairs, generate_candidate_pairs
from backend.models.schemas import Clause


def _make_clause(cid: str, doc_id: str, text: str) -> Clause:
    return Clause(
        clause_id=cid,
        document_id=doc_id,
        page=1,
        text=text,
    )


@pytest.mark.unit
def test_generates_only_cross_document_pairs() -> None:
    c1 = _make_clause("c1", "doc1", "Text 1")
    c2 = _make_clause("c2", "doc2", "Text 2")
    clauses_by_doc = {"doc1": [c1], "doc2": [c2]}

    pairs = generate_candidate_pairs(clauses_by_doc)
    assert len(pairs) == 1
    assert pairs[0][0].document_id != pairs[0][1].document_id


@pytest.mark.unit
def test_count_naive_pairs() -> None:
    c1 = _make_clause("c1", "doc1", "Text 1")
    c2 = _make_clause("c2", "doc1", "Text 2")
    c3 = _make_clause("c3", "doc2", "Text 3")
    c4 = _make_clause("c4", "doc2", "Text 4")
    clauses_by_doc = {"doc1": [c1, c2], "doc2": [c3, c4]}

    count = count_naive_pairs(clauses_by_doc)
    pairs = generate_candidate_pairs(clauses_by_doc)
    assert count == 4
    assert len(pairs) == 4


@pytest.mark.unit
def test_no_same_document_pairs() -> None:
    c1 = _make_clause("c1", "doc1", "Text 1")
    c2 = _make_clause("c2", "doc1", "Text 2")
    clauses_by_doc = {"doc1": [c1, c2]}

    pairs = generate_candidate_pairs(clauses_by_doc)
    assert len(pairs) == 0


@pytest.mark.unit
def test_empty_input() -> None:
    assert count_naive_pairs({}) == 0
    assert generate_candidate_pairs({}) == []


@pytest.mark.unit
def test_single_document() -> None:
    c1 = _make_clause("c1", "doc1", "Text 1")
    clauses_by_doc = {"doc1": [c1]}
    assert count_naive_pairs(clauses_by_doc) == 0
    assert generate_candidate_pairs(clauses_by_doc) == []


@pytest.mark.unit
def test_pair_count_formula() -> None:
    # 3 docs with 2, 3, 4 clauses
    # Cross doc pairs = (2*3) + (2*4) + (3*4) = 6 + 8 + 12 = 26
    c_doc1 = [_make_clause(f"1_{i}", "d1", "t") for i in range(2)]
    c_doc2 = [_make_clause(f"2_{i}", "d2", "t") for i in range(3)]
    c_doc3 = [_make_clause(f"3_{i}", "d3", "t") for i in range(4)]
    clauses_by_doc = {"d1": c_doc1, "d2": c_doc2, "d3": c_doc3}

    assert count_naive_pairs(clauses_by_doc) == 26
    assert len(generate_candidate_pairs(clauses_by_doc)) == 26
