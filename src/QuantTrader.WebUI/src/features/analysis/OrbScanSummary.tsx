import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { OrbScanRunResponse } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { StatBadge } from "../../shared/components/StatBadge";
import { formatPercent } from "../../shared/utils/format";

interface OrbScanSummaryProps {
  run: OrbScanRunResponse | null;
}

export function OrbScanSummary({ run }: OrbScanSummaryProps) {
  const chartData = run
    ? [
        { name: "전체 세션", value: run.summary.total_sessions },
        { name: "스캔 대상", value: run.summary.scanned_sessions },
        { name: "갭상승", value: run.summary.gap_up_sessions },
        { name: "돌파", value: run.summary.breakout_sessions }
      ]
    : [];

  return (
    <SectionCard
      title="Summary"
      subtitle="스캔 결과 요약"
      accent="coral"
      actions={run ? <p className="section-caption">Run ID: {run.run_id}</p> : null}
    >
      <div className="badge-grid">
        <StatBadge label="전체 세션" value={`${run?.summary.total_sessions ?? 0}`} />
        <StatBadge label="스캔 대상" value={`${run?.summary.scanned_sessions ?? 0}`} />
        <StatBadge label="갭상승 세션" value={`${run?.summary.gap_up_sessions ?? 0}`} tone="warning" />
        <StatBadge
          label="돌파 비율"
          value={formatPercent(run?.summary.breakout_rate)}
          tone="positive"
        />
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis dataKey="name" stroke="#d7d1c6" />
            <YAxis stroke="#d7d1c6" allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#f08c64" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
