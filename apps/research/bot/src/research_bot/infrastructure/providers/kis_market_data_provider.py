from __future__ import annotations

from datetime import date, datetime, time, timedelta

from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar
from research_bot.infrastructure.providers.kis_client import KisClient
from research_bot.infrastructure.providers.kis_universe_resolver import KisUniverseResolver
from research_bot.domain.orb.gap import calculate_gap_pct


MINUTE_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice"
MINUTE_CHART_TR_ID = "FHKST03010230"
DAILY_CHART_PATH = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
DAILY_CHART_TR_ID = "FHKST03010100"


class KisMarketDataProvider(MarketDataProvider):
    def __init__(self, client: KisClient, universe_resolver: KisUniverseResolver) -> None:
        self.client = client
        self.universe_resolver = universe_resolver

    @property
    def name(self) -> str:
        return "kis"

    def resolve_symbols(self, symbols: list[str]) -> list[str]:
        return self.universe_resolver.resolve_symbols(symbols)

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows: list[MinuteBar] = []
        for symbol in symbols:
            rows.extend(
                self._collect_symbol_minute_bars(
                    symbol=symbol,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
        rows.sort(key=lambda item: (item.trade_date, item.symbol, item.minute_ts))
        return rows

    def get_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        rows: list[MarketOpenSnapshot] = []
        for symbol in symbols:
            rows.extend(
                self._collect_symbol_market_open_snapshots(
                    symbol=symbol,
                    date_from=date_from,
                    date_to=date_to,
                )
            )
        rows.sort(key=lambda item: (item.trade_date, item.symbol))
        return rows

    def _collect_symbol_minute_bars(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        collected: dict[tuple[date, datetime], MinuteBar] = {}
        seen_cursors: set[tuple[str, str]] = set()
        cursor_at = datetime.combine(date_to, time(15, 30))
        symbol_name = self.universe_resolver.get_symbol_name(symbol)

        while cursor_at.date() >= date_from:
            cursor_key = (cursor_at.strftime("%Y%m%d"), cursor_at.strftime("%H%M%S"))
            if cursor_key in seen_cursors:
                break
            seen_cursors.add(cursor_key)

            payload = self.client.request(
                MINUTE_CHART_PATH,
                params={
                    "FID_COND_MRKT_DIV_CODE": "J",
                    "FID_INPUT_ISCD": symbol,
                    "FID_INPUT_DATE_1": cursor_at.strftime("%Y%m%d"),
                    "FID_INPUT_HOUR_1": cursor_at.strftime("%H%M%S"),
                    "FID_PW_DATA_INCU_YN": "Y",
                    "FID_FAKE_TICK_INCU_YN": "",
                },
                tr_id=MINUTE_CHART_TR_ID,
            )
            chunk = _parse_minute_rows(symbol, symbol_name, payload.get("output2", []))
            if not chunk:
                break

            for row in chunk:
                if date_from <= row.trade_date <= date_to:
                    collected[(row.trade_date, row.minute_ts)] = row

            oldest_bar = min(chunk, key=lambda item: item.minute_ts)
            next_cursor_at = oldest_bar.minute_ts - timedelta(minutes=1)
            if next_cursor_at >= cursor_at:
                break
            cursor_at = next_cursor_at

        return sorted(collected.values(), key=lambda item: item.minute_ts)

    def _collect_symbol_market_open_snapshots(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        symbol_name = self.universe_resolver.get_symbol_name(symbol)
        request_start = date_from - timedelta(days=14)
        payload = self.client.request(
            DAILY_CHART_PATH,
            params={
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": request_start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": date_to.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": "D",
                "FID_ORG_ADJ_PRC": "0",
            },
            tr_id=DAILY_CHART_TR_ID,
        )
        daily_rows = _parse_daily_rows(payload.get("output2", []))
        if not daily_rows:
            return []

        snapshot_rows: list[MarketOpenSnapshot] = []
        previous_close: float | None = None
        for trade_date, market_open_price, session_close in daily_rows:
            if previous_close is not None and date_from <= trade_date <= date_to:
                snapshot_rows.append(
                    MarketOpenSnapshot(
                        symbol=symbol,
                        symbol_name=symbol_name,
                        trade_date=trade_date,
                        prev_close=previous_close,
                        market_open_price=market_open_price,
                        gap_pct=calculate_gap_pct(previous_close, market_open_price),
                    )
                )
            previous_close = session_close
        return snapshot_rows


def _parse_minute_rows(
    symbol: str,
    symbol_name: str | None,
    payload: object,
) -> list[MinuteBar]:
    if not isinstance(payload, list):
        return []

    rows: list[MinuteBar] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        trade_date_text = str(item.get("stck_bsop_date", "")).strip()
        time_text = str(item.get("stck_cntg_hour", "")).strip()
        if len(trade_date_text) != 8 or len(time_text) != 6:
            continue

        trade_date = datetime.strptime(trade_date_text, "%Y%m%d").date()
        minute_ts = datetime.strptime(
            f"{trade_date_text}{time_text}",
            "%Y%m%d%H%M%S",
        )
        rows.append(
            MinuteBar(
                symbol=symbol,
                symbol_name=symbol_name,
                trade_date=trade_date,
                minute_ts=minute_ts,
                open=_to_float(item.get("stck_oprc")),
                high=_to_float(item.get("stck_hgpr")),
                low=_to_float(item.get("stck_lwpr")),
                close=_to_float(item.get("stck_prpr")),
                volume=_to_float(item.get("cntg_vol")),
            )
        )
    rows.sort(key=lambda item: item.minute_ts)
    return rows


def _parse_daily_rows(payload: object) -> list[tuple[date, float, float]]:
    if not isinstance(payload, list):
        return []

    rows: list[tuple[date, float, float]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        trade_date_text = str(item.get("stck_bsop_date", "")).strip()
        if len(trade_date_text) != 8:
            continue
        rows.append(
            (
                datetime.strptime(trade_date_text, "%Y%m%d").date(),
                _to_float(item.get("stck_oprc")),
                _to_float(item.get("stck_clpr")),
            )
        )
    rows.sort(key=lambda item: item[0])
    return rows


def _to_float(value: object) -> float:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return 0.0
    return float(text)
