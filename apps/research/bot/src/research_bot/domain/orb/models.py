from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


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
class OrbScanRecord:
    symbol: str
    trade_date: date
    prev_close: float | None
    session_open: float | None
    gap_pct: float | None
    gap_up: bool
    orb_window_minutes: int
    orb_high: float | None
    orb_low: float | None
    breakout: bool
    first_breakout_time: datetime | None
    first_breakout_price: float | None
    breakout_excess: float | None
    cutoff_price: float | None
    cutoff_above_orb_high: bool | None


@dataclass(frozen=True)
class OrbScanRun:
    run_id: str
    created_at: datetime
    date_from: date
    date_to: date
    orb_window_minutes: int
    breakout_buffer: float
    gap_mode: str
    gap_threshold_pct: float
    requested_symbols: list[str]
    total_sessions: int
    scanned_sessions: int
    gap_up_sessions: int
    breakout_sessions: int

    @property
    def breakout_rate(self) -> float:
        if self.scanned_sessions == 0:
            return 0.0
        return self.breakout_sessions / self.scanned_sessions
