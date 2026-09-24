"""Integration tests for job manager."""
from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.jobs.job_manager import JobManager
from backend.models.schemas import JobState
from backend.state.local_store import LocalStateStore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_lifecycle() -> None:
    store = LocalStateStore()
    settings = Settings()
    manager = JobManager(store, settings)

    # Create job
    job_id = await manager.create_job(
        ["doc1", "doc2"], session_id="s1", prompt_version="v1"
    )
    assert isinstance(job_id, str)

    # Initial status is QUEUED
    status = await manager.get_status(job_id, session_id="s1")
    assert status.state == JobState.QUEUED

    # Update state to ANALYZING
    await manager.update_state(job_id, JobState.ANALYZING)
    status2 = await manager.get_status(job_id, session_id="s1")
    assert status2.state == JobState.ANALYZING


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_idempotency() -> None:
    store = LocalStateStore()
    settings = Settings()
    manager = JobManager(store, settings)

    j1 = await manager.create_job(
        ["docA", "docB"], session_id="s1", prompt_version="v1"
    )
    j2 = await manager.create_job(
        ["docB", "docA"], session_id="s1", prompt_version="v1"
    )

    # Resubmitting sorted set of doc IDs returns same job ID
    assert j1 == j2
