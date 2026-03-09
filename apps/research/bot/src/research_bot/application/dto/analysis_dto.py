from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from research_bot.domain.orb.models import OrbScanRecord, OrbScanRun


@dataclass(frozen=True)
class OrbScanCommand:
    date_from: date
    date_to: date
    symbols: list[str]
    orb_window_minutes: int
    breakout_buffer: float
    gap_mode: str
    gap_threshold_pct: float


OrbScanReport = tuple[OrbScanRun, list[OrbScanRecord]]
