from __future__ import annotations

from functools import cached_property

from research_bot.application.use_cases.build_opening_bars import BuildOpeningBarsUseCase
from research_bot.application.use_cases.collect_historical_minute_bars import (
    CollectHistoricalMinuteBarsUseCase,
)
from research_bot.application.use_cases.collect_session_reference import (
    CollectSessionReferenceUseCase,
)
from research_bot.application.use_cases.scan_orb_breakouts import ScanOrbBreakoutsUseCase
from research_bot.bootstrap.settings import Settings, get_settings
from research_bot.infrastructure.providers.kis_client import KisClient
from research_bot.infrastructure.providers.kis_market_data_provider import (
    KisMarketDataProvider,
)
from research_bot.infrastructure.providers.mock_market_data_provider import (
    MockMarketDataProvider,
)
from research_bot.infrastructure.storage.analysis_repository_duckdb import (
    DuckDbAnalysisRepository,
)
from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory
from research_bot.infrastructure.storage.market_data_repository_duckdb import (
    DuckDbMarketDataRepository,
)
from research_bot.infrastructure.storage.schema_manager import DuckDbSchemaManager


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def connection_factory(self) -> DuckDbConnectionFactory:
        return DuckDbConnectionFactory(self.settings.duckdb_path)

    @cached_property
    def schema_manager(self) -> DuckDbSchemaManager:
        return DuckDbSchemaManager(self.connection_factory)

    @cached_property
    def kis_client(self) -> KisClient:
        return KisClient(self.settings)

    @cached_property
    def market_data_provider(self):
        if self.settings.market_data_provider.lower() == "kis":
            return KisMarketDataProvider(self.kis_client)
        return MockMarketDataProvider(self.settings.default_symbol_list)

    @cached_property
    def market_data_repository(self) -> DuckDbMarketDataRepository:
        return DuckDbMarketDataRepository(
            connection_factory=self.connection_factory,
            schema_manager=self.schema_manager,
            market_open=self.settings.market_open,
            opening_cutoff=self.settings.opening_cutoff,
        )

    @cached_property
    def analysis_repository(self) -> DuckDbAnalysisRepository:
        return DuckDbAnalysisRepository(
            connection_factory=self.connection_factory,
            schema_manager=self.schema_manager,
        )

    @cached_property
    def collect_historical_minute_bars_use_case(self) -> CollectHistoricalMinuteBarsUseCase:
        return CollectHistoricalMinuteBarsUseCase(
            provider=self.market_data_provider,
            repository=self.market_data_repository,
            default_symbols=self.settings.default_symbol_list,
        )

    @cached_property
    def collect_session_reference_use_case(self) -> CollectSessionReferenceUseCase:
        return CollectSessionReferenceUseCase(
            provider=self.market_data_provider,
            repository=self.market_data_repository,
            default_symbols=self.settings.default_symbol_list,
        )

    @cached_property
    def build_opening_bars_use_case(self) -> BuildOpeningBarsUseCase:
        return BuildOpeningBarsUseCase(
            repository=self.market_data_repository,
            default_symbols=self.settings.default_symbol_list,
        )

    @cached_property
    def scan_orb_breakouts_use_case(self) -> ScanOrbBreakoutsUseCase:
        return ScanOrbBreakoutsUseCase(
            market_data_repository=self.market_data_repository,
            analysis_repository=self.analysis_repository,
            market_open=self.settings.market_open,
            opening_cutoff=self.settings.opening_cutoff,
        )


def build_container(settings: Settings | None = None) -> Container:
    resolved_settings = settings or get_settings()
    container = Container(resolved_settings)
    container.schema_manager.initialize()
    return container
