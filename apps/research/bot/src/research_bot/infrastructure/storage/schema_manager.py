from __future__ import annotations

from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory


class DuckDbSchemaManager:
    def __init__(self, connection_factory: DuckDbConnectionFactory) -> None:
        self.connection_factory = connection_factory

    def initialize(self) -> None:
        with self.connection_factory.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS historical_minute_bars (
                    symbol VARCHAR NOT NULL,
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_reference (
                    symbol VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    prev_close DOUBLE NOT NULL,
                    session_open DOUBLE NOT NULL,
                    gap_pct DOUBLE NOT NULL,
                    source VARCHAR NOT NULL,
                    collected_at TIMESTAMP NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS opening_bars_1m (
                    symbol VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    minute_ts TIMESTAMP NOT NULL,
                    open DOUBLE NOT NULL,
                    high DOUBLE NOT NULL,
                    low DOUBLE NOT NULL,
                    close DOUBLE NOT NULL,
                    volume DOUBLE NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
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
                CREATE TABLE IF NOT EXISTS analysis_results (
                    run_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    prev_close DOUBLE,
                    session_open DOUBLE,
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
