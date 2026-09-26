"""Unit tests for Pydantic data models."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    AnalysisRequest,
    Clause,
    Confidence,
    ConsistencyEdge,
    ConsistencyGraph,
    Document,
    EvidenceSpan,
    Finding,
    JobState,
    QARequest,
    RawAnswer,
    RawEvidenceSpan,
    RawJudgment,
    RelationshipType,
    UploadResponse,
)


@pytest.mark.unit
def test_document_creation_serialization() -> None:
    doc = Document(
        document_id="doc-123",
        filename="test.pdf",
        page_count=5,
    )
    assert doc.document_id == "doc-123"
    assert doc.filename == "test.pdf"
    assert doc.page_count == 5
    data = doc.model_dump(mode="json")
    assert data["document_id"] == "doc-123"


@pytest.mark.unit
def test_clause_creation() -> None:
    clause = Clause(
        clause_id="c-1",
        document_id="doc-1",
        page=1,
        section="Section 1",
        text="This is a test clause.",
        entities=["Acme"],
        dates=["2024-01-01"],
        monetary_values=["$100"],
        topics=["payment"],
    )
    assert clause.clause_id == "c-1"
    assert clause.entities == ["Acme"]


@pytest.mark.unit
def test_evidence_span() -> None:
    span = EvidenceSpan(
        document_id="doc-1",
        clause_id="c-1",
        page=1,
        text_span="test clause",
    )
    assert span.document_id == "doc-1"
    assert span.text_span == "test clause"


@pytest.mark.unit
def test_finding_min_evidence() -> None:
    span = EvidenceSpan(
        document_id="doc-1", clause_id="c-1", page=1, text_span="test"
    )
    finding = Finding(
        finding_id="f-1",
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.STATED,
        explanation="Conflict found",
        evidence=[span],
        validated=True,
    )
    assert finding.finding_id == "f-1"
    assert len(finding.evidence) == 1

    finding_empty = Finding(
        finding_id="f-2",
        relationship_type=RelationshipType.CONFLICT,
        confidence=Confidence.NOT_ESTABLISHED,
        explanation="Conflict found but citation validation failed",
        evidence=[],
        validated=False,
    )
    assert len(finding_empty.evidence) == 0


@pytest.mark.unit
def test_enum_values_confidence() -> None:
    assert Confidence.STATED.value == "STATED"
    assert Confidence.INTERPRETED.value == "INTERPRETED"
    assert Confidence.NOT_ESTABLISHED.value == "NOT_ESTABLISHED"


@pytest.mark.unit
def test_enum_values_relationship() -> None:
    assert RelationshipType.CONSISTENT.value == "CONSISTENT"
    assert RelationshipType.CONFLICT.value == "CONFLICT"
    assert RelationshipType.OVERRIDE.value == "OVERRIDE"
    assert RelationshipType.AMBIGUOUS.value == "AMBIGUOUS"
    assert RelationshipType.UNADDRESSED.value == "UNADDRESSED"


@pytest.mark.unit
def test_enum_values_jobstate() -> None:
    assert JobState.QUEUED.value == "QUEUED"
    assert JobState.COMPLETE.value == "COMPLETE"
    assert JobState.FAILED.value == "FAILED"


@pytest.mark.unit
def test_raw_judgment_valid() -> None:
    raw = RawJudgment(
        relationship_type=RelationshipType.OVERRIDE,
        confidence=Confidence.STATED,
        explanation="Override clause",
        evidence=[
            RawEvidenceSpan(
                document_id="d1", clause_id="c1", page=1, text_span="span1"
            )
        ],
    )
    assert raw.relationship_type == RelationshipType.OVERRIDE


@pytest.mark.unit
def test_raw_answer_validation() -> None:
    answer = RawAnswer(
        answer="The term is 3 years.",
        confidence=Confidence.STATED,
        evidence=[
            RawEvidenceSpan(
                document_id="d1", clause_id="c1", page=1, text_span="3 years"
            )
        ],
    )
    assert answer.answer == "The term is 3 years."


@pytest.mark.unit
def test_analysis_request_min_max_docs() -> None:
    req = AnalysisRequest(document_ids=["doc1", "doc2"], session_id="s1")
    assert len(req.document_ids) == 2

    with pytest.raises(ValidationError):
        AnalysisRequest(document_ids=["doc1"], session_id="s1")

    with pytest.raises(ValidationError):
        AnalysisRequest(
            document_ids=["d1", "d2", "d3", "d4", "d5", "d6", "d7"],
            session_id="s1",
        )


@pytest.mark.unit
def test_upload_response_serialization() -> None:
    resp = UploadResponse(
        document_id="doc-1",
        filename="test.pdf",
        page_count=2,
        clause_count=10,
    )
    assert resp.clause_count == 10


@pytest.mark.unit
def test_qa_request_min_max_length() -> None:
    req = QARequest(job_id="job-1", question="What is the term?", session_id="s1")
    assert req.question == "What is the term?"

    with pytest.raises(ValidationError):
        QARequest(job_id="job-1", question="", session_id="s1")


@pytest.mark.unit
def test_consistency_graph_and_edge() -> None:
    edge = ConsistencyEdge(
        source_clause_id="c1",
        target_clause_id="c2",
        finding_id="f1",
        relationship_type=RelationshipType.CONSISTENT,
    )
    graph = ConsistencyGraph(
        nodes=["c1", "c2"], document_nodes=["d1", "d2"], edges=[edge]
    )
    assert len(graph.edges) == 1
    assert graph.nodes == ["c1", "c2"]
