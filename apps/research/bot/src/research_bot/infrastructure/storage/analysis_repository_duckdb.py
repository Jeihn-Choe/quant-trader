from __future__ import annotations

from research_bot.domain.orb.models import OrbScanRecord, OrbScanRun
from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory
from research_bot.infrastructure.storage.schema_manager import DuckDbSchemaManager


class DuckDbAnalysisRepository:
    def __init__(
        self,
        connection_factory: DuckDbConnectionFactory,
        schema_manager: DuckDbSchemaManager,
    ) -> None:
        self.connection_factory = connection_factory
        self.schema_manager = schema_manager

    def save_run(self, run: OrbScanRun) -> None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            connection.execute("DELETE FROM analysis_runs WHERE run_id = ?", [run.run_id])
            connection.execute(
                """
                INSERT INTO analysis_runs
                (run_id, created_at, date_from, date_to, orb_window_minutes, breakout_buffer,
                 gap_mode, gap_threshold_pct, requested_symbols, total_sessions, scanned_sessions,
                 gap_up_sessions, breakout_sessions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run.run_id,
                    run.created_at,
                    run.date_from,
                    run.date_to,
                    run.orb_window_minutes,
                    run.breakout_buffer,
                    run.gap_mode,
                    run.gap_threshold_pct,
                    ",".join(run.requested_symbols),
                    run.total_sessions,
                    run.scanned_sessions,
                    run.gap_up_sessions,
                    run.breakout_sessions,
                ],
            )

    def save_results(self, run_id: str, rows: list[OrbScanRecord]) -> None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            connection.execute("DELETE FROM analysis_results WHERE run_id = ?", [run_id])
            payload = [
                (
                    run_id,
                    row.symbol,
                    row.trade_date,
                    row.prev_close,
                    row.session_open,
                    row.gap_pct,
                    row.gap_up,
                    row.orb_window_minutes,
                    row.orb_high,
                    row.orb_low,
                    row.breakout,
                    row.first_breakout_time,
                    row.first_breakout_price,
                    row.breakout_excess,
                    row.cutoff_price,
                    row.cutoff_above_orb_high,
                )
                for row in rows
            ]
            if payload:
                connection.executemany(
                    """
                    INSERT INTO analysis_results
                    (run_id, symbol, trade_date, prev_close, session_open, gap_pct, gap_up,
                     orb_window_minutes, orb_high, orb_low, breakout, first_breakout_time,
                     first_breakout_price, breakout_excess, cutoff_price, cutoff_above_orb_high)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )

    def get_run(self, run_id: str) -> OrbScanRun | None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            row = connection.execute(
                """
                SELECT run_id, created_at, date_from, date_to, orb_window_minutes,
                       breakout_buffer, gap_mode, gap_threshold_pct, requested_symbols,
                       total_sessions, scanned_sessions, gap_up_sessions, breakout_sessions
                FROM analysis_runs
                WHERE run_id = ?
                """,
                [run_id],
            ).fetchone()
        if row is None:
            return None
        return _map_run(row)

    def list_runs(self, limit: int = 20) -> list[OrbScanRun]:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id, created_at, date_from, date_to, orb_window_minutes,
                       breakout_buffer, gap_mode, gap_threshold_pct, requested_symbols,
                       total_sessions, scanned_sessions, gap_up_sessions, breakout_sessions
                FROM analysis_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        return [_map_run(row) for row in rows]

    def list_results(self, run_id: str) -> list[OrbScanRecord]:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                """
                SELECT symbol, trade_date, prev_close, session_open, gap_pct, gap_up,
                       orb_window_minutes, orb_high, orb_low, breakout, first_breakout_time,
                       first_breakout_price, breakout_excess, cutoff_price, cutoff_above_orb_high
                FROM analysis_results
                WHERE run_id = ?
                ORDER BY trade_date DESC, symbol
                """,
                [run_id],
            ).fetchall()
        return [
            OrbScanRecord(
                symbol=row[0],
                trade_date=row[1],
                prev_close=row[2],
                session_open=row[3],
                gap_pct=row[4],
                gap_up=bool(row[5]),
                orb_window_minutes=row[6],
                orb_high=row[7],
                orb_low=row[8],
                breakout=bool(row[9]),
                first_breakout_time=row[10],
                first_breakout_price=row[11],
                breakout_excess=row[12],
                cutoff_price=row[13],
                cutoff_above_orb_high=row[14],
            )
            for row in rows
        ]


def _map_run(row) -> OrbScanRun:
    requested_symbols = [value for value in (row[8] or "").split(",") if value]
    return OrbScanRun(
        run_id=row[0],
        created_at=row[1],
        date_from=row[2],
        date_to=row[3],
        orb_window_minutes=row[4],
        breakout_buffer=row[5],
        gap_mode=row[6],
        gap_threshold_pct=row[7],
        requested_symbols=requested_symbols,
        total_sessions=row[9],
        scanned_sessions=row[10],
        gap_up_sessions=row[11],
        breakout_sessions=row[12],
    )
