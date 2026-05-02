from __future__ import annotations

import pytest

from nuclear_random_api.rate_limit import RateLimitExceeded, RedisRateLimiter
from nuclear_random_api.settings import settings


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def incr(self, key: str) -> int:
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


def test_rate_limiter_blocks_after_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "random_rate_limit_per_minute", 2)
    limiter = RedisRateLimiter(FakeRedis())

    limiter.check(identity="client")
    limiter.check(identity="client")

    with pytest.raises(RateLimitExceeded):
        limiter.check(identity="client")

