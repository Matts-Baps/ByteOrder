"""Fixed-window rate limiting in Redis, to protect the shared GPU.

Two limits apply: per client (best effort, as the client address comes from
X-Forwarded-For) and per kitchen (a hard ceiling no client can get around).
"""
import logging
import time
from typing import Callable

from redis.exceptions import RedisError

log = logging.getLogger(__name__)
WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(self, redis, per_client: int, per_kitchen: int, clock: Callable[[], float] = time.time):
        self.redis = redis
        self.per_client = per_client
        self.per_kitchen = per_kitchen
        self.clock = clock

    async def _hit(self, key: str) -> int:
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, WINDOW_SECONDS)
        return count

    async def allow(self, client_key: str, kitchen_id: str) -> bool:
        window = int(self.clock() // WINDOW_SECONDS)
        try:
            kitchen = await self._hit(f"assistant:rl:kitchen:{kitchen_id}:{window}")
            if kitchen > self.per_kitchen:
                return False
            client = await self._hit(f"assistant:rl:client:{kitchen_id}:{client_key}:{window}")
            return client <= self.per_client
        except RedisError:
            # Failing open keeps the assistant usable if Redis blips. The model
            # server's own queue is the backstop.
            log.warning("Rate limiter unavailable, allowing request", exc_info=True)
            return True
