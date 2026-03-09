import axios from "axios";

import type {
  BuildOpeningBarsResponse,
  CollectResponse,
  DateRangePayload,
  MarketDataOverview,
  OrbScanRequest,
  OrbScanRunListItem,
  OrbScanRunResponse,
  ProviderSession,
  SeedMockDataResponse
} from "./types";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api",
  timeout: 30_000
});

export async function getMarketDataOverview(): Promise<MarketDataOverview> {
  const response = await apiClient.get<MarketDataOverview>("/market-data/overview");
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

export async function seedMockData(payload: DateRangePayload): Promise<SeedMockDataResponse> {
  const response = await apiClient.post<SeedMockDataResponse>("/market-data/mock/seed", payload);
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

export async function collectSessionReferences(
  payload: DateRangePayload
): Promise<CollectResponse> {
  const response = await apiClient.post<CollectResponse>(
    "/market-data/session-references",
    payload
  );
  return response.data;
}

export async function buildOpeningBars(
  payload: DateRangePayload
): Promise<BuildOpeningBarsResponse> {
  const response = await apiClient.post<BuildOpeningBarsResponse>(
    "/market-data/opening-bars/build",
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
