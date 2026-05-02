# Deployment

The server must be managed through Docker. Do not install Redis, InfluxDB, or the API directly on the host.

## Local Docker Stack

```bash
cp server/.env.example server/.env
docker compose -p nuclear-random --project-directory server up -d redis influxdb api
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

The API listens on `127.0.0.1:19000` by default.

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
  - hostname: random.datanode.live
    service: http://127.0.0.1:19000
```

4. Reload or restart only the existing Cloudflare tunnel service after confirming the hostname.

The current deployment target is `random.datanode.live`.

## Memory Defaults

The compose file uses conservative defaults:

- Redis container limit: `96 MiB`
- Redis internal max memory: `64 MiB`
- Entropy pool: `1 MiB`
- InfluxDB container limit: `512 MiB`
- API container limit: `192 MiB`
- Collector container limit: `128 MiB`

The full stack is capped at `928 MiB` before Docker overhead. InfluxDB is the heaviest service, so check `docker stats` after startup.

## Collector Placement

The collector must run where the ESP32-C3 appears as a serial device. If the board is plugged into the home server, run:

```bash
docker compose -p nuclear-random --project-directory server --profile collector up -d collector
```

If the board stays on a laptop or workstation, run the collector there and point it at the server Redis endpoint through a private network or SSH tunnel.
