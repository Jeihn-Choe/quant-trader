from __future__ import annotations

from datetime import date
from typing import Protocol

from research_bot.application.dto.market_data_dto import (
    MarketDataDailySummary,
    MarketDataSymbolSummary,
    MarketDataOverview,
)
from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar


class MarketDataRepository(Protocol):
    def get_loaded_historical_minute_bar_symbols(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> set[str]: ...

    def is_historical_minute_bars_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> bool: ...

    def mark_historical_minute_bars_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None: ...

    def replace_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[MinuteBar],
        replace_existing: bool,
        source: str,
    ) -> int: ...

    def get_loaded_market_open_snapshot_symbols(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> set[str]: ...

    def is_market_open_snapshots_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> bool: ...

    def mark_market_open_snapshots_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None: ...

    def replace_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[MarketOpenSnapshot],
        replace_existing: bool,
        source: str,
    ) -> int: ...

    def get_market_data_overview(self) -> MarketDataOverview: ...

    def list_historical_minute_bars(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MinuteBar]: ...

    def list_market_open_snapshots(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MarketOpenSnapshot]: ...

    def list_daily_market_data_summary(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MarketDataDailySummary]: ...

    def list_symbol_market_data_summary(
        self,
        trade_date: date,
        symbols: list[str] | None = None,
    ) -> list[MarketDataSymbolSummary]: ...
