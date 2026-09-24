"""
Document management service.

Handles document upload, parsing, segmentation, metadata extraction,
and storage. Supports content-hash-based deduplication and session
isolation for document access.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.core.config import Settings
from backend.core.errors import DocumentNotFoundError, ValidationError
from backend.core.logging import get_logger
from backend.models.schemas import Clause, Document
from backend.parsing.segmenter import segment_clauses
from backend.parsing.text_layer_extractor import get_extractor
from backend.security.validation import (
    sanitize_filename,
    validate_docx_zip_safety,
    validate_upload,
)
from backend.state.base import StateStore
from backend.state.keys import content_hash

logger = get_logger("services.document")


class DocumentService:
    """Service for managing document uploads and retrieval.

    Orchestrates the upload pipeline: validation -> extraction ->
    segmentation -> metadata -> storage. Uses content-hash-based
    deduplication to avoid re-processing identical documents.

    Attributes:
        _state_store: State store for document and clause persistence.
        _settings: Application settings with upload limits.
    """

    def __init__(self, state_store: StateStore, settings: Settings) -> None:
        """Initialize the document service.

        Args:
            state_store: State store for persistence.
            settings: Application settings.
        """
        self._state_store = state_store
        self._settings = settings

    async def upload_document(
        self,
        filename: str,
        file_content: bytes,
        session_id: str = "",
    ) -> tuple[Document, list[Clause]]:
        """Upload and process a document through the parsing pipeline.

        Steps:
        1. Validate upload (security checks)
        2. Validate DOCX zip safety if applicable
        3. Sanitize filename
        4. Compute content hash for deduplication
        5. Check cache for existing parse results
        6. Extract text with page-level provenance
        7. Validate page count and character count
        8. Segment into clauses with metadata extraction
        9. Create Document model
        10. Store document and clauses in state store
        11. Return (document, clauses)

        Args:
            filename: Original uploaded filename.
            file_content: Raw file bytes.
            session_id: Client session ID for access control.

        Returns:
            Tuple of (Document, list of Clauses).

        Raises:
            ValidationError: If any validation check fails.
        """
        # 1. Security validation
        validate_upload(filename, file_content, self._settings)

        # 2. DOCX zip safety
        if filename.lower().endswith(".docx"):
            validate_docx_zip_safety(file_content, self._settings)

        # 3. Sanitize filename
        safe_filename = sanitize_filename(filename)

        # 4. Compute content hash
        doc_hash = content_hash(file_content)
        document_id = doc_hash[:16]

        # 5. Check cache
        cached_doc_data = await self._state_store.get(f"doc:{document_id}:data")
        if cached_doc_data is not None:
            logger.info("Document %s already parsed (cache hit)", document_id[:8])
            document = Document.model_validate(cached_doc_data)
            clauses = await self.get_clauses(document_id)
            # Register session ownership even for cached docs
            await self._state_store.set(
                f"session:{session_id}:doc:{document_id}", True
            )
            return document, clauses

        # 6. Extract text
        extractor = get_extractor(filename)
        extracted = extractor.extract(file_content, safe_filename)

        # 7. Validate limits
        if extracted.page_count > self._settings.max_page_count:
            raise ValidationError(
                f"Document exceeds maximum page count ({self._settings.max_page_count})."
            )
        if extracted.total_chars > self._settings.max_char_count:
            raise ValidationError(
                f"Document exceeds maximum character count ({self._settings.max_char_count})."
            )

        # 8. Segment into clauses
        clauses = segment_clauses(extracted, document_id)

        # 9. Create Document model
        document = Document(
            document_id=document_id,
            filename=safe_filename,
            page_count=extracted.page_count,
            uploaded_at=datetime.now(UTC),
        )

        # 10. Store document and clauses
        await self._state_store.set(
            f"doc:{document_id}:data",
            document.model_dump(mode="json"),
        )
        await self._state_store.set(
            f"doc:{document_id}:clauses",
            [clause.model_dump(mode="json") for clause in clauses],
        )
        await self._state_store.set(
            f"session:{session_id}:doc:{document_id}", True
        )

        logger.info(
            "Uploaded document '%s' (%s): %d pages, %d clauses",
            safe_filename,
            document_id[:8],
            extracted.page_count,
            len(clauses),
        )

        return document, clauses

    async def get_document(self, document_id: str, session_id: str) -> Document:
        """Retrieve a document with session isolation.

        Args:
            document_id: The document identifier.
            session_id: The requesting session ID.

        Returns:
            The document metadata.

        Raises:
            DocumentNotFoundError: If document doesn't exist or session
                doesn't have access.
        """
        # Check session ownership
        owns = await self._state_store.get(
            f"session:{session_id}:doc:{document_id}"
        )
        if owns is None:
            raise DocumentNotFoundError(document_id)

        doc_data = await self._state_store.get(f"doc:{document_id}:data")
        if doc_data is None:
            raise DocumentNotFoundError(document_id)

        return Document.model_validate(doc_data)

    async def get_clauses(self, document_id: str) -> list[Clause]:
        """Retrieve all clauses for a document.

        Args:
            document_id: The document identifier.

        Returns:
            List of clauses belonging to the document.
        """
        clauses_data = await self._state_store.get(f"doc:{document_id}:clauses")
        if clauses_data is None:
            return []
        return [Clause.model_validate(c) for c in clauses_data]

    async def get_documents_for_session(self, session_id: str) -> list[Document]:
        """List all documents uploaded by a session.

        Args:
            session_id: The session identifier.

        Returns:
            List of documents belonging to the session.
        """
        keys = await self._state_store.keys(f"session:{session_id}:doc:*")
        documents: list[Document] = []

        for key in keys:
            # Extract document_id from key: session:{sid}:doc:{doc_id}
            parts = key.split(":")
            if len(parts) >= 4:
                doc_id = parts[3]
                doc_data = await self._state_store.get(f"doc:{doc_id}:data")
                if doc_data is not None:
                    documents.append(Document.model_validate(doc_data))

        return documents
