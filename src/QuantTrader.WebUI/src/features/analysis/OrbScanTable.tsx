import type { OrbScanResultRow } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { formatDate, formatDateTime, formatNumber, formatPercent } from "../../shared/utils/format";

interface OrbScanTableProps {
  rows: OrbScanResultRow[];
}

function renderBreakoutText(row: OrbScanResultRow) {
  if (!row.breakout) {
    return "미발생";
  }
  const price = formatNumber(row.first_breakout_price, 2);
  const excess = formatNumber(row.breakout_excess, 2);
  return `${price} / +${excess}`;
}

export function OrbScanTable({ rows }: OrbScanTableProps) {
  return (
    <SectionCard
      title="Results"
      subtitle="세션별 ORB / 돌파 결과"
      accent="teal"
      actions={<p className="section-caption">행 수: {rows.length}</p>}
    >
      <div className="result-table-wrap">
        <table className="result-table">
          <thead>
            <tr>
              <th>거래일</th>
              <th>종목</th>
              <th>갭</th>
              <th>ORB 범위</th>
              <th>돌파 상태</th>
              <th>최초 돌파 시각</th>
              <th>10:00 가격</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.symbol}-${row.trade_date}`}>
                <td>{formatDate(row.trade_date)}</td>
                <td>
                  <div className="cell-stack">
                    <strong>{row.symbol_name ?? row.symbol}</strong>
                    <span>{row.symbol}</span>
                  </div>
                </td>
                <td>
                  <div className="cell-stack">
                    <strong>{formatPercent(row.gap_pct)}</strong>
                    <span>{row.gap_up ? "갭상승" : "전체 대상"}</span>
                  </div>
                </td>
                <td>
                  <div className="cell-stack">
                    <strong>{formatNumber(row.orb_high, 2)}</strong>
                    <span>Low {formatNumber(row.orb_low, 2)}</span>
                  </div>
                </td>
                <td>
                  <div className="cell-stack">
                    <strong>{row.breakout ? "발생" : "미발생"}</strong>
                    <span>{renderBreakoutText(row)}</span>
                  </div>
                </td>
                <td>{formatDateTime(row.first_breakout_time)}</td>
                <td>{formatNumber(row.cutoff_price, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length ? null : <p className="empty-state">표시할 결과가 없습니다.</p>}
      </div>
    </SectionCard>
  );
}
