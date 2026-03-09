from __future__ import annotations

from datetime import date
from typing import Protocol

from research_bot.application.dto.market_data_dto import MarketDataOverview
from research_bot.domain.market.entities import MinuteBar, SessionReference


class MarketDataRepository(Protocol):
    def replace_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[MinuteBar],
        replace_existing: bool,
        source: str,
    ) -> int: ...

    def replace_session_references(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[SessionReference],
        replace_existing: bool,
        source: str,
    ) -> int: ...

    def rebuild_opening_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        replace_existing: bool,
    ) -> int: ...

    def get_market_data_overview(self) -> MarketDataOverview: ...

    def list_opening_bars(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MinuteBar]: ...

    def list_session_references(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[SessionReference]: ...
