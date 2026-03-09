from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen
import zipfile

from research_bot.infrastructure.providers.kis_client import KisClientError


@dataclass(frozen=True)
class MarketMasterSource:
    market: str
    zip_url: str
    zip_name: str
    mst_name: str
    trailer_length: int


MASTER_SOURCES: dict[str, MarketMasterSource] = {
    "KOSPI": MarketMasterSource(
        market="KOSPI",
        zip_url="https://new.real.download.dws.co.kr/common/master/kospi_code.mst.zip",
        zip_name="kospi_code.zip",
        mst_name="kospi_code.mst",
        trailer_length=228,
    ),
    "KOSDAQ": MarketMasterSource(
        market="KOSDAQ",
        zip_url="https://new.real.download.dws.co.kr/common/master/kosdaq_code.mst.zip",
        zip_name="kosdaq_code.zip",
        mst_name="kosdaq_code.mst",
        trailer_length=222,
    ),
}


class KisUniverseResolver:
    def __init__(self, data_dir: Path, markets: list[str]) -> None:
        self.data_dir = data_dir
        self.markets = markets
        self.master_dir = data_dir / "masters"
        self._cached_symbols: list[str] | None = None
        self._cached_symbol_names: dict[str, str] | None = None

    def resolve_symbols(self, requested_symbols: list[str]) -> list[str]:
        if requested_symbols:
            return _normalize_symbols(requested_symbols)
        self._ensure_cache()
        if not self._cached_symbols:
            raise KisClientError("전종목 universe를 구성하지 못했습니다.")
        return self._cached_symbols

    def get_symbol_name(self, symbol: str) -> str | None:
        self._ensure_cache()
        if self._cached_symbol_names is None:
            return None
        return self._cached_symbol_names.get(symbol.strip())

    def _ensure_cache(self) -> None:
        if self._cached_symbols is not None and self._cached_symbol_names is not None:
            return

        symbol_names: dict[str, str] = {}
        for market in self.markets:
            source = MASTER_SOURCES.get(market)
            if source is None:
                continue
            for symbol, symbol_name in self._load_market_entries(source):
                if symbol not in symbol_names:
                    symbol_names[symbol] = symbol_name

        self._cached_symbols = _normalize_symbols(symbol_names.keys())
        self._cached_symbol_names = symbol_names

    def _load_market_entries(self, source: MarketMasterSource) -> list[tuple[str, str]]:
        self.master_dir.mkdir(parents=True, exist_ok=True)
        mst_path = self.master_dir / source.mst_name
        if not mst_path.exists():
            self._download_master(source)
        if not mst_path.exists():
            raise KisClientError(f"{source.market} 마스터 파일을 찾지 못했습니다.")

        entries: list[tuple[str, str]] = []
        with mst_path.open("r", encoding="cp949", errors="ignore") as handle:
            for raw_line in handle:
                if len(raw_line) <= source.trailer_length:
                    continue
                body = raw_line[: len(raw_line) - source.trailer_length]
                code = body[:9].rstrip()
                name = body[21:].strip()
                if not code:
                    continue
                entries.append((code, name))
        return entries

    def _download_master(self, source: MarketMasterSource) -> None:
        zip_path = self.master_dir / source.zip_name
        try:
            with urlopen(source.zip_url) as response:
                zip_path.write_bytes(response.read())
            with zipfile.ZipFile(zip_path) as zipped:
                zipped.extractall(self.master_dir)
        except Exception as error:  # noqa: BLE001
            raise KisClientError(
                f"{source.market} 종목 마스터 파일을 내려받지 못했습니다."
            ) from error
        finally:
            if zip_path.exists():
                zip_path.unlink()


def _normalize_symbols(symbols: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for symbol in symbols:
        code = symbol.strip()
        if not code or code in seen:
            continue
        seen.add(code)
        rows.append(code)
    return rows
