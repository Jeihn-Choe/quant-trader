from __future__ import annotations

from datetime import date

from research_bot.infrastructure.storage.postgresql_connection import PostgreSqlConnectionFactory


class PostgreSqlSchemaManager:
    def __init__(
        self,
        connection_factory: PostgreSqlConnectionFactory,
        schema_name: str = "public",
    ) -> None:
        self.connection_factory = connection_factory
        self.schema_name = schema_name

    def initialize(self) -> None:
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
                cursor.execute(f'SET search_path TO "{self.schema_name}"')
                self._ensure_partitioned_historical_minute_bars(cursor)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_open_snapshot (
                        symbol TEXT NOT NULL,
                        symbol_name TEXT,
                        trade_date DATE NOT NULL,
                        prev_close DOUBLE PRECISION NOT NULL,
                        market_open_price DOUBLE PRECISION NOT NULL,
                        gap_pct DOUBLE PRECISION NOT NULL,
                        source TEXT NOT NULL,
                        collected_at TIMESTAMP NOT NULL,
                        CONSTRAINT uq_market_open_snapshot UNIQUE (symbol, trade_date)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_runs (
                        run_id TEXT PRIMARY KEY,
                        created_at TIMESTAMP NOT NULL,
                        date_from DATE NOT NULL,
                        date_to DATE NOT NULL,
                        orb_window_minutes INTEGER NOT NULL,
                        breakout_buffer DOUBLE PRECISION NOT NULL,
                        gap_mode TEXT NOT NULL,
                        gap_threshold_pct DOUBLE PRECISION NOT NULL,
                        requested_symbols TEXT NOT NULL,
                        total_sessions INTEGER NOT NULL,
                        scanned_sessions INTEGER NOT NULL,
                        gap_up_sessions INTEGER NOT NULL,
                        breakout_sessions INTEGER NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS analysis_results (
                        run_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        symbol_name TEXT,
                        trade_date DATE NOT NULL,
                        prev_close DOUBLE PRECISION,
                        market_open_price DOUBLE PRECISION,
                        gap_pct DOUBLE PRECISION,
                        gap_up BOOLEAN NOT NULL,
                        orb_window_minutes INTEGER NOT NULL,
                        orb_high DOUBLE PRECISION,
                        orb_low DOUBLE PRECISION,
                        breakout BOOLEAN NOT NULL,
                        first_breakout_time TIMESTAMP,
                        first_breakout_price DOUBLE PRECISION,
                        breakout_excess DOUBLE PRECISION,
                        cutoff_price DOUBLE PRECISION,
                        cutoff_above_orb_high BOOLEAN,
                        CONSTRAINT uq_analysis_results UNIQUE (run_id, symbol, trade_date)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_data_load_ranges (
                        dataset TEXT NOT NULL,
                        scope_key TEXT NOT NULL,
                        date_from DATE NOT NULL,
                        date_to DATE NOT NULL,
                        source TEXT NOT NULL,
                        loaded_at TIMESTAMP NOT NULL,
                        CONSTRAINT uq_market_data_load_ranges UNIQUE (dataset, scope_key, date_from, date_to)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS ix_market_data_load_ranges_lookup
                    ON market_data_load_ranges(dataset, source, scope_key, date_from, date_to)
                    """
                )
            connection.commit()

    def ensure_historical_minute_bar_partitions(
        self,
        date_from: date,
        date_to: date,
    ) -> None:
        with self.connection_factory.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO "{self.schema_name}"')
                self._ensure_partitioned_historical_minute_bars(cursor)
                self._ensure_historical_partitions_for_range(cursor, date_from, date_to)
            connection.commit()

    def _ensure_partitioned_historical_minute_bars(self, cursor) -> None:
        base_table = "historical_minute_bars"
        legacy_table = "historical_minute_bars_legacy"

        if self._table_exists(cursor, base_table) and not self._is_partitioned_table(cursor, base_table):
            if not self._table_exists(cursor, legacy_table):
                cursor.execute(f"ALTER TABLE {base_table} RENAME TO {legacy_table}")

        if not self._table_exists(cursor, base_table):
            cursor.execute(
                """
                CREATE TABLE historical_minute_bars (
                    symbol TEXT NOT NULL,
                    symbol_name TEXT,
                    trade_date DATE NOT NULL,
                    minute_ts TIMESTAMP NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    source TEXT NOT NULL,
                    collected_at TIMESTAMP NOT NULL
                ) PARTITION BY RANGE (trade_date)
                """
            )

        if self._table_exists(cursor, legacy_table):
            cursor.execute(
                f"""
                SELECT MIN(trade_date), MAX(trade_date)
                FROM {legacy_table}
                """
            )
            row = cursor.fetchone()
            min_date = row[0] if row else None
            max_date = row[1] if row else None
            if min_date is not None and max_date is not None:
                self._ensure_historical_partitions_for_range(cursor, min_date, max_date)
                cursor.execute(
                    f"""
                    INSERT INTO historical_minute_bars
                    (symbol, symbol_name, trade_date, minute_ts, open, high, low, close, volume, source, collected_at)
                    SELECT
                        symbol,
                        symbol_name,
                        trade_date,
                        minute_ts,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        source,
                        collected_at
                    FROM {legacy_table}
                    """
                )
            cursor.execute(f"DROP TABLE {legacy_table}")

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_historical_minute_bars
            ON historical_minute_bars(symbol, trade_date, minute_ts)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_historical_minute_bars_trade_date_symbol_minute_ts
            ON historical_minute_bars(trade_date, symbol, minute_ts)
            """
        )

    def _ensure_historical_partitions_for_range(
        self,
        cursor,
        date_from: date,
        date_to: date,
    ) -> None:
        current = date(date_from.year, date_from.month, 1)
        final = date(date_to.year, date_to.month, 1)
        while current <= final:
            next_month = _next_month(current)
            partition_name = f"historical_minute_bars_{current.year}_{current.month:02d}"
            current_literal = current.isoformat()
            next_month_literal = next_month.isoformat()
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF historical_minute_bars
                FOR VALUES FROM ('{current_literal}') TO ('{next_month_literal}')
                """
            )
            current = next_month

    def _table_exists(self, cursor, table_name: str) -> bool:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            LIMIT 1
            """,
            [self.schema_name, table_name],
        )
        return cursor.fetchone() is not None

    def _is_partitioned_table(self, cursor, table_name: str) -> bool:
        cursor.execute(
            """
            SELECT 1
            FROM pg_partitioned_table pt
            JOIN pg_class c ON c.oid = pt.partrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = %s
            LIMIT 1
            """,
            [self.schema_name, table_name],
        )
        return cursor.fetchone() is not None


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)
