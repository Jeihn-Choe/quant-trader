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
class CollectSessionReferenceCommand:
    date_from: date
    date_to: date
    symbols: list[str]
    replace_existing: bool = True


@dataclass(frozen=True)
class BuildOpeningBarsCommand:
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


@dataclass(frozen=True)
class BuildOpeningBarsResult:
    symbols: list[str]
    date_from: date
    date_to: date
    rows_written: int


@dataclass(frozen=True)
class MarketDataOverview:
    historical_bar_count: int
    opening_bar_count: int
    session_reference_count: int
    symbol_count: int
    historical_date_min: date | None
    historical_date_max: date | None
    opening_date_min: date | None
    opening_date_max: date | None
    available_symbols: list[str]
