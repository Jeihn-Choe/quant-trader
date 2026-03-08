from __future__ import annotations

from datetime import date, datetime, time, timedelta
import unittest

from quant_trader.backtest.engine import OrbBacktestEngine
from quant_trader.config import AppConfig, FileConfig, SessionConfig, StrategyConfig
from quant_trader.models import MinuteBar, PriceTick, SessionData


class OrbBacktestEngineTests(unittest.TestCase):
    def test_gap_up_session_produces_breakout_record(self) -> None:
        trade_date = date(2026, 3, 9)
        minute_bars = self._build_minute_bars(trade_date)
        ticks = self._build_ticks(trade_date)

        config = AppConfig(
            files=FileConfig(
                minute_bar_csv=self._path("minute.csv"),
                tick_csv=self._path("tick.csv"),
                output_csv=self._path("output.csv"),
            ),
            session=SessionConfig(
                market_open=time(9, 0),
                analysis_cutoff=time(10, 0),
            ),
            strategy=StrategyConfig(
                min_gap_pct=0.0,
                orb_windows=(3,),
                confirmation_windows=(10, 30, 60),
                breakout_buffer=0.0,
            ),
        )
        session = SessionData(
            symbol="005930",
            trade_date=trade_date,
            prev_close=100.0,
            session_open=100.5,
            minute_bars=minute_bars,
            ticks=ticks,
        )

        records = OrbBacktestEngine(config).run([session])

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertTrue(record.gap_up)
        self.assertTrue(record.breakout)
        self.assertEqual(record.orb_high, 101.0)
        self.assertEqual(record.first_breakout_time, datetime(2026, 3, 9, 9, 3, 5))
        self.assertEqual(record.confirmations, {10: True, 30: True, 60: True})
        self.assertTrue(record.cutoff_above_orb_high)
        self.assertIsNotNone(record.retention_ratio)
        self.assertGreater(record.retention_ratio or 0.0, 0.9)

    @staticmethod
    def _build_minute_bars(trade_date: date) -> tuple[MinuteBar, ...]:
        bars: list[MinuteBar] = []
        session_start = datetime.combine(trade_date, time(9, 0))

        seed = [
            (100.5, 100.8, 100.4, 100.6),
            (100.6, 100.9, 100.5, 100.7),
            (100.7, 101.0, 100.6, 100.8),
            (100.8, 101.2, 100.8, 101.1),
        ]

        for index, (open_price, high, low, close) in enumerate(seed):
            bars.append(
                MinuteBar(
                    symbol="005930",
                    timestamp=session_start + timedelta(minutes=index),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=1000.0 + index,
                    prev_close=100.0,
                )
            )

        for index in range(4, 61):
            bars.append(
                MinuteBar(
                    symbol="005930",
                    timestamp=session_start + timedelta(minutes=index),
                    open=101.1,
                    high=101.4,
                    low=101.0,
                    close=101.2,
                    volume=1000.0 + index,
                    prev_close=100.0,
                )
            )

        return tuple(bars)

    @staticmethod
    def _build_ticks(trade_date: date) -> tuple[PriceTick, ...]:
        ticks = [
            PriceTick("005930", datetime(2026, 3, 9, 9, 3, 5), 101.05, 10.0),
            PriceTick("005930", datetime(2026, 3, 9, 9, 3, 15), 101.08, 12.0),
            PriceTick("005930", datetime(2026, 3, 9, 9, 3, 35), 101.10, 8.0),
            PriceTick("005930", datetime(2026, 3, 9, 9, 4, 5), 101.12, 9.0),
        ]

        for minute in range(5, 60):
            ticks.append(
                PriceTick(
                    "005930",
                    datetime.combine(trade_date, time(9, minute % 60, 5))
                    if minute < 60
                    else datetime.combine(trade_date, time(10, 0, 5)),
                    101.15,
                    5.0,
                )
            )

        ticks.append(PriceTick("005930", datetime(2026, 3, 9, 10, 0, 0), 101.2, 5.0))
        return tuple(ticks)

    @staticmethod
    def _path(name: str):
        from pathlib import Path

        return Path(name)
