"""Global exception handling with safe error responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.core.logging import get_logger

logger = get_logger("errors")


class ConsistencyMeshError(Exception):
    """Base exception for all ConsistencyMesh application errors."""

    def __init__(
        self,
        message: str = "An internal error occurred.",
        status_code: int = 500,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class ValidationError(ConsistencyMeshError):
    """Raised when input validation fails (file format, size, etc.)."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message=message, status_code=400, detail=detail)


class DocumentNotFoundError(ConsistencyMeshError):
    """Raised when a requested document does not exist."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            message="Document not found.",
            status_code=404,
            detail=f"Document ID: {document_id}",
        )


class JobNotFoundError(ConsistencyMeshError):
    """Raised when a requested job does not exist."""

    def __init__(self, job_id: str) -> None:
        super().__init__(
            message="Analysis job not found.",
            status_code=404,
            detail=f"Job ID: {job_id}",
        )


class ProviderError(ConsistencyMeshError):
    """Base exception for LLM provider errors."""

    pass


class RetryableProviderError(ProviderError):
    """LLM provider error that may succeed on retry (timeout, 5xx, rate limit)."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(
            message="AI service temporarily unavailable. Please try again.",
            status_code=503,
            detail=detail or message,
        )


class PermanentProviderError(ProviderError):
    """LLM provider error that will not succeed on retry (4xx, schema error)."""

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(
            message="AI analysis could not be completed.",
            status_code=502,
            detail=detail or message,
        )


class RateLimitError(ConsistencyMeshError):
    """Raised when a client exceeds the request rate limit."""

    def __init__(self, message: str = "Rate limit exceeded. Please wait before making more requests.") -> None:
        super().__init__(
            message=message,
            status_code=429,
        )


class SecurityError(ConsistencyMeshError):
    """Raised when a security check fails (zip bomb, path traversal, etc.)."""

    def __init__(self, message: str = "Request rejected for security reasons.") -> None:
        super().__init__(message=message, status_code=400)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application."""

    @app.exception_handler(ConsistencyMeshError)
    async def handle_app_error(
        request: Request, exc: ConsistencyMeshError
    ) -> JSONResponse:
        if exc.detail:
            logger.error(
                "Application error: %s | Detail: %s | Path: %s",
                exc.message,
                exc.detail,
                request.url.path,
            )
        else:
            logger.warning(
                "Application error: %s | Path: %s",
                exc.message,
                request.url.path,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_response(exc.message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unexpected error on %s: %s",
            request.url.path,
            type(exc).__name__,
        )
        return JSONResponse(
            status_code=500,
            content=_error_response("An internal error occurred. Please try again later."),
        )


def _error_response(message: str) -> dict[str, Any]:
    return {"error": True, "message": message}
