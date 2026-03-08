from __future__ import annotations

from datetime import datetime

from ..config import AppConfig
from ..models import BacktestRecord, PriceProbe, SessionData
from .breakout import find_first_breakout
from .gap import is_gap_up
from .orb import calculate_orb
from .retention import calculate_retention, evaluate_confirmations


class OrbBacktestEngine:
    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def run(self, sessions: list[SessionData]) -> list[BacktestRecord]:
        records: list[BacktestRecord] = []
        for session in sessions:
            records.extend(self._run_session(session))
        return records

    def _run_session(self, session: SessionData) -> list[BacktestRecord]:
        gap_up = is_gap_up(
            prev_close=session.prev_close,
            session_open=session.session_open,
            min_gap_pct=self.config.strategy.min_gap_pct,
        )
        cutoff_time = datetime.combine(
            session.trade_date, self.config.session.analysis_cutoff
        )
        minute_probes = _minute_probes(session)
        tick_probes = _tick_probes(session)
        analysis_probes = tick_probes or minute_probes
        records: list[BacktestRecord] = []

        for orb_window in self.config.strategy.orb_windows:
            try:
                orb_range = calculate_orb(
                    session.minute_bars,
                    window_minutes=orb_window,
                    market_open=self.config.session.market_open,
                )
            except ValueError:
                continue

            cutoff_price = _cutoff_price(minute_probes, cutoff_time)
            cutoff_above = (
                cutoff_price > orb_range.high if cutoff_price is not None else None
            )

            breakout = None
            confirmations = {
                window: None for window in self.config.strategy.confirmation_windows
            }
            retention = None

            if gap_up:
                breakout = find_first_breakout(
                    orb_high=orb_range.high,
                    probes=analysis_probes,
                    start_time=orb_range.end_time,
                    cutoff_time=cutoff_time,
                    breakout_buffer=self.config.strategy.breakout_buffer,
                )
                if breakout is not None:
                    confirmations = evaluate_confirmations(
                        orb_high=orb_range.high,
                        ticks=session.ticks,
                        breakout_time=breakout.timestamp,
                        windows=self.config.strategy.confirmation_windows,
                    )
                    retention = calculate_retention(
                        orb_high=orb_range.high,
                        probes=analysis_probes,
                        breakout_time=breakout.timestamp,
                        cutoff_time=cutoff_time,
                    )

            records.append(
                BacktestRecord(
                    symbol=session.symbol,
                    trade_date=session.trade_date,
                    gap_up=gap_up,
                    orb_window_minutes=orb_window,
                    orb_high=orb_range.high,
                    orb_low=orb_range.low,
                    breakout=breakout is not None,
                    first_breakout_time=breakout.timestamp if breakout else None,
                    first_breakout_price=breakout.price if breakout else None,
                    first_breakout_excess=breakout.excess if breakout else None,
                    cutoff_price=(
                        retention.cutoff_price if retention is not None else cutoff_price
                    ),
                    cutoff_above_orb_high=(
                        retention.cutoff_above_orb_high
                        if retention is not None
                        else cutoff_above
                    ),
                    retention_ratio=(
                        retention.retention_ratio if retention is not None else None
                    ),
                    confirmations=confirmations,
                )
            )

        return records


def _minute_probes(session: SessionData) -> tuple[PriceProbe, ...]:
    return tuple(
        PriceProbe(
            timestamp=bar.timestamp,
            high=bar.high,
            low=bar.low,
            close=bar.close,
        )
        for bar in session.minute_bars
    )


def _tick_probes(session: SessionData) -> tuple[PriceProbe, ...]:
    return tuple(
        PriceProbe(
            timestamp=tick.timestamp,
            high=tick.price,
            low=tick.price,
            close=tick.price,
        )
        for tick in session.ticks
    )


def _cutoff_price(probes: tuple[PriceProbe, ...], cutoff_time: datetime) -> float | None:
    candidates = tuple(probe for probe in probes if probe.timestamp <= cutoff_time)
    if not candidates:
        return None
    return candidates[-1].close
