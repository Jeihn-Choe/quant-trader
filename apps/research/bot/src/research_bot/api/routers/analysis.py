from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Request

from research_bot.api.schemas.analysis import (
    OrbScanRequest,
    OrbScanResultResponse,
    OrbScanRunListItemResponse,
    OrbScanRunResponse,
    OrbScanSummaryResponse,
)
from research_bot.application.dto.analysis_dto import OrbScanCommand


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/orb-scans", response_model=OrbScanRunResponse)
def scan_orb_breakouts(payload: OrbScanRequest, request: Request) -> OrbScanRunResponse:
    result = request.app.state.container.scan_orb_breakouts_use_case.execute(
        OrbScanCommand(
            date_from=date.fromisoformat(payload.date_from),
            date_to=date.fromisoformat(payload.date_to),
            symbols=payload.symbols,
            orb_window_minutes=payload.orb_window_minutes,
            breakout_buffer=payload.breakout_buffer,
            gap_mode=payload.gap_mode,
            gap_threshold_pct=payload.gap_threshold_pct,
        )
    )
    return _map_run_response(result)


@router.get("/orb-scans", response_model=list[OrbScanRunListItemResponse])
def list_orb_scans(request: Request) -> list[OrbScanRunListItemResponse]:
    runs = request.app.state.container.analysis_repository.list_runs(limit=20)
    return [
        OrbScanRunListItemResponse(
            run_id=run.run_id,
            created_at=run.created_at.isoformat(),
            date_from=run.date_from.isoformat(),
            date_to=run.date_to.isoformat(),
            orb_window_minutes=run.orb_window_minutes,
            gap_mode=run.gap_mode,
            breakout_sessions=run.breakout_sessions,
        )
        for run in runs
    ]


@router.get("/orb-scans/{run_id}", response_model=OrbScanRunResponse)
def get_orb_scan(run_id: str, request: Request) -> OrbScanRunResponse:
    repository = request.app.state.container.analysis_repository
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="백테스트 실행 이력이 없습니다.")
    results = repository.list_results(run_id)
    return _map_run_response((run, results))


@router.get("/orb-scans/{run_id}/results", response_model=list[OrbScanResultResponse])
def get_orb_scan_results(run_id: str, request: Request) -> list[OrbScanResultResponse]:
    results = request.app.state.container.analysis_repository.list_results(run_id)
    return [_map_result_row(row) for row in results]


def _map_run_response(result) -> OrbScanRunResponse:
    run, rows = result
    summary = OrbScanSummaryResponse(
        total_sessions=run.total_sessions,
        scanned_sessions=run.scanned_sessions,
        gap_up_sessions=run.gap_up_sessions,
        breakout_sessions=run.breakout_sessions,
        breakout_rate=run.breakout_rate,
    )
    return OrbScanRunResponse(
        run_id=run.run_id,
        created_at=run.created_at.isoformat(),
        date_from=run.date_from.isoformat(),
        date_to=run.date_to.isoformat(),
        orb_window_minutes=run.orb_window_minutes,
        breakout_buffer=run.breakout_buffer,
        gap_mode=run.gap_mode,
        gap_threshold_pct=run.gap_threshold_pct,
        requested_symbols=run.requested_symbols,
        summary=summary,
        results=[_map_result_row(row) for row in rows],
    )


def _map_result_row(row) -> OrbScanResultResponse:
    return OrbScanResultResponse(
        symbol=row.symbol,
        symbol_name=row.symbol_name,
        trade_date=row.trade_date.isoformat(),
        prev_close=row.prev_close,
        market_open_price=row.market_open_price,
        gap_pct=row.gap_pct,
        gap_up=row.gap_up,
        orb_window_minutes=row.orb_window_minutes,
        orb_high=row.orb_high,
        orb_low=row.orb_low,
        breakout=row.breakout,
        first_breakout_time=(
            row.first_breakout_time.isoformat() if row.first_breakout_time else None
        ),
        first_breakout_price=row.first_breakout_price,
        breakout_excess=row.breakout_excess,
        cutoff_price=row.cutoff_price,
        cutoff_above_orb_high=row.cutoff_above_orb_high,
    )
