from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import FastAPI, Header, HTTPException, Query

from .entropy import EntropyPoolEmpty, make_entropy_source
from .ingest import EntropyIngestor
from .settings import settings

app = FastAPI(title="Nuclear Random API", version="0.1.0")
entropy_source = make_entropy_source()
entropy_ingestor = EntropyIngestor()


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
def random_int(max_value: int = Query(alias="max", ge=0)) -> dict[str, int]:
    if max_value > settings.max_request_value:
        raise HTTPException(status_code=400, detail="max is too large for this service.")

    try:
        result = entropy_source.random_int(max_value)
    except EntropyPoolEmpty as exc:
        raise HTTPException(status_code=503, detail="Entropy pool is empty. Try again later.") from exc

    return {
        "value": result.value,
        "bits_used": result.bits_used,
        "rejected": result.rejected,
        "pool_size_bytes": result.pool_size_bytes,
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
    }
