from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from .entropy import EntropyPoolEmpty, make_entropy_source
from .settings import settings

app = FastAPI(title="Nuclear Random API", version="0.1.0")
entropy_source = make_entropy_source()


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

