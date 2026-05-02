from __future__ import annotations

import argparse
import json
import os
import time

import serial
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor Geiger click telemetry over USB serial.")
    parser.add_argument("--port", default=os.getenv("GEIGER_SERIAL_PORT", "/dev/ttyACM0"))
    parser.add_argument("--baud", type=int, default=int(os.getenv("GEIGER_SERIAL_BAUD", "115200")))
    args = parser.parse_args()

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
            _write_click(influx, timestamp_ns, sequence, event)


def _parse_event(line: str) -> dict[str, object]:
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        if "CLICK" in line.upper():
            return {"type": "pulse"}
        return {"type": "unknown", "raw": line}


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
) -> None:
    if influx is None:
        return
    client, org, bucket = influx
    point = (
        Point("geiger_click")
        .tag("source", "esp32c3_gpio6")
        .field("sequence", sequence)
        .field("dt_us", _as_int(event.get("dt_us")) or 0)
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
