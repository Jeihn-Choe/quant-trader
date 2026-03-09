from __future__ import annotations

from research_bot.domain.market.entities import MinuteBar
from research_bot.domain.orb.models import BreakoutEvent, OrbRange


def detect_first_breakout(
    bars: tuple[MinuteBar, ...],
    orb_range: OrbRange,
    breakout_buffer: float,
    cutoff_time,
) -> BreakoutEvent | None:
    threshold = orb_range.high + breakout_buffer
    for bar in bars:
        if bar.minute_ts < orb_range.end_time:
            continue
        if bar.minute_ts.time() > cutoff_time:
            continue
        if bar.high > threshold:
            return BreakoutEvent(
                timestamp=bar.minute_ts,
                price=bar.high,
                excess=bar.high - orb_range.high,
            )
    return None
