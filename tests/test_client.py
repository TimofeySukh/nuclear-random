from __future__ import annotations

import httpx
import pytest
import respx

from nuclear_random import NuclearRandomError, nuclear_random


@respx.mock
def test_nuclear_random_returns_value() -> None:
    route = respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(200, json={"value": 42, "bits_used": 7, "rejected": 0})
    )

    assert nuclear_random(100, api_url="https://api.example.test") == 42
    assert route.calls[0].request.url.params["max"] == "100"


def test_nuclear_random_short_circuits_zero() -> None:
    assert nuclear_random(0, api_url="https://api.example.test") == 0


def test_nuclear_random_rejects_negative_max() -> None:
    with pytest.raises(ValueError):
        nuclear_random(-1, api_url="https://api.example.test")


@respx.mock
def test_nuclear_random_wraps_service_errors() -> None:
    respx.get("https://api.example.test/v1/random/int").mock(
        return_value=httpx.Response(503, json={"detail": "Entropy pool is empty."})
    )

    with pytest.raises(NuclearRandomError, match="Entropy pool is empty"):
        nuclear_random(100, api_url="https://api.example.test")

