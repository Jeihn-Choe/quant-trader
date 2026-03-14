from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from research_bot.application.dto.analysis_dto import OrbScanCommand, OrbScanReport
from research_bot.application.ports.analysis_repository import AnalysisRepository
from research_bot.application.ports.market_data_repository import MarketDataRepository
from research_bot.domain.market.entities import MinuteBar
from research_bot.domain.orb.breakout_detector import detect_first_breakout
from research_bot.domain.orb.calculator import calculate_orb
from research_bot.domain.orb.gap import is_gap_up
from research_bot.domain.orb.models import OrbScanRecord, OrbScanRun


class ScanOrbBreakoutsUseCase:
    def __init__(
        self,
        market_data_repository: MarketDataRepository,
        analysis_repository: AnalysisRepository,
        market_open,
        opening_cutoff,
    ) -> None:
        self.market_data_repository = market_data_repository
        self.analysis_repository = analysis_repository
        self.market_open = market_open
        self.opening_cutoff = opening_cutoff

    def execute(self, command: OrbScanCommand) -> OrbScanReport:
        symbols = command.symbols or None
        bars = self.market_data_repository.list_historical_minute_bars(
            date_from=command.date_from,
            date_to=command.date_to,
            symbols=symbols,
        )
        market_open_snapshots = self.market_data_repository.list_market_open_snapshots(
            date_from=command.date_from,
            date_to=command.date_to,
            symbols=symbols,
        )

        scan_bars = [
            bar
            for bar in bars
            if self.market_open <= bar.minute_ts.time() <= self.opening_cutoff
        ]
        sessions = _group_bars_by_session(scan_bars)
        market_open_snapshot_map = {
            (row.symbol, row.trade_date): row for row in market_open_snapshots
        }
        total_sessions = len(sessions)
        gap_up_sessions = 0
        rows: list[OrbScanRecord] = []

        for key in sorted(sessions.keys()):
            session_bars = sessions[key]
            market_open_snapshot = market_open_snapshot_map.get(key)
            symbol_name = (
                market_open_snapshot.symbol_name
                if market_open_snapshot and market_open_snapshot.symbol_name
                else session_bars[0].symbol_name
            )
            gap_pct = market_open_snapshot.gap_pct if market_open_snapshot else None
            gap_up = is_gap_up(gap_pct, command.gap_threshold_pct)
            if gap_up:
                gap_up_sessions += 1
            if command.gap_mode == "gap_up_only" and not gap_up:
                continue

            orb_range = calculate_orb(
                bars=tuple(session_bars),
                orb_window_minutes=command.orb_window_minutes,
                market_open=self.market_open,
            )
            if orb_range is None:
                continue

            breakout = detect_first_breakout(
                bars=tuple(session_bars),
                orb_range=orb_range,
                breakout_buffer=command.breakout_buffer,
                cutoff_time=self.opening_cutoff,
            )
            cutoff_price = _find_cutoff_price(session_bars, self.opening_cutoff)

            rows.append(
                OrbScanRecord(
                    symbol=key[0],
                    symbol_name=symbol_name,
                    trade_date=key[1],
                    prev_close=market_open_snapshot.prev_close if market_open_snapshot else None,
                    market_open_price=(
                        market_open_snapshot.market_open_price
                        if market_open_snapshot
                        else None
                    ),
                    gap_pct=gap_pct,
                    gap_up=gap_up,
                    orb_window_minutes=command.orb_window_minutes,
                    orb_high=orb_range.high,
                    orb_low=orb_range.low,
                    breakout=breakout is not None,
                    first_breakout_time=breakout.timestamp if breakout else None,
                    first_breakout_price=breakout.price if breakout else None,
                    breakout_excess=breakout.excess if breakout else None,
                    cutoff_price=cutoff_price,
                    cutoff_above_orb_high=(
                        cutoff_price > orb_range.high if cutoff_price is not None else None
                    ),
                )
            )

        breakout_sessions = sum(1 for row in rows if row.breakout)
        run = OrbScanRun(
            run_id=uuid4().hex,
            created_at=datetime.now(),
            date_from=command.date_from,
            date_to=command.date_to,
            orb_window_minutes=command.orb_window_minutes,
            breakout_buffer=command.breakout_buffer,
            gap_mode=command.gap_mode,
            gap_threshold_pct=command.gap_threshold_pct,
            requested_symbols=command.symbols,
            total_sessions=total_sessions,
            scanned_sessions=len(rows),
            gap_up_sessions=gap_up_sessions,
            breakout_sessions=breakout_sessions,
        )
        self.analysis_repository.save_run(run)
        self.analysis_repository.save_results(run.run_id, rows)
        return run, rows


def _group_bars_by_session(bars: list[MinuteBar]) -> dict[tuple[str, object], list[MinuteBar]]:
    grouped: dict[tuple[str, object], list[MinuteBar]] = defaultdict(list)
    for bar in bars:
        grouped[(bar.symbol, bar.trade_date)].append(bar)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.minute_ts)
    return grouped


def _find_cutoff_price(bars: list[MinuteBar], opening_cutoff) -> float | None:
    candidates = [bar for bar in bars if bar.minute_ts.time() <= opening_cutoff]
    if not candidates:
        return None
    return candidates[-1].close
