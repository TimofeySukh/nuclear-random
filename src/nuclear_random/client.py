from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Generic, Sequence, TypeVar

import httpx

DEFAULT_API_URL = "https://nuclear-api.datanode.live"
DEFAULT_TIMEOUT = 10.0
T = TypeVar("T")


class NuclearRandomError(RuntimeError):
    """Raised when the random service cannot return randomness."""


@dataclass(frozen=True)
class RandomResponse:
    value: int
    bits_used: int
    rejected: int
    pool_size_bytes: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RandomResponse":
        try:
            return cls(
                value=int(payload["value"]),
                bits_used=int(payload["bits_used"]),
                rejected=int(payload["rejected"]),
                pool_size_bytes=_optional_int(payload.get("pool_size_bytes")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NuclearRandomError("The random service returned an invalid integer response.") from exc


@dataclass(frozen=True)
class BytesResponse:
    data: bytes
    bits_used: int
    pool_size_bytes: int | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BytesResponse":
        try:
            return cls(
                data=bytes.fromhex(str(payload["hex"])),
                bits_used=int(payload["bits_used"]),
                pool_size_bytes=_optional_int(payload.get("pool_size_bytes")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NuclearRandomError("The random service returned an invalid bytes response.") from exc


@dataclass(frozen=True)
class ServiceStatus:
    pool_size_bytes: int
    pool_bits: int
    total_clicks: int
    total_entropy_bytes: int
    total_raw_bits: int
    total_extracted_bits: int
    total_discarded_pairs: int
    total_random_requests: int
    total_bits_served: int
    total_rejections: int
    clicks_last_minute: int
    estimated_cpm: int
    last_click_at_unix: float | None
    last_click_source: str | None
    last_click_dt_us: int | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ServiceStatus":
        try:
            return cls(
                pool_size_bytes=int(payload["pool_size_bytes"]),
                pool_bits=int(payload["pool_bits"]),
                total_clicks=int(payload["total_clicks"]),
                total_entropy_bytes=int(payload["total_entropy_bytes"]),
                total_raw_bits=int(payload["total_raw_bits"]),
                total_extracted_bits=int(payload["total_extracted_bits"]),
                total_discarded_pairs=int(payload["total_discarded_pairs"]),
                total_random_requests=int(payload["total_random_requests"]),
                total_bits_served=int(payload["total_bits_served"]),
                total_rejections=int(payload["total_rejections"]),
                clicks_last_minute=int(payload["clicks_last_minute"]),
                estimated_cpm=int(payload["estimated_cpm"]),
                last_click_at_unix=_optional_float(payload.get("last_click_at_unix")),
                last_click_source=_optional_str(payload.get("last_click_source")),
                last_click_dt_us=_optional_int(payload.get("last_click_dt_us")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise NuclearRandomError("The random service returned an invalid status response.") from exc


class NuclearRandomClient(Generic[T]):
    """Synchronous client for the Nuclear Random API."""

    def __init__(
        self,
        *,
        api_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_url = _resolve_api_url(api_url)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

    def __enter__(self) -> "NuclearRandomClient[T]":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def random_response(self, max_value: int) -> RandomResponse:
        _validate_max_value(max_value)
        if max_value == 0:
            return RandomResponse(value=0, bits_used=0, rejected=0)

        payload = self._get_json("/v1/random/int", params={"max": max_value})
        return RandomResponse.from_payload(payload)

    def nuclear_random(self, max_value: int) -> int:
        """Return an unbiased random integer in the inclusive range 0..max_value."""

        return self.random_response(max_value).value

    def randint(self, min_value: int, max_value: int) -> int:
        """Return an unbiased random integer in the inclusive range min_value..max_value."""

        if not isinstance(min_value, int) or not isinstance(max_value, int):
            raise TypeError("min_value and max_value must be integers.")
        if min_value > max_value:
            raise ValueError("min_value must be less than or equal to max_value.")
        return min_value + self.nuclear_random(max_value - min_value)

    def random_bytes_response(self, length: int) -> BytesResponse:
        _validate_length(length)
        if length == 0:
            return BytesResponse(data=b"", bits_used=0)

        payload = self._get_json("/v1/random/bytes", params={"length": length})
        result = BytesResponse.from_payload(payload)
        if len(result.data) != length:
            raise NuclearRandomError("The random service returned the wrong number of bytes.")
        return result

    def random_bytes(self, length: int) -> bytes:
        """Return random bytes from the entropy pool."""

        return self.random_bytes_response(length).data

    def choice(self, items: Sequence[T]) -> T:
        """Return one item from a non-empty sequence."""

        if not items:
            raise ValueError("items must not be empty.")
        return items[self.nuclear_random(len(items) - 1)]

    def service_status(self) -> ServiceStatus:
        """Return live service status and entropy-pool metrics."""

        return ServiceStatus.from_payload(self._get_json("/v1/status"))

    def _get_json(self, path: str, *, params: dict[str, int] | None = None) -> dict[str, Any]:
        try:
            response = self._client.get(f"{self.api_url}{path}", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _extract_error_detail(exc.response)
            raise NuclearRandomError(f"The random service rejected the request: {detail}") from exc
        except httpx.HTTPError as exc:
            raise NuclearRandomError(f"Cannot reach the random service at {self.api_url}.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NuclearRandomError("The random service returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise NuclearRandomError("The random service returned an invalid JSON payload.")
        return payload


def nuclear_random(max_value: int, *, api_url: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> int:
    """Return an unbiased random integer in the inclusive range 0..max_value."""

    with NuclearRandomClient(api_url=api_url, timeout=timeout) as client:
        return client.nuclear_random(max_value)


def randint(
    min_value: int,
    max_value: int,
    *,
    api_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> int:
    """Return an unbiased random integer in the inclusive range min_value..max_value."""

    with NuclearRandomClient(api_url=api_url, timeout=timeout) as client:
        return client.randint(min_value, max_value)


def random_bytes(length: int, *, api_url: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> bytes:
    """Return random bytes from the entropy pool."""

    with NuclearRandomClient(api_url=api_url, timeout=timeout) as client:
        return client.random_bytes(length)


def choice(
    items: Sequence[T],
    *,
    api_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> T:
    """Return one item from a non-empty sequence."""

    with NuclearRandomClient[T](api_url=api_url, timeout=timeout) as client:
        return client.choice(items)


def service_status(
    *,
    api_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> ServiceStatus:
    """Return live service status and entropy-pool metrics."""

    with NuclearRandomClient(api_url=api_url, timeout=timeout) as client:
        return client.service_status()


def _resolve_api_url(api_url: str | None) -> str:
    return (api_url or os.getenv("NUCLEAR_RANDOM_API_URL") or DEFAULT_API_URL).rstrip("/")


def _validate_max_value(max_value: int) -> None:
    if not isinstance(max_value, int):
        raise TypeError("max_value must be an integer.")
    if max_value < 0:
        raise ValueError("max_value must be greater than or equal to zero.")


def _validate_length(length: int) -> None:
    if not isinstance(length, int):
        raise TypeError("length must be an integer.")
    if length < 0:
        raise ValueError("length must be greater than or equal to zero.")


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    detail = payload.get("detail") if isinstance(payload, dict) else None
    return str(detail) if detail else f"HTTP {response.status_code}"


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


def _optional_str(value: Any) -> str | None:
    return str(value) if value is not None else None
