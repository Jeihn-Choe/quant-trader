from __future__ import annotations

from datetime import time
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _bot_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[6]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RESEARCH_BOT_",
        env_file=_bot_root() / ".env",
        extra="ignore",
    )

    app_name: str = "QuantTrader Research Bot"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    market_data_provider: str = "mock"
    database_backend: str = "duckdb"
    duckdb_path: Path = _workspace_root() / "data" / "research" / "research.duckdb"
    data_dir: Path = _workspace_root() / "data" / "research"
    default_symbols: str = "005930,000660,035420,051910,105560,068270"
    market_open_time: str = "09:00"
    opening_cutoff_time: str = "10:00"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    kis_base_url: str = ""
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_api_timeout_seconds: float = 15.0
    kis_token_refresh_buffer_seconds: int = 300
    kis_token_cache_path: Path = _workspace_root() / "data" / "research" / "kis_token_cache.json"
    kis_universe_markets: str = "KOSPI,KOSDAQ"
    kis_parallel_workers: int = 10
    kis_request_delay_seconds: float = 0.5
    kis_initial_request_stagger_seconds: float = 1.0
    kis_request_max_retries: int = 2
    kis_request_retry_backoff_seconds: float = 1.5
    postgres_dsn: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_database: str = "QuantTrader"
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_schema: str = "public"

    @field_validator("duckdb_path", mode="before")
    @classmethod
    def _normalize_duckdb_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return _workspace_root() / "data" / "research" / "research.duckdb"
        return value

    @field_validator("data_dir", mode="before")
    @classmethod
    def _normalize_data_dir(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return _workspace_root() / "data" / "research"
        return value

    @field_validator("kis_token_cache_path", mode="before")
    @classmethod
    def _normalize_kis_token_cache_path(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return _workspace_root() / "data" / "research" / "kis_token_cache.json"
        return value

    @property
    def default_symbol_list(self) -> list[str]:
        return [symbol.strip() for symbol in self.default_symbols.split(",") if symbol.strip()]

    @property
    def market_open(self) -> time:
        return _parse_time(self.market_open_time)

    @property
    def opening_cutoff(self) -> time:
        return _parse_time(self.opening_cutoff_time)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def kis_universe_market_list(self) -> list[str]:
        return [market.strip().upper() for market in self.kis_universe_markets.split(",") if market.strip()]

    @property
    def postgres_conninfo(self) -> str:
        if self.postgres_dsn.strip():
            return self.postgres_dsn.strip()
        return (
            f"host={self.postgres_host} "
            f"port={self.postgres_port} "
            f"dbname={self.postgres_database} "
            f"user={self.postgres_user} "
            f"password={self.postgres_password}"
        )


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", maxsplit=1)
    return time(hour=int(hour), minute=int(minute))


@lru_cache
def get_settings() -> Settings:
    return Settings()
