"""
Job lifecycle management.

Manages analysis job creation, state transitions, and result storage.
Job IDs are deterministic (content-hash-derived) enabling idempotent
job submission — resubmitting the same document set returns the
existing job.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.core.config import Settings
from backend.core.errors import JobNotFoundError
from backend.core.logging import JobMetrics, get_logger
from backend.models.schemas import AnalysisResult, AnalysisStatusResponse, JobState
from backend.state.base import StateStore
from backend.state.keys import build_job_id

logger = get_logger("jobs.manager")


class JobManager:
    """Manages the lifecycle of analysis jobs.

    Handles job creation, state transitions, result storage, and
    status queries. Enforces cross-session isolation at the state
    access layer.

    Attributes:
        _state_store: The state store for persisting job data.
        _settings: Application settings.
    """

    def __init__(self, state_store: StateStore, settings: Settings) -> None:
        """Initialize the job manager.

        Args:
            state_store: State store for job persistence.
            settings: Application settings.
        """
        self._state_store = state_store
        self._settings = settings

    async def create_job(
        self,
        document_ids: list[str],
        session_id: str,
        prompt_version: str,
    ) -> str:
        """Create or retrieve an idempotent analysis job.

        If a job with the same document set and prompt version already
        exists, returns the existing job ID. Otherwise creates a new
        job in QUEUED state.

        Args:
            document_ids: List of document IDs to analyze.
            session_id: Client session ID for isolation.
            prompt_version: Current prompt template version.

        Returns:
            The job ID (deterministic hash of document set + prompt version).
        """
        # Build deterministic job ID from sorted document hashes + prompt version
        sorted_doc_ids = sorted(document_ids)
        job_id = build_job_id(sorted_doc_ids, prompt_version)

        # Check for existing job (idempotency)
        existing = await self._state_store.get(f"job:{job_id}:state")
        if existing is not None:
            logger.info("Reusing existing job %s (idempotent submission)", job_id)
            return job_id

        # Create new job
        job_data: dict[str, Any] = {
            "job_id": job_id,
            "document_ids": sorted_doc_ids,
            "session_id": session_id,
            "state": JobState.QUEUED.value,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt_version": prompt_version,
            "error_message": None,
        }

        await self._state_store.set(f"job:{job_id}:data", job_data)
        await self._state_store.set(f"job:{job_id}:state", JobState.QUEUED.value)
        await self._state_store.set(f"session:{session_id}:job:{job_id}", True)

        logger.info(
            "Created job %s for %d documents in session %s",
            job_id,
            len(document_ids),
            session_id[:8],
        )
        return job_id

    async def update_state(
        self,
        job_id: str,
        new_state: JobState,
        error_message: str | None = None,
    ) -> None:
        """Transition a job to a new state.

        Args:
            job_id: The job to update.
            new_state: The target state.
            error_message: Error message if transitioning to FAILED.
        """
        await self._state_store.set(f"job:{job_id}:state", new_state.value)

        if error_message:
            await self._state_store.set(f"job:{job_id}:error", error_message)

        logger.info("Job %s -> %s", job_id, new_state.value)

    async def store_result(
        self,
        job_id: str,
        result: AnalysisResult,
    ) -> None:
        """Store the completed analysis result.

        Args:
            job_id: The job that produced this result.
            result: The analysis result to store.
        """
        await self._state_store.set(
            f"job:{job_id}:result",
            result.model_dump(mode="json"),
            ttl=self._settings.cache_ttl_seconds,
        )

    async def store_metrics(
        self,
        job_id: str,
        metrics: JobMetrics,
    ) -> None:
        """Store job metrics for observability.

        Args:
            job_id: The job these metrics belong to.
            metrics: The metrics data to store.
        """
        await self._state_store.set(
            f"job:{job_id}:metrics",
            metrics.to_dict(),
            ttl=self._settings.cache_ttl_seconds,
        )

    async def get_status(
        self,
        job_id: str,
        session_id: str,
    ) -> AnalysisStatusResponse:
        """Get the current status and result of a job.

        Enforces cross-session isolation: a session can only query
        its own jobs.

        Args:
            job_id: The job to query.
            session_id: The requesting session ID.

        Returns:
            Current job status and result if complete.

        Raises:
            JobNotFoundError: If the job doesn't exist or belongs
                to a different session.
        """
        # Verify session ownership
        owns = await self._state_store.get(f"session:{session_id}:job:{job_id}")
        if owns is None:
            # Check if job exists at all
            state_val = await self._state_store.get(f"job:{job_id}:state")
            if state_val is None:
                raise JobNotFoundError(job_id)
            raise JobNotFoundError(job_id)

        state_val = await self._state_store.get(f"job:{job_id}:state")
        if state_val is None:
            raise JobNotFoundError(job_id)

        state = JobState(str(state_val))

        progress_messages: dict[str, str] = {
            JobState.QUEUED.value: "Job queued, waiting to start...",
            JobState.PARSING.value: "Parsing documents...",
            JobState.INDEXING.value: "Building search indices...",
            JobState.MATCHING.value: "Finding candidate clause pairs...",
            JobState.ANALYZING.value: "Analyzing relationships with AI...",
            JobState.VALIDATING.value: "Validating evidence citations...",
            JobState.COMPLETE.value: "Analysis complete.",
            JobState.FAILED.value: "Analysis failed.",
        }

        result: AnalysisResult | None = None
        if state == JobState.COMPLETE:
            result_data = await self._state_store.get(f"job:{job_id}:result")
            if result_data is not None:
                result = AnalysisResult.model_validate(result_data)

        error_msg = None
        if state == JobState.FAILED:
            error_msg = await self._state_store.get(f"job:{job_id}:error")

        return AnalysisStatusResponse(
            job_id=job_id,
            state=state,
            progress_detail=progress_messages.get(state.value, "Processing..."),
            result=AnalysisResult(
                job_id=job_id,
                state=state,
                error_message=str(error_msg) if error_msg else None,
            )
            if result is None and state == JobState.FAILED
            else result,
        )

    async def get_metrics(self, job_id: str) -> dict[str, Any]:
        """Get stored metrics for a job.

        Args:
            job_id: The job to get metrics for.

        Returns:
            Dictionary of metric values.

        Raises:
            JobNotFoundError: If the job doesn't exist.
        """
        metrics_data = await self._state_store.get(f"job:{job_id}:metrics")
        if metrics_data is None:
            raise JobNotFoundError(job_id)
        result: dict[str, Any] = dict(metrics_data)
        return result
