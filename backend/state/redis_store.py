import json
from typing import Any

import redis.asyncio as aioredis

from backend.core.logging import get_logger
from backend.state.base import CacheStore, StateStore

logger = get_logger(__name__)


class RedisStateStore(StateStore):
    """
    Redis implementation of StateStore.
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initialize the Redis state store.
        
        Args:
            redis_url: The URL of the Redis server.
        """
        self.redis_url = redis_url
        self.client = aioredis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the state store.
        """
        try:
            val = await self.client.get(key)
            if val is not None:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from RedisStateStore: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in the state store.
        """
        try:
            val = json.dumps(value)
            if ttl is not None:
                await self.client.setex(key, ttl, val)
            else:
                await self.client.set(key, val)
        except Exception as e:
            logger.error(f"Error setting key {key} in RedisStateStore: {e}")

    async def delete(self, key: str) -> None:
        """
        Delete a value from the state store.
        """
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key} from RedisStateStore: {e}")

    async def keys(self, pattern: str) -> list[str]:
        """
        Get all keys matching a pattern.
        """
        try:
            return await self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys for pattern {pattern} from RedisStateStore: {e}")
            return []

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the state store.
        """
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking existence for key {key} in RedisStateStore: {e}")
            return False


class RedisCacheStore(CacheStore):
    """
    Redis implementation of CacheStore.
    Uses 'cache:' prefix for keys to namespace them.
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initialize the Redis cache store.
        
        Args:
            redis_url: The URL of the Redis server.
        """
        self.redis_url = redis_url
        self.client = aioredis.from_url(redis_url, decode_responses=True)
        self.prefix = "cache:"

    def _make_key(self, key: str) -> str:
        """
        Prefix the key with the cache namespace.
        """
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """
        Get a value from the cache store.
        """
        try:
            val = await self.client.get(self._make_key(key))
            if val is not None:
                return json.loads(val)
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from RedisCacheStore: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set a value in the cache store.
        """
        try:
            val = json.dumps(value)
            prefixed_key = self._make_key(key)
            if ttl is not None:
                await self.client.setex(prefixed_key, ttl, val)
            else:
                await self.client.set(prefixed_key, val)
        except Exception as e:
            logger.error(f"Error setting key {key} in RedisCacheStore: {e}")

    async def delete(self, key: str) -> None:
        """
        Delete a value from the cache store.
        """
        try:
            await self.client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Error deleting key {key} from RedisCacheStore: {e}")

    async def keys(self, pattern: str) -> list[str]:
        """
        Get all keys matching a pattern.
        """
        try:
            prefixed_pattern = self._make_key(pattern)
            keys = await self.client.keys(prefixed_pattern)
            prefix_len = len(self.prefix)
            # Remove prefix from returned keys
            return [k[prefix_len:] for k in keys]
        except Exception as e:
            logger.error(f"Error getting keys for pattern {pattern} from RedisCacheStore: {e}")
            return []

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache store.
        """
        try:
            return await self.client.exists(self._make_key(key)) > 0
        except Exception as e:
            logger.error(f"Error checking existence for key {key} in RedisCacheStore: {e}")
            return False
