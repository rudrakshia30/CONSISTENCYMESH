"""
Analysis job API endpoints.

Handles job creation, status polling, and metrics retrieval.
Jobs run asynchronously — the POST endpoint returns immediately
with a job ID, and clients poll GET for status.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.core.config import Settings
from backend.jobs.job_manager import JobManager
from backend.jobs.worker import JobWorker
from backend.models.schemas import AnalysisRequest, AnalysisStatusResponse, MetricsResponse
from backend.prompts.consistency_judge import PROMPT_VERSION

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Module-level dependencies — set during app initialization in main.py
_job_manager: JobManager | None = None
_job_worker: JobWorker | None = None
_settings: Settings | None = None


def _get_job_manager() -> JobManager:
    """Get the job manager instance."""
    assert _job_manager is not None, "JobManager not initialized"
    return _job_manager


def _get_job_worker() -> JobWorker:
    """Get the job worker instance."""
    assert _job_worker is not None, "JobWorker not initialized"
    return _job_worker


@router.post("/")
async def create_analysis(
    request: AnalysisRequest,
) -> dict[str, str]:
    """Create a new analysis job.

    Creates an idempotent job for the given document set and submits
    it to the background worker. Returns immediately with the job ID.

    Args:
        request: Analysis request with document IDs and session ID.

    Returns:
        Dictionary with job_id and initial state 'QUEUED'.
    """
    job_manager = _get_job_manager()
    job_worker = _get_job_worker()

    job_id = await job_manager.create_job(
        document_ids=request.document_ids,
        session_id=request.session_id,
        prompt_version=PROMPT_VERSION,
    )

    await job_worker.submit_job(
        job_id=job_id,
        document_ids=request.document_ids,
        session_id=request.session_id,
    )

    return {"job_id": job_id, "state": "QUEUED"}


@router.get("/{job_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    job_id: str,
    session_id: str = Query(...),
) -> AnalysisStatusResponse:
    """Get the current status and result of an analysis job.

    Enforces session isolation — a session can only query its own jobs.

    Args:
        job_id: The analysis job identifier.
        session_id: Client session identifier for access control.

    Returns:
        Current job status and result if complete.
    """
    job_manager = _get_job_manager()
    return await job_manager.get_status(job_id, session_id)


@router.get("/{job_id}/metrics", response_model=MetricsResponse)
async def get_analysis_metrics(
    job_id: str,
) -> MetricsResponse:
    """Get performance metrics for an analysis job.

    Returns measured metrics including candidate reduction ratio,
    LLM call counts, cache hit rates, and latency percentiles.

    Args:
        job_id: The analysis job identifier.

    Returns:
        Job metrics response.
    """
    job_manager = _get_job_manager()
    metrics = await job_manager.get_metrics(job_id)
    return MetricsResponse(job_id=job_id, metrics=metrics)
