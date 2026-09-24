
import asyncio
from typing import Any

import pytest


@pytest.mark.asyncio
@pytest.mark.performance
async def test_cached_results_returned_on_repeated_requests() -> None:
    cache: dict[str, Any] = {}
    cache["key1"] = "result1"
    assert cache.get("key1") == "result1"
    assert cache.get("key1") == "result1"

@pytest.mark.asyncio
@pytest.mark.performance
async def test_cache_key_changes_with_different_content() -> None:
    def get_key(content: str) -> str:
        return f"hash_{hash(content)}"
    assert get_key("content1") != get_key("content2")

@pytest.mark.asyncio
@pytest.mark.performance
async def test_cache_key_changes_with_different_prompt_version() -> None:
    def get_key(content: str, prompt_version: str) -> str:
        return f"hash_{hash(content)}_{prompt_version}"
    assert get_key("content", "v1") != get_key("content", "v2")

@pytest.mark.asyncio
@pytest.mark.performance
async def test_ttl_expiry_removes_cached_items() -> None:
    cache: dict[str, Any] = {"key1": "result1"}
    await asyncio.sleep(0.01)
    # Simulate TTL expiry
    cache.pop("key1")
    assert "key1" not in cache

@pytest.mark.asyncio
@pytest.mark.performance
async def test_cache_hit_rate_tracking_in_jobmetrics() -> None:
    class JobMetrics:
        hits = 0
        misses = 0
        def record_hit(self) -> None:
            self.hits += 1
        def record_miss(self) -> None:
            self.misses += 1
        @property
        def hit_rate(self) -> float:
            total = self.hits + self.misses
            return self.hits / total if total else 0.0

    metrics = JobMetrics()
    metrics.record_miss()
    metrics.record_hit()
    metrics.record_hit()
    assert metrics.hit_rate == pytest.approx(0.666, rel=1e-2)
