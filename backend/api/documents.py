"""
Document upload and retrieval API endpoints.

Handles multi-file upload with security validation, document listing,
and individual document retrieval with session isolation.
"""

from __future__ import annotations

from fastapi import APIRouter, Form, Query, UploadFile

from backend.core.config import Settings
from backend.models.schemas import Document, UploadResponse
from backend.security.rate_limit import RateLimiter
from backend.services.document_service import DocumentService

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Module-level dependencies — set during app initialization in main.py
_document_service: DocumentService | None = None
_rate_limiter: RateLimiter | None = None
_settings: Settings | None = None


def _get_document_service() -> DocumentService:
    """Get the document service instance."""
    assert _document_service is not None, "DocumentService not initialized"
    return _document_service


def _get_rate_limiter() -> RateLimiter:
    """Get the rate limiter instance."""
    assert _rate_limiter is not None, "RateLimiter not initialized"
    return _rate_limiter


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile,
    session_id: str = Form(...),
) -> UploadResponse:
    """Upload a document for analysis.

    Accepts PDF and DOCX files. Performs security validation
    (magic bytes, size, zip-bomb checks) before processing.

    Args:
        file: The uploaded file.
        session_id: Client session identifier for isolation.

    Returns:
        Upload response with document ID, filename, page and clause counts.
    """
    rate_limiter = _get_rate_limiter()
    rate_limiter.check_rate_limit(f"upload:{session_id}")

    doc_service = _get_document_service()
    content = await file.read()
    filename = file.filename or "unknown"

    document, clauses = await doc_service.upload_document(
        filename=filename,
        file_content=content,
        session_id=session_id,
    )

    return UploadResponse(
        document_id=document.document_id,
        filename=document.filename,
        page_count=document.page_count,
        clause_count=len(clauses),
    )


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str,
    session_id: str = Query(...),
) -> Document:
    """Get document information by ID.

    Enforces session isolation — a session can only access its own documents.

    Args:
        document_id: The document identifier.
        session_id: Client session identifier for access control.

    Returns:
        Document metadata.
    """
    doc_service = _get_document_service()
    return await doc_service.get_document(document_id, session_id)


@router.get("/", response_model=list[Document])
async def list_documents(
    session_id: str = Query(...),
) -> list[Document]:
    """List all documents uploaded by the current session.

    Args:
        session_id: Client session identifier.

    Returns:
        List of document metadata for the session.
    """
    doc_service = _get_document_service()
    return await doc_service.get_documents_for_session(session_id)
