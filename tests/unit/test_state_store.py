"""Unit tests for LocalStateStore and LocalCacheStore."""
from __future__ import annotations

import asyncio

import pytest

from backend.state.local_store import LocalCacheStore, LocalStateStore


@pytest.fixture
def state_store() -> LocalStateStore:
    return LocalStateStore()


@pytest.fixture
def cache_store() -> LocalCacheStore:
    return LocalCacheStore()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_and_get(state_store: LocalStateStore) -> None:
    await state_store.set("key1", "val1")
    assert await state_store.get("key1") == "val1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key(state_store: LocalStateStore) -> None:
    assert await state_store.get("missing") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_removes_entry(state_store: LocalStateStore) -> None:
    await state_store.set("key1", "val1")
    await state_store.delete("key1")
    assert await state_store.get("key1") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exists_returns_correct_boolean(state_store: LocalStateStore) -> None:
    await state_store.set("key1", "val1")
    assert await state_store.exists("key1") is True
    assert await state_store.exists("missing") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keys_with_pattern_matching(state_store: LocalStateStore) -> None:
    await state_store.set("user:1:name", "Alice")
    await state_store.set("user:2:name", "Bob")
    await state_store.set("config:x", "y")
    keys = await state_store.keys("user:*:name")
    assert len(keys) == 2
    assert "user:1:name" in keys
    assert "user:2:name" in keys


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttl_expiry(state_store: LocalStateStore) -> None:
    await state_store.set("temp_key", "temp_val", ttl=1)
    assert await state_store.get("temp_key") == "temp_val"
    await asyncio.sleep(1.1)
    assert await state_store.get("temp_key") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_localcachestore_set_cached(cache_store: LocalCacheStore) -> None:
    await cache_store.set_cached("k1", "v1")
    assert await cache_store.get_cached("k1") == "v1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_localcachestore_get_cached(cache_store: LocalCacheStore) -> None:
    await cache_store.set_cached("k1", "v1")
    assert await cache_store.get_cached("k1") == "v1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_localcachestore_has(cache_store: LocalCacheStore) -> None:
    await cache_store.set_cached("k1", "v1")
    assert await cache_store.has("k1") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_localcachestore_invalidate(cache_store: LocalCacheStore) -> None:
    await cache_store.set_cached("k1", "v1")
    await cache_store.invalidate("k1")
    assert await cache_store.has("k1") is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_parity_between_statestore_and_cachestore_interfaces(cache_store: LocalCacheStore) -> None:
    assert hasattr(cache_store, "set") and hasattr(cache_store, "set_cached")
    assert hasattr(cache_store, "get") and hasattr(cache_store, "get_cached")
    assert hasattr(cache_store, "delete") and hasattr(cache_store, "invalidate")
    assert hasattr(cache_store, "exists") and hasattr(cache_store, "has")
