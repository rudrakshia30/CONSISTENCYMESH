"""Text layer extractors for PDF, DOCX, and TXT documents.

Provides concrete implementations of DocumentTextExtractor for
PDF (via PyMuPDF/fitz), DOCX (via python-docx / zipfile fallback), and TXT formats.
Each preserves page-level provenance for downstream clause segmentation.
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile

from backend.core.errors import ValidationError
from backend.core.logging import get_logger
from backend.parsing.extractor import DocumentTextExtractor, ExtractedDocument, PageText

logger = get_logger("parsing.text_layer")


class PDFTextExtractor(DocumentTextExtractor):
    """Extract text from PDF documents using PyMuPDF."""

    def extract(self, file_content: bytes, filename: str) -> ExtractedDocument:
        """Extract text from a PDF file with page-level provenance.

        Args:
            file_content: Raw bytes of the PDF file.
            filename: Original filename for metadata.

        Returns:
            Extracted document with per-page text.

        Raises:
            ValidationError: If the PDF cannot be opened or parsed.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError as e:
            raise ValidationError(
                "PDF processing library not available.",
                detail=str(e),
            ) from e

        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
        except Exception as e:
            raise ValidationError(
                "Unable to parse PDF document. The file may be corrupted.",
                detail=f"PyMuPDF error: {e}",
            ) from e

        pages: list[PageText] = []
        total_chars = 0

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text("text")
                pages.append(PageText(page_number=page_idx + 1, text=text))
                total_chars += len(text)
        finally:
            doc.close()

        result = ExtractedDocument(
            pages=pages,
            page_count=len(pages),
            total_chars=total_chars,
            filename=filename,
        )

        if not result.has_text:
            logger.warning(
                "PDF '%s' yielded no text — may be scanned/image-only. "
                "OCR extension point is available but not active.",
                filename,
            )

        return result

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".pdf")


class DOCXTextExtractor(DocumentTextExtractor):
    """Extract text from DOCX documents using python-docx with zipfile fallback."""

    def extract(self, file_content: bytes, filename: str) -> ExtractedDocument:
        paragraphs: list[str] = []

        # Strategy 1: Try python-docx
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(io.BytesIO(file_content))

            for para in doc.paragraphs:
                text = para.text.strip()
                if text:
                    paragraphs.append(text)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            paragraphs.append(cell_text)

        except Exception:
            # Strategy 2: Fallback to zipfile XML parsing
            try:
                with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
                    if "word/document.xml" in zf.namelist():
                        xml_bytes = zf.read("word/document.xml")
                        tree = ET.fromstring(xml_bytes)
                        texts = [elem.text for elem in tree.iter() if elem.text and elem.text.strip()]
                        if texts:
                            paragraphs.extend(texts)
            except Exception as e:
                raise ValidationError(
                    "Unable to parse DOCX document. The file may be corrupted.",
                    detail=f"DOCX extraction error: {e}",
                ) from e

        full_text = "\n\n".join(paragraphs)
        total_chars = len(full_text)
        page = PageText(page_number=1, text=full_text)

        result = ExtractedDocument(
            pages=[page],
            page_count=1,
            total_chars=total_chars,
            filename=filename,
        )

        if not result.has_text:
            logger.warning("DOCX '%s' yielded no text content.", filename)

        return result

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".docx")


class TXTTextExtractor(DocumentTextExtractor):
    """Extract text from plain text (.txt) documents."""

    def extract(self, file_content: bytes, filename: str) -> ExtractedDocument:
        try:
            text = file_content.decode("utf-8", errors="replace")
        except Exception as e:
            raise ValidationError(
                "Unable to parse text document.",
                detail=f"Text decoding error: {e}",
            ) from e

        page = PageText(page_number=1, text=text)
        return ExtractedDocument(
            pages=[page],
            page_count=1,
            total_chars=len(text),
            filename=filename,
        )

    def supports(self, filename: str) -> bool:
        return filename.lower().endswith(".txt")


def get_extractor(filename: str) -> DocumentTextExtractor:
    """Factory function to get the appropriate extractor for a file.

    Args:
        filename: The filename to determine the extractor for.

    Returns:
        An appropriate DocumentTextExtractor instance.

    Raises:
        ValidationError: If no extractor supports the file type.
    """
    extractors: list[DocumentTextExtractor] = [
        PDFTextExtractor(),
        DOCXTextExtractor(),
        TXTTextExtractor(),
    ]

    for extractor in extractors:
        if extractor.supports(filename):
            return extractor

    raise ValidationError(
        "Unsupported file type. Supported formats: PDF, DOCX, TXT.",
        detail=f"No extractor for: {filename}",
    )
