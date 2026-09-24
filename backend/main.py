"""
FastAPI application entry point for ConsistencyMesh.

Creates and configures the application with dependency injection
for all services, providers, and stores. Handles startup/shutdown
lifecycle and middleware configuration.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import analysis, documents, qa
from backend.core.config import Settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import get_logger, setup_logging
from backend.jobs.job_manager import JobManager
from backend.jobs.worker import JobWorker
from backend.providers.gemini_provider import GeminiProvider
from backend.providers.mock_provider import MockProvider
from backend.security.rate_limit import RateLimiter
from backend.services.document_service import DocumentService
from backend.services.qa_service import QAService
from backend.state.local_store import LocalCacheStore, LocalStateStore

logger = get_logger("main")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown.

    Sets up all services, stores, and providers on startup.
    Cleans up resources on shutdown.
    """
    settings = Settings()
    setup_logging(settings.log_level)

    logger.info("Starting ConsistencyMesh...")

    # Create state and cache stores
    if settings.is_redis_configured:
        try:
            from backend.state.redis_store import RedisCacheStore, RedisStateStore

            state_store = RedisStateStore(settings.redis_url)
            cache_store = RedisCacheStore(settings.redis_url)
            logger.info("Using Redis state and cache stores")
        except Exception as e:
            logger.warning("Redis connection failed (%s), falling back to local stores", e)
            state_store = LocalStateStore()
            cache_store = LocalCacheStore()
    else:
        logger.warning(
            "REDIS_URL not configured. Using in-memory local stores. "
            "This is a single-process, non-horizontally-scalable mode."
        )
        state_store = LocalStateStore()
        cache_store = LocalCacheStore()

    # Create LLM provider
    if settings.gemini_api_key:
        logger.info("Using GeminiProvider with model %s", settings.gemini_model)
        provider = GeminiProvider(settings)
    else:
        logger.warning(
            "GEMINI_API_KEY not configured. Using MockProvider. "
            "Analysis will use deterministic mock responses."
        )
        provider = MockProvider()

    # Create rate limiter
    rate_limiter = RateLimiter(
        max_requests=settings.rate_limit_requests_per_minute,
        window_seconds=60,
    )

    # Create services
    doc_service = DocumentService(
        state_store=state_store,
        settings=settings,
    )

    job_manager = JobManager(
        state_store=state_store,
        settings=settings,
    )

    job_worker = JobWorker(
        settings=settings,
        job_manager=job_manager,
        provider=provider,
        state_store=state_store,
        cache_store=cache_store,
    )

    qa_service = QAService(
        provider=provider,
        state_store=state_store,
        settings=settings,
    )

    # Wire dependencies into API route modules
    documents._document_service = doc_service
    documents._rate_limiter = rate_limiter
    documents._settings = settings

    analysis._job_manager = job_manager
    analysis._job_worker = job_worker
    analysis._settings = settings

    qa._qa_service = qa_service
    qa._rate_limiter = rate_limiter

    logger.info("ConsistencyMesh ready")

    yield

    # Shutdown
    logger.info("Shutting down ConsistencyMesh...")

    await job_worker.shutdown()

    if hasattr(provider, "close"):
        await provider.close()

    logger.info("ConsistencyMesh stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        The fully configured FastAPI application instance.
    """
    application = FastAPI(
        title="ConsistencyMesh",
        description=(
            "Multi-document consistency analysis system. "
            "Detects contradictions, overrides, and gaps across "
            "related legal and business documents."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    settings = Settings()

    # Register global exception handlers
    register_exception_handlers(application)

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    application.include_router(documents.router)
    application.include_router(analysis.router)
    application.include_router(qa.router)

    @application.get("/", tags=["root"])
    async def root() -> dict[str, str]:
        """Root endpoint returning API health status."""
        return {
            "name": "ConsistencyMesh",
            "version": "0.1.0",
            "status": "healthy",
        }

    return application


# Create the application instance
app = create_app()
