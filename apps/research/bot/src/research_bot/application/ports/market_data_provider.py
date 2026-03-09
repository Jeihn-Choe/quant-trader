from __future__ import annotations

from datetime import date
from typing import Protocol

from research_bot.domain.market.entities import MinuteBar, SessionReference


class MarketDataProvider(Protocol):
    @property
    def name(self) -> str: ...

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]: ...

    def get_session_references(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[SessionReference]: ...
