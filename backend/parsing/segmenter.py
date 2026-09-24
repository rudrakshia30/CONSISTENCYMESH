"""Clause segmentation module."""

from __future__ import annotations

import re

from backend.models.schemas import Clause
from backend.parsing.extractor import ExtractedDocument
from backend.parsing.metadata import extract_metadata


def detect_section_header(line: str) -> str | None:
    """Detect if a line of text represents a section header.

    Args:
        line: Single line of text.

    Returns:
        Cleaned section header string if detected, None otherwise.
    """
    cleaned = line.strip()
    if not cleaned or len(cleaned) > 80:
        return None

    # Specific uppercase header pattern (e.g., SECTION 1, ARTICLE IV, CONFIDENTIALITY)
    if re.match(r"^[A-Z\s\d\-]{4,50}:?$", cleaned) and len(cleaned.split()) <= 6:
        return cleaned

    # Explicit section keywords (e.g. SECTION 1 - TERM)
    if re.match(r"^(SECTION|ARTICLE|CLAUSE)\s+\d+.*$", cleaned, re.IGNORECASE) and len(cleaned) < 60:
        return cleaned

    # Short numbered heading (e.g., "1.1 Termination." or "1.1 Termination") under 35 chars
    if re.match(r"^\d+(\.\d+)*\s+[A-Z][a-zA-Z\s]{1,30}\.?$", cleaned) and len(cleaned) <= 35:
        return cleaned

    # Short title ending with colon
    if cleaned.endswith(":") and len(cleaned) < 50:
        return cleaned

    return None


def segment_clauses(extracted_doc: ExtractedDocument, document_id: str) -> list[Clause]:
    """Segment an ExtractedDocument into individual clauses with metadata.

    Args:
        extracted_doc: Extracted text with page-level provenance.
        document_id: Unique document identifier.

    Returns:
        List of segmented Clause models with extracted metadata.
    """
    clauses: list[Clause] = []
    global_idx = 0

    for page in extracted_doc.pages:
        page_num = page.page_number
        lines = page.text.split("\n")

        current_section: str | None = None
        current_buffer: list[str] = []

        def flush_buffer(section: str | None) -> None:
            nonlocal global_idx
            if not current_buffer:
                return

            raw_text = " ".join(" ".join(current_buffer).split())
            if not raw_text:
                return

            # Split into sentence-like clauses
            raw_clauses = re.split(r"(?<=\.)\s+(?=[A-Z0-9])", raw_text)

            for text_chunk in raw_clauses:
                clean_chunk = text_chunk.strip()
                if len(clean_chunk) < 20:
                    continue

                global_idx += 1
                clause_id = f"{document_id}_{page_num}_{global_idx}"
                meta = extract_metadata(clean_chunk)

                clauses.append(Clause(
                    clause_id=clause_id,
                    document_id=document_id,
                    page=page_num,
                    section=section,
                    text=clean_chunk,
                    entities=meta.entities,
                    dates=meta.dates,
                    monetary_values=meta.monetary_values,
                    topics=meta.topics,
                    numeric_attributes=meta.numeric_attributes,
                ))

            current_buffer.clear()

        for line in lines:
            header = detect_section_header(line)
            if header:
                flush_buffer(current_section)
                current_section = header
            else:
                if line.strip():
                    current_buffer.append(line.strip())

        flush_buffer(current_section)

    return clauses
