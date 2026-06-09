from __future__ import annotations

import json

import redis.asyncio as redis

from app.config import get_settings


class RedisConversationMemory:
    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 86_400):
        self.redis_url = redis_url or get_settings().redis_url
        self.ttl_seconds = ttl_seconds
        self.client = redis.from_url(self.redis_url, decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"cliniq:session:{session_id}:turns"

    async def get_history(self, session_id: str) -> list[dict]:
        values = await self.client.lrange(self._key(session_id), 0, 9)
        return [json.loads(value) for value in values]

    async def append_turn(self, session_id: str, role: str, content: str) -> None:
        key = self._key(session_id)
        await self.client.lpush(key, json.dumps({"role": role, "content": content}))
        await self.client.ltrim(key, 0, 9)
        await self.client.expire(key, self.ttl_seconds)

    async def close(self) -> None:
        await self.client.aclose()
