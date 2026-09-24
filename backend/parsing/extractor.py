"""
Document text extraction interface and implementations.

Defines the DocumentTextExtractor protocol and provides concrete
implementations for PDF (via PyMuPDF) and DOCX (via python-docx) formats.
Each extractor preserves page-level provenance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PageText:
    """Text content from a single page of a document.

    Attributes:
        page_number: 1-indexed page number.
        text: Extracted text content from this page.
    """

    page_number: int
    text: str


@dataclass
class ExtractedDocument:
    """Result of text extraction from a document.

    Attributes:
        pages: List of page-level text extractions.
        page_count: Total number of pages in the document.
        total_chars: Total character count across all pages.
        filename: Original filename of the document.
    """

    pages: list[PageText] = field(default_factory=list)
    page_count: int = 0
    total_chars: int = 0
    filename: str = ""

    @property
    def full_text(self) -> str:
        """Concatenate all page texts with page separators.

        Returns:
            Full document text with page breaks indicated.
        """
        return "\n\n".join(page.text for page in self.pages)

    @property
    def has_text(self) -> bool:
        """Whether any text was extracted.

        Returns:
            True if at least one page has non-empty text.
        """
        return any(page.text.strip() for page in self.pages)


class DocumentTextExtractor(ABC):
    """Abstract interface for document text extraction.

    Implementations extract text with page-level provenance from
    specific document formats (PDF, DOCX, etc.).
    """

    @abstractmethod
    def extract(self, file_content: bytes, filename: str) -> ExtractedDocument:
        """Extract text from document content.

        Args:
            file_content: Raw bytes of the document file.
            filename: Original filename for metadata.

        Returns:
            Extracted document with page-level text.

        Raises:
            ValidationError: If the document cannot be parsed.
        """
        ...

    @abstractmethod
    def supports(self, filename: str) -> bool:
        """Check whether this extractor supports the given file type.

        Args:
            filename: Filename to check (extension-based).

        Returns:
            True if this extractor can handle the file.
        """
        ...
