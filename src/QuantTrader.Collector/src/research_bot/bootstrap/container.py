from __future__ import annotations

from functools import cached_property
from research_bot.application.use_cases.collect_historical_minute_bars import (
    CollectHistoricalMinuteBarsUseCase,
)
from research_bot.application.use_cases.collect_market_open_snapshot import (
    CollectMarketOpenSnapshotUseCase,
)
from research_bot.application.services.market_data_fetch_job_service import (
    MarketDataFetchJobService,
)
from research_bot.application.use_cases.scan_orb_breakouts import ScanOrbBreakoutsUseCase
from research_bot.bootstrap.settings import Settings, get_settings
from research_bot.infrastructure.providers.kis_client import KisClient
from research_bot.infrastructure.providers.kis_market_data_provider import (
    KisMarketDataProvider,
)
from research_bot.infrastructure.providers.kis_universe_resolver import (
    KisUniverseResolver,
)
from research_bot.infrastructure.providers.mock_market_data_provider import (
    MockMarketDataProvider,
)
from research_bot.infrastructure.storage.analysis_repository_postgresql import (
    PostgreSqlAnalysisRepository,
)
from research_bot.infrastructure.storage.analysis_repository_duckdb import (
    DuckDbAnalysisRepository,
)
from research_bot.infrastructure.storage.duckdb_connection import DuckDbConnectionFactory
from research_bot.infrastructure.storage.market_data_repository_duckdb import (
    DuckDbMarketDataRepository,
)
from research_bot.infrastructure.storage.market_data_repository_postgresql import (
    PostgreSqlMarketDataRepository,
)
from research_bot.infrastructure.storage.postgresql_connection import (
    PostgreSqlConnectionFactory,
)
from research_bot.infrastructure.storage.postgresql_schema_manager import (
    PostgreSqlSchemaManager,
)
from research_bot.infrastructure.storage.schema_manager import DuckDbSchemaManager


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @cached_property
    def connection_factory(self) -> DuckDbConnectionFactory:
        return DuckDbConnectionFactory(self.settings.duckdb_path)

    @cached_property
    def postgresql_connection_factory(self) -> PostgreSqlConnectionFactory:
        return PostgreSqlConnectionFactory(self.settings.postgres_conninfo)

    @cached_property
    def schema_manager(self) -> DuckDbSchemaManager:
        if self.settings.database_backend.lower() == "postgresql":
            return PostgreSqlSchemaManager(
                self.postgresql_connection_factory,
                schema_name=self.settings.postgres_schema,
            )
        return DuckDbSchemaManager(self.connection_factory)

    @cached_property
    def kis_client(self) -> KisClient:
        return KisClient(
            self.settings,
            on_token_issued=self.kis_universe_resolver.refresh_masters,
        )

    @cached_property
    def kis_universe_resolver(self) -> KisUniverseResolver:
        return KisUniverseResolver(
            data_dir=self.settings.data_dir,
            markets=self.settings.kis_universe_market_list,
        )

    @cached_property
    def market_data_provider(self):
        if self.settings.market_data_provider.lower() == "kis":
            return KisMarketDataProvider(
                self.kis_client,
                self.kis_universe_resolver,
                max_workers=self.settings.kis_parallel_workers,
            )
        return MockMarketDataProvider(self.settings.default_symbol_list)

    @cached_property
    def market_data_repository(self) -> DuckDbMarketDataRepository:
        if self.settings.database_backend.lower() == "postgresql":
            return PostgreSqlMarketDataRepository(
                connection_factory=self.postgresql_connection_factory,
                schema_manager=self.schema_manager,
            )
        return DuckDbMarketDataRepository(
            connection_factory=self.connection_factory,
            schema_manager=self.schema_manager,
        )

    @cached_property
    def analysis_repository(self) -> DuckDbAnalysisRepository:
        if self.settings.database_backend.lower() == "postgresql":
            return PostgreSqlAnalysisRepository(
                connection_factory=self.postgresql_connection_factory,
                schema_manager=self.schema_manager,
            )
        return DuckDbAnalysisRepository(
            connection_factory=self.connection_factory,
            schema_manager=self.schema_manager,
        )

    @cached_property
    def collect_historical_minute_bars_use_case(self) -> CollectHistoricalMinuteBarsUseCase:
        return CollectHistoricalMinuteBarsUseCase(
            provider=self.market_data_provider,
            repository=self.market_data_repository,
            max_workers=self.settings.kis_parallel_workers,
        )

    @cached_property
    def collect_market_open_snapshot_use_case(self) -> CollectMarketOpenSnapshotUseCase:
        return CollectMarketOpenSnapshotUseCase(
            provider=self.market_data_provider,
            repository=self.market_data_repository,
            max_workers=self.settings.kis_parallel_workers,
        )

    @cached_property
    def scan_orb_breakouts_use_case(self) -> ScanOrbBreakoutsUseCase:
        return ScanOrbBreakoutsUseCase(
            market_data_repository=self.market_data_repository,
            analysis_repository=self.analysis_repository,
            market_open=self.settings.market_open,
            opening_cutoff=self.settings.opening_cutoff,
        )

    @cached_property
    def market_data_fetch_job_service(self) -> MarketDataFetchJobService:
        return MarketDataFetchJobService(
            historical_use_case=self.collect_historical_minute_bars_use_case,
            market_open_snapshot_use_case=self.collect_market_open_snapshot_use_case,
        )


def build_container(settings: Settings | None = None) -> Container:
    resolved_settings = settings or get_settings()
    container = Container(resolved_settings)
    container.schema_manager.initialize()
    return container
