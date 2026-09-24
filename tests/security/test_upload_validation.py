"""Security tests for upload validation."""
from __future__ import annotations

import io
import zipfile

import pytest

from backend.core.config import Settings
from backend.core.errors import ValidationError
from backend.security.validation import (
    sanitize_filename,
    validate_upload,
)


def _make_valid_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


@pytest.mark.security
def test_valid_pdf_passes() -> None:
    settings = Settings()
    content = b"%PDF-1.4 valid pdf content header"
    validate_upload("sample.pdf", content, settings)


@pytest.mark.security
def test_valid_docx_passes() -> None:
    settings = Settings()
    content = _make_valid_docx()
    validate_upload("sample.docx", content, settings)


@pytest.mark.security
def test_invalid_extension_rejected() -> None:
    settings = Settings()
    content = b"%PDF-1.4 text"
    with pytest.raises(ValidationError):
        validate_upload("script.sh", content, settings)

    with pytest.raises(ValidationError):
        validate_upload("malicious.exe", content, settings)


@pytest.mark.security
def test_zero_byte_file_rejected() -> None:
    settings = Settings()
    with pytest.raises(ValidationError):
        validate_upload("empty.pdf", b"", settings)


@pytest.mark.security
def test_oversized_file_rejected() -> None:
    settings = Settings(max_file_size_mb=1)
    large_content = b"%PDF-1.4" + b"x" * (2 * 1024 * 1024)
    with pytest.raises(ValidationError):
        validate_upload("large.pdf", large_content, settings)


@pytest.mark.security
def test_magic_byte_mismatch_rejected() -> None:
    settings = Settings()
    fake_pdf = b"Plain text content not a PDF"
    with pytest.raises(ValidationError):
        validate_upload("fake.pdf", fake_pdf, settings)


@pytest.mark.security
def test_sanitize_filename() -> None:
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("valid_file-123.pdf") == "valid_file-123.pdf"
    assert sanitize_filename("file with spaces.docx") == "file_with_spaces.docx"
