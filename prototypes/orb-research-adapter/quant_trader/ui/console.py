from __future__ import annotations

from pathlib import Path

from ..models import BacktestRecord


def print_summary(records: list[BacktestRecord], output_csv: Path) -> None:
    gap_up_count = sum(1 for record in records if record.gap_up)
    breakout_count = sum(1 for record in records if record.breakout)

    print(f"records: {len(records)}")
    print(f"gap-up records: {gap_up_count}")
    print(f"breakout records: {breakout_count}")
    print(f"output: {output_csv}")
