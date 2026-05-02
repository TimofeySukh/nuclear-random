from __future__ import annotations

import httpx
import pytest
import respx

from nuclear_random import (
    NuclearRandomClient,
    NuclearRandomError,
    choice,
    nuclear_random,
    randint,
    random_bytes,
    service_status,
)


@respx.mock
def test_nuclear_random_returns_value_for_any_max() -> None:
    route = respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(
            200,
            json={"value": 999, "bits_used": 10, "rejected": 0, "pool_size_bytes": 128},
        )
    )

    assert nuclear_random(1000, api_url="https://api.example.test") == 999
    assert route.calls[0].request.url.params["max"] == "1000"


def test_nuclear_random_short_circuits_zero() -> None:
    assert nuclear_random(0, api_url="https://api.example.test") == 0


def test_nuclear_random_rejects_negative_max() -> None:
    with pytest.raises(ValueError):
        nuclear_random(-1, api_url="https://api.example.test")


@respx.mock
def test_randint_offsets_service_value() -> None:
    respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(200, json={"value": 4, "bits_used": 4, "rejected": 0})
    )

    assert randint(10, 20, api_url="https://api.example.test") == 14


def test_randint_rejects_invalid_range() -> None:
    with pytest.raises(ValueError):
        randint(20, 10, api_url="https://api.example.test")


@respx.mock
def test_random_bytes_returns_bytes() -> None:
    route = respx.get("https://api.example.test/v1/random/bytes").mock(
        return_value=httpx.Response(
            200,
            json={"hex": "0001ff", "length": 3, "bits_used": 24, "pool_size_bytes": 128},
        )
    )

    assert random_bytes(3, api_url="https://api.example.test") == b"\x00\x01\xff"
    assert route.calls[0].request.url.params["length"] == "3"


def test_random_bytes_short_circuits_zero() -> None:
    assert random_bytes(0, api_url="https://api.example.test") == b""


@respx.mock
def test_choice_uses_random_index() -> None:
    respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(200, json={"value": 1, "bits_used": 2, "rejected": 0})
    )

    assert choice(["alpha", "beta", "gamma"], api_url="https://api.example.test") == "beta"


def test_choice_rejects_empty_sequence() -> None:
    with pytest.raises(ValueError):
        choice([], api_url="https://api.example.test")


@respx.mock
def test_service_status_returns_dataclass() -> None:
    respx.get("https://api.example.test/v1/status").mock(
        return_value=httpx.Response(
            200,
            json={
                "pool_size_bytes": 128,
                "total_clicks": 10,
                "total_entropy_bytes": 160,
                "total_random_requests": 2,
                "total_bits_served": 14,
                "total_rejections": 1,
                "clicks_last_minute": 5,
                "estimated_cpm": 5,
                "last_click_at_unix": 123.5,
                "last_click_source": "esp32c3_gpio6_wifi",
                "last_click_dt_us": 456,
            },
        )
    )

    status = service_status(api_url="https://api.example.test")

    assert status.pool_size_bytes == 128
    assert status.estimated_cpm == 5
    assert status.last_click_source == "esp32c3_gpio6_wifi"


@respx.mock
def test_client_can_be_reused() -> None:
    route = respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(200, json={"value": 7, "bits_used": 3, "rejected": 0})
    )

    with NuclearRandomClient(api_url="https://api.example.test") as client:
        assert client.nuclear_random(10) == 7
        assert client.nuclear_random(10) == 7

    assert route.call_count == 2


@respx.mock
def test_nuclear_random_wraps_service_errors() -> None:
    respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(503, json={"detail": "Entropy pool is empty."})
    )

    with pytest.raises(NuclearRandomError, match="Entropy pool is empty"):
        nuclear_random(100, api_url="https://api.example.test")

