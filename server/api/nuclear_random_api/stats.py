from __future__ import annotations

import time
from dataclasses import dataclass

import redis

from .settings import settings


@dataclass(frozen=True)
class ServiceStatus:
    pool_size_bytes: int
    total_clicks: int
    total_entropy_bytes: int
    total_raw_bits: int
    total_extracted_bits: int
    total_discarded_pairs: int
    total_random_requests: int
    total_bits_served: int
    total_rejections: int
    clicks_last_minute: int
    estimated_cpm: int
    last_click_at_unix: float | None
    last_click_source: str | None
    last_click_dt_us: int | None


class StatsStore:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client
        self._stats_key = f"{settings.redis_key_prefix}:stats"
        self._clicks_key = f"{settings.redis_key_prefix}:click_times"

    def record_click(
        self,
        *,
        timestamp_ns: int,
        source: str,
        dt_us: int,
        raw_bits_seen: int,
        extracted_bits_added: int,
        discarded_pairs: int,
        entropy_bytes_added: int,
    ) -> None:
        timestamp_ms = timestamp_ns // 1_000_000
        member = f"{timestamp_ns}:{source}"
        min_score = timestamp_ms - settings.status_click_window_seconds * 1000

        pipe = self._client.pipeline()
        pipe.hincrby(self._stats_key, "total_clicks", 1)
        pipe.hincrby(self._stats_key, "total_raw_bits", raw_bits_seen)
        pipe.hincrby(self._stats_key, "total_extracted_bits", extracted_bits_added)
        pipe.hincrby(self._stats_key, "total_discarded_pairs", discarded_pairs)
        pipe.hincrby(self._stats_key, "total_entropy_bytes", entropy_bytes_added)
        pipe.hset(
            self._stats_key,
            mapping={
                "last_click_at_ns": timestamp_ns,
                "last_click_source": source,
                "last_click_dt_us": dt_us,
            },
        )
        pipe.zadd(self._clicks_key, {member: timestamp_ms})
        pipe.zremrangebyscore(self._clicks_key, 0, min_score)
        pipe.expire(self._clicks_key, settings.status_click_window_seconds * 2)
        pipe.execute()

    def record_random_draw(self, *, bits_used: int, rejected: int) -> None:
        pipe = self._client.pipeline()
        pipe.hincrby(self._stats_key, "total_random_requests", 1)
        pipe.hincrby(self._stats_key, "total_bits_served", bits_used)
        pipe.hincrby(self._stats_key, "total_rejections", rejected)
        pipe.hset(self._stats_key, "last_random_at_ns", time.time_ns())
        pipe.execute()

    def status(self, *, pool_size_bytes: int) -> ServiceStatus:
        now_ms = time.time_ns() // 1_000_000
        min_score = now_ms - settings.status_click_window_seconds * 1000
        pipe = self._client.pipeline()
        pipe.zremrangebyscore(self._clicks_key, 0, min_score)
        pipe.zcount(self._clicks_key, min_score, now_ms)
        pipe.hgetall(self._stats_key)
        _, clicks_last_window, raw_stats = pipe.execute()
        stats = _decode_hash(raw_stats)

        last_click_at_ns = _int_or_none(stats.get("last_click_at_ns"))
        clicks_last_minute = int(clicks_last_window)
        estimated_cpm = round(clicks_last_minute * (60 / settings.status_click_window_seconds))

        return ServiceStatus(
            pool_size_bytes=pool_size_bytes,
            total_clicks=_int(stats.get("total_clicks")),
            total_entropy_bytes=_int(stats.get("total_entropy_bytes")),
            total_raw_bits=_int(stats.get("total_raw_bits")),
            total_extracted_bits=_int(stats.get("total_extracted_bits")),
            total_discarded_pairs=_int(stats.get("total_discarded_pairs")),
            total_random_requests=_int(stats.get("total_random_requests")),
            total_bits_served=_int(stats.get("total_bits_served")),
            total_rejections=_int(stats.get("total_rejections")),
            clicks_last_minute=clicks_last_minute,
            estimated_cpm=estimated_cpm,
            last_click_at_unix=(last_click_at_ns / 1_000_000_000) if last_click_at_ns else None,
            last_click_source=stats.get("last_click_source"),
            last_click_dt_us=_int_or_none(stats.get("last_click_dt_us")),
        )


def make_stats_store() -> StatsStore:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=False)
    return StatsStore(client)


def _decode_hash(raw: dict[bytes, bytes]) -> dict[str, str]:
    return {
        key.decode("utf-8", errors="replace"): value.decode("utf-8", errors="replace")
        for key, value in raw.items()
    }


def _int(value: str | None) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else 0


def _int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
