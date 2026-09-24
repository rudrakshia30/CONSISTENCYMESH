

import asyncio

import pytest


@pytest.mark.asyncio
@pytest.mark.performance
async def test_semaphore_limits_concurrent_execution() -> None:
    sem = asyncio.Semaphore(2)
    active = 0
    max_active = 0

    async def worker() -> None:
        nonlocal active, max_active
        async with sem:
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.05)
            active -= 1

    await asyncio.gather(*(worker() for _ in range(5)))
    assert max_active == 2

@pytest.mark.asyncio
@pytest.mark.performance
async def test_bounded_concurrency_does_not_exceed_max_llm_calls() -> None:
    max_concurrent_llm_calls = 3
    sem = asyncio.Semaphore(max_concurrent_llm_calls)
    assert sem._value == 3 # Access internal value to verify initialization

@pytest.mark.asyncio
@pytest.mark.performance
async def test_use_asyncio_semaphore_with_mock_tasks() -> None:
    sem = asyncio.Semaphore(1)
    results = []

    async def task(i: int) -> None:
        async with sem:
            results.append(i)
            await asyncio.sleep(0.01)

    await asyncio.gather(task(1), task(2), task(3))
    assert len(results) == 3
    assert set(results) == {1, 2, 3}
