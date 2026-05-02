from __future__ import annotations

import hashlib
import struct


def timestamp_fraction_to_seed(timestamp_ns: int) -> bytes:
    fraction_ns = timestamp_ns % 1_000_000_000
    return struct.pack(">Q", fraction_ns)


def whiten_click(timestamp_ns: int, sequence: int, dt_us: int | None) -> bytes:
    payload = timestamp_fraction_to_seed(timestamp_ns)
    payload += struct.pack(">Q", sequence)
    payload += struct.pack(">Q", max(dt_us or 0, 0))
    return hashlib.blake2s(payload, digest_size=16, person=b"nuclear-random").digest()

