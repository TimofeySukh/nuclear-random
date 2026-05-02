from __future__ import annotations

from nuclear_random_api.stats import StatsStore


class FakePipeline:
    def __init__(self, client: "FakeRedis") -> None:
        self.client = client
        self.commands: list[tuple[object, ...]] = []

    def hincrby(self, *args: object) -> "FakePipeline":
        self.commands.append(("hincrby", args))
        return self

    def hset(self, *args: object, **kwargs: object) -> "FakePipeline":
        self.commands.append(("hset", args, kwargs))
        return self

    def zadd(self, *args: object) -> "FakePipeline":
        self.commands.append(("zadd", args))
        return self

    def zremrangebyscore(self, *args: object) -> "FakePipeline":
        self.commands.append(("zremrangebyscore", args))
        return self

    def expire(self, *args: object) -> "FakePipeline":
        self.commands.append(("expire", args))
        return self

    def zcount(self, *args: object) -> "FakePipeline":
        self.commands.append(("zcount", args))
        return self

    def hgetall(self, *args: object) -> "FakePipeline":
        self.commands.append(("hgetall", args))
        return self

    def execute(self) -> list[object]:
        results: list[object] = []
        for item in self.commands:
            name = item[0]
            args = item[1]
            kwargs = item[2] if len(item) > 2 else {}
            results.append(getattr(self.client, name)(*args, **kwargs))
        return results


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[bytes, bytes]] = {}
        self.sorted_sets: dict[str, dict[str, int]] = {}

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)

    def hincrby(self, key: str, field: str, amount: int) -> int:
        current = int(self.hashes.setdefault(key, {}).get(field.encode(), b"0"))
        value = current + amount
        self.hashes[key][field.encode()] = str(value).encode()
        return value

    def hset(self, key: str, *args: object, **kwargs: object) -> int:
        mapping = kwargs.get("mapping")
        if mapping is None and args and isinstance(args[-1], dict):
            mapping = args[-1].get("mapping")
        if mapping is None and len(args) == 2:
            mapping = {args[0]: args[1]}
        assert isinstance(mapping, dict)
        target = self.hashes.setdefault(key, {})
        for field, value in mapping.items():
            target[str(field).encode()] = str(value).encode()
        return len(mapping)

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        return self.hashes.get(key, {})

    def zadd(self, key: str, mapping: dict[str, int]) -> int:
        self.sorted_sets.setdefault(key, {}).update(mapping)
        return len(mapping)

    def zremrangebyscore(self, key: str, minimum: int, maximum: int) -> int:
        values = self.sorted_sets.setdefault(key, {})
        removed = [member for member, score in values.items() if minimum <= score <= maximum]
        for member in removed:
            del values[member]
        return len(removed)

    def zcount(self, key: str, minimum: int, maximum: int) -> int:
        return sum(1 for score in self.sorted_sets.get(key, {}).values() if minimum <= score <= maximum)

    def expire(self, key: str, seconds: int) -> bool:
        return True


def test_stats_store_records_click_and_random_draw() -> None:
    store = StatsStore(FakeRedis())

    store.record_click(
        timestamp_ns=1_000_000_000,
        source="test",
        dt_us=123,
        entropy_bytes_added=16,
    )
    store.record_random_draw(bits_used=7, rejected=1)
    status = store.status(pool_size_bytes=16)

    assert status.pool_size_bytes == 16
    assert status.total_clicks == 1
    assert status.total_entropy_bytes == 16
    assert status.total_random_requests == 1
    assert status.total_bits_served == 7
    assert status.total_rejections == 1
    assert status.last_click_source == "test"
    assert status.last_click_dt_us == 123
