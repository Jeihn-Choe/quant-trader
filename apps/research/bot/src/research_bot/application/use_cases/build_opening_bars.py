from __future__ import annotations

from research_bot.application.dto.market_data_dto import (
    BuildOpeningBarsCommand,
    BuildOpeningBarsResult,
)
from research_bot.application.ports.market_data_repository import MarketDataRepository


class BuildOpeningBarsUseCase:
    def __init__(
        self,
        repository: MarketDataRepository,
        default_symbols: list[str],
    ) -> None:
        self.repository = repository
        self.default_symbols = default_symbols

    def execute(self, command: BuildOpeningBarsCommand) -> BuildOpeningBarsResult:
        symbols = command.symbols or self.default_symbols
        written = self.repository.rebuild_opening_bars(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            replace_existing=command.replace_existing,
        )
        return BuildOpeningBarsResult(
            symbols=symbols,
            date_from=command.date_from,
            date_to=command.date_to,
            rows_written=written,
        )
