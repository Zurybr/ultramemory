"""Redis client wrapper for caching and pub/sub."""

import json
from typing import Any
import redis.asyncio as redis


class RedisClientWrapper:
    """Wrapper for Redis client."""

    def __init__(self, url: str = "redis://localhost:6379", password: str | None = None):
        if password:
            url = url.replace("redis://", f"redis://:{password}@")
        self.redis = redis.from_url(url, decode_responses=True)

    async def set(self, key: str, value: Any, ex: int | None = None):
        """Set a value."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis.set(key, value, ex=ex)

    async def get(self, key: str) -> Any | None:
        """Get a value."""
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def delete(self, key: str):
        """Delete a key."""
        await self.redis.delete(key)

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern."""
        return await self.redis.keys(pattern)

    async def publish(self, channel: str, message: Any):
        """Publish a message."""
        if isinstance(message, (dict, list)):
            message = json.dumps(message)
        await self.redis.publish(channel, message)

    async def subscribe(self, channel: str):
        """Subscribe to a channel."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def health(self) -> bool:
        """Check if Redis is healthy."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def close(self):
        """Close the connection."""
        await self.redis.close()
