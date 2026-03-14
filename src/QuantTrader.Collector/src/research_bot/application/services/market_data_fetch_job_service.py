from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import date, datetime
import logging
from threading import Lock
from uuid import uuid4

from research_bot.application.dto.market_data_dto import (
    CollectHistoricalMinuteBarsCommand,
    CollectMarketOpenSnapshotCommand,
    CollectResult,
)
from research_bot.application.use_cases.collect_historical_minute_bars import (
    CollectHistoricalMinuteBarsUseCase,
)
from research_bot.application.use_cases.collect_market_open_snapshot import (
    CollectMarketOpenSnapshotUseCase,
)


JobStatus = str
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FullFetchJobRequest:
    date_from: date
    date_to: date
    symbols: list[str]
    replace_existing: bool


@dataclass(frozen=True)
class FullFetchJobResult:
    provider: str
    symbols: list[str]
    date_from: date
    date_to: date
    historical_minute_rows: int
    market_open_snapshot_rows: int
    historical_minute_skipped: bool
    market_open_snapshot_skipped: bool
    message: str


@dataclass(frozen=True)
class FullFetchJobState:
    job_id: str
    status: JobStatus
    request: FullFetchJobRequest
    message: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: FullFetchJobResult | None = None
    error: str | None = None


class MarketDataFetchJobService:
    def __init__(
        self,
        historical_use_case: CollectHistoricalMinuteBarsUseCase,
        market_open_snapshot_use_case: CollectMarketOpenSnapshotUseCase,
    ) -> None:
        self.historical_use_case = historical_use_case
        self.market_open_snapshot_use_case = market_open_snapshot_use_case
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="market-fetch-job")
        self._jobs: dict[str, FullFetchJobState] = {}
        self._lock = Lock()

    def start(self, request: FullFetchJobRequest) -> FullFetchJobState:
        job_id = str(uuid4())
        job_state = FullFetchJobState(
            job_id=job_id,
            status="queued",
            request=request,
            message="조회 작업을 대기열에 등록했습니다.",
            created_at=datetime.now(),
        )
        with self._lock:
            self._jobs[job_id] = job_state
        self.executor.submit(self._run_job, job_id)
        return job_state

    def get(self, job_id: str) -> FullFetchJobState | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job_id: str) -> None:
        queued_state = self.get(job_id)
        if queued_state is None:
            return

        logger.info(
            "full-fetch 시작 job_id=%s date_from=%s date_to=%s symbols=%s replace_existing=%s",
            job_id,
            queued_state.request.date_from.isoformat(),
            queued_state.request.date_to.isoformat(),
            len(queued_state.request.symbols),
            queued_state.request.replace_existing,
        )
        self._update(
            job_id,
            status="running",
            started_at=datetime.now(),
            message="과거 1분봉 조회를 시작했습니다.",
        )

        request = queued_state.request
        try:
            historical_result = self.historical_use_case.execute(
                CollectHistoricalMinuteBarsCommand(
                    date_from=request.date_from,
                    date_to=request.date_to,
                    symbols=request.symbols,
                    replace_existing=request.replace_existing,
                )
            )
            self._update(
                job_id,
                message="장 시작 스냅샷 조회를 진행 중입니다.",
            )
            snapshot_symbols = (
                historical_result.completed_symbols
                if historical_result.failed_symbols
                else request.symbols
            )
            if historical_result.failed_symbols and not snapshot_symbols:
                market_open_snapshot_result = CollectResult(
                    provider=historical_result.provider,
                    symbols=request.symbols,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    rows_written=0,
                    skipped=True,
                    completed_symbols=[],
                    failed_symbols=[],
                    warning_message="1분봉 성공 종목이 없어 장 시작 스냅샷 조회를 건너뛰었습니다.",
                )
            else:
                market_open_snapshot_result = self.market_open_snapshot_use_case.execute(
                    CollectMarketOpenSnapshotCommand(
                        date_from=request.date_from,
                        date_to=request.date_to,
                        symbols=snapshot_symbols,
                        replace_existing=request.replace_existing,
                    )
                )
        except Exception as error:  # noqa: BLE001
            logger.error(
                "full-fetch 실패 job_id=%s date_from=%s date_to=%s error=%s",
                job_id,
                request.date_from.isoformat(),
                request.date_to.isoformat(),
                error,
            )
            self._update(
                job_id,
                status="failed",
                completed_at=datetime.now(),
                message="조회 작업이 실패했습니다.",
                error=str(error),
            )
            return

        result = FullFetchJobResult(
            provider=historical_result.provider,
            symbols=historical_result.symbols,
            date_from=historical_result.date_from,
            date_to=historical_result.date_to,
            historical_minute_rows=historical_result.rows_written,
            market_open_snapshot_rows=market_open_snapshot_result.rows_written,
            historical_minute_skipped=historical_result.skipped,
            market_open_snapshot_skipped=market_open_snapshot_result.skipped,
            message=_resolve_full_fetch_message(
                historical_result,
                market_open_snapshot_result,
            ),
        )
        self._update(
            job_id,
            status="completed",
            completed_at=datetime.now(),
            message=result.message,
            result=result,
            error=None,
        )
        logger.info(
            "full-fetch 완료 job_id=%s historical_rows=%s snapshot_rows=%s message=%s",
            job_id,
            result.historical_minute_rows,
            result.market_open_snapshot_rows,
            result.message,
        )

    def _update(self, job_id: str, **changes) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = replace(current, **changes)


def _resolve_full_fetch_message(
    historical_result: CollectResult,
    market_open_snapshot_result: CollectResult,
) -> str:
    warnings = [message for message in (historical_result.warning_message, market_open_snapshot_result.warning_message) if message]
    if historical_result.skipped and market_open_snapshot_result.skipped:
        base_message = "같은 범위 데이터가 이미 로컬 DB에 있어 API 호출을 건너뛰었습니다."
        return f"{base_message} {' / '.join(warnings)}" if warnings else base_message
    if historical_result.skipped:
        base_message = "1분봉은 로컬 DB를 재사용했고, 장 시작 스냅샷만 새로 조회했습니다."
        return f"{base_message} {' / '.join(warnings)}" if warnings else base_message
    if market_open_snapshot_result.skipped:
        base_message = "장 시작 스냅샷은 로컬 DB를 재사용했고, 1분봉만 새로 조회했습니다."
        return f"{base_message} {' / '.join(warnings)}" if warnings else base_message
    base_message = "전체 데이터 조회가 완료되었습니다."
    return f"{base_message} {' / '.join(warnings)}" if warnings else base_message
