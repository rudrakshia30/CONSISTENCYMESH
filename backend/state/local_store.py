"""In-memory implementations of StateStore and CacheStore for development and testing."""

from __future__ import annotations

import fnmatch
import time
from typing import Any

from backend.state.base import CacheStore, StateStore


class LocalStateStore(StateStore):
    """In-memory implementation of StateStore for development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}

    def _cleanup_expired(self, key: str) -> bool:
        if key not in self._store:
            return False

        _, expiry = self._store[key]
        if expiry is not None and time.time() > expiry:
            del self._store[key]
            return False

        return True

    async def get(self, key: str) -> Any | None:
        if not self._cleanup_expired(key):
            return None
        return self._store[key][0]

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.time() + ttl if ttl is not None else None
        self._store[key] = (value, expiry)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def exists(self, key: str) -> bool:
        return self._cleanup_expired(key)

    async def keys(self, pattern: str = "*") -> list[str]:
        valid_keys = [k for k in list(self._store.keys()) if self._cleanup_expired(k)]

        if pattern == "*":
            return valid_keys

        return [k for k in valid_keys if fnmatch.fnmatch(k, pattern)]


class LocalCacheStore(CacheStore):
    """In-memory implementation of CacheStore for development and testing."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, float | None]] = {}

    def _cleanup_expired(self, key: str) -> bool:
        if key not in self._cache:
            return False

        _, expiry = self._cache[key]
        if expiry is not None and time.time() > expiry:
            del self._cache[key]
            return False

        return True

    async def get_cached(self, key: str) -> Any | None:
        if not self._cleanup_expired(key):
            return None
        return self._cache[key][0]

    async def set_cached(self, key: str, value: Any, ttl: int | None = None) -> None:
        expiry = time.time() + ttl if ttl is not None else None
        self._cache[key] = (value, expiry)

    async def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    async def has(self, key: str) -> bool:
        return self._cleanup_expired(key)

    # Aliases for StateStore interface compatibility
    async def get(self, key: str) -> Any | None:
        return await self.get_cached(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self.set_cached(key, value, ttl)

    async def delete(self, key: str) -> None:
        await self.invalidate(key)

    async def exists(self, key: str) -> bool:
        return await self.has(key)
