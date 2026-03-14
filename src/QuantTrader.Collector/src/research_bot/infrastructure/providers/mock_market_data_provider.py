from __future__ import annotations

from datetime import date, datetime, time, timedelta
from hashlib import sha256
import random

from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.domain.market.entities import MarketOpenSnapshot, MinuteBar
from research_bot.domain.orb.gap import calculate_gap_pct


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, default_symbols: list[str]) -> None:
        self.default_symbols = default_symbols

    @property
    def name(self) -> str:
        return "mock"

    def resolve_symbols(self, symbols: list[str]) -> list[str]:
        return symbols or self.default_symbols

    def get_symbol_name(self, symbol: str) -> str | None:
        return _symbol_name(symbol)

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows: list[MinuteBar] = []
        for symbol in symbols or self.default_symbols:
            rows.extend(self.get_symbol_historical_minute_bars(symbol, date_from, date_to))
        return rows

    def get_market_open_snapshots(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        rows: list[MarketOpenSnapshot] = []
        for symbol in symbols or self.default_symbols:
            rows.extend(self.get_symbol_market_open_snapshots(symbol, date_from, date_to))
        return rows

    def get_symbol_historical_minute_bars(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows: list[MinuteBar] = []
        for trade_date in _business_days(date_from, date_to):
            snapshot = _build_market_open_snapshot(symbol, trade_date)
            rows.extend(_build_session_bars(snapshot))
        return rows

    def get_symbol_market_open_snapshots(
        self,
        symbol: str,
        date_from: date,
        date_to: date,
    ) -> list[MarketOpenSnapshot]:
        return [
            _build_market_open_snapshot(symbol, trade_date)
            for trade_date in _business_days(date_from, date_to)
        ]

def _build_market_open_snapshot(symbol: str, trade_date: date) -> MarketOpenSnapshot:
    generator = random.Random(_seed(symbol, trade_date, "market-open"))
    prev_close = round(35000 + generator.random() * 110000, 2)
    gap_pct = round(generator.uniform(-0.025, 0.055), 4)
    market_open_price = round(prev_close * (1 + gap_pct), 2)
    return MarketOpenSnapshot(
        symbol=symbol,
        symbol_name=_symbol_name(symbol),
        trade_date=trade_date,
        prev_close=prev_close,
        market_open_price=market_open_price,
        gap_pct=calculate_gap_pct(prev_close, market_open_price),
    )


def _build_session_bars(snapshot: MarketOpenSnapshot) -> list[MinuteBar]:
    generator = random.Random(_seed(snapshot.symbol, snapshot.trade_date, "bars"))
    session_start = datetime.combine(snapshot.trade_date, time(9, 0))
    rows: list[MinuteBar] = []
    price = snapshot.market_open_price
    trend_bias = generator.uniform(-0.002, 0.018)
    breakout_bias = generator.random()

    for index in range(390):
        minute_ts = session_start + timedelta(minutes=index)
        intraday_drift = (index / 390.0) * trend_bias
        noise = generator.uniform(-0.0016, 0.0016)
        opening_impulse = 0.0
        if 6 <= index <= 18 and breakout_bias > 0.42:
            opening_impulse = generator.uniform(0.0008, 0.0045)
        anchor = snapshot.market_open_price * (1 + intraday_drift + noise + opening_impulse)

        open_price = price
        close = round(anchor, 2)
        high = round(max(open_price, close) * (1 + generator.uniform(0.0002, 0.0022)), 2)
        low = round(min(open_price, close) * (1 - generator.uniform(0.0002, 0.0020)), 2)
        volume = round(1500 + generator.random() * 8000 + max(0, 120 - index) * 25, 0)

        rows.append(
            MinuteBar(
                symbol=snapshot.symbol,
                symbol_name=snapshot.symbol_name,
                trade_date=snapshot.trade_date,
                minute_ts=minute_ts,
                open=round(open_price, 2),
                high=max(high, round(open_price, 2), close),
                low=min(low, round(open_price, 2), close),
                close=close,
                volume=volume,
            )
        )
        price = close
    return rows


def _business_days(date_from: date, date_to: date) -> list[date]:
    current = date_from
    rows: list[date] = []
    while current <= date_to:
        if current.weekday() < 5:
            rows.append(current)
        current += timedelta(days=1)
    return rows


def _seed(symbol: str, trade_date: date, salt: str) -> int:
    text = f"{symbol}-{trade_date.isoformat()}-{salt}"
    return int(sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def _symbol_name(symbol: str) -> str:
    names = {
        "005930": "삼성전자",
        "000660": "SK하이닉스",
        "035420": "NAVER",
        "051910": "LG화학",
        "105560": "KB금융",
        "068270": "셀트리온",
    }
    return names.get(symbol, symbol)
