"""Unit tests for clause segmentation."""
from __future__ import annotations

import pytest

from backend.parsing.extractor import ExtractedDocument, PageText
from backend.parsing.segmenter import detect_section_header, segment_clauses


@pytest.mark.unit
def test_segment_clauses_produces_clauses() -> None:
    text = (
        "SECTION 1 - TERMINATION\n\n"
        "1.1 Either party may terminate this agreement upon thirty days written notice to the other party.\n\n"
        "1.2 Upon termination, all fees shall become immediately due and payable to the provider.\n"
    )
    pages = [PageText(page_number=1, text=text)]
    doc = ExtractedDocument(
        pages=pages,
        page_count=1,
        total_chars=len(text),
        filename="test.pdf",
    )
    clauses = segment_clauses(doc, "doc123")
    assert len(clauses) >= 1
    assert clauses[0].document_id == "doc123"
    assert clauses[0].page == 1


@pytest.mark.unit
def test_section_header_detection() -> None:
    assert detect_section_header("SECTION 1 - TERM") is not None
    assert detect_section_header("1.1 Termination.") is not None
    assert detect_section_header("ARTICLE IV") is not None
    assert detect_section_header("regular paragraph text with no header pattern") is None


@pytest.mark.unit
def test_minimum_clause_length_filter() -> None:
    text = "Short.\n\nVery short sentence.\n\nThis is a long enough clause sentence that contains sufficient text for processing."
    pages = [PageText(page_number=1, text=text)]
    doc = ExtractedDocument(pages=pages, page_count=1, total_chars=len(text), filename="t.txt")
    clauses = segment_clauses(doc, "doc1")
    for c in clauses:
        assert len(c.text) >= 20


@pytest.mark.unit
def test_clause_id_format() -> None:
    text = "SECTION 1 - GOVERNING LAW\n\nThis agreement shall be governed by the laws of the State of New York."
    pages = [PageText(page_number=1, text=text)]
    doc = ExtractedDocument(pages=pages, page_count=1, total_chars=len(text), filename="t.pdf")
    clauses = segment_clauses(doc, "doc1")
    assert len(clauses) > 0
    assert clauses[0].clause_id.startswith("doc1_1_")


@pytest.mark.unit
def test_metadata_populated() -> None:
    text = "SECTION 2 - PAYMENT\n\nClient Acme Corp shall pay $50,000 USD to Provider on 2024-06-01 under this payment schedule."
    pages = [PageText(page_number=1, text=text)]
    doc = ExtractedDocument(pages=pages, page_count=1, total_chars=len(text), filename="t.pdf")
    clauses = segment_clauses(doc, "doc1")
    assert len(clauses) > 0
    c = clauses[0]
    assert len(c.topics) > 0
    assert len(c.monetary_values) > 0 or len(c.dates) > 0
