"""Upload validation and security checks."""

from __future__ import annotations

import io
import os
import re
import zipfile

from backend.core.config import Settings
from backend.core.errors import SecurityError, ValidationError


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by stripping path components and dangerous characters.

    Replaces spaces with underscores and keeps alphanumeric, dash, underscore, and dot.

    Args:
        filename: Original filename.

    Returns:
        Sanitized safe filename string.
    """
    base_name = os.path.basename(filename)
    base_name = base_name.replace(" ", "_")
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "", base_name)
    if not sanitized:
        return "unnamed_file"
    return sanitized


def validate_docx_zip_safety(file_content: bytes, settings: Settings) -> None:
    """Validate DOCX zip structure against zip bombs and excessive entries.

    Args:
        file_content: DOCX raw bytes.
        settings: Application settings.

    Raises:
        SecurityError: If compression ratio or entry count exceeds bounds.
        ValidationError: If the file is not a valid zip archive.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
            total_uncompressed = 0
            num_entries = len(zf.infolist())

            if num_entries > settings.max_zip_entries:
                raise SecurityError("Too many entries in DOCX archive.")

            for info in zf.infolist():
                entry_size_mb = info.file_size / (1024 * 1024)
                if entry_size_mb > settings.max_zip_entry_size_mb:
                    raise SecurityError(f"Entry {info.filename} exceeds maximum size.")
                total_uncompressed += info.file_size

            compressed_size = len(file_content)
            if compressed_size > 0:
                ratio = total_uncompressed / compressed_size
                if ratio > settings.max_zip_ratio:
                    raise SecurityError("Compression ratio too high, possible zip bomb.")
    except zipfile.BadZipFile:
        raise ValidationError("Invalid DOCX format.")


def validate_upload(filename: str, file_content: bytes, settings: Settings) -> None:
    """Validate upload against file size, magic bytes, and extension rules.

    Args:
        filename: Upload filename.
        file_content: Raw bytes.
        settings: Application settings.

    Raises:
        ValidationError: If validation fails.
    """
    if not file_content or len(file_content) == 0:
        raise ValidationError("File is empty (zero bytes).")

    if len(file_content) > settings.max_file_size_bytes:
        raise ValidationError(
            f"File exceeds maximum allowed size ({settings.max_file_size_mb} MB)."
        )

    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".pdf", ".docx", ".txt"}
    if ext not in allowed_exts:
        raise ValidationError(f"File extension '{ext}' is not supported. Allowed: .pdf, .docx, .txt")

    if ext == ".pdf":
        if not file_content.startswith(b"%PDF"):
            raise ValidationError("Invalid PDF magic bytes.")
    elif ext == ".docx":
        if not file_content.startswith(b"\x50\x4B\x03\x04"):
            raise ValidationError("Invalid DOCX magic bytes.")
        validate_docx_zip_safety(file_content, settings)
