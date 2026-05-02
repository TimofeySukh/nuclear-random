from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_API_URL = "https://nuclear-api.datanode.live"


class NuclearRandomError(RuntimeError):
    """Raised when the random service cannot return a number."""


@dataclass(frozen=True)
class RandomResponse:
    value: int
    bits_used: int
    rejected: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RandomResponse":
        try:
            return cls(
                value=int(payload["value"]),
                bits_used=int(payload["bits_used"]),
                rejected=int(payload["rejected"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NuclearRandomError("The random service returned an invalid response.") from exc


def nuclear_random(max_value: int, *, api_url: str | None = None, timeout: float = 10.0) -> int:
    """Return an unbiased random integer in the inclusive range 0..max_value."""

    if not isinstance(max_value, int):
        raise TypeError("max_value must be an integer.")
    if max_value < 0:
        raise ValueError("max_value must be greater than or equal to zero.")
    if max_value == 0:
        return 0

    base_url = (api_url or os.getenv("NUCLEAR_RANDOM_API_URL") or DEFAULT_API_URL).rstrip("/")
    try:
        response = httpx.get(f"{base_url}/v1/random/int", params={"max": max_value}, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = _extract_error_detail(exc.response)
        raise NuclearRandomError(f"The random service rejected the request: {detail}") from exc
    except httpx.HTTPError as exc:
        raise NuclearRandomError(f"Cannot reach the random service at {base_url}.") from exc

    return RandomResponse.from_payload(response.json()).value


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    detail = payload.get("detail")
    return str(detail) if detail else f"HTTP {response.status_code}"

