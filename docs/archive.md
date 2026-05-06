# Archive

The API keeps an append-only archive of extracted bytes so that long-running collection can be tested later with larger statistical batteries.

## Layout

Archive path inside the API container:

```text
/var/lib/nuclear-random/archive
```

Contents:

- `manifest.json`
- `entropy_*.bin`

The manifest records:

- extractor name
- `RAW_BITS_PER_CLICK`
- rotation size
- total archived bytes
- current shard name
- shard list with byte counts

## Docker

The archive is stored in a dedicated Docker volume:

```text
archive-data
```

## Export

To inspect the archive on the server:

```bash
docker volume inspect archive-data
docker exec nuclear-random-api ls -lah /var/lib/nuclear-random/archive
docker exec nuclear-random-api cat /var/lib/nuclear-random/archive/manifest.json
```

To copy shards out for offline testing:

```bash
docker cp nuclear-random-api:/var/lib/nuclear-random/archive ./entropy-archive
```
