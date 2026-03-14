from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta
import logging
from typing import Callable, TypeVar

from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar
from research_bot.infrastructure.providers.kis_client import KisClient, KisClientError
from research_bot.infrastructure.providers.kis_universe_resolver import KisUniverseResolver
from research_bot.domain.orb.gap import calculate_gap_pct


MINUTE_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
MINUTE_CHART_TR_ID = "FHKST03010230"
DAILY_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
DAILY_CHART_TR_ID = "FHKST03010100"
MAX_ERROR_PREVIEW = 5
T = TypeVar("T")
logger = logging.getLogger(__name__)


class KisMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        client: KisClient,
        universe_resolver: KisUniverseResolver,
        max_workers: int = 10,
    ) -> None:
        self.client = client
        self.universe_resolver = universe_resolver
        self.max_workers = max(1, max_workers)

    @property
    def name(self) -> str:
        return "kis"

    def resolve_symbols(self, symbols: list[str]) -> list[str]:
        if not symbols:
            self.client.ensure_access_token()
        return self.universe_resolver.resolve_symbols(symbols)

    def get_symbol_name(self, symbol: str) -> str | None:
        return self.universe_resolver.get_symbol_name(symbol)

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows = self._collect_parallel(
            symbols=symbols,
            fetcher=lambda symbol: self.get_symbol_historical_minute_bars(
                symbol=symbol,
                date_from=date_from,
                date_to=date_to,
            ),
            dataset_label="과거 1분봉",
        )
        rows.sort(key=lambda item: (item.trade_date, item.symbol, item.minute_ts))
        return rows

    def get_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        rows = self._collect_parallel(
            symbols=symbols,
            fetcher=lambda symbol: self.get_symbol_market_open_snapshots(
                symbol=symbol,
                date_from=date_from,
                date_to=date_to,
            ),
            dataset_label="장 시작 스냅샷",
        )
        rows.sort(key=lambda item: (item.trade_date, item.symbol))
        return rows

    def get_symbol_historical_minute_bars(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows, _ = self._collect_symbol_minute_bars(
            symbol=symbol,
            date_from=date_from,
            date_to=date_to,
        )
        return rows

    def get_symbol_market_open_snapshots(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        return self._collect_symbol_market_open_snapshots(
            symbol=symbol,
            date_from=date_from,
            date_to=date_to,
        )

    def _collect_parallel(
        self,
        symbols: list[str],
        fetcher: Callable[[str], list[T]],
        dataset_label: str,
    ) -> list[T]:
        total_symbols = len(symbols)
        progress_by_date: dict[date, int] = {}

        if len(symbols) <= 1 or self.max_workers == 1:
            rows: list[T] = []
            logger.info("%s 조회 시작 - worker=1, symbols=%s", dataset_label, total_symbols)
            for symbol in symbols:
                symbol_rows = fetcher(symbol)
                rows.extend(symbol_rows)
                self._log_symbol_progress(
                    dataset_label=dataset_label,
                    symbol=symbol,
                    symbol_rows=symbol_rows,
                    progress_by_date=progress_by_date,
                    total_symbols=total_symbols,
                )
            return rows

        rows: list[T] = []
        errors: list[str] = []
        worker_count = min(self.max_workers, len(symbols))
        logger.info(
            "%s 병렬 조회 시작 - workers=%s, symbols=%s",
            dataset_label,
            worker_count,
            total_symbols,
        )

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="kis-fetch") as executor:
            future_map = {
                executor.submit(fetcher, symbol): symbol
                for symbol in symbols
            }
            for future in as_completed(future_map):
                symbol = future_map[future]
                try:
                    symbol_rows = future.result()
                    rows.extend(symbol_rows)
                    self._log_symbol_progress(
                        dataset_label=dataset_label,
                        symbol=symbol,
                        symbol_rows=symbol_rows,
                        progress_by_date=progress_by_date,
                        total_symbols=total_symbols,
                    )
                except Exception as error:  # noqa: BLE001
                    logger.warning("%s 조회 실패 - symbol=%s, error=%s", dataset_label, symbol, error)
                    errors.append(f"{symbol}: {error}")

        if errors:
            preview = "; ".join(errors[:MAX_ERROR_PREVIEW])
            remainder = len(errors) - MAX_ERROR_PREVIEW
            suffix = f" 외 {remainder}건" if remainder > 0 else ""
            raise KisClientError(
                f"{dataset_label} 병렬 조회 중 일부 종목이 실패했습니다. {preview}{suffix}"
            )
        return rows

    def _log_symbol_progress(
        self,
        dataset_label: str,
        symbol: str,
        symbol_rows: list[T],
        progress_by_date: dict[date, int],
        total_symbols: int,
    ) -> None:
        trade_dates = sorted(
            {
                getattr(row, "trade_date")
                for row in symbol_rows
                if getattr(row, "trade_date", None) is not None
            }
        )
        if not trade_dates:
            logger.info("%s 진행 - no-date symbol=%s, rows=%s", dataset_label, symbol, len(symbol_rows))
            return

        for trade_date in trade_dates:
            progress_by_date[trade_date] = progress_by_date.get(trade_date, 0) + 1
            logger.info(
                "date=%s %s 진행 [%s/%s] symbol=%s rows=%s",
                trade_date.isoformat(),
                dataset_label,
                progress_by_date[trade_date],
                total_symbols,
                symbol,
                len(symbol_rows),
            )

    def _collect_symbol_minute_bars(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> tuple[list[MinuteBar], int]:
        collected: dict[tuple[date, datetime], MinuteBar] = {}
        seen_cursors: set[tuple[str, str]] = set()
        cursor_at = datetime.combine(date_to, time(15, 30))
        symbol_name = self.universe_resolver.get_symbol_name(symbol)
        request_count = 0

        while cursor_at.date() >= date_from:
            cursor_key = (cursor_at.strftime("%Y%m%d"), cursor_at.strftime("%H%M%S"))
            if cursor_key in seen_cursors:
                break
            seen_cursors.add(cursor_key)
            request_count += 1

            chunk = self._fetch_minute_bar_chunk(
                symbol=symbol,
                symbol_name=symbol_name,
                cursor_at=cursor_at,
            )
            if not chunk:
                break

            for row in chunk:
                if date_from <= row.trade_date <= date_to:
                    collected[(row.trade_date, row.minute_ts)] = row

            oldest_bar = min(chunk, key=lambda item: item.minute_ts)
            next_cursor_at = oldest_bar.minute_ts - timedelta(minutes=1)
            if next_cursor_at >= cursor_at:
                break
            cursor_at = next_cursor_at

        return sorted(collected.values(), key=lambda item: item.minute_ts), request_count

    def _collect_symbol_market_open_snapshots(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        symbol_name = self.universe_resolver.get_symbol_name(symbol)
        request_start = date_from - timedelta(days=14)
        payload = self.client.request(
            DAILY_CHART_PATH,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": request_start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": date_to.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            },
            tr_id=DAILY_CHART_TR_ID,
        )
        daily_rows = _parse_daily_rows(payload.get("output2", []))
        if not daily_rows:
            return []

        snapshot_rows: list[MarketOpenSnapshot] = []
        previous_close: float | None = None
        for trade_date, market_open_price, session_close in daily_rows:
            if previous_close is not None and date_from <= trade_date <= date_to:
                snapshot_rows.append(
                    MarketOpenSnapshot(
                        symbol=symbol,
                        symbol_name=symbol_name,
                        trade_date=trade_date,
                        prev_close=previous_close,
                        market_open_price=market_open_price,
                        gap_pct=calculate_gap_pct(previous_close, market_open_price),
                    )
                )
            previous_close = session_close
        return snapshot_rows

    def _fetch_minute_bar_chunk(
        self,
        symbol: str,
        symbol_name: str | None,
        cursor_at: datetime,
    ) -> list[MinuteBar]:
        payload = self.client.request(
            MINUTE_CHART_PATH,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": cursor_at.strftime("%Y%m%d"),
                "FID_INPUT_HOUR_1": cursor_at.strftime("%H%M%S"),
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_FAKE_TICK_INCU_YN": "",
            },
            tr_id=MINUTE_CHART_TR_ID,
        )
        return _parse_minute_rows(symbol, symbol_name, payload.get("output2", []))


def _parse_minute_rows(
    symbol: str,
    symbol_name: str | None,
    payload: object,
) -> list[MinuteBar]:
    if not isinstance(payload, list):
        return []

    rows: list[MinuteBar] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        trade_date_text = str(item.get("stck_bsop_date", "")).strip()
        time_text = str(item.get("stck_cntg_hour", "")).strip()
        if len(trade_date_text) != 8 or len(time_text) != 6:
            continue

        trade_date = datetime.strptime(trade_date_text, "%Y%m%d").date()
        minute_ts = datetime.strptime(
            f"{trade_date_text}{time_text}",
            "%Y%m%d%H%M%S",
        )
        rows.append(
            MinuteBar(
                symbol=symbol,
                symbol_name=symbol_name,
                trade_date=trade_date,
                minute_ts=minute_ts,
                open=_to_float(item.get("stck_oprc")),
                high=_to_float(item.get("stck_hgpr")),
                low=_to_float(item.get("stck_lwpr")),
                close=_to_float(item.get("stck_prpr")),
                volume=_to_float(item.get("cntg_vol")),
            )
        )
    rows.sort(key=lambda item: item.minute_ts)
    return rows


def _parse_daily_rows(payload: object) -> list[tuple[date, float, float]]:
    if not isinstance(payload, list):
        return []

    rows: list[tuple[date, float, float]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        trade_date_text = str(item.get("stck_bsop_date", "")).strip()
        if len(trade_date_text) != 8:
            continue
        rows.append(
            (
                datetime.strptime(trade_date_text, "%Y%m%d").date(),
                _to_float(item.get("stck_oprc")),
                _to_float(item.get("stck_clpr")),
            )
        )
    rows.sort(key=lambda item: item[0])
    return rows


def _to_float(value: object) -> float:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0.0
    return float(text)
