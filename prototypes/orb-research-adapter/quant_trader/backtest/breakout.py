from __future__ import annotations

from datetime import datetime

from ..models import BreakoutEvent, PriceProbe


def find_first_breakout(
    orb_high: float,
    probes: tuple[PriceProbe, ...],
    start_time: datetime,
    cutoff_time: datetime,
    breakout_buffer: float = 0.0,
) -> BreakoutEvent | None:
    threshold = orb_high + breakout_buffer
    for probe in probes:
        if probe.timestamp < start_time or probe.timestamp > cutoff_time:
            continue
        if probe.high > threshold:
            return BreakoutEvent(
                timestamp=probe.timestamp,
                price=probe.high,
                excess=probe.high - orb_high,
            )
    return None
