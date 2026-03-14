from __future__ import annotations

from research_bot.domain.orb.models import OrbScanRecord, OrbScanRun
from research_bot.infrastructure.storage.postgresql_connection import PostgreSqlConnectionFactory
from research_bot.infrastructure.storage.postgresql_schema_manager import PostgreSqlSchemaManager


class PostgreSqlAnalysisRepository:
    def __init__(
        self,
        connection_factory: PostgreSqlConnectionFactory,
        schema_manager: PostgreSqlSchemaManager,
    ) -> None:
        self.connection_factory = connection_factory
        self.schema_manager = schema_manager

    def save_run(self, run: OrbScanRun) -> None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                self._set_search_path(cursor)
                cursor.execute("DELETE FROM analysis_runs WHERE run_id = %s", [run.run_id])
                cursor.execute(
                    """
                    INSERT INTO analysis_runs
                    (run_id, created_at, date_from, date_to, orb_window_minutes, breakout_buffer,
                     gap_mode, gap_threshold_pct, requested_symbols, total_sessions, scanned_sessions,
                     gap_up_sessions, breakout_sessions)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            connection.commit()

    def save_results(self, run_id: str, rows: list[OrbScanRecord]) -> None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                self._set_search_path(cursor)
                cursor.execute("DELETE FROM analysis_results WHERE run_id = %s", [run_id])
                payload = [
                    (
                        run_id,
                        row.symbol,
                        row.symbol_name,
                        row.trade_date,
                        row.prev_close,
                        row.market_open_price,
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
                    cursor.executemany(
                        """
                        INSERT INTO analysis_results
                        (run_id, symbol, symbol_name, trade_date, prev_close, market_open_price, gap_pct, gap_up,
                         orb_window_minutes, orb_high, orb_low, breakout, first_breakout_time,
                         first_breakout_price, breakout_excess, cutoff_price, cutoff_above_orb_high)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        payload,
                    )
            connection.commit()

    def get_run(self, run_id: str) -> OrbScanRun | None:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                self._set_search_path(cursor)
                cursor.execute(
                    """
                    SELECT run_id, created_at, date_from, date_to, orb_window_minutes,
                           breakout_buffer, gap_mode, gap_threshold_pct, requested_symbols,
                           total_sessions, scanned_sessions, gap_up_sessions, breakout_sessions
                    FROM analysis_runs
                    WHERE run_id = %s
                    """,
                    [run_id],
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return _map_run(row)

    def list_runs(self, limit: int = 20) -> list[OrbScanRun]:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                self._set_search_path(cursor)
                cursor.execute(
                    """
                    SELECT run_id, created_at, date_from, date_to, orb_window_minutes,
                           breakout_buffer, gap_mode, gap_threshold_pct, requested_symbols,
                           total_sessions, scanned_sessions, gap_up_sessions, breakout_sessions
                    FROM analysis_runs
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    [limit],
                )
                rows = cursor.fetchall()
        return [_map_run(row) for row in rows]

    def list_results(self, run_id: str) -> list[OrbScanRecord]:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                self._set_search_path(cursor)
                cursor.execute(
                    """
                    SELECT symbol, symbol_name, trade_date, prev_close, market_open_price, gap_pct, gap_up,
                           orb_window_minutes, orb_high, orb_low, breakout, first_breakout_time,
                           first_breakout_price, breakout_excess, cutoff_price, cutoff_above_orb_high
                    FROM analysis_results
                    WHERE run_id = %s
                    ORDER BY trade_date DESC, symbol
                    """,
                    [run_id],
                )
                rows = cursor.fetchall()
        return [
            OrbScanRecord(
                symbol=row[0],
                symbol_name=row[1],
                trade_date=row[2],
                prev_close=row[3],
                market_open_price=row[4],
                gap_pct=row[5],
                gap_up=bool(row[6]),
                orb_window_minutes=row[7],
                orb_high=row[8],
                orb_low=row[9],
                breakout=bool(row[10]),
                first_breakout_time=row[11],
                first_breakout_price=row[12],
                breakout_excess=row[13],
                cutoff_price=row[14],
                cutoff_above_orb_high=bool(row[15]) if row[15] is not None else None,
            )
            for row in rows
        ]

    def _set_search_path(self, cursor) -> None:
        cursor.execute(f'SET search_path TO "{self.schema_manager.schema_name}"')


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
