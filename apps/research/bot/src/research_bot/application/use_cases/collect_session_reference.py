from __future__ import annotations

from research_bot.application.dto.market_data_dto import (
    CollectResult,
    CollectSessionReferenceCommand,
)
from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.application.ports.market_data_repository import MarketDataRepository


class CollectSessionReferenceUseCase:
    def __init__(
        self,
        provider: MarketDataProvider,
        repository: MarketDataRepository,
        default_symbols: list[str],
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.default_symbols = default_symbols

    def execute(self, command: CollectSessionReferenceCommand) -> CollectResult:
        symbols = command.symbols or self.default_symbols
        rows = self.provider.get_session_references(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
        )
        written = self.repository.replace_session_references(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            rows=rows,
            replace_existing=command.replace_existing,
            source=self.provider.name,
        )
        return CollectResult(
            provider=self.provider.name,
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            rows_written=written,
        )
