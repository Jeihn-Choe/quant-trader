from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Request

from research_bot.api.schemas.market_data import (
    BuildOpeningBarsRequest,
    BuildOpeningBarsResponse,
    CollectHistoricalMinuteBarsRequest,
    CollectResponse,
    CollectSessionReferenceRequest,
    MarketDataOverviewResponse,
    ProviderSessionResponse,
    SeedMockDataRequest,
    SeedMockDataResponse,
)
from research_bot.application.dto.market_data_dto import (
    BuildOpeningBarsCommand,
    CollectHistoricalMinuteBarsCommand,
    CollectSessionReferenceCommand,
)
from research_bot.infrastructure.providers.kis_client import KisClientError


router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/overview", response_model=MarketDataOverviewResponse)
def get_market_data_overview(request: Request) -> MarketDataOverviewResponse:
    overview = request.app.state.container.market_data_repository.get_market_data_overview()
    return MarketDataOverviewResponse(
        historical_bar_count=overview.historical_bar_count,
        opening_bar_count=overview.opening_bar_count,
        session_reference_count=overview.session_reference_count,
        symbol_count=overview.symbol_count,
        historical_date_min=_date_text(overview.historical_date_min),
        historical_date_max=_date_text(overview.historical_date_max),
        opening_date_min=_date_text(overview.opening_date_min),
        opening_date_max=_date_text(overview.opening_date_max),
        available_symbols=overview.available_symbols,
    )


@router.get("/provider-session", response_model=ProviderSessionResponse)
def get_provider_session(request: Request) -> ProviderSessionResponse:
    container = request.app.state.container
    if container.settings.market_data_provider.lower() == "kis":
        return _map_provider_session(container.kis_client.get_token_status())
    return ProviderSessionResponse(
        provider="mock",
        configured=True,
        authenticated=False,
        base_url=None,
        token_expires_at=None,
        message="현재 mock 공급자를 사용 중입니다.",
    )


@router.post("/provider-session/refresh", response_model=ProviderSessionResponse)
def refresh_provider_session(request: Request) -> ProviderSessionResponse:
    container = request.app.state.container
    if container.settings.market_data_provider.lower() != "kis":
        return ProviderSessionResponse(
            provider="mock",
            configured=True,
            authenticated=False,
            base_url=None,
            token_expires_at=None,
            message="mock 공급자는 토큰 발급이 필요하지 않습니다.",
        )
    try:
        return _map_provider_session(
            container.kis_client.authenticate(force_refresh=True),
            message="KIS access token을 발급받았습니다.",
        )
    except KisClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/historical-minute-bars", response_model=CollectResponse)
def collect_historical_minute_bars(
    payload: CollectHistoricalMinuteBarsRequest,
    request: Request,
) -> CollectResponse:
    use_case = request.app.state.container.collect_historical_minute_bars_use_case
    try:
        result = use_case.execute(
            CollectHistoricalMinuteBarsCommand(
                date_from=date.fromisoformat(payload.date_from),
                date_to=date.fromisoformat(payload.date_to),
                symbols=payload.symbols,
                replace_existing=payload.replace_existing,
            )
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    return CollectResponse(
        message="과거 1분봉 적재가 완료되었습니다.",
        provider=result.provider,
        symbols=result.symbols,
        date_from=result.date_from.isoformat(),
        date_to=result.date_to.isoformat(),
        rows_written=result.rows_written,
    )


@router.post("/session-references", response_model=CollectResponse)
def collect_session_references(
    payload: CollectSessionReferenceRequest,
    request: Request,
) -> CollectResponse:
    use_case = request.app.state.container.collect_session_reference_use_case
    try:
        result = use_case.execute(
            CollectSessionReferenceCommand(
                date_from=date.fromisoformat(payload.date_from),
                date_to=date.fromisoformat(payload.date_to),
                symbols=payload.symbols,
                replace_existing=payload.replace_existing,
            )
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    return CollectResponse(
        message="세션 기준값 적재가 완료되었습니다.",
        provider=result.provider,
        symbols=result.symbols,
        date_from=result.date_from.isoformat(),
        date_to=result.date_to.isoformat(),
        rows_written=result.rows_written,
    )


@router.post("/opening-bars/build", response_model=BuildOpeningBarsResponse)
def build_opening_bars(
    payload: BuildOpeningBarsRequest,
    request: Request,
) -> BuildOpeningBarsResponse:
    use_case = request.app.state.container.build_opening_bars_use_case
    result = use_case.execute(
        BuildOpeningBarsCommand(
            date_from=date.fromisoformat(payload.date_from),
            date_to=date.fromisoformat(payload.date_to),
            symbols=payload.symbols,
            replace_existing=payload.replace_existing,
        )
    )
    return BuildOpeningBarsResponse(
        message="오프닝 1시간 1분봉 생성이 완료되었습니다.",
        symbols=result.symbols,
        date_from=result.date_from.isoformat(),
        date_to=result.date_to.isoformat(),
        rows_written=result.rows_written,
    )


@router.post("/mock/seed", response_model=SeedMockDataResponse)
def seed_mock_data(payload: SeedMockDataRequest, request: Request) -> SeedMockDataResponse:
    try:
        historical_result = (
            request.app.state.container.collect_historical_minute_bars_use_case.execute(
                CollectHistoricalMinuteBarsCommand(
                    date_from=date.fromisoformat(payload.date_from),
                    date_to=date.fromisoformat(payload.date_to),
                    symbols=payload.symbols,
                    replace_existing=payload.replace_existing,
                )
            )
        )
        session_result = request.app.state.container.collect_session_reference_use_case.execute(
            CollectSessionReferenceCommand(
                date_from=date.fromisoformat(payload.date_from),
                date_to=date.fromisoformat(payload.date_to),
                symbols=payload.symbols,
                replace_existing=payload.replace_existing,
            )
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    opening_result = request.app.state.container.build_opening_bars_use_case.execute(
        BuildOpeningBarsCommand(
            date_from=date.fromisoformat(payload.date_from),
            date_to=date.fromisoformat(payload.date_to),
            symbols=payload.symbols,
            replace_existing=payload.replace_existing,
        )
    )
    return SeedMockDataResponse(
        message="모의 데이터 전체 적재가 완료되었습니다.",
        provider=historical_result.provider,
        symbols=historical_result.symbols,
        date_from=historical_result.date_from.isoformat(),
        date_to=historical_result.date_to.isoformat(),
        historical_minute_rows=historical_result.rows_written,
        session_reference_rows=session_result.rows_written,
        opening_bar_rows=opening_result.rows_written,
    )


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _map_provider_session(status, message: str | None = None) -> ProviderSessionResponse:
    return ProviderSessionResponse(
        provider=status.provider,
        configured=status.configured,
        authenticated=status.authenticated,
        base_url=status.base_url,
        token_expires_at=(
            status.token_expires_at.isoformat() if status.token_expires_at else None
        ),
        message=message or status.message,
    )
