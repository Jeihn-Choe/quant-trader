from __future__ import annotations

from datetime import datetime, timedelta, time

from ..models import MinuteBar, OrbRange


def calculate_orb(
    minute_bars: tuple[MinuteBar, ...], window_minutes: int, market_open: time
) -> OrbRange:
    if not minute_bars:
        raise ValueError("Cannot calculate ORB without minute bars.")

    trade_date = minute_bars[0].timestamp.date()
    start_time = datetime.combine(trade_date, market_open)
    end_time = start_time + timedelta(minutes=window_minutes)
    orb_bars = tuple(
        bar for bar in minute_bars if start_time <= bar.timestamp < end_time
    )
    if not orb_bars:
        raise ValueError(f"No bars found for ORB window {window_minutes}.")

    return OrbRange(
        start_time=start_time,
        end_time=end_time,
        high=max(bar.high for bar in orb_bars),
        low=min(bar.low for bar in orb_bars),
    )
