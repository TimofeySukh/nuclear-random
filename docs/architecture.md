# Architecture

Nuclear Random turns Geiger counter decay timing into a small public random-number service.

## Data Flow

1. An ESP32-C3 listens for falling edges from the Geiger counter on GPIO 6.
2. On each accepted pulse, the firmware sends a JSON event over Wi-Fi to `/v1/entropy/click`.
3. The API extracts a small number of raw timing bits from `dt_us`, the time between clicks.
4. Raw bits pass through a Von Neumann debiasing extractor: `01 -> 0`, `10 -> 1`, `00/11 -> discard`.
5. The API packs accepted bits into bytes, pushes only full extracted bytes into Redis, and writes raw click telemetry to InfluxDB.
6. The API pops extracted bits from Redis and serves unbiased integers with rejection sampling.
7. The Python package calls the public API and returns an integer to the user.

The API also stores lightweight service stats in Redis for `/v1/status`, including pool size, total clicks, raw bits, extracted bits, discarded pairs, random request counts, and estimated CPM.

The website chart uses `/v1/clicks/timeline`, which reads recent click timestamps from Redis and returns cumulative buckets for the rolling timeline window.

## Extraction

Each click provides `dt_us`, the number of microseconds since the previous click.

The API takes `RAW_BITS_PER_CLICK` low bits from `dt_us`, defaulting to `2`. These are raw timing bits, not final output bits.

The Von Neumann extractor consumes raw bits in pairs:

```text
01 -> 0
10 -> 1
00 -> discard
11 -> discard
```

Accepted bits are packed into bytes. Redis receives only complete extracted bytes.

## Range Algorithm

For `nuclear_random(100)`, the API needs 7 bits because `100.bit_length() == 7`.

It reads 7 bits from Redis-backed entropy, converts them to a candidate in `0..127`, and returns the candidate only when it is less than or equal to `100`. Values above `100` are rejected and the API reads the next 7 bits.

For `nuclear_random(131)`, the API reads 8 bits, producing a candidate in `0..255`, and rejects values above `131`.

This avoids modulo bias.

The same algorithm is used for any non-negative maximum value. For example, `nuclear_random(10_000)` reads 14-bit candidates and rejects values greater than `10_000`.

The Python client uses the same range algorithm for helpers. `nuclear_randint(min_value, max_value)` draws an offset in `0..max_value-min_value`, and `nuclear_choice(items)` draws an index in `0..len(items)-1`.

If the Redis pool is empty, the API waits up to `RANDOM_WAIT_SECONDS` for a fresh extracted byte before returning `503`.

## Redis

Redis stores the extracted entropy byte pool at `nuclear_random:v2:entropy_bytes`.

The API bounds the pool with `MAX_POOL_BYTES`, defaulting to `1 MiB`. Redis is configured with `64 MiB` max memory in Docker Compose to protect a small home server.

Redis also stores:

- service counters at `nuclear_random:v2:stats`
- recent click timestamps at `nuclear_random:v2:click_times`
- per-client random endpoint rate limit keys under `nuclear_random:v2:rate:*`

## InfluxDB

InfluxDB stores operational telemetry, not the entropy source of truth. The `geiger_click` measurement includes:

- source
- sequence
- device time
- device-provided `dt_us`
- Redis pool size
- raw bits seen
- extracted bits added
- discarded Von Neumann pairs

## Security Notes

This is an experimental QRNG-style entropy service. It uses radioactive decay timing and Von Neumann debiasing, but it is not certified. Do not use it as the only entropy source for high-stakes cryptographic key generation until the full pipeline has been reviewed and tested.
