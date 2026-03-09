from __future__ import annotations

from datetime import date

from research_bot.application.ports.market_data_provider import MarketDataProvider
from research_bot.domain.market.entities import MinuteBar, SessionReference
from research_bot.infrastructure.providers.kis_client import KisClient


class KisMarketDataProvider(MarketDataProvider):
    def __init__(self, client: KisClient) -> None:
        self.client = client

    @property
    def name(self) -> str:
        return "kis"

    def get_historical_minute_bars(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[MinuteBar]:
        raise NotImplementedError(
            "한국투자증권 과거 1분봉 적재 로직은 인증 정보를 받은 뒤 구현해야 합니다."
        )

    def get_session_references(
        self,
        symbols: list[str],
        date_from: date,
        date_to: date,
    ) -> list[SessionReference]:
        raise NotImplementedError(
            "한국투자증권 전일 종가/당일 시가 적재 로직은 인증 정보를 받은 뒤 구현해야 합니다."
        )
