"""
Async bounded-concurrency worker for background job processing.

Runs analysis jobs asynchronously using asyncio tasks with a bounded
worker pool (semaphore). The HTTP request thread is never blocked
on the full analysis — clients poll for status.
"""

from __future__ import annotations

import asyncio
import time
import traceback

from backend.core.config import Settings
from backend.core.logging import JobMetrics, get_logger
from backend.jobs.job_manager import JobManager
from backend.models.schemas import JobState
from backend.providers.base import LLMProvider
from backend.services.consistency_engine import ConsistencyEngine
from backend.state.base import CacheStore, StateStore

logger = get_logger("jobs.worker")


class JobWorker:
    """Async worker that processes analysis jobs in the background.

    Uses an asyncio.Semaphore to bound the number of concurrent jobs.
    Each job runs through the full pipeline: parse -> index -> match ->
    analyze -> validate -> complete.

    Attributes:
        _settings: Application settings.
        _job_manager: Job lifecycle manager.
        _engine: Consistency analysis engine.
        _semaphore: Bounds concurrent job execution.
        _active_tasks: Tracks in-flight job tasks.
    """

    def __init__(
        self,
        settings: Settings,
        job_manager: JobManager,
        provider: LLMProvider,
        state_store: StateStore,
        cache_store: CacheStore,
    ) -> None:
        """Initialize the job worker.

        Args:
            settings: Application settings.
            job_manager: Job lifecycle manager.
            provider: LLM provider for analysis.
            state_store: State store for persistence.
            cache_store: Cache store for result caching.
        """
        self._settings = settings
        self._job_manager = job_manager
        self._engine = ConsistencyEngine(
            provider=provider,
            state_store=state_store,
            cache_store=cache_store,
            settings=settings,
        )
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_llm_calls)
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def submit_job(
        self,
        job_id: str,
        document_ids: list[str],
        session_id: str,
    ) -> None:
        """Submit a job for background processing.

        If the job is already in-flight, this is a no-op (deduplication).

        Args:
            job_id: The job to process.
            document_ids: Documents to analyze.
            session_id: Client session ID.
        """
        if job_id in self._active_tasks:
            task = self._active_tasks[job_id]
            if not task.done():
                logger.info("Job %s already in-flight, deduplicating", job_id)
                return

        task = asyncio.create_task(
            self._run_job(job_id, document_ids, session_id),
            name=f"job-{job_id}",
        )
        self._active_tasks[job_id] = task

        # Clean up completed tasks
        self._cleanup_completed_tasks()

    async def _run_job(
        self,
        job_id: str,
        document_ids: list[str],
        session_id: str,
    ) -> None:
        """Execute the full analysis pipeline for a job.

        Progresses through all job states, catching and handling errors
        at each stage. If individual pairwise analyses fail, the job
        still completes with those findings downgraded rather than
        failing entirely.

        Args:
            job_id: The job being processed.
            document_ids: Documents to analyze.
            session_id: Client session ID.
        """
        metrics = JobMetrics(job_id=job_id)
        metrics.document_count = len(document_ids)
        metrics.start_time = time.time()

        try:
            async with self._semaphore:
                logger.info("Starting job %s with %d documents", job_id, len(document_ids))

                # Run the analysis engine
                await self._job_manager.update_state(job_id, JobState.PARSING)
                await self._job_manager.update_state(job_id, JobState.INDEXING)
                await self._job_manager.update_state(job_id, JobState.MATCHING)
                await self._job_manager.update_state(job_id, JobState.ANALYZING)

                result = await self._engine.analyze(
                    document_ids=document_ids,
                    session_id=session_id,
                    job_metrics=metrics,
                )

                await self._job_manager.update_state(job_id, JobState.VALIDATING)

                # Finalize
                metrics.end_time = time.time()
                result.state = JobState.COMPLETE
                result.metrics = metrics.to_dict()

                await self._job_manager.store_result(job_id, result)
                await self._job_manager.store_metrics(job_id, metrics)
                await self._job_manager.update_state(job_id, JobState.COMPLETE)

                logger.info(
                    "Job %s complete: %d findings, %.1fs wall time, "
                    "%.1f%% candidate reduction",
                    job_id,
                    len(result.findings),
                    metrics.wall_clock_seconds,
                    metrics.candidate_reduction_percent,
                )

        except Exception as e:
            metrics.end_time = time.time()
            error_detail = traceback.format_exc()
            logger.error("Job %s failed: %s\n%s", job_id, str(e), error_detail)

            # Store what metrics we have even on failure
            await self._job_manager.store_metrics(job_id, metrics)

            # Safe error message for clients — no internal details
            safe_message = "Analysis could not be completed. Please try again."
            await self._job_manager.update_state(
                job_id,
                JobState.FAILED,
                error_message=safe_message,
            )

    def _cleanup_completed_tasks(self) -> None:
        """Remove completed tasks from the active tasks dict."""
        completed = [
            job_id
            for job_id, task in self._active_tasks.items()
            if task.done()
        ]
        for job_id in completed:
            del self._active_tasks[job_id]

    async def shutdown(self) -> None:
        """Gracefully shut down the worker, cancelling in-flight tasks."""
        for job_id, task in self._active_tasks.items():
            if not task.done():
                logger.warning("Cancelling in-flight job %s", job_id)
                task.cancel()

        if self._active_tasks:
            await asyncio.gather(
                *self._active_tasks.values(),
                return_exceptions=True,
            )

        self._active_tasks.clear()
        logger.info("Job worker shut down")
