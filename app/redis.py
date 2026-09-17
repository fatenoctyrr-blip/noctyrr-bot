import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)
redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)


async def initialize_redis() -> None:
    settings = get_settings()
    retries = max(1, settings.db_connect_retries)
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            await redis_client.ping()
            logger.info("Redis connection is ready")
            return
        except (OSError, RedisError) as exc:
            last_error = exc
            if attempt == retries:
                break
            logger.warning(
                "Redis unavailable (attempt %s/%s); retrying in %ss",
                attempt,
                retries,
                settings.db_retry_seconds,
            )
            await asyncio.sleep(max(1, settings.db_retry_seconds))

    raise RuntimeError(
        "Redis'ga ulanib bo'lmadi. REDIS_URL ni tekshiring: "
        "Docker Compose ichida host 'redis', alohida serverda esa "
        "Redis serverining haqiqiy hosti bo'lishi kerak."
    ) from last_error


async def close_redis() -> None:
    await redis_client.aclose()