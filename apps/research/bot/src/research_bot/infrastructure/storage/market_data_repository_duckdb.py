from __future__ import annotations

from datetime import date, datetime, timedelta

from research_bot.application.dto.market_data_dto import (
    MarketDataDailySummary,
    MarketDataSymbolSummary,
    MarketDataOverview,
)
from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar
from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory
from research_bot.infrastructure.storage.schema_manager import DuckDbSchemaManager


class DuckDbMarketDataRepository:
    def __init__(
        self,
        connection_factory: DuckDbConnectionFactory,
        schema_manager: DuckDbSchemaManager,
    ) -> None:
        self.connection_factory = connection_factory
        self.schema_manager = schema_manager

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
            try:
                connection.begin()
                before_count = self._count_rows_in_range(
                    connection,
                    "historical_minute_bars",
                    symbols,
                    date_from,
                    date_to,
                )
                if replace_existing:
                    self._delete_range(
                        connection,
                        "historical_minute_bars",
                        symbols,
                        date_from,
                        date_to,
                    )
                elif source != "mock":
                    self._delete_range_by_source(
                        connection,
                        "historical_minute_bars",
                        symbols,
                        date_from,
                        date_to,
                        "mock",
                    )
                payload = [
                    (
                        row.symbol,
                        row.symbol_name,
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
                    insert_sql = (
                        """
                        INSERT INTO historical_minute_bars
                        (symbol, symbol_name, trade_date, minute_ts, open, high, low, close, volume, source, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        if replace_existing
                        else """
                        INSERT OR IGNORE INTO historical_minute_bars
                        (symbol, symbol_name, trade_date, minute_ts, open, high, low, close, volume, source, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                    )
                    connection.executemany(insert_sql, payload)
                after_count = self._count_rows_in_range(
                    connection,
                    "historical_minute_bars",
                    symbols,
                    date_from,
                    date_to,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            return (
                after_count
                if replace_existing
                else max(0, after_count - before_count)
            )

    def is_historical_minute_bars_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> bool:
        return self._is_dataset_loaded(
            dataset="historical_minute_bars",
            requested_symbols=requested_symbols,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )

    def mark_historical_minute_bars_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None:
        self._mark_dataset_loaded(
            dataset="historical_minute_bars",
            requested_symbols=requested_symbols,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )

    def replace_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        rows: list[MarketOpenSnapshot],
        replace_existing: bool,
        source: str,
    ) -> int:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            try:
                connection.begin()
                before_count = self._count_rows_in_range(
                    connection,
                    "market_open_snapshot",
                    symbols,
                    date_from,
                    date_to,
                )
                if replace_existing:
                    self._delete_range(
                        connection,
                        "market_open_snapshot",
                        symbols,
                        date_from,
                        date_to,
                    )
                elif source != "mock":
                    self._delete_range_by_source(
                        connection,
                        "market_open_snapshot",
                        symbols,
                        date_from,
                        date_to,
                        "mock",
                    )
                payload = [
                    (
                        row.symbol,
                        row.symbol_name,
                        row.trade_date,
                        row.prev_close,
                        row.market_open_price,
                        row.gap_pct,
                        source,
                        datetime.now(),
                    )
                    for row in rows
                ]
                if payload:
                    insert_sql = (
                        """
                        INSERT INTO market_open_snapshot
                        (symbol, symbol_name, trade_date, prev_close, market_open_price, gap_pct, source, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        if replace_existing
                        else """
                        INSERT OR IGNORE INTO market_open_snapshot
                        (symbol, symbol_name, trade_date, prev_close, market_open_price, gap_pct, source, collected_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """
                    )
                    connection.executemany(insert_sql, payload)
                after_count = self._count_rows_in_range(
                    connection,
                    "market_open_snapshot",
                    symbols,
                    date_from,
                    date_to,
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            return (
                after_count
                if replace_existing
                else max(0, after_count - before_count)
            )

    def is_market_open_snapshots_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> bool:
        return self._is_dataset_loaded(
            dataset="market_open_snapshot",
            requested_symbols=requested_symbols,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )

    def mark_market_open_snapshots_loaded(
        self,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None:
        self._mark_dataset_loaded(
            dataset="market_open_snapshot",
            requested_symbols=requested_symbols,
            date_from=date_from,
            date_to=date_to,
            source=source,
        )

    def get_market_data_overview(self) -> MarketDataOverview:
        self.schema_manager.initialize()
        with self.connection_factory.connect() as connection:
            historical = connection.execute(
                """
                SELECT COUNT(*), MIN(trade_date), MAX(trade_date), COUNT(DISTINCT symbol)
                FROM historical_minute_bars
                """
            ).fetchone()
            market_open_snapshot_count = connection.execute(
                "SELECT COUNT(*) FROM market_open_snapshot"
            ).fetchone()[0]
            available_symbols = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT symbol
                    FROM (
                        SELECT DISTINCT symbol FROM historical_minute_bars
                        UNION
                        SELECT DISTINCT symbol FROM market_open_snapshot
                    )
                    ORDER BY symbol
                    """
                ).fetchall()
            ]
            return MarketDataOverview(
                historical_bar_count=int(historical[0] or 0),
                market_open_snapshot_count=int(market_open_snapshot_count or 0),
                symbol_count=len(available_symbols),
                historical_date_min=historical[1],
                historical_date_max=historical[2],
                available_symbols=available_symbols,
            )

    def list_historical_minute_bars(
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
                SELECT symbol, symbol_name, trade_date, minute_ts, open, high, low, close, volume
                FROM historical_minute_bars
                WHERE {filters}
                ORDER BY trade_date, symbol, minute_ts
                """,
                params,
            ).fetchall()
        return [
            MinuteBar(
                symbol=row[0],
                symbol_name=row[1],
                trade_date=row[2],
                minute_ts=row[3],
                open=row[4],
                high=row[5],
                low=row[6],
                close=row[7],
                volume=row[8],
            )
            for row in rows
        ]

    def list_market_open_snapshots(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MarketOpenSnapshot]:
        self.schema_manager.initialize()
        filters, params = self._date_symbol_filters(symbols or [], date_from, date_to)
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT symbol, symbol_name, trade_date, prev_close, market_open_price, gap_pct
                FROM market_open_snapshot
                WHERE {filters}
                ORDER BY trade_date, symbol
                """,
                params,
            ).fetchall()
        return [
            MarketOpenSnapshot(
                symbol=row[0],
                symbol_name=row[1],
                trade_date=row[2],
                prev_close=row[3],
                market_open_price=row[4],
                gap_pct=row[5],
            )
            for row in rows
        ]

    def list_daily_market_data_summary(
        self,
        date_from: date,
        date_to: date,
        symbols: list[str] | None = None,
    ) -> list[MarketDataDailySummary]:
        self.schema_manager.initialize()
        symbol_filters, symbol_params = self._date_symbol_filters(symbols or [], date_from, date_to)
        union_filters, union_params = self._union_date_symbol_filters(
            symbols or [],
            date_from,
            date_to,
        )
        with self.connection_factory.connect() as connection:
            historical_rows = connection.execute(
                f"""
                SELECT trade_date, COUNT(*) AS historical_bar_count, COUNT(DISTINCT symbol) AS symbol_count
                FROM historical_minute_bars
                WHERE {symbol_filters}
                GROUP BY trade_date
                ORDER BY trade_date DESC
                """,
                symbol_params,
            ).fetchall()
            snapshot_rows = connection.execute(
                f"""
                SELECT trade_date, COUNT(*) AS market_open_snapshot_count, COUNT(DISTINCT symbol) AS symbol_count
                FROM market_open_snapshot
                WHERE {symbol_filters}
                GROUP BY trade_date
                ORDER BY trade_date DESC
                """,
                symbol_params,
            ).fetchall()
            preview_rows = connection.execute(
                f"""
                SELECT trade_date, symbol, COALESCE(MAX(symbol_name), symbol) AS display_name
                FROM (
                    SELECT trade_date, symbol, symbol_name
                    FROM historical_minute_bars
                    WHERE {union_filters}
                    UNION ALL
                    SELECT trade_date, symbol, symbol_name
                    FROM market_open_snapshot
                    WHERE {union_filters}
                ) source_rows
                GROUP BY trade_date, symbol
                ORDER BY trade_date DESC, symbol
                """,
                union_params,
            ).fetchall()

        summary_map: dict[date, dict[str, object]] = {}
        for trade_date, historical_bar_count, symbol_count in historical_rows:
            summary_map[trade_date] = {
                "trade_date": trade_date,
                "symbol_count": int(symbol_count or 0),
                "historical_bar_count": int(historical_bar_count or 0),
                "market_open_snapshot_count": 0,
                "preview_symbols": [],
            }
        for trade_date, market_open_snapshot_count, snapshot_symbol_count in snapshot_rows:
            row = summary_map.setdefault(
                trade_date,
                {
                    "trade_date": trade_date,
                    "symbol_count": 0,
                    "historical_bar_count": 0,
                    "market_open_snapshot_count": 0,
                    "preview_symbols": [],
                },
            )
            row["market_open_snapshot_count"] = int(market_open_snapshot_count or 0)
            row["symbol_count"] = max(
                int(row["symbol_count"]),
                int(snapshot_symbol_count or 0),
            )
        for trade_date, symbol, display_name in preview_rows:
            row = summary_map.setdefault(
                trade_date,
                {
                    "trade_date": trade_date,
                    "symbol_count": 0,
                    "historical_bar_count": 0,
                    "market_open_snapshot_count": 0,
                    "preview_symbols": [],
                },
            )
            preview_symbols = row["preview_symbols"]
            if isinstance(preview_symbols, list) and len(preview_symbols) < 3:
                label = f"{display_name} ({symbol})" if display_name and display_name != symbol else symbol
                preview_symbols.append(label)

        return [
            MarketDataDailySummary(
                trade_date=trade_date,
                symbol_count=int(row["symbol_count"]),
                historical_bar_count=int(row["historical_bar_count"]),
                market_open_snapshot_count=int(row["market_open_snapshot_count"]),
                preview_symbols=list(row["preview_symbols"]),
            )
            for trade_date, row in sorted(summary_map.items(), key=lambda item: item[0], reverse=True)
        ]

    def list_symbol_market_data_summary(
        self,
        trade_date: date,
        symbols: list[str] | None = None,
    ) -> list[MarketDataSymbolSummary]:
        self.schema_manager.initialize()
        filters = ["trade_date = ?"]
        params: list[object] = [trade_date]
        if symbols:
            placeholders = ", ".join("?" for _ in symbols)
            filters.append(f"symbol IN ({placeholders})")
            params.extend(symbols)

        where_clause = " AND ".join(filters)
        query_params = [*params, *params]
        with self.connection_factory.connect() as connection:
            rows = connection.execute(
                f"""
                WITH ranked_bars AS (
                    SELECT
                        bars.trade_date,
                        bars.symbol,
                        bars.symbol_name,
                        bars.minute_ts,
                        bars.open,
                        bars.high,
                        bars.low,
                        bars.close,
                        bars.volume,
                        ROW_NUMBER() OVER (
                            PARTITION BY bars.trade_date, bars.symbol
                            ORDER BY bars.minute_ts ASC
                        ) AS rn_open,
                        ROW_NUMBER() OVER (
                            PARTITION BY bars.trade_date, bars.symbol
                            ORDER BY bars.minute_ts DESC
                        ) AS rn_close
                    FROM historical_minute_bars bars
                    WHERE {where_clause}
                ),
                bar_summary AS (
                    SELECT
                        ranked_bars.trade_date,
                        ranked_bars.symbol,
                        MAX(ranked_bars.symbol_name) AS symbol_name,
                        COUNT(*) AS minute_bar_count,
                        MAX(CASE WHEN ranked_bars.rn_open = 1 THEN ranked_bars.open END) AS session_open,
                        MAX(ranked_bars.high) AS session_high,
                        MIN(ranked_bars.low) AS session_low,
                        MAX(CASE WHEN ranked_bars.rn_close = 1 THEN ranked_bars.close END) AS session_close,
                        SUM(ranked_bars.volume) AS total_volume
                    FROM ranked_bars
                    GROUP BY ranked_bars.trade_date, ranked_bars.symbol
                ),
                snapshot_summary AS (
                    SELECT
                        trade_date,
                        symbol,
                        MAX(symbol_name) AS symbol_name,
                        MAX(gap_pct) AS gap_pct
                    FROM market_open_snapshot
                    WHERE {where_clause}
                    GROUP BY trade_date, symbol
                ),
                daily_symbols AS (
                    SELECT trade_date, symbol, symbol_name
                    FROM bar_summary
                    UNION ALL
                    SELECT trade_date, symbol, symbol_name
                    FROM snapshot_summary
                )
                SELECT
                    daily_symbols.trade_date,
                    daily_symbols.symbol,
                    COALESCE(MAX(daily_symbols.symbol_name), daily_symbols.symbol) AS symbol_name,
                    MAX(bar_summary.minute_bar_count) AS minute_bar_count,
                    MAX(bar_summary.session_open) AS session_open,
                    MAX(bar_summary.session_high) AS session_high,
                    MIN(bar_summary.session_low) AS session_low,
                    MAX(bar_summary.session_close) AS session_close,
                    MAX(bar_summary.total_volume) AS total_volume,
                    MAX(snapshot_summary.gap_pct) AS gap_pct
                FROM daily_symbols
                LEFT JOIN bar_summary
                  ON daily_symbols.trade_date = bar_summary.trade_date
                 AND daily_symbols.symbol = bar_summary.symbol
                LEFT JOIN snapshot_summary
                  ON daily_symbols.trade_date = snapshot_summary.trade_date
                 AND daily_symbols.symbol = snapshot_summary.symbol
                GROUP BY daily_symbols.trade_date, daily_symbols.symbol
                ORDER BY daily_symbols.symbol
                """,
                query_params,
            ).fetchall()

        return [
            MarketDataSymbolSummary(
                trade_date=row[0],
                symbol=row[1],
                symbol_name=row[2],
                minute_bar_count=int(row[3] or 0),
                session_open=row[4],
                session_high=row[5],
                session_low=row[6],
                session_close=row[7],
                total_volume=row[8],
                gap_pct=row[9],
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

    def _delete_range_by_source(
        self,
        connection,
        table_name: str,
        symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None:
        filters, params = self._date_symbol_filters(symbols, date_from, date_to)
        connection.execute(
            f"DELETE FROM {table_name} WHERE {filters} AND source = ?",
            [*params, source],
        )

    def _count_rows_in_range(
        self,
        connection,
        table_name: str,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> int:
        filters, params = self._date_symbol_filters(symbols, date_from, date_to)
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table_name} WHERE {filters}",
            params,
        ).fetchone()
        return int(row[0] or 0)

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

    def _union_date_symbol_filters(
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
        combined_params = [*params, *params]
        return " AND ".join(filters), combined_params

    def _is_dataset_loaded(
        self,
        dataset: str,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> bool:
        self.schema_manager.initialize()
        scope_key = _scope_key(requested_symbols)
        with self.connection_factory.connect() as connection:
            if scope_key == "__ALL__":
                row = connection.execute(
                    """
                    SELECT 1
                    FROM market_data_load_ranges
                    WHERE dataset = ?
                      AND source = ?
                      AND scope_key = '__ALL__'
                      AND date_from <= ?
                      AND date_to >= ?
                    LIMIT 1
                    """,
                    [dataset, source, date_from, date_to],
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT 1
                    FROM market_data_load_ranges
                    WHERE dataset = ?
                      AND source = ?
                      AND (scope_key = ? OR scope_key = '__ALL__')
                      AND date_from <= ?
                      AND date_to >= ?
                    LIMIT 1
                    """,
                    [dataset, source, scope_key, date_from, date_to],
                ).fetchone()
        return row is not None

    def _mark_dataset_loaded(
        self,
        dataset: str,
        requested_symbols: list[str],
        date_from: date,
        date_to: date,
        source: str,
    ) -> None:
        self.schema_manager.initialize()
        scope_key = _scope_key(requested_symbols)
        merge_from = date_from
        merge_to = date_to
        overlap_start = date_from - timedelta(days=1)
        overlap_end = date_to + timedelta(days=1)

        with self.connection_factory.connect() as connection:
            try:
                connection.begin()
                overlapping_rows = connection.execute(
                    """
                    SELECT date_from, date_to
                    FROM market_data_load_ranges
                    WHERE dataset = ?
                      AND scope_key = ?
                      AND date_from <= ?
                      AND date_to >= ?
                    """,
                    [dataset, scope_key, overlap_end, overlap_start],
                ).fetchall()
                for existing_from, existing_to in overlapping_rows:
                    if existing_from < merge_from:
                        merge_from = existing_from
                    if existing_to > merge_to:
                        merge_to = existing_to

                connection.execute(
                    """
                    DELETE FROM market_data_load_ranges
                    WHERE dataset = ?
                      AND scope_key = ?
                      AND date_from <= ?
                      AND date_to >= ?
                    """,
                    [dataset, scope_key, overlap_end, overlap_start],
                )
                connection.execute(
                    """
                    INSERT INTO market_data_load_ranges
                    (dataset, scope_key, date_from, date_to, source, loaded_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [dataset, scope_key, merge_from, merge_to, source, datetime.now()],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise


def _scope_key(requested_symbols: list[str]) -> str:
    normalized = sorted({symbol.strip() for symbol in requested_symbols if symbol.strip()})
    if not normalized:
        return "__ALL__"
    return ",".join(normalized)
