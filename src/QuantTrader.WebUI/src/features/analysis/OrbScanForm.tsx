import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { scanOrbBreakouts } from "../../api/client";
import type { OrbScanRequest, OrbScanRunResponse } from "../../api/types";
import { SectionCard } from "../../shared/components/SectionCard";
import { formatInputDate } from "../../shared/utils/format";

interface OrbScanFormProps {
  onCompleted: (result: OrbScanRunResponse) => void;
}

function defaultRange() {
  const today = new Date();
  const earlier = new Date();
  earlier.setDate(today.getDate() - 10);
  return {
    dateFrom: formatInputDate(earlier),
    dateTo: formatInputDate(today)
  };
}

export function OrbScanForm({ onCompleted }: OrbScanFormProps) {
  const queryClient = useQueryClient();
  const defaults = useMemo(() => defaultRange(), []);
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom);
  const [dateTo, setDateTo] = useState(defaults.dateTo);
  const [orbWindowMinutes, setOrbWindowMinutes] = useState(5);
  const [breakoutBuffer, setBreakoutBuffer] = useState(0);
  const [gapMode, setGapMode] = useState<"all" | "gap_up_only">("all");
  const [gapThresholdPct, setGapThresholdPct] = useState(0);
  const [symbolsText, setSymbolsText] = useState("");
  const [statusMessage, setStatusMessage] = useState("저장된 1분봉 원천 데이터 기준으로 ORB 스캔을 실행합니다.");

  const scanMutation = useMutation({
    mutationFn: (payload: OrbScanRequest) => scanOrbBreakouts(payload),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["orb-runs"] });
      setStatusMessage("ORB 스캔이 완료되었습니다.");
      onCompleted(result);
    },
    onError: (error: unknown) => {
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
        setStatusMessage(error.response.data.detail);
        return;
      }
      setStatusMessage(error instanceof Error ? error.message : "ORB 스캔 중 오류가 발생했습니다.");
    }
  });

  const submit = () => {
    scanMutation.mutate({
      date_from: dateFrom,
      date_to: dateTo,
      orb_window_minutes: orbWindowMinutes,
      breakout_buffer: breakoutBuffer,
      gap_mode: gapMode,
      gap_threshold_pct: gapThresholdPct / 100,
      symbols: symbolsText
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean)
    });
  };

  return (
    <SectionCard
      title="Analysis"
      subtitle="ORB 계산과 돌파 탐지를 실행합니다"
      accent="teal"
    >
      <div className="form-stack">
        <div className="field-grid">
          <label>
            <span>시작일</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label>
            <span>종료일</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label>
            <span>ORB 분</span>
            <select
              value={orbWindowMinutes}
              onChange={(event) => setOrbWindowMinutes(Number(event.target.value))}
            >
              <option value={3}>3분</option>
              <option value={5}>5분</option>
              <option value={10}>10분</option>
              <option value={15}>15분</option>
            </select>
          </label>
          <label>
            <span>돌파 버퍼</span>
            <input
              type="number"
              step="0.01"
              value={breakoutBuffer}
              onChange={(event) => setBreakoutBuffer(Number(event.target.value))}
            />
          </label>
          <label>
            <span>갭 모드</span>
            <select
              value={gapMode}
              onChange={(event) => setGapMode(event.target.value as "all" | "gap_up_only")}
            >
              <option value="all">전체 종목</option>
              <option value="gap_up_only">갭상승만</option>
            </select>
          </label>
          <label>
            <span>갭 임계값(%)</span>
            <input
              type="number"
              step="0.1"
              value={gapThresholdPct}
              onChange={(event) => setGapThresholdPct(Number(event.target.value))}
            />
          </label>
        </div>
        <label className="field-wide">
          <span>종목 제한</span>
          <textarea
            rows={2}
            value={symbolsText}
            onChange={(event) => setSymbolsText(event.target.value)}
            placeholder="비워두면 저장된 전체 종목을 대상으로 실행"
          />
        </label>
        <div className="action-row">
          <button className="primary-button" onClick={submit}>
            ORB 스캔 실행
          </button>
        </div>
        <p className="status-line">
          {scanMutation.isPending ? "ORB 스캔을 실행 중입니다." : statusMessage}
        </p>
      </div>
    </SectionCard>
  );
}
