import json
from typing import Any

from redis.asyncio import Redis


class GameStore:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def save(self, chat_id: int, state: dict[str, Any], ttl: int = 28800) -> None:
        await self.redis.set(f"game:{chat_id}", json.dumps(state), ex=ttl)

    async def load(self, chat_id: int) -> dict[str, Any] | None:
        raw = await self.redis.get(f"game:{chat_id}")
        return json.loads(raw) if raw else None

    async def delete(self, chat_id: int) -> None:
        await self.redis.delete(f"game:{chat_id}")