from __future__ import annotations

from datetime import date, datetime, time

from research_bot.application.dto.market_data_dto import MarketDataOverview
from research_bot.domain.market.entities import MinuteBar, SessionReference
from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory
from research_bot.infrastructure.storage.schema_manager import DuckDbSchemaManager


class DuckDbMarketDataRepository:
    def __init__(
        self,
        connection_factory: DuckDbConnectionFactory,
        schema_manager: DuckDbSchemaManager,
        market_open: time,
        opening_cutoff: time,
    ) -> None:
        self.connection_factory = connection_factory
        self.schema_manager = schema_manager
        self.market_open = market_open
        self.opening_cutoff = opening_cutoff

    def replace_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[MinuteBar],
        replace_existing: bool,
        source: str,
    ) -> int:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            if replace_existing:
                self._delete_range(connection, "historical_minute_bars", symbols, date_from, date_to)
            payload = [
                (
                    row.symbol,
                    row.trade_date,
                    row.minute_ts,
                    row.open,
                    row.high,
                    row.low,
                    row.close,
                    row.volume,
                    source,
                    datetime.now(),
                )
                for row in rows
            ]
            if payload:
                connection.executemany(
                    """
                    INSERT INTO historical_minute_bars
                    (symbol, trade_date, minute_ts, open, high, low, close, volume, source, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
            return len(payload)

    def replace_session_references(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[SessionReference],
        replace_existing: bool,
        source: str,
    ) -> int:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            if replace_existing:
                self._delete_range(connection, "session_reference", symbols, date_from, date_to)
            payload = [
                (
                    row.symbol,
                    row.trade_date,
                    row.prev_close,
                    row.session_open,
                    row.gap_pct,
                    source,
                    datetime.now(),
                )
                for row in rows
            ]
            if payload:
                connection.executemany(
                    """
                    INSERT INTO session_reference
                    (symbol, trade_date, prev_close, session_open, gap_pct, source, collected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
            return len(payload)

    def rebuild_opening_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        replace_existing: bool,
    ) -> int:
        self.schema_manager.initialize()
        market_open_text = self.market_open.strftime("%H:%M:%S")
        opening_cutoff_text = self.opening_cutoff.strftime("%H:%M:%S")
        with self.connection_factory.connect() as connection:
            if replace_existing:
                self._delete_range(connection, "opening_bars_1m", symbols, date_from, date_to)

            filters, params = self._date_symbol_filters(symbols, date_from, date_to)
            connection.execute(
                f"""
                INSERT INTO opening_bars_1m
                (symbol, trade_date, minute_ts, open, high, low, close, volume, created_at)
                SELECT
                    symbol,
                    trade_date,
                    minute_ts,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    CURRENT_TIMESTAMP
                FROM historical_minute_bars
                WHERE {filters}
                  AND CAST(minute_ts AS TIME) >= CAST(? AS TIME)
                  AND CAST(minute_ts AS TIME) <= CAST(? AS TIME)
                ORDER BY trade_date, symbol, minute_ts
                """,
                [*params, market_open_text, opening_cutoff_text],
            )
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM opening_bars_1m WHERE {filters}",
                params,
            ).fetchone()[0]
            return int(row_count)

    def get_market_data_overview(self) -> MarketDataOverview:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            historical = connection.execute(
                """
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date), COUNT(DISTINCT symbol)
                FROM historical_minute_bars
                """
            ).fetchone()
            opening = connection.execute(
                "SELECT COUNT(*), MIN(trade_date), MAX(trade_date) FROM opening_bars_1m"
            ).fetchone()
            session_reference_count = connection.execute(
                "SELECT COUNT(*) FROM session_reference"
            ).fetchone()[0]
            available_symbols = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT symbol
                    FROM (
                        SELECT DISTINCT symbol FROM historical_minute_bars
                        UNION
                        SELECT DISTINCT symbol FROM session_reference
                    )
                    ORDER BY symbol
                    """
                ).fetchall()
            ]
            return MarketDataOverview(
                historical_bar_count=int(historical[0] or 0),
                opening_bar_count=int(opening[0] or 0),
                session_reference_count=int(session_reference_count or 0),
                symbol_count=len(available_symbols),
                historical_date_min=historical[1],
                historical_date_max=historical[2],
                opening_date_min=opening[1],
                opening_date_max=opening[2],
                available_symbols=available_symbols,
            )

    def list_opening_bars(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MinuteBar]:
        self.schema_manager.initialize()
        filters, params = self._date_symbol_filters(symbols or [], date_from, date_to)
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT symbol, trade_date, minute_ts, open, high, low, close, volume
                FROM opening_bars_1m
                WHERE {filters}
                ORDER BY trade_date, symbol, minute_ts
                """,
                params,
            ).fetchall()
        return [
            MinuteBar(
                symbol=row[0],
                trade_date=row[1],
                minute_ts=row[2],
                open=row[3],
                high=row[4],
                low=row[5],
                close=row[6],
                volume=row[7],
            )
            for row in rows
        ]

    def list_session_references(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[SessionReference]:
        self.schema_manager.initialize()
        filters, params = self._date_symbol_filters(symbols or [], date_from, date_to)
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT symbol, trade_date, prev_close, session_open, gap_pct
                FROM session_reference
                WHERE {filters}
                ORDER BY trade_date, symbol
                """,
                params,
            ).fetchall()
        return [
            SessionReference(
                symbol=row[0],
                trade_date=row[1],
                prev_close=row[2],
                session_open=row[3],
                gap_pct=row[4],
            )
            for row in rows
        ]

    def _delete_range(
        self,
        connection,
        table_name: str,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> None:
        filters, params = self._date_symbol_filters(symbols, date_from, date_to)
        connection.execute(f"DELETE FROM {table_name} WHERE {filters}", params)

    def _date_symbol_filters(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> tuple[str, list[object]]:
        filters = ["trade_date BETWEEN ? AND ?"]
        params: list[object] = [date_from, date_to]
        if symbols:
            placeholders = ", ".join("?" for _ in symbols)
            filters.append(f"symbol IN ({placeholders})")
            params.extend(symbols)
        return " AND ".join(filters), params
