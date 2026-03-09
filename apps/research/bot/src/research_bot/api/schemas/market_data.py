from __future__ import annotations

from pydantic import BaseModel, Field


class DateRangeRequest(BaseModel):
    date_from: str
    date_to: str
    symbols: list[str] = Field(default_factory=list)


class CollectHistoricalMinuteBarsRequest(DateRangeRequest):
    replace_existing: bool = True


class CollectMarketOpenSnapshotRequest(DateRangeRequest):
    replace_existing: bool = True


class CollectAllMarketDataRequest(DateRangeRequest):
    replace_existing: bool = True


class CollectResponse(BaseModel):
    message: str
    provider: str
    symbols: list[str]
    date_from: str
    date_to: str
    rows_written: int
    skipped: bool = False


class CollectAllMarketDataResponse(BaseModel):
    message: str
    provider: str
    symbols: list[str]
    date_from: str
    date_to: str
    historical_minute_rows: int
    market_open_snapshot_rows: int
    historical_minute_skipped: bool = False
    market_open_snapshot_skipped: bool = False


class MarketDataOverviewResponse(BaseModel):
    historical_bar_count: int
    market_open_snapshot_count: int
    symbol_count: int
    historical_date_min: str | None
    historical_date_max: str | None
    available_symbols: list[str]


class MarketDataDailySummaryResponse(BaseModel):
    trade_date: str
    symbol_count: int
    historical_bar_count: int
    market_open_snapshot_count: int
    preview_symbols: list[str]


class MarketDataSymbolSummaryResponse(BaseModel):
    trade_date: str
    symbol: str
    symbol_name: str | None
    minute_bar_count: int
    session_open: float | None
    session_high: float | None
    session_low: float | None
    session_close: float | None
    total_volume: float | None
    gap_pct: float | None


class MinuteBarResponse(BaseModel):
    symbol: str
    symbol_name: str | None
    trade_date: str
    minute_ts: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class ProviderSessionResponse(BaseModel):
    provider: str
    configured: bool
    authenticated: bool
    base_url: str | None
    token_expires_at: str | None
    message: str
