from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CollectHistoricalMinuteBarsCommand:
    date_from: date
    date_to: date
    symbols: list[str]
    replace_existing: bool = True


@dataclass(frozen=True)
class CollectMarketOpenSnapshotCommand:
    date_from: date
    date_to: date
    symbols: list[str]
    replace_existing: bool = True


@dataclass(frozen=True)
class CollectResult:
    provider: str
    symbols: list[str]
    date_from: date
    date_to: date
    rows_written: int
    skipped: bool = False


@dataclass(frozen=True)
class MarketDataOverview:
    historical_bar_count: int
    market_open_snapshot_count: int
    symbol_count: int
    historical_date_min: date | None
    historical_date_max: date | None
    available_symbols: list[str]


@dataclass(frozen=True)
class MarketDataDailySummary:
    trade_date: date
    symbol_count: int
    historical_bar_count: int
    market_open_snapshot_count: int
    preview_symbols: list[str]


@dataclass(frozen=True)
class MarketDataSymbolSummary:
    trade_date: date
    symbol: str
    symbol_name: str | None
    minute_bar_count: int
    session_open: float | None
    session_high: float | None
    session_low: float | None
    session_close: float | None
    total_volume: float | None
    gap_pct: float | None
