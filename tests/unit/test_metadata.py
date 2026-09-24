"""Unit tests for deterministic metadata extraction."""
from __future__ import annotations

import pytest

from backend.parsing.metadata import (
    extract_dates,
    extract_entities,
    extract_metadata,
    extract_monetary_values,
    extract_topics,
)


@pytest.mark.unit
def test_extract_entities_company_names() -> None:
    text = "Agreement between Acme Corporation and TechStar Solutions Inc."
    entities = extract_entities(text)
    assert any("Acme" in e for e in entities)
    assert any("TechStar" in e for e in entities)


@pytest.mark.unit
def test_extract_dates() -> None:
    text = "Effective Date: 2024-01-15. Notice required by January 1, 2024."
    dates = extract_dates(text)
    assert len(dates) >= 1
    assert any("2024" in d for d in dates)


@pytest.mark.unit
def test_extract_monetary_values() -> None:
    text = "The total fee is $450,000 USD, payable in installments."
    values = extract_monetary_values(text)
    assert len(values) >= 1
    assert any("450,000" in v or "USD" in v for v in values)


@pytest.mark.unit
def test_extract_topics() -> None:
    text = "Either party may terminate this agreement upon notice. Payment is due in 30 days."
    topics = extract_topics(text)
    assert "termination" in topics
    assert "payment" in topics or "notice" in topics


@pytest.mark.unit
def test_extract_metadata_full() -> None:
    text = "Acme Corp shall pay $10,000 on 2024-05-01 for software licenses under this Agreement."
    res = extract_metadata(text)
    assert len(res.entities) >= 1
    assert len(res.dates) >= 1
    assert len(res.monetary_values) >= 1
    assert len(res.topics) >= 1


@pytest.mark.unit
def test_extract_metadata_empty() -> None:
    res = extract_metadata("")
    assert res.entities == []
    assert res.dates == []
    assert res.monetary_values == []
    assert res.topics == []
