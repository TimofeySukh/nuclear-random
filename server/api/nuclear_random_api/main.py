from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .entropy import EntropyPoolEmpty, make_entropy_source
from .ingest import EntropyIngestor
from .rate_limit import RateLimitExceeded, make_rate_limiter
from .settings import settings
from .stats import make_stats_store

app = FastAPI(title="Nuclear Random API", version="0.1.0")
entropy_source = make_entropy_source()
stats_store = make_stats_store()
entropy_ingestor = EntropyIngestor(stats_store=stats_store)
rate_limiter = make_rate_limiter()


class ClickIngestRequest(BaseModel):
    source: str = Field(default="esp32c3_wifi", max_length=64)
    sequence: int = Field(ge=0)
    device_time_us: int = Field(ge=0)
    dt_us: int = Field(ge=0)
    total: int = Field(ge=0)
    dropped: int = Field(default=0, ge=0)


@app.get("/healthz")
def healthz() -> dict[str, int | str]:
    return {"status": "ok", "pool_size_bytes": entropy_source.pool_size()}


@app.get("/v1/random/int")
def random_int(request: Request, max_value: int = Query(alias="max", ge=0)) -> dict[str, int]:
    if max_value > settings.max_request_value:
        raise HTTPException(status_code=400, detail="max is too large for this service.")

    try:
        rate_limiter.check(identity=_client_identity(request))
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    try:
        result = entropy_source.random_int(max_value)
    except EntropyPoolEmpty as exc:
        raise HTTPException(status_code=503, detail="Entropy pool is empty. Try again later.") from exc

    stats_store.record_random_draw(bits_used=result.bits_used, rejected=result.rejected)
    return {
        "value": result.value,
        "bits_used": result.bits_used,
        "rejected": result.rejected,
        "pool_size_bytes": result.pool_size_bytes,
    }


@app.get("/v1/random/bytes")
def random_bytes(request: Request, length: int = Query(ge=0, le=4096)) -> dict[str, int | str]:
    try:
        rate_limiter.check(identity=_client_identity(request))
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    try:
        data = entropy_source.random_bytes(length)
    except EntropyPoolEmpty as exc:
        raise HTTPException(status_code=503, detail="Entropy pool is empty. Try again later.") from exc

    bits_used = length * 8
    stats_store.record_random_draw(bits_used=bits_used, rejected=0)
    return {
        "hex": data.hex(),
        "length": length,
        "bits_used": bits_used,
        "pool_size_bytes": entropy_source.pool_size(),
    }


@app.get("/v1/status")
def service_status() -> dict[str, int | float | str | None]:
    status = stats_store.status(pool_size_bytes=entropy_source.pool_size())
    return {
        "pool_size_bytes": status.pool_size_bytes,
        "pool_bits": status.pool_size_bytes * 8,
        "total_clicks": status.total_clicks,
        "total_entropy_bytes": status.total_entropy_bytes,
        "total_raw_bits": status.total_raw_bits,
        "total_extracted_bits": status.total_extracted_bits,
        "total_discarded_pairs": status.total_discarded_pairs,
        "total_random_requests": status.total_random_requests,
        "total_bits_served": status.total_bits_served,
        "total_rejections": status.total_rejections,
        "clicks_last_minute": status.clicks_last_minute,
        "estimated_cpm": status.estimated_cpm,
        "last_click_at_unix": status.last_click_at_unix,
        "last_click_source": status.last_click_source,
        "last_click_dt_us": status.last_click_dt_us,
    }


@app.post("/v1/entropy/click")
def ingest_click(
    request: ClickIngestRequest,
    x_nuclear_random_token: str | None = Header(default=None),
) -> dict[str, bool | int]:
    if settings.ingest_token and x_nuclear_random_token != settings.ingest_token:
        raise HTTPException(status_code=401, detail="Invalid ingest token.")

    result = entropy_ingestor.ingest_click(
        source=request.source,
        sequence=request.sequence,
        device_time_us=request.device_time_us,
        dt_us=request.dt_us,
        total=request.total,
        dropped=request.dropped,
    )
    return {
        "accepted": result.accepted,
        "pool_size_bytes": result.pool_size_bytes,
        "entropy_bytes_added": result.entropy_bytes_added,
        "raw_bits_seen": result.raw_bits_seen,
        "extracted_bits_added": result.extracted_bits_added,
        "discarded_pairs": result.discarded_pairs,
    }


def _client_identity(request: Request) -> str:
    forwarded_for = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else "unknown"
