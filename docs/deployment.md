# Deployment

The server must be managed through Docker. Do not install Redis, InfluxDB, or the API directly on the host.

## Local Docker Stack

```bash
cp server/.env.example server/.env
docker compose -p nuclear-random --project-directory server up -d redis influxdb api
docker compose -p nuclear-random --project-directory server up -d site
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

The API listens on `127.0.0.1:19000` by default. The public website listens on `127.0.0.1:19100`.

## Home Server Layout

The inspected home server already runs a Cloudflare tunnel with this config:

```yaml
ingress:
  - hostname: onewordtext.tech
    service: http://127.0.0.1:5000
  - hostname: weather.datanode.live
    service: http://127.0.0.1:13000
  - hostname: robot.datanode.live
    service: http://127.0.0.1:14000
  - service: http_status:404
```

Chosen integration for the home server:

1. Copy this repository to `/home/server/nuclear_random`.
2. Start the Docker stack with API bound to `127.0.0.1:19000`.
3. Add one Cloudflare ingress entry before the final `http_status:404` rule:

```yaml
  - hostname: nuclear-api.datanode.live
    service: http://127.0.0.1:19000
  - hostname: random.datanode.live
    service: http://127.0.0.1:19100
```

4. Reload or restart only the existing Cloudflare tunnel service after confirming the hostname.

The current deployment target is `nuclear-api.datanode.live`.
The current website target is `random.datanode.live`.

Cloudflare DNS must contain:

```text
Type: CNAME
Name: nuclear-api
Target: a58c8086-b534-454d-99d0-bf8006633e1b.cfargotunnel.com
Proxy: enabled
```

The website uses the same tunnel target:

```text
Type: CNAME
Name: random
Target: a58c8086-b534-454d-99d0-bf8006633e1b.cfargotunnel.com
Proxy: enabled
```

After changing `/home/server/.cloudflared/config.yml`, restart the existing tunnel:

```bash
sudo systemctl restart cloudflared
```

## Memory Defaults

The compose file uses conservative defaults:

- Redis container limit: `96 MiB`
- Redis internal max memory: `64 MiB`
- Entropy pool: `1 MiB`
- Archive rotation: `128 MiB` per shard
- InfluxDB container limit: `512 MiB`
- API container limit: `192 MiB`
- Site container limit: `64 MiB`
- Collector container limit: `128 MiB`

The full stack with the diagnostic collector is capped at `992 MiB` before Docker overhead. InfluxDB is the heaviest service, so check `docker stats` after startup.

Long-term extracted-bit archival is enabled by default:

```text
ARCHIVE_ENABLED=true
ARCHIVE_ROTATE_BYTES=134217728
```

Archive files are stored in the Docker volume mounted at `/var/lib/nuclear-random/archive`.

The public random endpoint is rate limited with Redis. The default is `120` requests per minute per client identity and can be changed with:

```text
RANDOM_RATE_LIMIT_PER_MINUTE=120
```

The extraction rate is controlled with:

```text
RAW_BITS_PER_CLICK=2
```

This is intentionally conservative. Increasing it makes the service faster but requires statistical justification.

When the pool is empty, random endpoints wait for fresh entropy before returning an error:

```text
RANDOM_WAIT_SECONDS=90
```

The website click chart window is controlled with:

```text
CLICK_TIMELINE_WINDOW_SECONDS=900
```

## Collector Placement

The preferred deployment is Wi-Fi firmware. The ESP32-C3 posts directly to:

```text
https://nuclear-api.datanode.live/v1/entropy/click
```

The firmware `INGEST_TOKEN` must match `INGEST_TOKEN` in `/home/server/nuclear_random/server/.env`.

The USB collector is diagnostic-only. The QRNG entropy path is Wi-Fi ingest through `/v1/entropy/click`. If the board is plugged into the home server and you want serial telemetry in InfluxDB, run:

```bash
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

The USB collector does not write entropy into Redis.
