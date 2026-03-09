from __future__ import annotations

from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory


class DuckDbSchemaManager:
    def __init__(self, connection_factory: DuckDbConnectionFactory) -> None:
        self.connection_factory = connection_factory

    def initialize(self) -> None:
        with self.connection_factory.connect() as connection:
            self._migrate_legacy_market_open_snapshot(connection)
            self._migrate_legacy_analysis_results(connection)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS historical_minute_bars (
                    symbol VARCHAR NOT NULL,
                    symbol_name VARCHAR,
                    trade_date DATE NOT NULL,
                    minute_ts TIMESTAMP NOT NULL,
                    open DOUBLE NOT NULL,
                    high DOUBLE NOT NULL,
                    low DOUBLE NOT NULL,
                    close DOUBLE NOT NULL,
                    volume DOUBLE NOT NULL,
                    source VARCHAR NOT NULL,
                    collected_at TIMESTAMP NOT NULL
                )
                """
            )
            self._ensure_optional_column(connection, "historical_minute_bars", "symbol_name", "VARCHAR")
            self._deduplicate_historical_minute_bars(connection)
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_historical_minute_bars
                ON historical_minute_bars(symbol, trade_date, minute_ts)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_open_snapshot (
                    symbol VARCHAR NOT NULL,
                    symbol_name VARCHAR,
                    trade_date DATE NOT NULL,
                    prev_close DOUBLE NOT NULL,
                    market_open_price DOUBLE NOT NULL,
                    gap_pct DOUBLE NOT NULL,
                    source VARCHAR NOT NULL,
                    collected_at TIMESTAMP NOT NULL
                )
                """
            )
            self._ensure_optional_column(connection, "market_open_snapshot", "symbol_name", "VARCHAR")
            self._deduplicate_market_open_snapshot(connection)
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_market_open_snapshot
                ON market_open_snapshot(symbol, trade_date)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    run_id VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    date_from DATE NOT NULL,
                    date_to DATE NOT NULL,
                    orb_window_minutes INTEGER NOT NULL,
                    breakout_buffer DOUBLE NOT NULL,
                    gap_mode VARCHAR NOT NULL,
                    gap_threshold_pct DOUBLE NOT NULL,
                    requested_symbols VARCHAR NOT NULL,
                    total_sessions INTEGER NOT NULL,
                    scanned_sessions INTEGER NOT NULL,
                    gap_up_sessions INTEGER NOT NULL,
                    breakout_sessions INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_runs
                ON analysis_runs(run_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_results (
                    run_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    symbol_name VARCHAR,
                    trade_date DATE NOT NULL,
                    prev_close DOUBLE,
                    market_open_price DOUBLE,
                    gap_pct DOUBLE,
                    gap_up BOOLEAN NOT NULL,
                    orb_window_minutes INTEGER NOT NULL,
                    orb_high DOUBLE,
                    orb_low DOUBLE,
                    breakout BOOLEAN NOT NULL,
                    first_breakout_time TIMESTAMP,
                    first_breakout_price DOUBLE,
                    breakout_excess DOUBLE,
                    cutoff_price DOUBLE,
                    cutoff_above_orb_high BOOLEAN
                )
                """
            )
            self._ensure_optional_column(connection, "analysis_results", "symbol_name", "VARCHAR")
            self._deduplicate_analysis_results(connection)
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_results
                ON analysis_results(run_id, symbol, trade_date)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_load_ranges (
                    dataset VARCHAR NOT NULL,
                    scope_key VARCHAR NOT NULL,
                    date_from DATE NOT NULL,
                    date_to DATE NOT NULL,
                    source VARCHAR NOT NULL,
                    loaded_at TIMESTAMP NOT NULL
                )
                """
            )
            self._deduplicate_market_data_load_ranges(connection)
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_market_data_load_ranges
                ON market_data_load_ranges(dataset, scope_key, date_from, date_to)
                """
            )

    def _deduplicate_historical_minute_bars(self, connection) -> None:
        connection.execute(
            """
            DELETE FROM historical_minute_bars
            WHERE rowid IN (
                SELECT rowid
                FROM (
                    SELECT
                        rowid,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol, trade_date, minute_ts
                            ORDER BY collected_at DESC
                        ) AS rn
                    FROM historical_minute_bars
                ) dedup
                WHERE rn > 1
            )
            """
        )

    def _deduplicate_market_open_snapshot(self, connection) -> None:
        connection.execute(
            """
            DELETE FROM market_open_snapshot
            WHERE rowid IN (
                SELECT rowid
                FROM (
                    SELECT
                        rowid,
                        ROW_NUMBER() OVER (
                            PARTITION BY symbol, trade_date
                            ORDER BY collected_at DESC
                        ) AS rn
                    FROM market_open_snapshot
                ) dedup
                WHERE rn > 1
            )
            """
        )

    def _deduplicate_analysis_results(self, connection) -> None:
        connection.execute(
            """
            DELETE FROM analysis_results
            WHERE rowid IN (
                SELECT rowid
                FROM (
                    SELECT
                        rowid,
                        ROW_NUMBER() OVER (
                            PARTITION BY run_id, symbol, trade_date
                            ORDER BY trade_date DESC
                        ) AS rn
                    FROM analysis_results
                ) dedup
                WHERE rn > 1
            )
            """
        )

    def _deduplicate_market_data_load_ranges(self, connection) -> None:
        connection.execute(
            """
            DELETE FROM market_data_load_ranges
            WHERE rowid IN (
                SELECT rowid
                FROM (
                    SELECT
                        rowid,
                        ROW_NUMBER() OVER (
                            PARTITION BY dataset, scope_key, date_from, date_to
                            ORDER BY loaded_at DESC
                        ) AS rn
                    FROM market_data_load_ranges
                ) dedup
                WHERE rn > 1
            )
            """
        )

    def _migrate_legacy_market_open_snapshot(self, connection) -> None:
        if self._table_exists(connection, "session_reference") and not self._table_exists(
            connection, "market_open_snapshot"
        ):
            connection.execute("DROP INDEX IF EXISTS uq_session_reference")
            connection.execute("ALTER TABLE session_reference RENAME TO market_open_snapshot")

        if self._column_exists(connection, "market_open_snapshot", "session_open") and not (
            self._column_exists(connection, "market_open_snapshot", "market_open_price")
        ):
            connection.execute(
                """
                ALTER TABLE market_open_snapshot
                RENAME COLUMN session_open TO market_open_price
                """
            )

    def _migrate_legacy_analysis_results(self, connection) -> None:
        if self._column_exists(connection, "analysis_results", "session_open") and not (
            self._column_exists(connection, "analysis_results", "market_open_price")
        ):
            connection.execute(
                """
                ALTER TABLE analysis_results
                RENAME COLUMN session_open TO market_open_price
                """
            )

    def _ensure_optional_column(
        self,
        connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        if self._column_exists(connection, table_name, column_name):
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )

    def _table_exists(self, connection, table_name: str) -> bool:
        row = connection.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name = ?
            LIMIT 1
            """,
            [table_name],
        ).fetchone()
        return row is not None

    def _column_exists(self, connection, table_name: str, column_name: str) -> bool:
        row = connection.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            LIMIT 1
            """,
            [table_name, column_name],
        ).fetchone()
        return row is not None
