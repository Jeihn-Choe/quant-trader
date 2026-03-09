export interface MarketDataOverview {
  historical_bar_count: number;
  opening_bar_count: number;
  session_reference_count: number;
  symbol_count: number;
  historical_date_min: string | null;
  historical_date_max: string | null;
  opening_date_min: string | null;
  opening_date_max: string | null;
  available_symbols: string[];
}

export interface ProviderSession {
  provider: string;
  configured: boolean;
  authenticated: boolean;
  base_url: string | null;
  token_expires_at: string | null;
  message: string;
}

export interface DateRangePayload {
  date_from: string;
  date_to: string;
  symbols: string[];
  replace_existing?: boolean;
}

export interface CollectResponse {
  message: string;
  provider: string;
  symbols: string[];
  date_from: string;
  date_to: string;
  rows_written: number;
}

export interface BuildOpeningBarsResponse {
  message: string;
  symbols: string[];
  date_from: string;
  date_to: string;
  rows_written: number;
}

export interface SeedMockDataResponse {
  message: string;
  provider: string;
  symbols: string[];
  date_from: string;
  date_to: string;
  historical_minute_rows: number;
  session_reference_rows: number;
  opening_bar_rows: number;
}

export interface OrbScanRequest {
  date_from: string;
  date_to: string;
  symbols: string[];
  orb_window_minutes: number;
  breakout_buffer: number;
  gap_mode: "all" | "gap_up_only";
  gap_threshold_pct: number;
}

export interface OrbScanSummary {
  total_sessions: number;
  scanned_sessions: number;
  gap_up_sessions: number;
  breakout_sessions: number;
  breakout_rate: number;
}

export interface OrbScanResultRow {
  symbol: string;
  trade_date: string;
  prev_close: number | null;
  session_open: number | null;
  gap_pct: number | null;
  gap_up: boolean;
  orb_window_minutes: number;
  orb_high: number | null;
  orb_low: number | null;
  breakout: boolean;
  first_breakout_time: string | null;
  first_breakout_price: number | null;
  breakout_excess: number | null;
  cutoff_price: number | null;
  cutoff_above_orb_high: boolean | null;
}

export interface OrbScanRunResponse {
  run_id: string;
  created_at: string;
  date_from: string;
  date_to: string;
  orb_window_minutes: number;
  breakout_buffer: number;
  gap_mode: "all" | "gap_up_only";
  gap_threshold_pct: number;
  requested_symbols: string[];
  summary: OrbScanSummary;
  results: OrbScanResultRow[];
}

export interface OrbScanRunListItem {
  run_id: string;
  created_at: string;
  date_from: string;
  date_to: string;
  orb_window_minutes: number;
  gap_mode: string;
  breakout_sessions: number;
}
