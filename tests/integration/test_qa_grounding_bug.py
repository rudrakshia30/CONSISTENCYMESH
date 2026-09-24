"""Regression and integration tests for query intent extraction, staged hybrid retrieval, and grounding logic.

Verifies that cross-clause questions retrieve topic-matched clauses and exclude
irrelevant clauses matching generic stop words.
"""

from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.matching.retrieval import retrieve_relevant_clauses
from backend.models.schemas import Clause, Confidence, RelationshipType
from backend.parsing.intent import extract_query_intent
from backend.parsing.metadata import extract_numeric_attributes
from backend.providers.mock_provider import MockProvider
from backend.services.qa_service import QAService
from backend.state.local_store import LocalStateStore


def _make_clause(cid: str, doc_id: str, text: str, section: str | None = None) -> Clause:
    from backend.parsing.metadata import extract_metadata
    meta = extract_metadata(text)
    return Clause(
        clause_id=cid,
        document_id=doc_id,
        page=1,
        section=section,
        text=text,
        entities=meta.entities,
        dates=meta.dates,
        monetary_values=meta.monetary_values,
        topics=meta.topics,
        numeric_attributes=meta.numeric_attributes,
    )


@pytest.mark.integration
def test_query_intent_extraction_generalization() -> None:
    # 1. Termination query
    intent1 = extract_query_intent("What are the conflicting termination periods in this document?")
    assert intent1.topic == "termination"
    assert intent1.has_comparison_intent is True

    # 2. Payment query
    intent2 = extract_query_intent("What payment deadlines conflict?")
    assert intent2.topic == "payment"
    assert intent2.has_comparison_intent is True

    # 3. Renewal query
    intent3 = extract_query_intent("What are the different renewal periods?")
    assert intent3.topic == "term_duration"
    assert intent3.has_comparison_intent is True

    # 4. Retention query
    intent4 = extract_query_intent("Which documents contain inconsistent retention periods?")
    assert intent4.topic == "term_duration"
    assert intent4.has_comparison_intent is True

    # 5. Liability limit query
    intent5 = extract_query_intent("Are the liability limits consistent?")
    assert intent5.topic == "liability"
    assert intent5.has_comparison_intent is True


@pytest.mark.integration
def test_retrieval_excludes_payment_clause_for_termination_query() -> None:
    # Exact bug scenario setup
    c_term1 = _make_clause("c1", "docA", "1.1 Either party may terminate this agreement upon ninety (90) days written notice.", section="SECTION 1 - TERMINATION")
    c_term2 = _make_clause("c2", "docB", "5.1 This Agreement may be terminated by either party giving thirty (30) days notice.", section="SECTION 5 - TERMINATION")
    c_payment = _make_clause("c3", "docB", "3.1 Payment Terms — Invoices under this SOW are due fifteen (15) days after receipt.", section="SECTION 3 - PAYMENT")

    clauses = [c_term1, c_term2, c_payment]
    query = "What are the conflicting termination periods in this document?"

    intent, retrieved = retrieve_relevant_clauses(query, clauses, top_k=10, min_threshold=0.25)
    retrieved_clause_ids = [c.clause_id for c, score in retrieved]

    # Verify termination clauses are retrieved
    assert "c1" in retrieved_clause_ids
    assert "c2" in retrieved_clause_ids

    # Verify payment clause is EXCLUDED from retrieved candidates
    assert "c3" not in retrieved_clause_ids

    # Verify numeric values extracted
    nums_1 = extract_numeric_attributes(c_term1.text)
    nums_2 = extract_numeric_attributes(c_term2.text)
    assert any(n.value == 90.0 for n in nums_1)
    assert any(n.value == 30.0 for n in nums_2)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qa_service_exact_bug_fix() -> None:
    store = LocalStateStore()
    settings = Settings()
    provider = MockProvider()
    service = QAService(provider, store, settings)

    c_term1 = _make_clause("c1", "docA", "1.1 Either party may terminate this agreement upon ninety (90) days written notice.", section="SECTION 1 - TERMINATION")
    c_term2 = _make_clause("c2", "docB", "5.1 This Agreement may be terminated by either party giving thirty (30) days notice.", section="SECTION 5 - TERMINATION")
    c_payment = _make_clause("c3", "docB", "3.1 Payment Terms — Invoices under this SOW are due fifteen (15) days after receipt.", section="SECTION 3 - PAYMENT")

    # Store job and clauses
    job_id = "job_bug_test"
    session_id = "s_test"
    await store.set(f"session:{session_id}:job:{job_id}", True)
    await store.set(f"job:{job_id}:data", {"document_ids": ["docA", "docB"]})
    await store.set("doc:docA:clauses", [c_term1.model_dump(mode="json")])
    await store.set("doc:docB:clauses", [c_term2.model_dump(mode="json"), c_payment.model_dump(mode="json")])

    query = "What are the conflicting termination periods in this document?"
    resp = await service.answer_question(job_id, query, session_id)

    # Assert primary evidence excludes payment clause c3
    evidence_ids = [e.clause_id for e in resp.evidence]
    assert "c3" not in evidence_ids
    assert len(resp.evidence) == 2
    assert "c1" in evidence_ids
    assert "c2" in evidence_ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qa_service_insufficient_evidence_when_single_clause() -> None:
    store = LocalStateStore()
    settings = Settings()
    provider = MockProvider()
    service = QAService(provider, store, settings)

    c_term1 = _make_clause("c1", "docA", "1.1 Either party may terminate upon ninety (90) days written notice.", section="SECTION 1 - TERMINATION")
    c_payment = _make_clause("c2", "docA", "3.1 Payment is due fifteen (15) days after receipt.", section="SECTION 3 - PAYMENT")

    job_id = "job_single_clause"
    session_id = "s_test"
    await store.set(f"session:{session_id}:job:{job_id}", True)
    await store.set(f"job:{job_id}:data", {"document_ids": ["docA"]})
    await store.set("doc:docA:clauses", [c_term1.model_dump(mode="json"), c_payment.model_dump(mode="json")])

    query = "What are the conflicting termination periods?"
    resp = await service.answer_question(job_id, query, session_id)

    # Must NOT hallucinate or answer from 1 clause
    assert "couldn't find enough relevant evidence" in resp.answer or "Insufficient" in resp.answer
    assert resp.confidence == Confidence.NOT_ESTABLISHED
    assert len(resp.evidence) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_qa_service_conflicting_payment_terms() -> None:
    store = LocalStateStore()
    settings = Settings()
    provider = MockProvider()
    service = QAService(provider, store, settings)

    c1 = _make_clause("c1", "docA", "Invoices are due net 30 days.", section="SECTION 2 - PAYMENT")
    c2 = _make_clause("c2", "docB", "Invoices are due net 60 days.", section="SECTION 4 - PAYMENT")

    job_id = "job_payment_test"
    session_id = "s_test"
    await store.set(f"session:{session_id}:job:{job_id}", True)
    await store.set(f"job:{job_id}:data", {"document_ids": ["docA", "docB"]})
    await store.set("doc:docA:clauses", [c1.model_dump(mode="json")])
    await store.set("doc:docB:clauses", [c2.model_dump(mode="json")])

    query = "What payment deadlines conflict?"
    resp = await service.answer_question(job_id, query, session_id)

    evidence_ids = [e.clause_id for e in resp.evidence]
    assert "c1" in evidence_ids
    assert "c2" in evidence_ids
