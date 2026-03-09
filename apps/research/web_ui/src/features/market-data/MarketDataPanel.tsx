import { Fragment, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  collectAllMarketData,
  getMarketDataDailyGrid,
  getMarketDataDaySymbols,
  getMarketDataMinuteBars,
  getProviderSession,
  refreshProviderSession
} from "../../api/client";
import type { DateRangePayload } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { StatBadge } from "../../shared/components/StatBadge";
import {
  formatDateTime,
  formatInputDate,
  formatNumber,
  formatPercent,
  formatTime
} from "../../shared/utils/format";

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
  const rangeDays = Math.floor((end.getTime() - start.getTime()) / 86_400_000) + 1;
  if (rangeDays > 99) {
    return "백필 기간은 최대 99일까지만 요청할 수 있습니다.";
  }
  return null;
}

export function MarketDataPanel() {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => defaultDateRange(), []);
  const todayText = useMemo(() => formatInputDate(new Date()), []);
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom);
  const [dateTo, setDateTo] = useState(defaults.dateTo);
  const [isTodayOnly, setIsTodayOnly] = useState(true);
  const [symbolsText, setSymbolsText] = useState("");
  const [selectedTradeDate, setSelectedTradeDate] = useState<string>("");
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
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
  const dailyGridQuery = useQuery({
    queryKey: ["market-data-daily-grid", resolvedDateFrom, resolvedDateTo, parsedSymbols],
    queryFn: () =>
      getMarketDataDailyGrid({
        date_from: resolvedDateFrom,
        date_to: resolvedDateTo,
        symbols: parsedSymbols
      }),
    enabled: !isBackfillBlocked
  });
  const daySymbolsQuery = useQuery({
    queryKey: ["market-data-day-symbols", selectedTradeDate, parsedSymbols],
    queryFn: () =>
      getMarketDataDaySymbols({
        trade_date: selectedTradeDate,
        symbols: parsedSymbols
      }),
    enabled: Boolean(selectedTradeDate) && !isBackfillBlocked
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

  const makePayload = (): DateRangePayload => ({
    date_from: resolvedDateFrom,
    date_to: resolvedDateTo,
    symbols: parsedSymbols,
    replace_existing: false
  });

  const mutationOptions = {
    onSuccess: (data: Record<string, unknown>) => {
      queryClient.invalidateQueries({ queryKey: ["market-data-daily-grid"] });
      queryClient.invalidateQueries({ queryKey: ["market-data-day-symbols"] });
      queryClient.invalidateQueries({ queryKey: ["market-data-minute-bars"] });
      const message =
        typeof data.message === "string" ? data.message : "작업이 완료되었습니다.";
      setStatusMessage(message);
    },
    onError: (error: unknown) => {
      setStatusMessage(resolveErrorMessage(error));
    }
  };

  const collectAllMutation = useMutation({
    mutationFn: collectAllMarketData,
    ...mutationOptions
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
  const dailyRows = dailyGridQuery.data ?? [];
  const availableDates = dailyRows.map((row) => row.trade_date).sort((left, right) => right.localeCompare(left));
  const symbolRows = daySymbolsQuery.data ?? [];
  const minuteRows = minuteBarsQuery.data ?? [];
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
      averageGap,
      topGapRow
    };
  }, [symbolRows]);

  useEffect(() => {
    if (!selectedTradeDate && availableDates.length) {
      setSelectedTradeDate(availableDates[0]);
    }
  }, [availableDates, selectedTradeDate]);

  useEffect(() => {
    setExpandedSymbol(null);
  }, [selectedTradeDate]);

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
                onClick={() => collectAllMutation.mutate(makePayload())}
                disabled={isBackfillBlocked}
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
              disabled={providerSession?.provider !== "kis"}
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
            {collectAllMutation.isPending
              ? "현재 조회 범위 데이터를 불러오는 중입니다."
              : daySymbolsQuery.isLoading
              ? "선택 날짜 종목 요약을 불러오는 중입니다."
              : selectedTradeDate
              ? `${selectedTradeDate} 기준 ${symbolRows.length}종목`
              : "표시할 날짜가 없습니다."}
          </p>
        </div>
        {collectAllMutation.isPending ? (
          <div className="loading-panel">
            <div className="loading-spinner" />
            <div>
              <strong>현재 조회 범위 데이터를 불러오는 중입니다.</strong>
              <p className="section-caption">
                1분봉과 장 시작 스냅샷을 순서대로 확인하고 있습니다.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="date-selector-bar">
              <label className="date-selector-field">
                <span>표시 날짜</span>
                <input
                  type="date"
                  value={selectedTradeDate}
                  min={availableDates[availableDates.length - 1] ?? undefined}
                  max={availableDates[0] ?? undefined}
                  onChange={(event) => setSelectedTradeDate(event.target.value)}
                  disabled={!availableDates.length}
                />
              </label>
              <p className="section-caption">
                휴일도 선택할 수 있고, 데이터가 없으면 빈 화면으로 유지됩니다.
              </p>
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
                  label="평균 갭"
                  value={formatPercent(selectedSnapshot.averageGap)}
                />
                <StatBadge
                  label="최대 갭 종목"
                  value={selectedSnapshot.topGapRow?.symbol_name ?? selectedSnapshot.topGapRow?.symbol ?? "-"}
                  tone="positive"
                />
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
                  {symbolRows.map((row) => {
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
              {symbolRows.length ? null : (
                <p className="empty-state">선택한 날짜에 표시할 종목 데이터가 없습니다.</p>
              )}
            </div>
          </>
        )}
      </div>
    </SectionCard>
  );
}
