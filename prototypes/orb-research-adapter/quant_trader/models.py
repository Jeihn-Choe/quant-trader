from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class MinuteBar:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    prev_close: float


@dataclass(frozen=True)
class PriceTick:
    symbol: str
    timestamp: datetime
    price: float
    volume: float = 0.0


@dataclass(frozen=True)
class PriceProbe:
    timestamp: datetime
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class SessionData:
    symbol: str
    trade_date: date
    prev_close: float
    session_open: float
    minute_bars: tuple[MinuteBar, ...]
    ticks: tuple[PriceTick, ...] = ()


@dataclass(frozen=True)
class OrbRange:
    start_time: datetime
    end_time: datetime
    high: float
    low: float


@dataclass(frozen=True)
class BreakoutEvent:
    timestamp: datetime
    price: float
    excess: float


@dataclass(frozen=True)
class RetentionMetrics:
    cutoff_price: float
    cutoff_above_orb_high: bool
    retention_ratio: float


@dataclass(frozen=True)
class BacktestRecord:
    symbol: str
    trade_date: date
    gap_up: bool
    orb_window_minutes: int
    orb_high: float | None
    orb_low: float | None
    breakout: bool
    first_breakout_time: datetime | None
    first_breakout_price: float | None
    first_breakout_excess: float | None
    cutoff_price: float | None
    cutoff_above_orb_high: bool | None
    retention_ratio: float | None
    confirmations: dict[int, bool | None] = field(default_factory=dict)

    def to_dict(self, confirmation_windows: tuple[int, ...]) -> dict[str, object]:
        row = {
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat(),
            "gap_up": self.gap_up,
            "orb_window_minutes": self.orb_window_minutes,
            "orb_high": self.orb_high,
            "orb_low": self.orb_low,
            "breakout": self.breakout,
            "first_breakout_time": (
                self.first_breakout_time.isoformat() if self.first_breakout_time else ""
            ),
            "first_breakout_price": self.first_breakout_price,
            "first_breakout_excess": self.first_breakout_excess,
            "cutoff_price": self.cutoff_price,
            "cutoff_above_orb_high": self.cutoff_above_orb_high,
            "retention_ratio": self.retention_ratio,
        }
        for window in confirmation_windows:
            row[f"confirm_{window}s"] = self.confirmations.get(window)
        return row
