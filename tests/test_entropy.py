from __future__ import annotations

from nuclear_random_api.entropy import RedisEntropySource


class FakeRedis:
    def __init__(self) -> None:
        self.items: list[bytes] = []

    def rpush(self, key: str, *values: bytes) -> None:
        self.items.extend(values)

    def lpop(self, key: str, count: int | None = None) -> list[bytes] | bytes | None:
        if not self.items:
            return None
        if count is None:
            return self.items.pop(0)
        values = self.items[:count]
        del self.items[:count]
        return values

    def llen(self, key: str) -> int:
        return len(self.items)


def test_random_int_uses_rejection_sampling() -> None:
    client = FakeRedis()
    client.rpush("pool", bytes([254]), bytes([168]))
    source = RedisEntropySource(client, "pool")

    result = source.random_int(100)

    assert result.value == 42
    assert result.bits_used == 14
    assert result.rejected == 1
