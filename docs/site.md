# Website

The public website runs at `https://random.datanode.live`.

It is a static site served by a small Nginx container. The same container proxies browser API calls from `/api/` to the internal FastAPI service, so the browser does not need cross-origin access to `nuclear-api.datanode.live`.

The interface is split into pages:

- Overview: live service cards
- Entropy: rolling Geiger click chart, per-bucket click activity, extractor counters, pool history, and CPM history
- Draw: public random-number and choice request tools
- Docs: Python install, helper API, and entropy path

The overview and docs pages link to `https://pypi.org/project/nuclear-random/`.

## Runtime

```bash
docker compose -p nuclear-random --project-directory server up -d site
```

Default port binding:

```text
127.0.0.1:19100 -> site:80
```

Cloudflare tunnel ingress:

```yaml
  - hostname: random.datanode.live
    service: http://127.0.0.1:19100
```

Cloudflare DNS:

```text
Type: CNAME
Name: random
Target: a58c8086-b534-454d-99d0-bf8006633e1b.cfargotunnel.com
Proxy: enabled
```
