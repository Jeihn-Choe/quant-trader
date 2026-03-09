import type { OrbScanResultRow } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { formatDate, formatDateTime, formatNumber, formatPercent } from "../../shared/utils/format";

interface OrbScanTableProps {
  rows: OrbScanResultRow[];
}

export function OrbScanTable({ rows }: OrbScanTableProps) {
  return (
    <SectionCard
      title="Results"
      subtitle="세션별 ORB / 돌파 결과"
      accent="teal"
      actions={<p className="section-caption">행 수: {rows.length}</p>}
    >
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>종목</th>
              <th>거래일</th>
              <th>갭%</th>
              <th>갭상승</th>
              <th>ORB High</th>
              <th>ORB Low</th>
              <th>돌파</th>
              <th>최초 돌파 시각</th>
              <th>돌파가</th>
              <th>초과폭</th>
              <th>10:00 가격</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.symbol}-${row.trade_date}`}>
                <td>{row.symbol}</td>
                <td>{formatDate(row.trade_date)}</td>
                <td>{formatPercent(row.gap_pct)}</td>
                <td>{row.gap_up ? "Y" : "N"}</td>
                <td>{formatNumber(row.orb_high, 2)}</td>
                <td>{formatNumber(row.orb_low, 2)}</td>
                <td>{row.breakout ? "Y" : "N"}</td>
                <td>{formatDateTime(row.first_breakout_time)}</td>
                <td>{formatNumber(row.first_breakout_price, 2)}</td>
                <td>{formatNumber(row.breakout_excess, 2)}</td>
                <td>{formatNumber(row.cutoff_price, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </SectionCard>
  );
}
