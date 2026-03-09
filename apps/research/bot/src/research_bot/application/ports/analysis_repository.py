from __future__ import annotations

from typing import Protocol

from research_bot.domain.orb.models import OrbScanRecord, OrbScanRun


class AnalysisRepository(Protocol):
    def save_run(self, run: OrbScanRun) -> None: ...

    def save_results(self, run_id: str, rows: list[OrbScanRecord]) -> None: ...

    def get_run(self, run_id: str) -> OrbScanRun | None: ...

    def list_runs(self, limit: int = 20) -> list[OrbScanRun]: ...

    def list_results(self, run_id: str) -> list[OrbScanRecord]: ...
