from __future__ import annotations

from dataclasses import dataclass

import redis

from .settings import settings


class EntropyPoolEmpty(RuntimeError):
    pass


@dataclass(frozen=True)
class DrawResult:
    value: int
    bits_used: int
    rejected: int
    pool_size_bytes: int


class RedisEntropySource:
    def __init__(self, client: redis.Redis, key: str) -> None:
        self._client = client
        self._key = key
        self._buffer = bytearray()
        self._bit_offset = 0

    def random_int(self, max_value: int) -> DrawResult:
        if max_value < 0:
            raise ValueError("max_value must be greater than or equal to zero.")
        if max_value == 0:
            return DrawResult(value=0, bits_used=0, rejected=0, pool_size_bytes=self.pool_size())

        bit_count = max_value.bit_length()
        rejected = 0
        bits_used = 0

        while True:
            candidate = self._read_bits(bit_count)
            bits_used += bit_count
            if candidate <= max_value:
                return DrawResult(
                    value=candidate,
                    bits_used=bits_used,
                    rejected=rejected,
                    pool_size_bytes=self.pool_size(),
                )
            rejected += 1

    def pool_size(self) -> int:
        return int(self._client.llen(self._key))

    def _read_bits(self, bit_count: int) -> int:
        value = 0
        for _ in range(bit_count):
            if self._bit_offset >= len(self._buffer) * 8:
                self._load_more()
            byte_index = self._bit_offset // 8
            bit_index = 7 - (self._bit_offset % 8)
            bit = (self._buffer[byte_index] >> bit_index) & 1
            value = (value << 1) | bit
            self._bit_offset += 1
        return value

    def _load_more(self) -> None:
        chunk = self._client.lpop(self._key, settings.redis_max_lpop_count)
        if not chunk:
            raise EntropyPoolEmpty("The entropy pool is empty.")

        self._buffer = bytearray()
        for item in chunk if isinstance(chunk, list) else [chunk]:
            if isinstance(item, int):
                self._buffer.append(item)
            else:
                self._buffer.extend(item[:1])
        self._bit_offset = 0


def make_entropy_source() -> RedisEntropySource:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    return RedisEntropySource(client, settings.redis_entropy_key)

