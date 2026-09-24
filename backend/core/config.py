"""
Core configuration for ConsistencyMesh.

All configurable thresholds, limits, and settings are centralized here
and loaded from environment variables via pydantic-settings. No magic
constants should exist outside this module.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings loaded from environment variables.

    Every threshold, limit, and configuration value used anywhere in the
    application is defined here with a documented default. All values can
    be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- AI Provider ---
    gemini_api_key: str = Field(
        default="",
        description="Google Gemini API key. Required for real analysis.",
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model identifier to use for analysis.",
    )
    llm_timeout_seconds: int = Field(
        default=20,
        description="Timeout in seconds for each LLM API call.",
    )
    llm_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for retryable LLM errors.",
    )
    max_concurrent_llm_calls: int = Field(
        default=5,
        description="Maximum simultaneous in-flight LLM calls (semaphore bound).",
    )

    # --- Upload / Document Limits ---
    max_file_size_mb: int = Field(
        default=50,
        description="Maximum upload file size in megabytes.",
    )
    max_page_count: int = Field(
        default=500,
        description="Maximum number of pages per document.",
    )
    max_char_count: int = Field(
        default=2_000_000,
        description="Maximum extracted character count per document.",
    )
    max_documents_per_job: int = Field(
        default=6,
        description="Maximum number of documents in a single analysis job.",
    )
    min_documents_per_job: int = Field(
        default=2,
        description="Minimum number of documents for analysis.",
    )
    max_zip_ratio: float = Field(
        default=100.0,
        description="Maximum compression ratio for zip-based formats (e.g., DOCX).",
    )
    max_zip_entries: int = Field(
        default=1000,
        description="Maximum number of entries in a zip-based document.",
    )
    max_zip_entry_size_mb: int = Field(
        default=100,
        description="Maximum uncompressed size of a single zip entry in MB.",
    )

    # --- Candidate Matching ---
    candidate_similarity_threshold: float = Field(
        default=0.15,
        description="Minimum TF-IDF cosine similarity for candidate pair inclusion.",
    )
    candidate_topic_overlap_weight: float = Field(
        default=0.3,
        description="Weight for topic overlap in composite candidate score.",
    )
    candidate_entity_overlap_weight: float = Field(
        default=0.25,
        description="Weight for entity overlap in composite candidate score.",
    )
    candidate_date_overlap_weight: float = Field(
        default=0.15,
        description="Weight for date overlap in composite candidate score.",
    )
    candidate_tfidf_weight: float = Field(
        default=0.3,
        description="Weight for TF-IDF cosine similarity in composite candidate score.",
    )
    candidate_composite_threshold: float = Field(
        default=0.1,
        description="Minimum composite score for a candidate pair to be analyzed.",
    )

    # --- Rate Limiting ---
    rate_limit_requests_per_minute: int = Field(
        default=30,
        description="Maximum requests per minute per IP for rate-limited endpoints.",
    )

    # --- Redis / State ---
    redis_url: str = Field(
        default="",
        description="Redis connection URL. If empty, falls back to in-memory local store.",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Time-to-live for cached results in seconds.",
    )

    # --- Server ---
    environment: str = Field(
        default="development",
        description="Runtime environment: development, staging, production.",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL.",
    )
    cors_origins: str = Field(
        default="*",
        description="Comma-separated CORS allowed origins or * for all origins.",
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Maximum upload file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed list of CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_redis_configured(self) -> bool:
        """Whether a Redis URL is configured."""
        return bool(self.redis_url)


def get_settings() -> Settings:
    """Factory function for settings, used with FastAPI dependency injection."""
    return Settings()
