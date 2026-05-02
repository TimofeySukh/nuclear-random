from __future__ import annotations

import time

import redis

from .settings import settings


class RateLimitExceeded(RuntimeError):
    pass


class RedisRateLimiter:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def check(self, *, identity: str) -> None:
        if settings.random_rate_limit_per_minute <= 0:
            return

        minute = int(time.time() // 60)
        key = f"{settings.redis_key_prefix}:rate:{identity}:{minute}"
        count = int(self._client.incr(key))
        if count == 1:
            self._client.expire(key, 120)
        if count > settings.random_rate_limit_per_minute:
            raise RateLimitExceeded("Random request rate limit exceeded.")


def make_rate_limiter() -> RedisRateLimiter:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    return RedisRateLimiter(client)

