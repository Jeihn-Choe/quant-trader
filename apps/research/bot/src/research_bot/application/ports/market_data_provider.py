from __future__ import annotations

from datetime import date
from typing import Protocol

from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar


class MarketDataProvider(Protocol):
    @property
    def name(self) -> str: ...

    def resolve_symbols(self, symbols: list[str]) -> list[str]: ...

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]: ...

    def get_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]: ...
