"""Security tests for cross-session isolation."""
from __future__ import annotations

import io
import zipfile

import pytest

from backend.core.config import Settings
from backend.core.errors import DocumentNotFoundError, JobNotFoundError
from backend.jobs.job_manager import JobManager
from backend.services.document_service import DocumentService
from backend.state.local_store import LocalStateStore


def _make_valid_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


@pytest.mark.security
@pytest.mark.asyncio
async def test_session_cannot_access_other_session_document() -> None:
    store = LocalStateStore()
    settings = Settings()
    service = DocumentService(store, settings)

    docx_content = _make_valid_docx()

    # Session A uploads
    doc_a, _ = await service.upload_document(
        "doc_a.docx", docx_content, session_id="session_A"
    )

    # Session A can access
    doc = await service.get_document(doc_a.document_id, session_id="session_A")
    assert doc.document_id == doc_a.document_id

    # Session B cannot access
    with pytest.raises(DocumentNotFoundError):
        await service.get_document(doc_a.document_id, session_id="session_B")


@pytest.mark.security
@pytest.mark.asyncio
async def test_session_cannot_access_other_session_job() -> None:
    store = LocalStateStore()
    settings = Settings()
    manager = JobManager(store, settings)

    # Session A creates job
    job_id = await manager.create_job(
        ["doc1", "doc2"], session_id="session_A", prompt_version="v1"
    )

    # Session A gets status
    status_a = await manager.get_status(job_id, session_id="session_A")
    assert status_a.job_id == job_id

    # Session B gets 404/NotFoundError
    with pytest.raises(JobNotFoundError):
        await manager.get_status(job_id, session_id="session_B")
