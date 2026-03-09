import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  buildOpeningBars,
  collectHistoricalMinuteBars,
  collectSessionReferences,
  getProviderSession,
  getMarketDataOverview,
  refreshProviderSession,
  seedMockData
} from "../../api/client";
import type { DateRangePayload } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { StatBadge } from "../../shared/components/StatBadge";
import { formatDate, formatDateTime, formatInputDate, formatNumber } from "../../shared/utils/format";


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

export function MarketDataPanel() {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => defaultDateRange(), []);
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom);
  const [dateTo, setDateTo] = useState(defaults.dateTo);
  const [symbolsText, setSymbolsText] = useState("005930,000660,035420,051910");
  const [statusMessage, setStatusMessage] = useState("모의 데이터 또는 실제 적재 API를 실행할 수 있습니다.");

  const overviewQuery = useQuery({
    queryKey: ["market-data-overview"],
    queryFn: getMarketDataOverview
  });
  const providerSessionQuery = useQuery({
    queryKey: ["provider-session"],
    queryFn: getProviderSession
  });

  const makePayload = (): DateRangePayload => ({
    date_from: dateFrom,
    date_to: dateTo,
    symbols: symbolsText
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    replace_existing: true
  });

  const mutationOptions = {
    onSuccess: (data: Record<string, unknown>) => {
      queryClient.invalidateQueries({ queryKey: ["market-data-overview"] });
      const message =
        typeof data.message === "string" ? data.message : "작업이 완료되었습니다.";
      setStatusMessage(message);
    },
    onError: (error: unknown) => {
      setStatusMessage(resolveErrorMessage(error));
    }
  };

  const seedMutation = useMutation({
    mutationFn: seedMockData,
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
  const minuteMutation = useMutation({
    mutationFn: collectHistoricalMinuteBars,
    ...mutationOptions
  });
  const sessionMutation = useMutation({
    mutationFn: collectSessionReferences,
    ...mutationOptions
  });
  const openingMutation = useMutation({
    mutationFn: buildOpeningBars,
    ...mutationOptions
  });

  const overview = overviewQuery.data;
  const providerSession = providerSessionQuery.data;

  return (
    <SectionCard
      title="Market Data"
      subtitle="로컬 연구 데이터를 적재합니다"
      accent="amber"
      actions={
        <p className="section-caption">
          공급자: {providerSession?.provider ?? "loading"}
          {providerSession?.provider === "kis" ? " / KIS 인증 연동 가능" : " / mock 공급자"}
        </p>
      }
    >
      <div className="panel-grid">
        <div className="form-stack">
          <div className="provider-status-card">
            <div className="badge-grid">
              <StatBadge
                label="공급자"
                value={providerSession?.provider?.toUpperCase() ?? "-"}
              />
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
          <label>
            <span>시작일</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label>
            <span>종료일</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label className="field-wide">
            <span>종목 목록</span>
            <textarea
              rows={3}
              value={symbolsText}
              onChange={(event) => setSymbolsText(event.target.value)}
              placeholder="콤마로 구분: 005930,000660"
            />
          </label>
          <div className="action-row">
            <button className="primary-button" onClick={() => seedMutation.mutate(makePayload())}>
              모의 데이터 전체 적재
            </button>
            <button onClick={() => minuteMutation.mutate(makePayload())}>과거 1분봉 적재</button>
            <button onClick={() => sessionMutation.mutate(makePayload())}>세션 기준값 적재</button>
            <button onClick={() => openingMutation.mutate(makePayload())}>오프닝 1시간 생성</button>
          </div>
          <p className="status-line">
            {overviewQuery.isLoading || providerSessionQuery.isLoading
              ? "저장 상태를 조회 중입니다."
              : statusMessage}
          </p>
        </div>

        <div className="stats-wrap">
          <div className="badge-grid">
            <StatBadge label="과거 1분봉" value={formatNumber(overview?.historical_bar_count)} />
            <StatBadge label="오프닝 1분봉" value={formatNumber(overview?.opening_bar_count)} />
            <StatBadge label="세션 기준값" value={formatNumber(overview?.session_reference_count)} />
            <StatBadge label="종목 수" value={formatNumber(overview?.symbol_count)} tone="positive" />
          </div>
          <div className="overview-notes">
            <p>과거 1분봉 범위: {formatDate(overview?.historical_date_min)} ~ {formatDate(overview?.historical_date_max)}</p>
            <p>오프닝 1분봉 범위: {formatDate(overview?.opening_date_min)} ~ {formatDate(overview?.opening_date_max)}</p>
            <p>저장 종목: {overview?.available_symbols.join(", ") || "-"}</p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
