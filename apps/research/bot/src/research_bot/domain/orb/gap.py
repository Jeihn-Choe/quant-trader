from __future__ import annotations


def calculate_gap_pct(prev_close: float, market_open_price: float) -> float:
    if prev_close == 0:
        return 0.0
    return (market_open_price - prev_close) / prev_close


def is_gap_up(gap_pct: float | None, threshold_pct: float) -> bool:
    if gap_pct is None:
        return False
    return gap_pct >= threshold_pct
