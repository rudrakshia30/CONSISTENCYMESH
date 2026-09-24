"""
Follow-up Q&A API endpoint.

Handles grounded question answering over analyzed document sets,
with the same evidence/confidence discipline as the main report.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.models.schemas import QARequest, QAResponse
from backend.security.rate_limit import RateLimiter
from backend.services.qa_service import QAService

router = APIRouter(prefix="/api/qa", tags=["qa"])

# Module-level dependencies — set during app initialization in main.py
_qa_service: QAService | None = None
_rate_limiter: RateLimiter | None = None


def _get_qa_service() -> QAService:
    """Get the QA service instance."""
    assert _qa_service is not None, "QAService not initialized"
    return _qa_service


def _get_rate_limiter() -> RateLimiter:
    """Get the rate limiter instance."""
    assert _rate_limiter is not None, "RateLimiter not initialized"
    return _rate_limiter


@router.post("/", response_model=QAResponse)
async def answer_question(
    request: QARequest,
) -> QAResponse:
    """Answer a follow-up question about an analyzed document set.

    Retrieves relevant clauses via TF-IDF similarity and generates
    a grounded answer with validated evidence citations.

    Args:
        request: QA request with job_id, question, and session_id.

    Returns:
        Grounded answer with confidence tier and evidence spans.
    """
    rate_limiter = _get_rate_limiter()
    rate_limiter.check_rate_limit(f"qa:{request.session_id}")

    qa_service = _get_qa_service()
    return await qa_service.answer_question(
        job_id=request.job_id,
        question=request.question,
        session_id=request.session_id,
    )
