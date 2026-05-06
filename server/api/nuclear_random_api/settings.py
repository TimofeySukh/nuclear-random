from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_key_prefix: str = "nuclear_random:v2"
    redis_url: str = "redis://redis:6379/0"
    redis_entropy_key: str = "nuclear_random:v2:entropy_bytes"
    redis_max_lpop_count: int = 256
    max_pool_bytes: int = 1_048_576
    max_request_value: int = 2**63 - 1
    pool_low_watermark_bytes: int = 1024
    raw_bits_per_click: int = 2
    random_wait_seconds: int = 90
    status_click_window_seconds: int = 60
    click_timeline_window_seconds: int = 900
    archive_enabled: bool = True
    archive_dir: str = "/var/lib/nuclear-random/archive"
    archive_rotate_bytes: int = 134_217_728
    random_rate_limit_per_minute: int = 120
    ingest_token: str | None = None
    influxdb_url: str | None = None
    influxdb_token: str | None = None
    influxdb_org: str | None = None
    influxdb_bucket: str | None = None

    model_config = SettingsConfigDict(env_prefix="NUCLEAR_RANDOM_", env_file=".env")


settings = Settings()
