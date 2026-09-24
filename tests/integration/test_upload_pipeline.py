"""Integration tests for upload and parsing pipeline."""
from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.services.document_service import DocumentService
from backend.state.local_store import LocalStateStore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_pipeline_end_to_end() -> None:
    store = LocalStateStore()
    settings = Settings()
    service = DocumentService(store, settings)

    pdf_content = (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 55 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (SECTION 1 - TERMINATION) Tj ET\n"
        b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n300\n%%EOF\n"
    )

    # Simple text upload via text_layer_extractor
    doc, clauses = await service.upload_document(
        filename="test.pdf",
        file_content=pdf_content,
        session_id="session_1",
    )

    assert doc.document_id is not None
    assert doc.filename == "test.pdf"
    assert doc.page_count >= 1

    # Verify session retrieval
    session_docs = await service.get_documents_for_session("session_1")
    assert len(session_docs) == 1
    assert session_docs[0].document_id == doc.document_id
