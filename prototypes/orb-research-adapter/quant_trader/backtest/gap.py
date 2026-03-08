def is_gap_up(prev_close: float, session_open: float, min_gap_pct: float) -> bool:
    threshold = prev_close * (1.0 + min_gap_pct)
    return session_open >= threshold
