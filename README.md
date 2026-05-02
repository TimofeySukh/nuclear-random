# Nuclear Random

Experimental Python random integers backed by Geiger counter decay timing.

```bash
pip install nuclear-random
```

```python
from nuclear_random import (
    nuclear_choice,
    nuclear_randint,
    nuclear_random,
    nuclear_random_bytes,
    service_status,
)

print(nuclear_random(100))      # 0..100 inclusive
print(nuclear_random(10_000))   # 0..10000 inclusive
print(nuclear_randint(10, 20))  # 10..20 inclusive
print(nuclear_random_bytes(16).hex())
print(nuclear_choice(["red", "green", "blue"]))

status = service_status()
print(status.pool_size_bytes, status.estimated_cpm)
```

The public service uses a slow physical source. Calls can wait for fresh extracted bits when the pool is empty.

## How It Works

The public API consumes extracted bits from an ESP32-C3 connected to a Geiger counter on GPIO 6. Each click sends the time since the previous click. The server takes a small number of raw timing bits and runs them through a Von Neumann debiasing extractor before storing full bytes in Redis.

For any request `nuclear_random(max_value)`, the API reads `max_value.bit_length()` extracted bits and returns the candidate only if it is `<= max_value`. Candidates above the requested maximum are rejected and the API reads the next bits.

This rejection-sampling step avoids modulo bias.

## Client API

```python
from nuclear_random import (
    nuclear_choice,
    nuclear_randint,
    nuclear_random,
    nuclear_random_bytes,
    service_status,
)
```

- `nuclear_random(max_value)` returns an integer in `0..max_value`.
- `nuclear_randint(min_value, max_value)` returns an integer in `min_value..max_value`.
- `nuclear_choice(items)` returns one item from a non-empty sequence by drawing a QRNG-backed index.
- `nuclear_random_bytes(length)` returns extracted bytes from the entropy pool. This is slow on the public service.
- `service_status()` returns pool size, click rate, and extractor counters.

The shorter names `randint`, `choice`, and `random_bytes` remain as backward-compatible aliases.

## Configuration

By default the client uses:

```text
https://nuclear-api.datanode.live
```

Override it while testing:

```bash
export NUCLEAR_RANDOM_API_URL=http://127.0.0.1:19000
```

or per call:

```python
nuclear_random(131, api_url="http://127.0.0.1:19000")
```

## Server

The server stack is Docker-only and includes:

- FastAPI API
- static public website
- Redis extracted entropy byte pool
- InfluxDB telemetry
- Wi-Fi ingest endpoint for the ESP32-C3
- USB serial monitor for diagnostics
- status metrics for the future website
- Redis-backed public API rate limiting

```bash
cp server/.env.example server/.env
docker compose -p nuclear-random --project-directory server up -d redis influxdb api site
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

See [docs/architecture.md](docs/architecture.md), [docs/deployment.md](docs/deployment.md), and [docs/hardware.md](docs/hardware.md).
See [docs/publishing.md](docs/publishing.md) for PyPI release steps.

The ESP32-C3 firmware posts click events to `https://nuclear-api.datanode.live/v1/entropy/click`. Its `INGEST_TOKEN` must match the server `INGEST_TOKEN` in `/home/server/nuclear_random/server/.env`. It should still be built with `CDCOnBoot=cdc` so the USB serial debug stream is visible on `/dev/ttyACM0`.

Useful API endpoints:

```text
GET  /healthz
GET  /v1/status
GET  /v1/clicks/timeline
GET  /v1/random/int?max=100
GET  /v1/random/bytes?length=16
POST /v1/entropy/click
```

The public website is intended for `https://random.datanode.live`.

## Status

This project is alpha-quality. It uses radioactive decay timing with Von Neumann debiasing, but it has not been cryptographically certified. Throughput is intentionally low because the service does not synthesize extra bytes from each click.

## License

MIT
