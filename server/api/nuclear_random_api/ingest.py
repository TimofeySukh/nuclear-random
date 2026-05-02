from __future__ import annotations

import time
from dataclasses import dataclass

import redis
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision

from .extractor import VonNeumannExtractor, raw_bits_from_dt_us
from .settings import settings
from .stats import StatsStore, make_stats_store


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    pool_size_bytes: int
    raw_bits_seen: int
    extracted_bits_added: int
    discarded_pairs: int
    entropy_bytes_added: int


class EntropyIngestor:
    def __init__(self, stats_store: StatsStore | None = None) -> None:
        self._redis = redis.Redis.from_url(settings.redis_url, decode_responses=False)
        self._influx = self._make_influx_client()
        self._stats = stats_store or make_stats_store()
        self._extractor = VonNeumannExtractor()

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
        raw_bits = raw_bits_from_dt_us(dt_us, bit_count=settings.raw_bits_per_click)
        extracted = self._extractor.feed_raw_bits(raw_bits)
        pool_size = self._push_entropy(extracted.output_bytes)
        self._stats.record_click(
            timestamp_ns=timestamp_ns,
            source=source,
            dt_us=dt_us,
            raw_bits_seen=extracted.raw_bits_seen,
            extracted_bits_added=extracted.accepted_bit_count,
            discarded_pairs=extracted.discarded_pairs,
            entropy_bytes_added=len(extracted.output_bytes),
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
            raw_bits_seen=extracted.raw_bits_seen,
            extracted_bits_added=extracted.accepted_bit_count,
            discarded_pairs=extracted.discarded_pairs,
        )
        return IngestResult(
            accepted=True,
            pool_size_bytes=pool_size,
            raw_bits_seen=extracted.raw_bits_seen,
            extracted_bits_added=extracted.accepted_bit_count,
            discarded_pairs=extracted.discarded_pairs,
            entropy_bytes_added=len(extracted.output_bytes),
        )

    def _push_entropy(self, entropy: bytes) -> int:
        if not entropy:
            return int(self._redis.llen(settings.redis_entropy_key))
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
        raw_bits_seen: int,
        extracted_bits_added: int,
        discarded_pairs: int,
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
            .field("raw_bits_seen", raw_bits_seen)
            .field("extracted_bits_added", extracted_bits_added)
            .field("discarded_pairs", discarded_pairs)
            .time(timestamp_ns, WritePrecision.NS)
        )
        client.write_api(write_options=WriteOptions(batch_size=1)).write(bucket=bucket, org=org, record=point)
