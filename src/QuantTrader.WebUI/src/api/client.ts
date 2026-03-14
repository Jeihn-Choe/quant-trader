import axios from "axios";

import type {
  CollectResponse,
  DateRangePayload,
  FullFetchJobStatus,
  MarketDataDailySummaryRow,
  MarketDataSymbolSummaryRow,
  MarketDataOverview,
  MinuteBarRow,
  OrbScanRequest,
  OrbScanRunListItem,
  OrbScanRunResponse,
  ProviderSession
} from "./types";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api",
  timeout: 30_000
});

export async function getMarketDataOverview(): Promise<MarketDataOverview> {
  const response = await apiClient.get<MarketDataOverview>("/market-data/overview");
  return response.data;
}

export async function getMarketDataDailyGrid(
  payload: DateRangePayload
): Promise<MarketDataDailySummaryRow[]> {
  const response = await apiClient.get<MarketDataDailySummaryRow[]>("/market-data/daily-grid", {
    params: {
      date_from: payload.date_from,
      date_to: payload.date_to,
      symbols: payload.symbols.join(",")
    }
  });
  return response.data;
}

export async function getMarketDataDaySymbols(params: {
  trade_date: string;
  symbols: string[];
}): Promise<MarketDataSymbolSummaryRow[]> {
  const response = await apiClient.get<MarketDataSymbolSummaryRow[]>("/market-data/day-symbols", {
    params: {
      trade_date: params.trade_date,
      symbols: params.symbols.join(",")
    }
  });
  return response.data;
}

export async function getMarketDataMinuteBars(params: {
  trade_date: string;
  symbol: string;
}): Promise<MinuteBarRow[]> {
  const response = await apiClient.get<MinuteBarRow[]>(
    `/market-data/day-symbols/${params.symbol}/minute-bars`,
    {
      params: {
        trade_date: params.trade_date
      }
    }
  );
  return response.data;
}

export async function getProviderSession(): Promise<ProviderSession> {
  const response = await apiClient.get<ProviderSession>("/market-data/provider-session");
  return response.data;
}

export async function refreshProviderSession(): Promise<ProviderSession> {
  const response = await apiClient.post<ProviderSession>("/market-data/provider-session/refresh");
  return response.data;
}

export async function startFullFetchJob(
  payload: DateRangePayload
): Promise<FullFetchJobStatus> {
  const response = await apiClient.post<FullFetchJobStatus>(
    "/market-data/full-fetch",
    payload
  );
  return response.data;
}

export async function getFullFetchJob(jobId: string): Promise<FullFetchJobStatus> {
  const response = await apiClient.get<FullFetchJobStatus>(`/market-data/full-fetch/jobs/${jobId}`);
  return response.data;
}

export async function collectHistoricalMinuteBars(
  payload: DateRangePayload
): Promise<CollectResponse> {
  const response = await apiClient.post<CollectResponse>(
    "/market-data/historical-minute-bars",
    payload
  );
  return response.data;
}

export async function collectMarketOpenSnapshots(
  payload: DateRangePayload
): Promise<CollectResponse> {
  const response = await apiClient.post<CollectResponse>(
    "/market-data/market-open-snapshots",
    payload
  );
  return response.data;
}

export async function scanOrbBreakouts(
  payload: OrbScanRequest
): Promise<OrbScanRunResponse> {
  const response = await apiClient.post<OrbScanRunResponse>("/analysis/orb-scans", payload);
  return response.data;
}

export async function listOrbScans(): Promise<OrbScanRunListItem[]> {
  const response = await apiClient.get<OrbScanRunListItem[]>("/analysis/orb-scans");
  return response.data;
}

export async function getOrbScan(runId: string): Promise<OrbScanRunResponse> {
  const response = await apiClient.get<OrbScanRunResponse>(`/analysis/orb-scans/${runId}`);
  return response.data;
}
