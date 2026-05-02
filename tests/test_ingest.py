from __future__ import annotations

from nuclear_random_api.ingest import timestamp_fraction_to_seed, whiten_click


def test_timestamp_fraction_to_seed_uses_nanoseconds_after_second() -> None:
    assert timestamp_fraction_to_seed(1_234_567_890) == (234_567_890).to_bytes(8, "big")


def test_whiten_click_is_deterministic() -> None:
    first = whiten_click(timestamp_ns=1_234_567_890, sequence=7, device_time_us=100, dt_us=50)
    second = whiten_click(timestamp_ns=1_234_567_890, sequence=7, device_time_us=100, dt_us=50)

    assert first == second
    assert len(first) == 16

