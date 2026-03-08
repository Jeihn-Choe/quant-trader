from __future__ import annotations

from csv import DictWriter
from pathlib import Path

from ..models import BacktestRecord


def write_results(
    output_csv: Path,
    records: list[BacktestRecord],
    confirmation_windows: tuple[int, ...],
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "symbol",
        "trade_date",
        "gap_up",
        "orb_window_minutes",
        "orb_high",
        "orb_low",
        "breakout",
        "first_breakout_time",
        "first_breakout_price",
        "first_breakout_excess",
        "cutoff_price",
        "cutoff_above_orb_high",
        "retention_ratio",
    ] + [f"confirm_{window}s" for window in confirmation_windows]

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict(confirmation_windows))
