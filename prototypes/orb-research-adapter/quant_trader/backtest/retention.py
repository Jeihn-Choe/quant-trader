from __future__ import annotations

from datetime import datetime, timedelta

from ..models import PriceProbe, PriceTick, RetentionMetrics


def evaluate_confirmations(
    orb_high: float,
    ticks: tuple[PriceTick, ...],
    breakout_time: datetime,
    windows: tuple[int, ...],
) -> dict[int, bool | None]:
    if not ticks:
        return {window: None for window in windows}

    results: dict[int, bool | None] = {}
    future_ticks = tuple(tick for tick in ticks if tick.timestamp >= breakout_time)

    for window in windows:
        window_end = breakout_time + timedelta(seconds=window)
        window_ticks = tuple(
            tick for tick in future_ticks if breakout_time <= tick.timestamp <= window_end
        )
        covered = any(tick.timestamp >= window_end for tick in future_ticks)
        if not window_ticks or not covered:
            results[window] = None
            continue
        results[window] = all(tick.price > orb_high for tick in window_ticks)

    return results


def calculate_retention(
    orb_high: float,
    probes: tuple[PriceProbe, ...],
    breakout_time: datetime,
    cutoff_time: datetime,
) -> RetentionMetrics | None:
    active_probes = tuple(
        probe for probe in probes if breakout_time <= probe.timestamp <= cutoff_time
    )
    if not active_probes:
        return None

    above_count = sum(1 for probe in active_probes if probe.close > orb_high)
    cutoff_probe = active_probes[-1]
    return RetentionMetrics(
        cutoff_price=cutoff_probe.close,
        cutoff_above_orb_high=cutoff_probe.close > orb_high,
        retention_ratio=above_count / len(active_probes),
    )
