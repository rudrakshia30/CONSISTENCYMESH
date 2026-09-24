"""
Pydantic data models for ConsistencyMesh.

Defines the complete type system for documents, clauses, findings,
jobs, and API request/response bodies. All AI-generated data must
conform to these schemas before use.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    """Three-way confidence tier for every AI-generated finding.

    STATED: Evidence directly and explicitly supports the finding.
    INTERPRETED: Evidence requires interpretation; the finding is plausible
        but not directly stated.
    NOT_ESTABLISHED: Evidence is insufficient, or citation validation failed.
    """

    STATED = "STATED"
    INTERPRETED = "INTERPRETED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class RelationshipType(str, Enum):
    """Fixed, closed taxonomy of inter-clause relationships.

    The AI may only choose from this set — no invented relationship types.

    CONSISTENT: The clauses are mutually compatible.
    CONFLICT: The clauses contain contradictory requirements or statements.
    OVERRIDE: One clause explicitly supersedes or amends the other.
    AMBIGUOUS: The relationship is unclear or could be read multiple ways.
    UNADDRESSED: A topic covered in one clause has no counterpart in the other.
    """

    CONSISTENT = "CONSISTENT"
    CONFLICT = "CONFLICT"
    OVERRIDE = "OVERRIDE"
    AMBIGUOUS = "AMBIGUOUS"
    UNADDRESSED = "UNADDRESSED"


class JobState(str, Enum):
    """Lifecycle states for an analysis job.

    Progresses sequentially from QUEUED through COMPLETE, or to FAILED
    if an unrecoverable error occurs at any stage.
    """

    QUEUED = "QUEUED"
    PARSING = "PARSING"
    INDEXING = "INDEXING"
    MATCHING = "MATCHING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Domain Models
# ---------------------------------------------------------------------------


class NumericAttribute(BaseModel):
    """Structured numerical or legal attribute extracted from text.

    Attributes:
        attribute: Attribute category (e.g., "notice_period", "payment_term", "duration", "cap").
        value: Numeric value (e.g., 90.0, 30.0, 15.0).
        unit: Unit of measurement (e.g., "days", "months", "years", "percent", "USD").
        raw_text: Original text fragment.
    """

    attribute: str
    value: float
    unit: str
    raw_text: str = ""


class QueryIntent(BaseModel):
    """Structured representation of query intent extracted prior to retrieval.

    Attributes:
        topic: Primary topic detected (e.g., "termination", "payment", "liability").
        subtopics: Secondary topics or aspects (e.g., ["notice_period"]).
        relationship: Detected relationship filter (e.g., "conflict", "override").
        entities: Specific entities mentioned in query.
        requested_attributes: Requested attributes or units (e.g., ["days", "notice"]).
        answer_type: Expected answer structure ("cross_clause_comparison", "lookup").
        has_comparison_intent: True if question asks for conflicts/differences/overrides.
    """

    topic: str | None = None
    subtopics: list[str] = Field(default_factory=list)
    relationship: str | None = None
    entities: list[str] = Field(default_factory=list)
    requested_attributes: list[str] = Field(default_factory=list)
    answer_type: str = "cross_clause_comparison"
    has_comparison_intent: bool = False


class Document(BaseModel):
    """A parsed document with provenance metadata.

    Attributes:
        document_id: Content-hash-derived unique identifier.
        filename: Original upload filename (sanitized).
        page_count: Number of pages extracted.
        uploaded_at: Timestamp when the document was uploaded.
    """

    document_id: str
    filename: str
    page_count: int
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Clause(BaseModel):
    """A segmented clause extracted from a document.

    Each clause carries page-level provenance and deterministically
    extracted metadata (entities, dates, monetary values, topics, numeric_attributes).

    Attributes:
        clause_id: Unique identifier for this clause.
        document_id: Parent document identifier.
        page: 1-indexed page number where this clause appears.
        section: Section heading if detected, None otherwise.
        text: The full text of the clause.
        entities: Named entities extracted from the clause text.
        dates: Date references found in the clause text.
        monetary_values: Monetary amounts found in the clause text.
        topics: Topic labels assigned to this clause.
        numeric_attributes: Structured numerical attributes (e.g. 90 days notice).
    """

    clause_id: str
    document_id: str
    page: int
    section: str | None = None
    text: str
    entities: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    monetary_values: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    numeric_attributes: list[NumericAttribute] = Field(default_factory=list)


class EvidenceSpan(BaseModel):
    """A citation pointing to a specific text span in a source document.

    Used to back every finding with verifiable evidence.

    Attributes:
        document_id: The document containing the cited text.
        clause_id: The clause within the document.
        page: Page number of the evidence.
        text_span: The exact quoted text serving as evidence.
    """

    document_id: str
    clause_id: str
    page: int
    text_span: str


class Finding(BaseModel):
    """A validated relationship finding between clauses in different documents.

    Every finding carries a relationship type, confidence tier, explanation,
    and validated evidence spans. The 'validated' flag is set by the
    EvidenceValidator, never by the LLM.

    Attributes:
        finding_id: Unique identifier for this finding.
        relationship_type: The type of relationship detected.
        confidence: Confidence tier for this finding.
        explanation: Human-readable explanation of the finding.
        evidence: List of evidence spans backing the finding (min 1).
        uncertainty: Explicit uncertainty note when confidence is NOT_ESTABLISHED.
        validated: Whether evidence has been deterministically validated.
    """

    finding_id: str
    relationship_type: RelationshipType
    confidence: Confidence
    explanation: str
    evidence: list[EvidenceSpan] = Field(min_length=1)
    uncertainty: str | None = None
    validated: bool = False


# ---------------------------------------------------------------------------
# LLM Response Schemas (what the AI returns, before post-processing)
# ---------------------------------------------------------------------------


class RawEvidenceSpan(BaseModel):
    """Evidence span as returned by the LLM, before validation.

    Attributes:
        document_id: Claimed source document.
        clause_id: Claimed source clause.
        page: Claimed page number.
        text_span: Claimed text excerpt.
    """

    document_id: str
    clause_id: str
    page: int
    text_span: str


class RawJudgment(BaseModel):
    """Structured judgment returned by the LLM for a clause pair.

    This schema is what the AI must produce; finding_id and validated
    are assigned after deterministic validation.

    Attributes:
        relationship_type: The detected relationship type.
        confidence: The AI's confidence assessment.
        explanation: Why this relationship was detected.
        evidence: Supporting evidence spans (claimed, not yet validated).
        uncertainty: Optional uncertainty note.
    """

    relationship_type: RelationshipType
    confidence: Confidence
    explanation: str
    evidence: list[RawEvidenceSpan] = Field(min_length=1)
    uncertainty: str | None = None


class RawAnswer(BaseModel):
    """Structured answer returned by the LLM for a follow-up question.

    Attributes:
        answer: The answer text.
        confidence: Confidence in the answer.
        evidence: Supporting evidence spans.
        uncertainty: Optional uncertainty note.
    """

    answer: str
    confidence: Confidence
    evidence: list[RawEvidenceSpan] = Field(default_factory=list)
    uncertainty: str | None = None


# ---------------------------------------------------------------------------
# API Request/Response Models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    """Response after successful document upload.

    Attributes:
        document_id: The assigned document identifier.
        filename: Original filename.
        page_count: Number of pages extracted.
        clause_count: Number of clauses segmented.
    """

    document_id: str
    filename: str
    page_count: int
    clause_count: int


class AnalysisRequest(BaseModel):
    """Request to create a new analysis job.

    Attributes:
        document_ids: List of 2-6 document IDs to analyze.
        session_id: Client session identifier for isolation.
    """

    document_ids: list[str] = Field(min_length=2, max_length=6)
    session_id: str


class ConsistencyEdge(BaseModel):
    """An edge in the consistency graph between two clauses.

    Attributes:
        source_clause_id: ID of the first clause.
        target_clause_id: ID of the second clause.
        finding_id: The finding describing this relationship.
        relationship_type: Type of the relationship.
    """

    source_clause_id: str
    target_clause_id: str
    finding_id: str
    relationship_type: RelationshipType


class ConsistencyGraph(BaseModel):
    """Graph model of document/clause relationships.

    Attributes:
        nodes: List of clause IDs serving as nodes.
        document_nodes: List of document IDs serving as group nodes.
        edges: Relationships between clauses.
    """

    nodes: list[str] = Field(default_factory=list)
    document_nodes: list[str] = Field(default_factory=list)
    edges: list[ConsistencyEdge] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Complete result of an analysis job.

    Attributes:
        job_id: The analysis job identifier.
        state: Current job state.
        documents: Documents included in the analysis.
        findings: Validated findings.
        graph: Consistency graph model.
        metrics: Job performance metrics.
        error_message: Safe error message if job failed.
    """

    job_id: str
    state: JobState
    documents: list[Document] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    graph: ConsistencyGraph = Field(default_factory=ConsistencyGraph)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None


class AnalysisStatusResponse(BaseModel):
    """Response for job status polling.

    Attributes:
        job_id: The analysis job identifier.
        state: Current job state.
        progress_detail: Human-readable progress message.
        result: Full result if job is COMPLETE.
    """

    job_id: str
    state: JobState
    progress_detail: str = ""
    result: AnalysisResult | None = None


class QARequest(BaseModel):
    """Request for a follow-up question about an analysis.

    Attributes:
        job_id: The analysis job to query against.
        question: The user's follow-up question.
        session_id: Client session identifier for isolation.
    """

    job_id: str
    question: str = Field(min_length=1, max_length=2000)
    session_id: str


class QAResponse(BaseModel):
    """Response to a follow-up question.

    Attributes:
        answer: The grounded answer text.
        confidence: Confidence tier for the answer.
        evidence: Supporting evidence spans.
        uncertainty: Uncertainty note if applicable.
    """

    answer: str
    confidence: Confidence
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: str | None = None


class MetricsResponse(BaseModel):
    """Response containing job performance metrics.

    Attributes:
        job_id: The analysis job identifier.
        metrics: Dictionary of metric name-value pairs.
    """

    job_id: str
    metrics: dict[str, Any]
