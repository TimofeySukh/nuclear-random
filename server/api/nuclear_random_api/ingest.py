from __future__ import annotations

import hashlib
import struct
import time
from dataclasses import dataclass

import redis
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision

from .settings import settings
from .stats import StatsStore, make_stats_store


def timestamp_fraction_to_seed(timestamp_ns: int) -> bytes:
    fraction_ns = timestamp_ns % 1_000_000_000
    return struct.pack(">Q", fraction_ns)


def whiten_click(timestamp_ns: int, sequence: int, device_time_us: int, dt_us: int) -> bytes:
    payload = timestamp_fraction_to_seed(timestamp_ns)
    payload += struct.pack(">Q", max(sequence, 0))
    payload += struct.pack(">Q", max(device_time_us, 0))
    payload += struct.pack(">Q", max(dt_us, 0))
    return hashlib.blake2s(payload, digest_size=16, person=b"nucrand1").digest()


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    pool_size_bytes: int
    entropy_bytes_added: int


class EntropyIngestor:
    def __init__(self, stats_store: StatsStore | None = None) -> None:
        self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=False)
        self._influx = self._make_influx_client()
        self._stats = stats_store or make_stats_store()

    def ingest_click(
        self,
        *,
        source: str,
        sequence: int,
        device_time_us: int,
        dt_us: int,
        total: int,
        dropped: int,
    ) -> IngestResult:
        timestamp_ns = time.time_ns()
        entropy = whiten_click(timestamp_ns, sequence, device_time_us, dt_us)
        pool_size = self._push_entropy(entropy)
        self._stats.record_click(
            timestamp_ns=timestamp_ns,
            source=source,
            dt_us=dt_us,
            entropy_bytes_added=len(entropy),
        )
        self._write_click(
            timestamp_ns=timestamp_ns,
            source=source,
            sequence=sequence,
            device_time_us=device_time_us,
            dt_us=dt_us,
            total=total,
            dropped=dropped,
            pool_size_bytes=pool_size,
        )
        return IngestResult(accepted=True, pool_size_bytes=pool_size, entropy_bytes_added=len(entropy))

    def _push_entropy(self, entropy: bytes) -> int:
        pipe = self._redis.pipeline()
        pipe.rpush(settings.redis_entropy_key, *[bytes([value]) for value in entropy])
        pipe.ltrim(settings.redis_entropy_key, -settings.max_pool_bytes, -1)
        pipe.llen(settings.redis_entropy_key)
        results = pipe.execute()
        return int(results[-1])

    def _make_influx_client(self) -> tuple[InfluxDBClient, str, str] | None:
        if not all([settings.influxdb_url, settings.influxdb_token, settings.influxdb_org, settings.influxdb_bucket]):
            return None
        client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )
        return client, settings.influxdb_org, settings.influxdb_bucket

    def _write_click(
        self,
        *,
        timestamp_ns: int,
        source: str,
        sequence: int,
        device_time_us: int,
        dt_us: int,
        total: int,
        dropped: int,
        pool_size_bytes: int,
    ) -> None:
        if self._influx is None:
            return

        client, org, bucket = self._influx
        point = (
            Point("geiger_click")
            .tag("source", source)
            .field("sequence", sequence)
            .field("device_time_us", device_time_us)
            .field("dt_us", dt_us)
            .field("total", total)
            .field("dropped", dropped)
            .field("pool_size_bytes", pool_size_bytes)
            .time(timestamp_ns, WritePrecision.NS)
        )
        client.write_api(write_options=WriteOptions(batch_size=1)).write(bucket=bucket, org=org, record=point)
