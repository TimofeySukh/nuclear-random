# Nuclear Random

Experimental Python random integers backed by Geiger counter click timing.

```bash
pip install nuclear-random
```

```python
from nuclear_random import nuclear_random

value = nuclear_random(100)
print(value)  # 0..100 inclusive
```

## How It Works

The public API consumes entropy bytes collected from an ESP32-C3 connected to a Geiger counter on GPIO 6. For a request like `nuclear_random(100)`, the API reads 7 bits, builds a candidate in `0..127`, and returns it only if it is `<= 100`. Candidates above the requested maximum are rejected and the API reads the next 7 bits.

This rejection-sampling step avoids modulo bias.

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
- Redis entropy byte pool
- InfluxDB telemetry
- Wi-Fi ingest endpoint for the ESP32-C3
- serial collector fallback for USB deployments

```bash
cp server/.env.example server/.env
docker compose -p nuclear-random --project-directory server up -d redis influxdb api
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

See [docs/architecture.md](docs/architecture.md), [docs/deployment.md](docs/deployment.md), and [docs/hardware.md](docs/hardware.md).

The ESP32-C3 firmware posts click events to `https://nuclear-api.datanode.live/v1/entropy/click`. Its `INGEST_TOKEN` must match the server `INGEST_TOKEN` in `/home/server/nuclear_random/server/.env`. It should still be built with `CDCOnBoot=cdc` so the USB serial debug stream is visible on `/dev/ttyACM0`.

## Status

This project is alpha-quality. It is suitable for experimentation and public demos, but it has not been cryptographically audited.

## License

MIT
