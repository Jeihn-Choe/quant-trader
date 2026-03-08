from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any
import tomllib


@dataclass(frozen=True)
class FileConfig:
    minute_bar_csv: Path
    tick_csv: Path | None
    output_csv: Path


@dataclass(frozen=True)
class SessionConfig:
    market_open: time
    analysis_cutoff: time


@dataclass(frozen=True)
class StrategyConfig:
    min_gap_pct: float
    orb_windows: tuple[int, ...]
    confirmation_windows: tuple[int, ...]
    breakout_buffer: float


@dataclass(frozen=True)
class AppConfig:
    files: FileConfig
    session: SessionConfig
    strategy: StrategyConfig


def load_config(path: Path) -> AppConfig:
    config_path = path.resolve()
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)

    files_section = raw.get("files", {})
    session_section = raw.get("session", {})
    strategy_section = raw.get("strategy", {})

    base_dir = config_path.parent
    tick_csv = files_section.get("tick_csv", "")

    return AppConfig(
        files=FileConfig(
            minute_bar_csv=_resolve_path(base_dir, files_section["minute_bar_csv"]),
            tick_csv=_resolve_path(base_dir, tick_csv) if tick_csv else None,
            output_csv=_resolve_path(base_dir, files_section["output_csv"]),
        ),
        session=SessionConfig(
            market_open=_parse_clock(session_section.get("market_open", "09:00")),
            analysis_cutoff=_parse_clock(
                session_section.get("analysis_cutoff", "10:00")
            ),
        ),
        strategy=StrategyConfig(
            min_gap_pct=float(strategy_section.get("min_gap_pct", 0.0)),
            orb_windows=_parse_int_tuple(strategy_section.get("orb_windows", [3, 5, 10, 15])),
            confirmation_windows=_parse_int_tuple(
                strategy_section.get("confirmation_windows", [10, 30, 60])
            ),
            breakout_buffer=float(strategy_section.get("breakout_buffer", 0.0)),
        ),
    )


def _resolve_path(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _parse_clock(value: str) -> time:
    hour_text, minute_text = value.split(":", maxsplit=1)
    return time(hour=int(hour_text), minute=int(minute_text))


def _parse_int_tuple(values: Any) -> tuple[int, ...]:
    return tuple(int(value) for value in values)
