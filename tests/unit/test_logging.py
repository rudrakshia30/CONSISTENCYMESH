"""Unit tests for logging and metrics."""
from __future__ import annotations

import logging

import pytest

from backend.core.logging import JobMetrics, LLMCallMetric, SecretSafeFormatter


@pytest.mark.unit
def test_secret_safe_formatter_redacts() -> None:
    formatter = SecretSafeFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="API key is api_key='sk-1234567890abcdef1234567890'",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "[REDACTED]" in formatted
    assert "sk-1234567890" not in formatted


@pytest.mark.unit
def test_redacts_google_api_key() -> None:
    formatter = SecretSafeFormatter()
    key = "AIzaSy" + "A" * 33
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"Using key {key}",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "[REDACTED]" in formatted
    assert key not in formatted


@pytest.mark.unit
def test_metrics_candidate_reduction_ratio() -> None:
    metrics = JobMetrics(job_id="job1")
    metrics.naive_candidate_pairs = 100
    metrics.filtered_candidate_pairs = 20
    assert metrics.candidate_reduction_ratio == 0.2
    assert metrics.candidate_reduction_percent == 80.0


@pytest.mark.unit
def test_metrics_cache_hit_rate() -> None:
    metrics = JobMetrics(job_id="job1")
    metrics.cache_hits = 3
    metrics.cache_misses = 1
    assert metrics.cache_hit_rate == 0.75


@pytest.mark.unit
def test_metrics_record_llm_call() -> None:
    metrics = JobMetrics(job_id="job1")
    call = LLMCallMetric(
        provider="gemini",
        operation="judge",
        latency_ms=150.0,
        success=True,
        retry_count=1,
        estimated_tokens=50,
        cache_hit=False,
    )
    metrics.record_llm_call(call)
    assert metrics.llm_calls_made == 1
    assert metrics.total_estimated_tokens == 50
    assert metrics.total_retries == 1
    assert metrics.cache_misses == 1


@pytest.mark.unit
def test_metrics_to_dict() -> None:
    metrics = JobMetrics(job_id="job1")
    metrics.naive_candidate_pairs = 50
    metrics.filtered_candidate_pairs = 10
    d = metrics.to_dict()
    assert d["job_id"] == "job1"
    assert d["candidate_reduction_percent"] == 80.0
    assert "p50_llm_latency_ms" in d


@pytest.mark.unit
def test_metrics_p50_p95() -> None:
    metrics = JobMetrics(job_id="job1")
    for lat in [100.0, 200.0, 300.0, 400.0, 500.0]:
        metrics.record_llm_call(
            LLMCallMetric(
                provider="gemini",
                operation="judge",
                latency_ms=lat,
                success=True,
            )
        )
    assert metrics.p50_llm_latency_ms == 300.0
    assert metrics.p95_llm_latency_ms == 500.0
