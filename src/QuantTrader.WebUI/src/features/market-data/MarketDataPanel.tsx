import { Fragment, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getFullFetchJob,
  getMarketDataDaySymbols,
  getMarketDataMinuteBars,
  getProviderSession,
  refreshProviderSession,
  startFullFetchJob
} from "../../api/client";
import type { DateRangePayload } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { StatBadge } from "../../shared/components/StatBadge";
import {
  formatDateTime,
  formatInputDate,
  formatNumber,
  formatPercent,
  formatTime,
  getKoreanMarketDateInfo
} from "../../shared/utils/format";

type GapFilterKey = "all" | "gap_up" | "5_10" | "10_15" | "15_plus";

const GAP_FILTER_OPTIONS: Array<{ key: GapFilterKey; label: string }> = [
  { key: "all", label: "전체" },
  { key: "gap_up", label: "갭상승" },
  { key: "5_10", label: "5%~10%" },
  { key: "10_15", label: "10%~15%" },
  { key: "15_plus", label: "15% 이상" }
];

function resolveErrorMessage(error: unknown) {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error &&
    typeof error.response === "object" &&
    error.response !== null &&
    "data" in error.response &&
    typeof error.response.data === "object" &&
    error.response.data !== null &&
    "detail" in error.response.data &&
    typeof error.response.data.detail === "string"
  ) {
    return error.response.data.detail;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "작업 중 오류가 발생했습니다.";
}

function defaultDateRange() {
  const today = new Date();
  const earlier = new Date();
  earlier.setDate(today.getDate() - 20);
  return {
    dateFrom: formatInputDate(earlier),
    dateTo: formatInputDate(today)
  };
}

function getBackfillValidationMessage(dateFrom: string, dateTo: string) {
  if (!dateFrom || !dateTo) {
    return null;
  }
  const start = new Date(dateFrom);
  const end = new Date(dateTo);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return "날짜 형식이 올바르지 않습니다.";
  }
  if (start > end) {
    return "시작일은 종료일보다 늦을 수 없습니다.";
  }
  return null;
}

function shiftDateText(value: string, offsetDays: number) {
  if (!value) {
    return value;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  parsed.setDate(parsed.getDate() + offsetDays);
  return formatInputDate(parsed);
}

function matchesGapFilter(gapPct: number | null, filter: GapFilterKey) {
  if (filter === "all") {
    return true;
  }
  if (gapPct === null) {
    return false;
  }
  if (filter === "gap_up") {
    return gapPct > 0;
  }
  if (filter === "5_10") {
    return gapPct >= 0.05 && gapPct < 0.1;
  }
  if (filter === "10_15") {
    return gapPct >= 0.1 && gapPct < 0.15;
  }
  return gapPct >= 0.15;
}

export function MarketDataPanel() {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => defaultDateRange(), []);
  const todayText = useMemo(() => formatInputDate(new Date()), []);
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom);
  const [dateTo, setDateTo] = useState(defaults.dateTo);
  const [isTodayOnly, setIsTodayOnly] = useState(true);
  const [symbolsText, setSymbolsText] = useState("");
  const [selectedTradeDate, setSelectedTradeDate] = useState<string>(todayText);
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [selectedGapFilter, setSelectedGapFilter] = useState<GapFilterKey>("all");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState("조회 범위를 기준으로 데이터를 불러올 수 있습니다.");

  const parsedSymbols = useMemo(
    () =>
      symbolsText
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    [symbolsText]
  );

  const resolvedDateFrom = isTodayOnly ? todayText : dateFrom;
  const resolvedDateTo = isTodayOnly ? todayText : dateTo;
  const backfillValidationMessage = getBackfillValidationMessage(resolvedDateFrom, resolvedDateTo);
  const isBackfillBlocked = backfillValidationMessage !== null;

  const providerSessionQuery = useQuery({
    queryKey: ["provider-session"],
    queryFn: getProviderSession
  });
  const daySymbolsQuery = useQuery({
    queryKey: ["market-data-day-symbols", selectedTradeDate, parsedSymbols],
    queryFn: () =>
      getMarketDataDaySymbols({
        trade_date: selectedTradeDate,
        symbols: parsedSymbols
      }),
    enabled: Boolean(selectedTradeDate)
  });
  const minuteBarsQuery = useQuery({
    queryKey: ["market-data-minute-bars", selectedTradeDate, expandedSymbol],
    queryFn: () =>
      getMarketDataMinuteBars({
        trade_date: selectedTradeDate,
        symbol: expandedSymbol!
    }),
    enabled: Boolean(selectedTradeDate && expandedSymbol)
  });
  const fullFetchJobQuery = useQuery({
    queryKey: ["full-fetch-job", activeJobId],
    queryFn: () => getFullFetchJob(activeJobId!),
    enabled: Boolean(activeJobId),
    refetchInterval: 1500
  });

  const makePayload = (): DateRangePayload => ({
    date_from: resolvedDateFrom,
    date_to: resolvedDateTo,
    symbols: parsedSymbols,
    replace_existing: false
  });

  const startFullFetchMutation = useMutation({
    mutationFn: startFullFetchJob,
    onSuccess: (data) => {
      setActiveJobId(data.job_id);
      setStatusMessage(data.message);
    },
    onError: (error: unknown) => {
      setStatusMessage(resolveErrorMessage(error));
    }
  });
  const providerSessionMutation = useMutation({
    mutationFn: refreshProviderSession,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["provider-session"] });
      setStatusMessage(data.message);
    },
    onError: (error: unknown) => {
      setStatusMessage(resolveErrorMessage(error));
    }
  });
  const providerSession = providerSessionQuery.data;
  const activeJob = fullFetchJobQuery.data;
  const symbolRows = daySymbolsQuery.data ?? [];
  const minuteRows = minuteBarsQuery.data ?? [];
  const selectedDateInfo = useMemo(
    () => getKoreanMarketDateInfo(selectedTradeDate),
    [selectedTradeDate]
  );
  const gapFilterCounts = useMemo(
    () => ({
      all: symbolRows.length,
      gap_up: symbolRows.filter((row) => (row.gap_pct ?? 0) > 0).length,
      "5_10": symbolRows.filter((row) => matchesGapFilter(row.gap_pct, "5_10")).length,
      "10_15": symbolRows.filter((row) => matchesGapFilter(row.gap_pct, "10_15")).length,
      "15_plus": symbolRows.filter((row) => matchesGapFilter(row.gap_pct, "15_plus")).length
    }),
    [symbolRows]
  );
  const filteredSymbolRows = useMemo(
    () => symbolRows.filter((row) => matchesGapFilter(row.gap_pct, selectedGapFilter)),
    [selectedGapFilter, symbolRows]
  );
  const selectedSnapshot = useMemo(() => {
    const snapshotRows = symbolRows.filter((row) => row.gap_pct !== null);
    const gapUpRows = snapshotRows.filter((row) => (row.gap_pct ?? 0) > 0);
    const averageGap =
      snapshotRows.length === 0
        ? null
        : snapshotRows.reduce((sum, row) => sum + (row.gap_pct ?? 0), 0) / snapshotRows.length;
    const topGapRow = snapshotRows.reduce<(typeof snapshotRows)[number] | null>((best, row) => {
      if (!best) {
        return row;
      }
      return (row.gap_pct ?? Number.NEGATIVE_INFINITY) > (best.gap_pct ?? Number.NEGATIVE_INFINITY)
        ? row
        : best;
    }, null);
    return {
      snapshotCount: snapshotRows.length,
      gapUpCount: gapUpRows.length,
      gapBucketCounts: {
        fiveToTen: snapshotRows.filter((row) => matchesGapFilter(row.gap_pct, "5_10")).length,
        tenToFifteen: snapshotRows.filter((row) => matchesGapFilter(row.gap_pct, "10_15")).length,
        fifteenPlus: snapshotRows.filter((row) => matchesGapFilter(row.gap_pct, "15_plus")).length
      },
      averageGap,
      topGapRow
    };
  }, [symbolRows]);
  useEffect(() => {
    setExpandedSymbol(null);
  }, [selectedTradeDate]);

  useEffect(() => {
    if (expandedSymbol && !filteredSymbolRows.some((row) => row.symbol === expandedSymbol)) {
      setExpandedSymbol(null);
    }
  }, [expandedSymbol, filteredSymbolRows]);

  useEffect(() => {
    if (!activeJob) {
      return;
    }
    setStatusMessage(activeJob.error ?? activeJob.result?.message ?? activeJob.message);
    if (activeJob.status === "completed") {
      queryClient.invalidateQueries({ queryKey: ["market-data-day-symbols"] });
      queryClient.invalidateQueries({ queryKey: ["market-data-minute-bars"] });
      setActiveJobId(null);
      return;
    }
    if (activeJob.status === "failed") {
      setActiveJobId(null);
    }
  }, [activeJob, queryClient]);

  useEffect(() => {
    if (!activeJobId || !fullFetchJobQuery.error) {
      return;
    }
    setStatusMessage(`조회 작업 상태를 복구하지 못했습니다. ${resolveErrorMessage(fullFetchJobQuery.error)}`);
    setActiveJobId(null);
  }, [activeJobId, fullFetchJobQuery.error]);

  const isFetchPending =
    startFullFetchMutation.isPending ||
    activeJob?.status === "queued" ||
    activeJob?.status === "running";
  const loadingMessage = activeJob?.message ?? "현재 조회 범위 데이터를 불러오는 중입니다.";

  return (
    <SectionCard
      title="Market Data"
      subtitle="조회 범위를 기준으로 로컬 데이터를 불러옵니다"
      accent="amber"
      actions={
        <p className="section-caption">
          공급자: {providerSession?.provider ?? "loading"}
          {providerSession?.provider === "kis" ? " / KIS 인증 연동 가능" : " / mock 공급자"}
        </p>
      }
    >
      <div className="market-data-top-grid">
        <div className="market-data-controls-panel">
          <div className="form-stack">
            <div className="control-panel-header">
              <p className="section-eyebrow">Range</p>
              <h3>조회 범위와 불러오기 작업</h3>
              <p className="section-caption">조회 버튼은 1분봉과 장 시작 스냅샷을 함께 불러옵니다.</p>
            </div>

            <div className="control-top-row">
              <label className="checkbox-label checkbox-card">
                <input
                  type="checkbox"
                  checked={isTodayOnly}
                  onChange={(event) => setIsTodayOnly(event.target.checked)}
                />
                <span>당일 조회</span>
              </label>
              <button
                className="primary-button"
                onClick={() => startFullFetchMutation.mutate(makePayload())}
                disabled={isBackfillBlocked || isFetchPending}
              >
                조회
              </button>
            </div>

            <div className="field-grid">
              <label>
                <span>시작일</span>
                <input
                  type="date"
                  value={resolvedDateFrom}
                  onChange={(event) => setDateFrom(event.target.value)}
                  disabled={isTodayOnly}
                />
              </label>
              <label>
                <span>종료일</span>
                <input
                  type="date"
                  value={resolvedDateTo}
                  onChange={(event) => setDateTo(event.target.value)}
                  disabled={isTodayOnly}
                />
              </label>
            </div>

            <label className="field-wide">
              <span>종목 목록</span>
              <textarea
                rows={3}
                value={symbolsText}
                onChange={(event) => setSymbolsText(event.target.value)}
                placeholder="비워두면 전체 종목, 직접 넣으면 콤마로 구분: 005930,000660"
              />
            </label>

            <p className="status-line">
              {backfillValidationMessage
                ? backfillValidationMessage
                : isFetchPending
                ? loadingMessage
                : providerSessionQuery.isLoading
                ? "공급자 상태를 조회 중입니다."
                : statusMessage}
            </p>
          </div>
        </div>

        <div className="provider-status-card">
          <div className="provider-status-header">
            <div>
              <p className="section-eyebrow">Connection</p>
              <h3>공급자 연결 상태</h3>
            </div>
            <p className="section-caption">
            {providerSession?.provider === "kis" ? "KIS 인증 확인" : "mock 연결 상태"}
            </p>
          </div>
          <div className="badge-grid">
            <StatBadge label="공급자" value={providerSession?.provider?.toUpperCase() ?? "-"} />
            <StatBadge
              label="설정 상태"
              value={providerSession?.configured ? "완료" : "미설정"}
              tone={providerSession?.configured ? "positive" : "warning"}
            />
            <StatBadge
              label="토큰 상태"
              value={providerSession?.authenticated ? "발급됨" : "미발급"}
              tone={providerSession?.authenticated ? "positive" : "warning"}
            />
            <StatBadge
              label="만료 시각"
              value={formatDateTime(providerSession?.token_expires_at)}
            />
          </div>
          <div className="overview-notes">
            <p>Base URL: {providerSession?.base_url ?? "-"}</p>
            <p>상태: {providerSession?.message ?? "공급자 상태를 조회 중입니다."}</p>
          </div>
          <div className="action-row">
            <button
              onClick={() => providerSessionMutation.mutate()}
              disabled={providerSession?.provider !== "kis" || isFetchPending}
            >
              KIS 토큰 발급
            </button>
          </div>
        </div>
      </div>

      <div className="data-grid-section">
        <div className="data-grid-header">
          <div>
            <p className="section-eyebrow">Daily View</p>
            <h3>선택 날짜 종목 요약</h3>
          </div>
          <p className="section-caption">
            {isFetchPending
              ? loadingMessage
              : daySymbolsQuery.isLoading
              ? "선택 날짜 종목 요약을 불러오는 중입니다."
              : selectedTradeDate
              ? `${selectedTradeDate} 기준 ${filteredSymbolRows.length}종목`
              : "표시할 날짜가 없습니다."}
          </p>
        </div>
        {isFetchPending ? (
          <div className="loading-panel">
            <div className="loading-spinner" />
            <div>
              <strong>{loadingMessage}</strong>
              <p className="section-caption">
                조회 작업은 백그라운드에서 계속 진행되고, 화면은 상태를 주기적으로 확인합니다.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="date-selector-bar">
              <div className="date-selector-field">
                <span>표시 날짜</span>
                <div className="date-navigation-row">
                  <button
                    type="button"
                    className="date-nav-button"
                    onClick={() => setSelectedTradeDate((current) => shiftDateText(current, -1))}
                    disabled={!selectedTradeDate}
                  >
                    이전 날짜
                  </button>
                  <input
                    type="date"
                    value={selectedTradeDate}
                    onChange={(event) => setSelectedTradeDate(event.target.value)}
                  />
                  <button
                    type="button"
                    className="date-nav-button"
                    onClick={() => setSelectedTradeDate((current) => shiftDateText(current, 1))}
                    disabled={!selectedTradeDate}
                  >
                    다음 날짜
                  </button>
                </div>
              </div>
              <div className="date-status-block">
                <strong className="date-status-line">{selectedDateInfo.statusLabel}</strong>
                <p className="section-caption">
                  {selectedDateInfo.holidayName
                    ? `한국 공휴일: ${selectedDateInfo.holidayName}`
                    : "휴일도 선택할 수 있고, 데이터가 없으면 빈 화면으로 유지됩니다."}
                </p>
              </div>
            </div>

            <div className="snapshot-strip">
              <div className="badge-grid snapshot-badges">
                <StatBadge label="스냅샷 종목 수" value={formatNumber(selectedSnapshot.snapshotCount)} />
                <StatBadge
                  label="갭상승 종목 수"
                  value={formatNumber(selectedSnapshot.gapUpCount)}
                  tone="warning"
                />
                <StatBadge
                  label="5%~10%"
                  value={formatNumber(selectedSnapshot.gapBucketCounts.fiveToTen)}
                  tone="warning"
                />
                <StatBadge
                  label="10%~15%"
                  value={formatNumber(selectedSnapshot.gapBucketCounts.tenToFifteen)}
                  tone="warning"
                />
                <StatBadge
                  label="15% 이상"
                  value={formatNumber(selectedSnapshot.gapBucketCounts.fifteenPlus)}
                  tone="warning"
                />
                <StatBadge
                  label="평균 갭"
                  value={formatPercent(selectedSnapshot.averageGap)}
                />
              </div>
              <div className="filter-chip-row">
                {GAP_FILTER_OPTIONS.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    className={`filter-chip ${selectedGapFilter === option.key ? "is-active" : ""}`}
                    onClick={() => setSelectedGapFilter(option.key)}
                  >
                    {option.label} {formatNumber(gapFilterCounts[option.key])}
                  </button>
                ))}
              </div>
              <div className="overview-notes">
                <p>
                  장 시작 스냅샷 기준:{" "}
                  {selectedSnapshot.topGapRow
                    ? `${selectedSnapshot.topGapRow.symbol_name ?? selectedSnapshot.topGapRow.symbol} ${formatPercent(selectedSnapshot.topGapRow.gap_pct)}`
                    : "표시할 스냅샷 데이터가 없습니다."}
                </p>
              </div>
            </div>

            <div className="result-table-wrap">
              <table className="result-table symbol-summary-table">
                <thead>
                  <tr>
                    <th>종목</th>
                    <th>갭%</th>
                    <th>분봉 수</th>
                    <th>시가</th>
                    <th>고가</th>
                    <th>저가</th>
                    <th>종가</th>
                    <th>거래량</th>
                    <th>상세</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSymbolRows.map((row) => {
                    const isExpanded = expandedSymbol === row.symbol;
                    return (
                      <Fragment key={`${row.trade_date}-${row.symbol}`}>
                        <tr>
                          <td>
                            <div className="cell-stack">
                              <strong>{row.symbol_name ?? row.symbol}</strong>
                              <span>{row.symbol}</span>
                            </div>
                          </td>
                          <td>{formatPercent(row.gap_pct)}</td>
                          <td>{formatNumber(row.minute_bar_count)}</td>
                          <td>{formatNumber(row.session_open, 2)}</td>
                          <td>{formatNumber(row.session_high, 2)}</td>
                          <td>{formatNumber(row.session_low, 2)}</td>
                          <td>{formatNumber(row.session_close, 2)}</td>
                          <td>{formatNumber(row.total_volume)}</td>
                          <td>
                            <button
                              type="button"
                              className={`inline-button ${isExpanded ? "is-active" : ""}`}
                              onClick={() => setExpandedSymbol(isExpanded ? null : row.symbol)}
                            >
                              {isExpanded ? "닫기" : "보기"}
                            </button>
                          </td>
                        </tr>
                        {isExpanded ? (
                          <tr>
                            <td colSpan={9}>
                              <div className="expanded-detail-panel">
                                <div className="expanded-detail-header">
                                  <strong>{row.symbol_name ?? row.symbol} 분봉 상세</strong>
                                  <span>
                                    {minuteBarsQuery.isLoading
                                      ? "분봉을 불러오는 중입니다."
                                      : `${minuteRows.length}개 분봉`}
                                  </span>
                                </div>
                                <div className="nested-table-wrap">
                                  <table className="minute-bar-table">
                                    <thead>
                                      <tr>
                                        <th>시각</th>
                                        <th>시가</th>
                                        <th>고가</th>
                                        <th>저가</th>
                                        <th>종가</th>
                                        <th>거래량</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {minuteRows.map((minuteRow) => (
                                        <tr key={minuteRow.minute_ts}>
                                          <td>{formatTime(minuteRow.minute_ts)}</td>
                                          <td>{formatNumber(minuteRow.open, 2)}</td>
                                          <td>{formatNumber(minuteRow.high, 2)}</td>
                                          <td>{formatNumber(minuteRow.low, 2)}</td>
                                          <td>{formatNumber(minuteRow.close, 2)}</td>
                                          <td>{formatNumber(minuteRow.volume)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                  {minuteRows.length ? null : (
                                    <p className="empty-state">표시할 분봉 데이터가 없습니다.</p>
                                  )}
                                </div>
                              </div>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
              {filteredSymbolRows.length ? null : (
                <p className="empty-state">
                  {symbolRows.length
                    ? "선택한 갭상승 구간에 해당하는 종목이 없습니다."
                    : "선택한 날짜에 표시할 종목 데이터가 없습니다."}
                </p>
              )}
            </div>
          </>
        )}
      </div>
    </SectionCard>
  );
}
