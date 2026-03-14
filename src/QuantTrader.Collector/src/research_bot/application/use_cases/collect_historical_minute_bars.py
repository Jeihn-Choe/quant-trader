from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
import logging
import time

from research_bot.application.dto.market_data_dto import (
    CollectHistoricalMinuteBarsCommand,
    CollectResult,
)
from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.application.ports.market_data_repository import MarketDataRepository
from research_bot.infrastructure.providers.kis_client import KisClientError


MAX_ERROR_PREVIEW = 5
logger = logging.getLogger(__name__)


class CollectHistoricalMinuteBarsUseCase:
    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
        max_workers: int = 1,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.max_workers = max(1, max_workers)

    def execute(self, command: CollectHistoricalMinuteBarsCommand) -> CollectResult:
        requested_symbols = command.symbols
        if (
            not command.replace_existing
            and self.repository.is_historical_minute_bars_loaded(
                requested_symbols=requested_symbols,
                date_from=command.date_from,
                date_to=command.date_to,
                source=self.provider.name,
            )
        ):
            return CollectResult(
                provider=self.provider.name,
                symbols=requested_symbols,
                date_from=command.date_from,
                date_to=command.date_to,
                rows_written=0,
                skipped=True,
                completed_symbols=requested_symbols,
            )
        symbols = self.provider.resolve_symbols(command.symbols)
        logger.info(
            "과거 1분봉 대상 종목 확인 완료 - requested=%s resolved=%s",
            len(command.symbols),
            len(symbols),
        )
        logger.info("과거 1분봉 pending 종목 확인 시작")
        pending_symbols = self._resolve_pending_symbols(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            replace_existing=command.replace_existing,
        )
        logger.info("과거 1분봉 pending 종목 확인 완료 - pending=%s", len(pending_symbols))
        if not pending_symbols:
            self.repository.mark_historical_minute_bars_loaded(
                requested_symbols=requested_symbols,
                date_from=command.date_from,
                date_to=command.date_to,
                source=self.provider.name,
            )
            return CollectResult(
                provider=self.provider.name,
                symbols=requested_symbols,
                date_from=command.date_from,
                date_to=command.date_to,
                rows_written=0,
                skipped=True,
                completed_symbols=symbols,
            )

        written = 0
        errors: list[str] = []
        completed_symbols: list[str] = []
        progress_by_date: dict[date, int] = {}
        total_symbols = len(pending_symbols)
        worker_count = min(self.max_workers, total_symbols)
        logger.info(
            "과거 1분봉 종목 단위 조회 시작 - workers=%s, symbols=%s",
            worker_count,
            total_symbols,
        )

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="minute-fetch") as executor:
            future_map = {
                executor.submit(
                    self.provider.get_symbol_historical_minute_bars,
                    symbol,
                    command.date_from,
                    command.date_to,
                ): (symbol, time.perf_counter())
                for symbol in pending_symbols
            }
            for future in as_completed(future_map):
                symbol, started_at = future_map[future]
                try:
                    rows = future.result()
                    elapsed_seconds = time.perf_counter() - started_at
                    if not rows:
                        symbol_name = self.provider.get_symbol_name(symbol) or symbol
                        self.repository.mark_historical_minute_bars_loaded(
                            requested_symbols=[symbol],
                            date_from=command.date_from,
                            date_to=command.date_to,
                            source=self.provider.name,
                        )
                        _log_symbol_no_data(
                            symbol=symbol,
                            symbol_name=symbol_name,
                            date_from=command.date_from,
                            date_to=command.date_to,
                            total_symbols=total_symbols,
                            progress_by_date=progress_by_date,
                            elapsed_seconds=elapsed_seconds,
                        )
                        completed_symbols.append(symbol)
                        continue
                    _validate_minute_bars(rows, command.date_from, command.date_to)
                    symbol_written = self.repository.replace_historical_minute_bars(
                        symbols=[symbol],
                        date_from=command.date_from,
                        date_to=command.date_to,
                        rows=rows,
                        replace_existing=command.replace_existing,
                        source=self.provider.name,
                    )
                    self.repository.mark_historical_minute_bars_loaded(
                        requested_symbols=[symbol],
                        date_from=command.date_from,
                        date_to=command.date_to,
                        source=self.provider.name,
                    )
                    written += symbol_written
                    completed_symbols.append(symbol)
                    _log_symbol_progress(
                        symbol=symbol,
                        rows=rows,
                        written=symbol_written,
                        total_symbols=total_symbols,
                        progress_by_date=progress_by_date,
                        elapsed_seconds=elapsed_seconds,
                    )
                except Exception as error:  # noqa: BLE001
                    symbol_name = self.provider.get_symbol_name(symbol) or symbol
                    logger.warning(
                        "[ERR ] %s %s %s elapsed=%.2fs %s: %s",
                        command.date_from.isoformat(),
                        symbol,
                        symbol_name,
                        time.perf_counter() - started_at,
                        "1분봉 조회실패",
                        error,
                    )
                    errors.append(f"{symbol}: {error}")

        warning_message = None
        if errors:
            preview = "; ".join(errors[:MAX_ERROR_PREVIEW])
            remainder = len(errors) - MAX_ERROR_PREVIEW
            suffix = f" 외 {remainder}건" if remainder > 0 else ""
            warning_message = (
                f"과거 1분봉 종목 단위 조회 중 일부 종목이 실패했습니다. {preview}{suffix}"
            )
        else:
            self.repository.mark_historical_minute_bars_loaded(
                requested_symbols=requested_symbols,
                date_from=command.date_from,
                date_to=command.date_to,
                source=self.provider.name,
            )
        return CollectResult(
            provider=self.provider.name,
            symbols=requested_symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            rows_written=written,
            completed_symbols=completed_symbols,
            failed_symbols=[entry.split(":", 1)[0] for entry in errors],
            warning_message=warning_message,
        )

    def _resolve_pending_symbols(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
        replace_existing: bool,
    ) -> list[str]:
        if replace_existing:
            return symbols
        loaded_symbols = self.repository.get_loaded_historical_minute_bar_symbols(
            symbols=symbols,
            date_from=date_from,
            date_to=date_to,
            source=self.provider.name,
        )
        return [
            symbol
            for symbol in symbols
            if symbol not in loaded_symbols
        ]


def _validate_minute_bars(rows, date_from, date_to) -> None:
    if not rows:
        raise ValueError("과거 1분봉 API에서 적재할 데이터가 없습니다.")
    seen_keys: set[tuple[str, object, object]] = set()
    for row in rows:
        if not (date_from <= row.trade_date <= date_to):
            raise ValueError("과거 1분봉 응답에 요청 범위를 벗어난 데이터가 포함되어 있습니다.")
        key = (row.symbol, row.trade_date, row.minute_ts)
        if key in seen_keys:
            raise ValueError("과거 1분봉 응답에 중복 분봉이 포함되어 있습니다.")
        seen_keys.add(key)


def _log_symbol_progress(
    symbol: str,
    rows,
    written: int,
    total_symbols: int,
    progress_by_date: dict[date, int],
    elapsed_seconds: float,
) -> None:
    trade_dates = sorted({row.trade_date for row in rows})
    symbol_name = next((row.symbol_name for row in rows if getattr(row, "symbol_name", None)), symbol)
    if not trade_dates:
        logger.info(
            "[OK ] [0/%s] %s %s %s rows=0 elapsed=%.2fs %s",
            total_symbols,
            "no-date",
            symbol,
            symbol_name,
            elapsed_seconds,
            "1분봉 저장완료",
        )
        return

    for trade_date in trade_dates:
        progress_by_date[trade_date] = progress_by_date.get(trade_date, 0) + 1
        logger.info(
            "[OK ] [%s/%s] %s %s %s rows=%s elapsed=%.2fs %s",
            progress_by_date[trade_date],
            total_symbols,
            trade_date.isoformat(),
            symbol,
            symbol_name,
            len(rows),
            elapsed_seconds,
            "1분봉 저장완료",
        )


def _log_symbol_no_data(
    symbol: str,
    symbol_name: str,
    date_from: date,
    date_to: date,
    total_symbols: int,
    progress_by_date: dict[date, int],
    elapsed_seconds: float,
) -> None:
    trade_date = date_from
    progress_by_date[trade_date] = progress_by_date.get(trade_date, 0) + 1
    logger.info(
        "[SKIP] [%s/%s] %s %s %s rows=0 elapsed=%.2fs %s",
        progress_by_date[trade_date],
        total_symbols,
        trade_date.isoformat(),
        symbol,
        symbol_name,
        elapsed_seconds,
        "1분봉 데이터없음",
    )
