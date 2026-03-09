from __future__ import annotations

from research_bot.application.dto.market_data_dto import (
    CollectResult,
    CollectMarketOpenSnapshotCommand,
)
from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.application.ports.market_data_repository import MarketDataRepository


class CollectMarketOpenSnapshotUseCase:
    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
    ) -> None:
        self.provider = provider
        self.repository = repository

    def execute(self, command: CollectMarketOpenSnapshotCommand) -> CollectResult:
        requested_symbols = command.symbols
        if (
            not command.replace_existing
            and self.repository.is_market_open_snapshots_loaded(
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
            )
        symbols = self.provider.resolve_symbols(command.symbols)
        rows = self.provider.get_market_open_snapshots(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
        )
        _validate_market_open_snapshots(rows, symbols, command.date_from, command.date_to)
        written = self.repository.replace_market_open_snapshots(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            rows=rows,
            replace_existing=command.replace_existing,
            source=self.provider.name,
        )
        self.repository.mark_market_open_snapshots_loaded(
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
        )


def _validate_market_open_snapshots(rows, symbols, date_from, date_to) -> None:
    if not rows:
        raise ValueError("장 시작 스냅샷 API에서 적재할 데이터가 없습니다.")
    seen_keys: set[tuple[str, object]] = set()
    symbol_set = set(symbols)
    for row in rows:
        if row.symbol not in symbol_set:
            raise ValueError("장 시작 스냅샷 응답에 요청하지 않은 종목이 포함되어 있습니다.")
        if not (date_from <= row.trade_date <= date_to):
            raise ValueError("장 시작 스냅샷 응답에 요청 범위를 벗어난 데이터가 포함되어 있습니다.")
        key = (row.symbol, row.trade_date)
        if key in seen_keys:
            raise ValueError("장 시작 스냅샷 응답에 중복 일자가 포함되어 있습니다.")
        seen_keys.add(key)
