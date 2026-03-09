from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class MinuteBar:
    symbol: str
    trade_date: date
    minute_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class SessionReference:
    symbol: str
    trade_date: date
    prev_close: float
    session_open: float
    gap_pct: float
