import { useEffect, useState, useTransition } from "react";
import { useQuery } from "@tanstack/react-query";

import { getOrbScan, listOrbScans } from "../../api/client";
import type { OrbScanRunResponse } from "../../api/types";
import { OrbScanForm } from "../analysis/OrbScanForm";
import { OrbScanSummary } from "../analysis/OrbScanSummary";
import { OrbScanTable } from "../analysis/OrbScanTable";
import { MarketDataPanel } from "../market-data/MarketDataPanel";
import { SectionCard } from "../../shared/components/SectionCard";
import { formatDate, formatDateTime } from "../../shared/utils/format";

export function ResearchDashboard() {
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<OrbScanRunResponse | null>(null);
  const [isPending, startTransition] = useTransition();

  const runsQuery = useQuery({
    queryKey: ["orb-runs"],
    queryFn: listOrbScans
  });

  const activeRunQuery = useQuery({
    queryKey: ["orb-run", activeRunId],
    queryFn: () => getOrbScan(activeRunId!),
    enabled: Boolean(activeRunId)
  });

  useEffect(() => {
    if (activeRunQuery.data) {
      setActiveRun(activeRunQuery.data);
    }
  }, [activeRunQuery.data]);

  useEffect(() => {
    if (!activeRunId && runsQuery.data?.length) {
      setActiveRunId(runsQuery.data[0].run_id);
    }
  }, [activeRunId, runsQuery.data]);

  return (
    <div className="page-shell">
      <div className="page-hero">
        <p className="hero-kicker">QuantTrader Research Workspace</p>
        <h1>오프닝 ORB 연구 콘솔</h1>
        <p className="hero-copy">
          로컬 DuckDB에 데이터를 적재하고, ORB 계산과 ORB High 돌파 이벤트를 빠르게 비교하는
          연구용 화면입니다.
        </p>
      </div>

      <div className="layout-grid">
        <div className="main-column">
          <MarketDataPanel />
          <OrbScanForm
            onCompleted={(result) => {
              setActiveRun(result);
              setActiveRunId(result.run_id);
            }}
          />
          <OrbScanSummary run={activeRun} />
          <OrbScanTable rows={activeRun?.results ?? []} />
        </div>

        <aside className="side-column">
          <SectionCard
            title="Recent Runs"
            subtitle="최근 실행 이력"
            accent="amber"
            actions={isPending ? <p className="section-caption">로딩 중...</p> : null}
          >
            <div className="run-list">
              {(runsQuery.data ?? []).map((run) => (
                <button
                  key={run.run_id}
                  className={`run-item ${activeRun?.run_id === run.run_id ? "is-active" : ""}`}
                  onClick={() =>
                    startTransition(() => {
                      setActiveRunId(run.run_id);
                    })
                  }
                >
                  <strong>{formatDateTime(run.created_at)}</strong>
                  <span>{formatDate(run.date_from)} ~ {formatDate(run.date_to)}</span>
                  <span>ORB {run.orb_window_minutes}분</span>
                  <span>돌파 세션 {run.breakout_sessions}</span>
                </button>
              ))}
              {runsQuery.data?.length ? null : (
                <p className="empty-state">아직 실행 이력이 없습니다.</p>
              )}
            </div>
          </SectionCard>
        </aside>
      </div>
    </div>
  );
}
