from __future__ import annotations

from datetime import date, datetime, time, timedelta
from hashlib import sha256
import random

from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.domain.market.entities import MinuteBar, SessionReference
from research_bot.domain.orb.gap import calculate_gap_pct


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, default_symbols: list[str]) -> None:
        self.default_symbols = default_symbols

    @property
    def name(self) -> str:
        return "mock"

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        rows: list[MinuteBar] = []
        for trade_date in _business_days(date_from, date_to):
            for symbol in symbols or self.default_symbols:
                reference = _build_session_reference(symbol, trade_date)
                rows.extend(_build_session_bars(reference))
        return rows

    def get_session_references(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[SessionReference]:
        rows: list[SessionReference] = []
        for trade_date in _business_days(date_from, date_to):
            for symbol in symbols or self.default_symbols:
                rows.append(_build_session_reference(symbol, trade_date))
        return rows


def _build_session_reference(symbol: str, trade_date: date) -> SessionReference:
    generator = random.Random(_seed(symbol, trade_date, "session"))
    prev_close = round(35000 + generator.random() * 110000, 2)
    gap_pct = round(generator.uniform(-0.025, 0.055), 4)
    session_open = round(prev_close * (1 + gap_pct), 2)
    return SessionReference(
        symbol=symbol,
        trade_date=trade_date,
        prev_close=prev_close,
        session_open=session_open,
        gap_pct=calculate_gap_pct(prev_close, session_open),
    )


def _build_session_bars(reference: SessionReference) -> list[MinuteBar]:
    generator = random.Random(_seed(reference.symbol, reference.trade_date, "bars"))
    session_start = datetime.combine(reference.trade_date, time(9, 0))
    rows: list[MinuteBar] = []
    price = reference.session_open
    trend_bias = generator.uniform(-0.002, 0.018)
    breakout_bias = generator.random()

    for index in range(390):
        minute_ts = session_start + timedelta(minutes=index)
        intraday_drift = (index / 390.0) * trend_bias
        noise = generator.uniform(-0.0016, 0.0016)
        opening_impulse = 0.0
        if 6 <= index <= 18 and breakout_bias > 0.42:
            opening_impulse = generator.uniform(0.0008, 0.0045)
        anchor = reference.session_open * (1 + intraday_drift + noise + opening_impulse)

        open_price = price
        close = round(anchor, 2)
        high = round(max(open_price, close) * (1 + generator.uniform(0.0002, 0.0022)), 2)
        low = round(min(open_price, close) * (1 - generator.uniform(0.0002, 0.0020)), 2)
        volume = round(1500 + generator.random() * 8000 + max(0, 120 - index) * 25, 0)

        rows.append(
            MinuteBar(
                symbol=reference.symbol,
                trade_date=reference.trade_date,
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
