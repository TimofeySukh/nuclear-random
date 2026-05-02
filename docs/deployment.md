# Deployment

The server must be managed through Docker. Do not install Redis, InfluxDB, or the API directly on the host.

## Local Docker Stack

```bash
cp server/.env.example server/.env
docker compose --project-directory server up -d redis influxdb api
docker compose --project-directory server --profile collector up -d collector
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

Recommended integration:

1. Copy this repository to `/home/server/nuclear_random`.
2. Start the Docker stack with API bound to `127.0.0.1:19000`.
3. Add one Cloudflare ingress entry before the final `http_status:404` rule:

```yaml
  - hostname: api.nuclear-random.example.com
    service: http://127.0.0.1:19000
```

4. Reload or restart only the existing Cloudflare tunnel service after confirming the hostname.

No tunnel change has been applied automatically because the public hostname must be chosen first.

## Memory Defaults

The compose file uses conservative defaults:

- Redis max memory: `64 MiB`
- Entropy pool: `1 MiB`
- API: one Uvicorn process
- Collector: one serial reader process

InfluxDB is the heaviest service. If the server is too tight on memory, run Redis and API first, then add InfluxDB after confirming available RAM.

