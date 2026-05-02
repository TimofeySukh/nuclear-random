# Architecture

Nuclear Random turns Geiger counter click timing into a small public random-number service.

## Data Flow

1. An ESP32-C3 listens for falling edges from the Geiger counter on GPIO 6.
2. On each accepted pulse, the firmware sends a JSON event over Wi-Fi to `/v1/entropy/click`.
3. The API records the receive timestamp. It takes the fractional nanoseconds of that timestamp as eight bytes, mixes in the ESP32 sequence number, ESP32 `micros()` value, and pulse delta, then hashes the payload with BLAKE2s.
4. The API pushes the resulting bytes into Redis and writes click telemetry to InfluxDB.
5. The API pops entropy bytes from Redis and serves unbiased integers with rejection sampling.
6. The Python package calls the public API and returns an integer to the user.

## Range Algorithm

For `nuclear_random(100)`, the API needs 7 bits because `100.bit_length() == 7`.

It reads 7 bits from Redis-backed entropy, converts them to a candidate in `0..127`, and returns the candidate only when it is less than or equal to `100`. Values above `100` are rejected and the API reads the next 7 bits.

For `nuclear_random(131)`, the API reads 8 bits, producing a candidate in `0..255`, and rejects values above `131`.

This avoids modulo bias.

## Redis

Redis stores the entropy byte pool at `nuclear_random:entropy_bytes`.

The collector bounds the pool with `MAX_POOL_BYTES`, defaulting to `1 MiB`. Redis is configured with `64 MiB` max memory in Docker Compose to protect a small home server.

## InfluxDB

InfluxDB stores operational telemetry, not the entropy source of truth. The `geiger_click` measurement includes:

- source
- sequence
- device time
- device-provided `dt_us`
- Redis pool size

## Security Notes

This is an experimental entropy service. The collector hashes timing data before inserting bytes into Redis, but the project has not had a cryptographic audit. Do not use it as the only entropy source for high-stakes cryptographic key generation until the full pipeline has been reviewed and tested.
