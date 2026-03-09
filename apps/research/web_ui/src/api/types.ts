export interface MarketDataOverview {
  historical_bar_count: number;
  market_open_snapshot_count: number;
  symbol_count: number;
  historical_date_min: string | null;
  historical_date_max: string | null;
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
  skipped: boolean;
}

export interface MarketDataDailySummaryRow {
  trade_date: string;
  symbol_count: number;
  historical_bar_count: number;
  market_open_snapshot_count: number;
  preview_symbols: string[];
}

export interface MarketDataSymbolSummaryRow {
  trade_date: string;
  symbol: string;
  symbol_name: string | null;
  minute_bar_count: number;
  session_open: number | null;
  session_high: number | null;
  session_low: number | null;
  session_close: number | null;
  total_volume: number | null;
  gap_pct: number | null;
}

export interface MinuteBarRow {
  symbol: string;
  symbol_name: string | null;
  trade_date: string;
  minute_ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface CollectAllMarketDataResponse {
  message: string;
  provider: string;
  symbols: string[];
  date_from: string;
  date_to: string;
  historical_minute_rows: number;
  market_open_snapshot_rows: number;
  historical_minute_skipped: boolean;
  market_open_snapshot_skipped: boolean;
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
  symbol_name: string | null;
  trade_date: string;
  prev_close: number | null;
  market_open_price: number | null;
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
