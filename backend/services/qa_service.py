"""Follow-up Q&A service with staged hybrid retrieval and intent-aware grounding."""

from __future__ import annotations

from backend.core.config import Settings
from backend.core.errors import JobNotFoundError
from backend.core.logging import get_logger
from backend.matching.retrieval import retrieve_relevant_clauses
from backend.models.schemas import (
    Clause,
    Confidence,
    QAResponse,
)
from backend.providers.base import LLMProvider
from backend.security.sanitize import sanitize_llm_output
from backend.services.evidence_validator import EvidenceValidator
from backend.state.base import StateStore

logger = get_logger("services.qa")


class QAService:
    """Follow-up Q&A service for grounded question answering."""

    def __init__(
        self,
        provider: LLMProvider,
        state_store: StateStore,
        settings: Settings,
    ) -> None:
        self._provider = provider
        self._state_store = state_store
        self._settings = settings
        self._validator = EvidenceValidator()

    async def answer_question(
        self,
        job_id: str,
        question: str,
        session_id: str,
    ) -> QAResponse:
        """Answer a follow-up question about an analyzed document set.

        Steps:
        1. Verify session ownership of the job
        2. Load all clauses from the analysis
        3. Extract QueryIntent and retrieve relevant clauses via Staged Hybrid Retrieval
        4. Enforce minimum clause requirement for cross-clause comparison questions
        5. Call LLM provider with grounded clauses
        6. Validate evidence spans and intent alignment
        7. Return grounded answer or evidence fallback

        Args:
            job_id: The analysis job to query against.
            question: The user's question.
            session_id: Client session ID for isolation.

        Returns:
            QA response with answer, confidence, and validated evidence.

        Raises:
            JobNotFoundError: If job doesn't exist or session doesn't own it.
        """
        # 1. Verify session ownership
        owns = await self._state_store.get(f"session:{session_id}:job:{job_id}")
        if owns is None:
            raise JobNotFoundError(job_id)

        # 2. Load job data to get document IDs
        job_data = await self._state_store.get(f"job:{job_id}:data")
        if job_data is None:
            raise JobNotFoundError(job_id)

        document_ids: list[str] = job_data.get("document_ids", [])

        # 3. Load all clauses across documents
        all_clauses: list[Clause] = []
        for doc_id in document_ids:
            clauses_data = await self._state_store.get(f"doc:{doc_id}:clauses")
            if clauses_data is not None:
                all_clauses.extend(Clause.model_validate(c) for c in clauses_data)

        if not all_clauses:
            return QAResponse(
                answer="I couldn't find enough relevant evidence across the documents to determine a conflict.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty="No document clauses are available to answer the question.",
            )

        # 4. Staged Hybrid Retrieval & Intent Reranking
        intent, scored_candidates = retrieve_relevant_clauses(
            query=question,
            clauses=all_clauses,
            top_k=10,
            min_threshold=0.25,
        )

        relevant_clauses = [c for c, score in scored_candidates]

        # REQUIREMENT 5: Check cross-clause comparison minimum clause count
        if intent.has_comparison_intent and len(relevant_clauses) < 2:
            return QAResponse(
                answer="I couldn't find enough relevant evidence across the documents to determine a conflict.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty="Fewer than two relevant clauses addressing the requested topic were found.",
            )

        if not relevant_clauses:
            return QAResponse(
                answer="I couldn't find enough relevant evidence across the documents to determine a conflict.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty="No relevant clauses met the minimum similarity threshold for this query.",
            )

        # 5. Call LLM Provider
        try:
            raw_answer = await self._provider.answer_question(question, relevant_clauses)
        except Exception as e:
            logger.warning("QA LLM call failed: %s", str(e))
            return QAResponse(
                answer="Unable to generate an answer at this time.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty=f"AI service error: {type(e).__name__}",
            )

        # 6. Validate evidence spans and intent alignment
        valid_evidence, confidence, uncertainty_note = self._validator.validate_qa_evidence(
            raw_evidence=raw_answer.evidence,
            candidate_clauses=relevant_clauses,
            intent=intent,
        )

        # If comparison intent required but validation failed to find >= 2 distinct clause evidence
        if intent.has_comparison_intent and len(valid_evidence) < 2:
            return QAResponse(
                answer="I couldn't find enough relevant evidence across the documents to determine a conflict.",
                confidence=Confidence.NOT_ESTABLISHED,
                evidence=[],
                uncertainty="Evidence validation could not confirm citations from multiple clauses.",
            )

        safe_answer = sanitize_llm_output(raw_answer.answer)

        return QAResponse(
            answer=safe_answer,
            confidence=confidence if valid_evidence else Confidence.NOT_ESTABLISHED,
            evidence=valid_evidence,
            uncertainty=uncertainty_note or raw_answer.uncertainty,
        )
