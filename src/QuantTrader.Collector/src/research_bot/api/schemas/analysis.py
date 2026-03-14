from __future__ import annotations

from pydantic import BaseModel, Field


class OrbScanRequest(BaseModel):
    date_from: str
    date_to: str
    symbols: list[str] = Field(default_factory=list)
    orb_window_minutes: int = 5
    breakout_buffer: float = 0.0
    gap_mode: str = "all"
    gap_threshold_pct: float = 0.0


class OrbScanSummaryResponse(BaseModel):
    total_sessions: int
    scanned_sessions: int
    gap_up_sessions: int
    breakout_sessions: int
    breakout_rate: float


class OrbScanResultResponse(BaseModel):
    symbol: str
    symbol_name: str | None
    trade_date: str
    prev_close: float | None
    market_open_price: float | None
    gap_pct: float | None
    gap_up: bool
    orb_window_minutes: int
    orb_high: float | None
    orb_low: float | None
    breakout: bool
    first_breakout_time: str | None
    first_breakout_price: float | None
    breakout_excess: float | None
    cutoff_price: float | None
    cutoff_above_orb_high: bool | None


class OrbScanRunResponse(BaseModel):
    run_id: str
    created_at: str
    date_from: str
    date_to: str
    orb_window_minutes: int
    breakout_buffer: float
    gap_mode: str
    gap_threshold_pct: float
    requested_symbols: list[str]
    summary: OrbScanSummaryResponse
    results: list[OrbScanResultResponse]


class OrbScanRunListItemResponse(BaseModel):
    run_id: str
    created_at: str
    date_from: str
    date_to: str
    orb_window_minutes: int
    gap_mode: str
    breakout_sessions: int
