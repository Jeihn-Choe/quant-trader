from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Request

from research_bot.api.schemas.market_data import (
    CollectAllMarketDataRequest,
    CollectAllMarketDataResponse,
    CollectMarketOpenSnapshotRequest,
    CollectHistoricalMinuteBarsRequest,
    CollectResponse,
    MarketDataDailySummaryResponse,
    MarketDataSymbolSummaryResponse,
    MarketDataOverviewResponse,
    MinuteBarResponse,
    ProviderSessionResponse,
)
from research_bot.application.dto.market_data_dto import (
    CollectMarketOpenSnapshotCommand,
    CollectHistoricalMinuteBarsCommand,
)
from research_bot.infrastructure.providers.kis_client import KisClientError


router = APIRouter(prefix="/market-data", tags=["market-data"])
MAX_BACKFILL_DAYS = 99


@router.get("/daily-grid", response_model=list[MarketDataDailySummaryResponse])
def get_daily_market_data_grid(
    request: Request,
    date_from: str,
    date_to: str,
    symbols: str | None = None,
) -> list[MarketDataDailySummaryResponse]:
    resolved_date_from, resolved_date_to = _validate_backfill_range(date_from, date_to)
    symbol_list = [value.strip() for value in (symbols or "").split(",") if value.strip()]
    rows = request.app.state.container.market_data_repository.list_daily_market_data_summary(
        date_from=resolved_date_from,
        date_to=resolved_date_to,
        symbols=symbol_list or None,
    )
    return [
        MarketDataDailySummaryResponse(
            trade_date=row.trade_date.isoformat(),
            symbol_count=row.symbol_count,
            historical_bar_count=row.historical_bar_count,
            market_open_snapshot_count=row.market_open_snapshot_count,
            preview_symbols=row.preview_symbols,
        )
        for row in rows
    ]


@router.get("/day-symbols", response_model=list[MarketDataSymbolSummaryResponse])
def get_day_symbol_grid(
    request: Request,
    trade_date: str,
    symbols: str | None = None,
) -> list[MarketDataSymbolSummaryResponse]:
    resolved_trade_date = _parse_iso_date(trade_date)
    symbol_list = [value.strip() for value in (symbols or "").split(",") if value.strip()]
    rows = request.app.state.container.market_data_repository.list_symbol_market_data_summary(
        trade_date=resolved_trade_date,
        symbols=symbol_list or None,
    )
    return [
        MarketDataSymbolSummaryResponse(
            trade_date=row.trade_date.isoformat(),
            symbol=row.symbol,
            symbol_name=row.symbol_name,
            minute_bar_count=row.minute_bar_count,
            session_open=row.session_open,
            session_high=row.session_high,
            session_low=row.session_low,
            session_close=row.session_close,
            total_volume=row.total_volume,
            gap_pct=row.gap_pct,
        )
        for row in rows
    ]


@router.get("/day-symbols/{symbol}/minute-bars", response_model=list[MinuteBarResponse])
def get_symbol_minute_bars(
    request: Request,
    symbol: str,
    trade_date: str,
) -> list[MinuteBarResponse]:
    resolved_trade_date = _parse_iso_date(trade_date)
    rows = request.app.state.container.market_data_repository.list_historical_minute_bars(
        date_from=resolved_trade_date,
        date_to=resolved_trade_date,
        symbols=[symbol],
    )
    return [
        MinuteBarResponse(
            symbol=row.symbol,
            symbol_name=row.symbol_name,
            trade_date=row.trade_date.isoformat(),
            minute_ts=row.minute_ts.isoformat(),
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
        )
        for row in rows
    ]


@router.get("/overview", response_model=MarketDataOverviewResponse)
def get_market_data_overview(request: Request) -> MarketDataOverviewResponse:
    overview = request.app.state.container.market_data_repository.get_market_data_overview()
    return MarketDataOverviewResponse(
        historical_bar_count=overview.historical_bar_count,
        market_open_snapshot_count=overview.market_open_snapshot_count,
        symbol_count=overview.symbol_count,
        historical_date_min=_date_text(overview.historical_date_min),
        historical_date_max=_date_text(overview.historical_date_max),
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
    date_from, date_to = _validate_backfill_range(payload.date_from, payload.date_to)
    use_case = request.app.state.container.collect_historical_minute_bars_use_case
    try:
        result = use_case.execute(
            CollectHistoricalMinuteBarsCommand(
                date_from=date_from,
                date_to=date_to,
                symbols=payload.symbols,
                replace_existing=payload.replace_existing,
            )
        )
    except KisClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    return CollectResponse(
        message=(
            "같은 범위의 1분봉이 이미 로컬 DB에 있어 API 호출을 건너뛰었습니다."
            if result.skipped
            else "과거 1분봉 적재가 완료되었습니다."
        ),
        provider=result.provider,
        symbols=result.symbols,
        date_from=result.date_from.isoformat(),
        date_to=result.date_to.isoformat(),
        rows_written=result.rows_written,
        skipped=result.skipped,
    )


@router.post("/market-open-snapshots", response_model=CollectResponse)
def collect_market_open_snapshots(
    payload: CollectMarketOpenSnapshotRequest,
    request: Request,
) -> CollectResponse:
    date_from, date_to = _validate_backfill_range(payload.date_from, payload.date_to)
    use_case = request.app.state.container.collect_market_open_snapshot_use_case
    try:
        result = use_case.execute(
            CollectMarketOpenSnapshotCommand(
                date_from=date_from,
                date_to=date_to,
                symbols=payload.symbols,
                replace_existing=payload.replace_existing,
            )
        )
    except KisClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    return CollectResponse(
        message=(
            "같은 범위의 장 시작 스냅샷이 이미 로컬 DB에 있어 API 호출을 건너뛰었습니다."
            if result.skipped
            else "장 시작 스냅샷 적재가 완료되었습니다."
        ),
        provider=result.provider,
        symbols=result.symbols,
        date_from=result.date_from.isoformat(),
        date_to=result.date_to.isoformat(),
        rows_written=result.rows_written,
        skipped=result.skipped,
    )


@router.post("/full-fetch", response_model=CollectAllMarketDataResponse)
def collect_all_market_data(
    payload: CollectAllMarketDataRequest,
    request: Request,
) -> CollectAllMarketDataResponse:
    date_from, date_to = _validate_backfill_range(payload.date_from, payload.date_to)
    try:
        historical_result = (
            request.app.state.container.collect_historical_minute_bars_use_case.execute(
                CollectHistoricalMinuteBarsCommand(
                    date_from=date_from,
                    date_to=date_to,
                    symbols=payload.symbols,
                    replace_existing=payload.replace_existing,
                )
            )
        )
        market_open_snapshot_result = (
            request.app.state.container.collect_market_open_snapshot_use_case.execute(
                CollectMarketOpenSnapshotCommand(
                    date_from=date_from,
                    date_to=date_to,
                    symbols=payload.symbols,
                    replace_existing=payload.replace_existing,
                )
            )
        )
    except KisClientError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except NotImplementedError as error:
        raise HTTPException(status_code=501, detail=str(error)) from error
    return CollectAllMarketDataResponse(
        message=_full_fetch_message(
            historical_skipped=historical_result.skipped,
            snapshot_skipped=market_open_snapshot_result.skipped,
        ),
        provider=historical_result.provider,
        symbols=historical_result.symbols,
        date_from=historical_result.date_from.isoformat(),
        date_to=historical_result.date_to.isoformat(),
        historical_minute_rows=historical_result.rows_written,
        market_open_snapshot_rows=market_open_snapshot_result.rows_written,
        historical_minute_skipped=historical_result.skipped,
        market_open_snapshot_skipped=market_open_snapshot_result.skipped,
    )


def _date_text(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _validate_backfill_range(date_from_text: str, date_to_text: str) -> tuple[date, date]:
    date_from = _parse_iso_date(date_from_text)
    date_to = _parse_iso_date(date_to_text)
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="시작일은 종료일보다 늦을 수 없습니다.")
    range_days = (date_to - date_from).days + 1
    if range_days > MAX_BACKFILL_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"백필 기간은 최대 {MAX_BACKFILL_DAYS}일까지만 요청할 수 있습니다.",
        )
    return date_from, date_to


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다.") from error


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


def _full_fetch_message(historical_skipped: bool, snapshot_skipped: bool) -> str:
    if historical_skipped and snapshot_skipped:
        return "같은 범위 데이터가 이미 로컬 DB에 있어 API 호출을 건너뛰었습니다."
    if historical_skipped:
        return "1분봉은 로컬 DB를 재사용했고, 장 시작 스냅샷만 새로 조회했습니다."
    if snapshot_skipped:
        return "장 시작 스냅샷은 로컬 DB를 재사용했고, 1분봉만 새로 조회했습니다."
    return "전체 데이터 조회가 완료되었습니다."
