from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StateStore(ABC):
    """
    Abstract base class defining the interface for a state store.
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """
        Get a value by its key.

        Args:
            key: The key to retrieve.

        Returns:
            The stored value, or None if not found or expired.
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value with an optional time-to-live (TTL).

        Args:
            key: The key to store the value under.
            value: The value to store.
            ttl: Optional time-to-live in seconds.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """
        Delete a value by its key.

        Args:
            key: The key to delete.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the store.

        Args:
            key: The key to check.

        Returns:
            True if the key exists and has not expired, False otherwise.
        """
        pass

    @abstractmethod
    async def keys(self, pattern: str = '*') -> list[str]:
        """
        List keys matching a specific pattern.

        Args:
            pattern: A string pattern to match keys against (e.g., '*').

        Returns:
            A list of matching keys.
        """
        pass


class CacheStore(ABC):
    """
    Abstract base class defining the interface for a cache store.
    """

    @abstractmethod
    async def get_cached(self, key: str) -> Any | None:
        """
        Get a cached value by its key.

        Args:
            key: The cache key to retrieve.

        Returns:
            The cached value, or None if not found or expired.
        """
        pass

    @abstractmethod
    async def set_cached(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Cache a value with an optional time-to-live (TTL).

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Optional time-to-live in seconds.
        """
        pass

    @abstractmethod
    async def invalidate(self, key: str) -> None:
        """
        Invalidate a cache entry.

        Args:
            key: The cache key to invalidate.
        """
        pass

    @abstractmethod
    async def has(self, key: str) -> bool:
        """
        Check if a cache entry exists.

        Args:
            key: The cache key to check.

        Returns:
            True if the entry exists and has not expired, False otherwise.
        """
        pass
