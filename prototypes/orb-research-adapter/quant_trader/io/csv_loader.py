from __future__ import annotations

from collections import defaultdict
from csv import DictReader
from datetime import date, datetime
from pathlib import Path

from ..models import MinuteBar, PriceTick, SessionData


def load_sessions(minute_bar_csv: Path, tick_csv: Path | None = None) -> list[SessionData]:
    minute_groups: dict[tuple[str, date], list[MinuteBar]] = defaultdict(list)

    with minute_bar_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = DictReader(handle)
        for row in reader:
            timestamp = _parse_timestamp(row["timestamp"])
            key = (row["symbol"], timestamp.date())
            minute_groups[key].append(
                MinuteBar(
                    symbol=row["symbol"],
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                    prev_close=float(row["prev_close"]),
                )
            )

    tick_groups: dict[tuple[str, date], list[PriceTick]] = defaultdict(list)
    if tick_csv:
        with tick_csv.open("r", encoding="utf-8", newline="") as handle:
            reader = DictReader(handle)
            for row in reader:
                timestamp = _parse_timestamp(row["timestamp"])
                key = (row["symbol"], timestamp.date())
                tick_groups[key].append(
                    PriceTick(
                        symbol=row["symbol"],
                        timestamp=timestamp,
                        price=float(row["price"]),
                        volume=float(row.get("volume") or 0.0),
                    )
                )

    sessions: list[SessionData] = []
    for (symbol, trade_date), bars in sorted(minute_groups.items()):
        ordered_bars = tuple(sorted(bars, key=lambda item: item.timestamp))
        ordered_ticks = tuple(
            sorted(tick_groups.get((symbol, trade_date), []), key=lambda item: item.timestamp)
        )
        first_bar = ordered_bars[0]
        sessions.append(
            SessionData(
                symbol=symbol,
                trade_date=trade_date,
                prev_close=first_bar.prev_close,
                session_open=first_bar.open,
                minute_bars=ordered_bars,
                ticks=ordered_ticks,
            )
        )

    return sessions


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)
