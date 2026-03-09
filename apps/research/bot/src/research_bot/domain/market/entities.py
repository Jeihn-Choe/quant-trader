from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class MinuteBar:
    symbol: str
    symbol_name: str | None
    trade_date: date
    minute_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketOpenSnapshot:
    symbol: str
    symbol_name: str | None
    trade_date: date
    prev_close: float
    market_open_price: float
    gap_pct: float
