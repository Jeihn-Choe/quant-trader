from __future__ import annotations


def calculate_gap_pct(prev_close: float, session_open: float) -> float:
    if prev_close == 0:
        return 0.0
    return (session_open - prev_close) / prev_close


def is_gap_up(gap_pct: float | None, threshold_pct: float) -> bool:
    if gap_pct is None:
        return False
    return gap_pct >= threshold_pct
