from __future__ import annotations

from pydantic import BaseModel, Field


class DateRangeRequest(BaseModel):
    date_from: str
    date_to: str
    symbols: list[str] = Field(default_factory=list)


class CollectHistoricalMinuteBarsRequest(DateRangeRequest):
    replace_existing: bool = True


class CollectSessionReferenceRequest(DateRangeRequest):
    replace_existing: bool = True


class BuildOpeningBarsRequest(DateRangeRequest):
    replace_existing: bool = True


class SeedMockDataRequest(DateRangeRequest):
    replace_existing: bool = True


class CollectResponse(BaseModel):
    message: str
    provider: str
    symbols: list[str]
    date_from: str
    date_to: str
    rows_written: int


class BuildOpeningBarsResponse(BaseModel):
    message: str
    symbols: list[str]
    date_from: str
    date_to: str
    rows_written: int


class SeedMockDataResponse(BaseModel):
    message: str
    provider: str
    symbols: list[str]
    date_from: str
    date_to: str
    historical_minute_rows: int
    session_reference_rows: int
    opening_bar_rows: int


class MarketDataOverviewResponse(BaseModel):
    historical_bar_count: int
    opening_bar_count: int
    session_reference_count: int
    symbol_count: int
    historical_date_min: str | None
    historical_date_max: str | None
    opening_date_min: str | None
    opening_date_max: str | None
    available_symbols: list[str]


class ProviderSessionResponse(BaseModel):
    provider: str
    configured: bool
    authenticated: bool
    base_url: str | None
    token_expires_at: str | None
    message: str
