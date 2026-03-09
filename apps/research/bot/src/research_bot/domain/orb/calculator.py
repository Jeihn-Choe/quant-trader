from __future__ import annotations

from datetime import datetime, timedelta

from research_bot.domain.market.entities import MinuteBar
from research_bot.domain.orb.models import OrbRange


def calculate_orb(
    bars: tuple[MinuteBar, ...],
    orb_window_minutes: int,
    market_open,
) -> OrbRange | None:
    if not bars:
        return None

    start_time = datetime.combine(bars[0].trade_date, market_open)
    end_time = start_time + timedelta(minutes=orb_window_minutes)
    orb_bars = [bar for bar in bars if start_time <= bar.minute_ts < end_time]
    if not orb_bars:
        return None

    return OrbRange(
        start_time=start_time,
        end_time=end_time,
        high=max(bar.high for bar in orb_bars),
        low=min(bar.low for bar in orb_bars),
    )
