from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"
    redis_entropy_key: str = "nuclear_random:entropy_bytes"
    redis_max_lpop_count: int = 256
    max_request_value: int = 2**63 - 1
    pool_low_watermark_bytes: int = 1024

    model_config = SettingsConfigDict(env_prefix="NUCLEAR_RANDOM_", env_file=".env")


settings = Settings()

