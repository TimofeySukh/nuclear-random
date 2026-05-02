from __future__ import annotations

import argparse
import json
import os
import time

import redis
import serial
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision

from .extractor import whiten_click


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect Geiger click entropy into Redis.")
    parser.add_argument("--port", default=os.getenv("GEIGER_SERIAL_PORT", "/dev/ttyACM0"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("GEIGER_SERIAL_BAUD", "115200")))
    parser.add_argument("--redis-url", default=os.getenv("REDIS_URL", "redis://redis:6379/0"))
    parser.add_argument("--redis-key", default=os.getenv("REDIS_ENTROPY_KEY", "nuclear_random:entropy_bytes"))
    parser.add_argument("--max-pool-bytes", type=int, default=int(os.getenv("MAX_POOL_BYTES", "1048576")))
    args = parser.parse_args()

    redis_client = redis.Redis.from_url(args.redis_url, decode_responses=False)
    influx = _make_influx_client()
    sequence = 0

    with serial.Serial(args.port, args.baud, timeout=2) as device:
        time.sleep(2.0)
        device.reset_input_buffer()
        device.write(b"STATUS\n")

        while True:
            line = device.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue

            timestamp_ns = time.time_ns()
            event = _parse_event(line)
            if event.get("type") != "pulse":
                continue

            sequence += 1
            entropy = whiten_click(timestamp_ns, sequence, _as_int(event.get("dt_us")))
            _push_entropy(redis_client, args.redis_key, entropy, args.max_pool_bytes)
            _write_click(influx, timestamp_ns, sequence, event, redis_client.llen(args.redis_key))


def _parse_event(line: str) -> dict[str, object]:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        if "CLICK" in line.upper():
            return {"type": "pulse"}
        return {"type": "unknown", "raw": line}


def _push_entropy(client: redis.Redis, key: str, entropy: bytes, max_pool_bytes: int) -> None:
    pipe = client.pipeline()
    pipe.rpush(key, *[bytes([value]) for value in entropy])
    pipe.ltrim(key, -max_pool_bytes, -1)
    pipe.execute()


def _make_influx_client() -> tuple[InfluxDBClient, str, str] | None:
    url = os.getenv("INFLUXDB_URL")
    token = os.getenv("INFLUXDB_TOKEN")
    org = os.getenv("INFLUXDB_ORG")
    bucket = os.getenv("INFLUXDB_BUCKET")
    if not all([url, token, org, bucket]):
        return None
    client = InfluxDBClient(url=url, token=token, org=org)
    return client, org, bucket


def _write_click(
    influx: tuple[InfluxDBClient, str, str] | None,
    timestamp_ns: int,
    sequence: int,
    event: dict[str, object],
    pool_size_bytes: int,
) -> None:
    if influx is None:
        return
    client, org, bucket = influx
    point = (
        Point("geiger_click")
        .tag("source", "esp32c3_gpio6")
        .field("sequence", sequence)
        .field("dt_us", _as_int(event.get("dt_us")) or 0)
        .field("pool_size_bytes", pool_size_bytes)
        .time(timestamp_ns, WritePrecision.NS)
    )
    client.write_api(write_options=WriteOptions(batch_size=1)).write(bucket=bucket, org=org, record=point)


def _as_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
