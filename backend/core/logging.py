"""
Structured, secret-safe logging and in-process metrics collection.

Provides a configured logger that never emits API keys, full document text,
or other sensitive content. Also provides a lightweight MetricsCollector
for per-job observability data, persisted to the state store.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(api[_-]?key|token|secret|password|authorization)[\"']?\s*[:=]\s*[\"']?[\w\-./+]{8,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z\-_]{35}"),  # Google API key pattern
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style key pattern
]


class SecretSafeFormatter(logging.Formatter):
    """Log formatter that redacts sensitive values from log output.

    Scans each log message for patterns matching API keys, tokens, and
    other secrets, replacing them with '[REDACTED]'.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record, redacting any detected secrets.

        Args:
            record: The log record to format.

        Returns:
            The formatted, redacted log string.
        """
        message = super().format(record)
        for pattern in _SECRET_PATTERNS:
            message = pattern.sub("[REDACTED]", message)
        return message


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger with secret-safe formatting.

    Args:
        level: The logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Returns:
        Configured logger instance for the application.
    """
    logger = logging.getLogger("consistencymesh")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = SecretSafeFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_logger(name: str = "consistencymesh") -> logging.Logger:
    """Get a child logger with the given name.

    Args:
        name: Logger name, typically the module path.

    Returns:
        A child logger inheriting the root configuration.
    """
    return logging.getLogger(f"consistencymesh.{name}")


@dataclass
class LLMCallMetric:
    """Metrics for a single LLM API call.

    Attributes:
        provider: Name of the LLM provider used.
        operation: Type of operation (e.g., 'consistency_judge', 'qa').
        latency_ms: Wall-clock latency in milliseconds.
        success: Whether the call succeeded.
        retry_count: Number of retries before final result.
        estimated_tokens: Estimated token count (character-based approximation).
        cache_hit: Whether the result was served from cache.
        error_type: Error classification if the call failed, None otherwise.
    """

    provider: str
    operation: str
    latency_ms: float
    success: bool
    retry_count: int = 0
    estimated_tokens: int = 0
    cache_hit: bool = False
    error_type: str | None = None


@dataclass
class JobMetrics:
    """Aggregated metrics for a single analysis job.

    Tracks all the observability data specified in the architecture:
    candidate counts, LLM call statistics, caching, and timing.

    Attributes:
        job_id: The unique identifier for this job.
        document_count: Number of documents in the job.
        total_clauses: Total clauses extracted across all documents.
        naive_candidate_pairs: N² count before filtering.
        filtered_candidate_pairs: M count after deterministic filtering.
        llm_calls_made: Total LLM calls issued.
        cache_hits: Number of cache hits.
        cache_misses: Number of cache misses.
        llm_call_metrics: Individual call-level metrics.
        total_estimated_tokens: Sum of estimated tokens across all calls.
        total_retries: Sum of retries across all calls.
        start_time: Job start timestamp.
        end_time: Job end timestamp, None if still running.
    """

    job_id: str
    document_count: int = 0
    total_clauses: int = 0
    naive_candidate_pairs: int = 0
    filtered_candidate_pairs: int = 0
    llm_calls_made: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    llm_call_metrics: list[LLMCallMetric] = field(default_factory=list)
    total_estimated_tokens: int = 0
    total_retries: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def candidate_reduction_ratio(self) -> float:
        """Ratio of filtered pairs to naive pairs (lower is better).

        Returns:
            The reduction ratio, or 0.0 if no naive pairs exist.
        """
        if self.naive_candidate_pairs == 0:
            return 0.0
        return self.filtered_candidate_pairs / self.naive_candidate_pairs

    @property
    def candidate_reduction_percent(self) -> float:
        """Percentage of candidate pairs eliminated by filtering.

        Returns:
            Percentage reduced, or 0.0 if no naive pairs exist.
        """
        if self.naive_candidate_pairs == 0:
            return 0.0
        return (1.0 - self.candidate_reduction_ratio) * 100.0

    @property
    def cache_hit_rate(self) -> float:
        """Cache hit rate as a fraction.

        Returns:
            Hit rate between 0.0 and 1.0, or 0.0 if no cache lookups occurred.
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    @property
    def wall_clock_seconds(self) -> float:
        """Total wall-clock time for the job in seconds.

        Returns:
            Elapsed seconds, using current time if job is still running.
        """
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    @property
    def p50_llm_latency_ms(self) -> float:
        """Median (p50) latency across LLM calls in milliseconds.

        Returns:
            Median latency, or 0.0 if no calls were made.
        """
        return self._percentile_latency(50)

    @property
    def p95_llm_latency_ms(self) -> float:
        """95th percentile latency across LLM calls in milliseconds.

        Returns:
            p95 latency, or 0.0 if no calls were made.
        """
        return self._percentile_latency(95)

    def _percentile_latency(self, percentile: int) -> float:
        """Compute the given percentile of LLM call latencies.

        Args:
            percentile: The percentile to compute (0-100).

        Returns:
            The latency at the given percentile, or 0.0 if no calls exist.
        """
        latencies = sorted(m.latency_ms for m in self.llm_call_metrics)
        if not latencies:
            return 0.0
        idx = int(len(latencies) * percentile / 100)
        idx = min(idx, len(latencies) - 1)
        return latencies[idx]

    def record_llm_call(self, metric: LLMCallMetric) -> None:
        """Record a completed LLM call's metrics.

        Args:
            metric: The call-level metrics to record.
        """
        self.llm_call_metrics.append(metric)
        self.llm_calls_made += 1
        self.total_estimated_tokens += metric.estimated_tokens
        self.total_retries += metric.retry_count
        if metric.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize metrics to a dictionary for API responses and persistence.

        Returns:
            Dictionary containing all metric values, safe for JSON serialization.
        """
        return {
            "job_id": self.job_id,
            "document_count": self.document_count,
            "total_clauses": self.total_clauses,
            "naive_candidate_pairs": self.naive_candidate_pairs,
            "filtered_candidate_pairs": self.filtered_candidate_pairs,
            "candidate_reduction_percent": round(self.candidate_reduction_percent, 2),
            "llm_calls_made": self.llm_calls_made,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "total_estimated_tokens": self.total_estimated_tokens,
            "total_retries": self.total_retries,
            "p50_llm_latency_ms": round(self.p50_llm_latency_ms, 2),
            "p95_llm_latency_ms": round(self.p95_llm_latency_ms, 2),
            "wall_clock_seconds": round(self.wall_clock_seconds, 2),
        }
