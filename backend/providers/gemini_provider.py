"""Google Gemini LLM provider implementation.

Fully async via httpx.AsyncClient. Handles timeout, retry with
exponential backoff, error classification, and metrics emission.
Model name and config sourced from environment variables.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx

from backend.core.config import Settings
from backend.core.errors import PermanentProviderError, RetryableProviderError
from backend.core.logging import LLMCallMetric, get_logger
from backend.models.schemas import Clause, RawAnswer, RawJudgment
from backend.prompts.consistency_judge import (
    build_consistency_prompt,
    estimate_prompt_tokens,
)
from backend.prompts.qa_prompt import build_qa_prompt
from backend.providers.base import LLMProvider

logger = get_logger("providers.gemini")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """Google Gemini provider using async HTTP calls.
    
    All calls go through httpx.AsyncClient with configurable timeout
    and bounded exponential backoff retry.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
        self._model = settings.gemini_model
        self._api_key = settings.gemini_api_key
        self._max_retries = settings.llm_max_retries
        # Metrics callback - set externally by the engine
        self._metrics_callback: Any = None

    async def analyze_consistency(
        self, clause_a: Clause, clause_b: Clause, context: dict[str, str]
    ) -> RawJudgment:
        system_prompt, user_prompt = build_consistency_prompt(clause_a, clause_b, context)
        estimated_tokens = estimate_prompt_tokens(system_prompt, user_prompt)

        response_text = await self._call_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            operation="consistency_judge",
            estimated_tokens=estimated_tokens,
        )

        try:
            data = self._parse_json_response(response_text)
            return RawJudgment.model_validate(data)
        except Exception as e:
            raise PermanentProviderError(
                "Failed to parse consistency judgment",
                detail=f"Parse error: {e}, response: {response_text[:500]}",
            ) from e

    async def classify_candidate(
        self, clause_a: Clause, clause_b: Clause
    ) -> bool:
        # Simple pass-through - deterministic filtering handles this
        return True

    async def answer_question(
        self, question: str, clauses: list[Clause]
    ) -> RawAnswer:
        system_prompt, user_prompt = build_qa_prompt(question, clauses)
        estimated_tokens = estimate_prompt_tokens(system_prompt, user_prompt)

        response_text = await self._call_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            operation="qa",
            estimated_tokens=estimated_tokens,
        )

        try:
            data = self._parse_json_response(response_text)
            return RawAnswer.model_validate(data)
        except Exception as e:
            raise PermanentProviderError(
                "Failed to parse QA answer",
                detail=f"Parse error: {e}, response: {response_text[:500]}",
            ) from e

    async def _call_gemini(
        self,
        system_prompt: str,
        user_prompt: str,
        operation: str,
        estimated_tokens: int,
    ) -> str:
        """Make an async HTTP call to the Gemini API with retry and backoff."""
        url = f"{GEMINI_API_BASE}/{self._model}:generateContent?key={self._api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        last_error: Exception | None = None
        start_time = time.monotonic()
        retry_count = 0

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(url, json=payload)
                latency_ms = (time.monotonic() - start_time) * 1000

                if response.status_code == 200:
                    self._emit_metric(LLMCallMetric(
                        provider="gemini",
                        operation=operation,
                        latency_ms=latency_ms,
                        success=True,
                        retry_count=retry_count,
                        estimated_tokens=estimated_tokens,
                    ))

                    resp_data = response.json()
                    # Extract text from Gemini response format
                    candidates = resp_data.get("candidates", [])
                    if not candidates:
                        raise PermanentProviderError(
                            "Empty response from Gemini",
                            detail=f"Response: {resp_data}",
                        )
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if not parts:
                        raise PermanentProviderError(
                            "No content parts in Gemini response",
                            detail=f"Response: {resp_data}",
                        )
                    return str(parts[0].get("text", ""))

                elif response.status_code == 429 or response.status_code >= 500:
                    retry_count += 1
                    last_error = RetryableProviderError(
                        f"Gemini API error {response.status_code}",
                        detail=f"Status: {response.status_code}, Body: {response.text[:500]}",
                    )
                    if attempt < self._max_retries:
                        backoff = min(2 ** attempt, 8)
                        logger.warning(
                            "Retryable Gemini error (attempt %d/%d): %d, backing off %ds",
                            attempt + 1, self._max_retries + 1, response.status_code, backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                else:
                    self._emit_metric(LLMCallMetric(
                        provider="gemini",
                        operation=operation,
                        latency_ms=latency_ms,
                        success=False,
                        retry_count=retry_count,
                        estimated_tokens=estimated_tokens,
                        error_type="permanent",
                    ))
                    raise PermanentProviderError(
                        f"Gemini API error {response.status_code}",
                        detail=f"Status: {response.status_code}, Body: {response.text[:500]}",
                    )

            except httpx.TimeoutException as e:
                retry_count += 1
                last_error = RetryableProviderError(
                    "Gemini API timeout",
                    detail=str(e),
                )
                if attempt < self._max_retries:
                    backoff = min(2 ** attempt, 8)
                    logger.warning(
                        "Gemini timeout (attempt %d/%d), backing off %ds",
                        attempt + 1, self._max_retries + 1, backoff,
                    )
                    await asyncio.sleep(backoff)
                    continue
            except (PermanentProviderError, RetryableProviderError):
                raise
            except httpx.HTTPError as e:
                retry_count += 1
                last_error = RetryableProviderError(
                    f"HTTP error: {e}",
                    detail=str(e),
                )
                if attempt < self._max_retries:
                    backoff = min(2 ** attempt, 8)
                    await asyncio.sleep(backoff)
                    continue

        latency_ms = (time.monotonic() - start_time) * 1000
        self._emit_metric(LLMCallMetric(
            provider="gemini",
            operation=operation,
            latency_ms=latency_ms,
            success=False,
            retry_count=retry_count,
            estimated_tokens=estimated_tokens,
            error_type="retryable_exhausted",
        ))

        if last_error:
            raise last_error
        raise RetryableProviderError("All retries exhausted")

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Parse JSON from LLM response text, handling markdown code blocks."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result: dict[str, Any] = json.loads(cleaned)
        return result

    def _emit_metric(self, metric: LLMCallMetric) -> None:
        """Emit a metric via the callback if registered."""
        if self._metrics_callback:
            self._metrics_callback(metric)
        logger.info(
            "LLM call: op=%s success=%s latency=%.0fms retries=%d tokens~%d",
            metric.operation,
            metric.success,
            metric.latency_ms,
            metric.retry_count,
            metric.estimated_tokens,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
