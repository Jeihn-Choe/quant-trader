namespace QuantTrader.Contracts.Data.Market;

/// <summary>
/// 장 시작 시점의 시가 및 갭 정보를 담은 데이터 모델입니다.
/// 1차 종목 필터링(갭 상승률 등)의 기준 데이터로 사용됩니다.
/// </summary>
public readonly record struct MarketOpenSnapshot
{
    /// <summary>
    /// 종목 코드 (예: 005930)
    /// </summary>
    public string Symbol { get; init; }

    /// <summary>
    /// 해당 스냅샷 데이터의 기준 거래일
    /// </summary>
    public DateTime TradeDate { get; init; }

    /// <summary>
    /// 전일 종가 (수정 주가 기준 권장)
    /// </summary>
    public double PrevClose { get; init; }

    /// <summary>
    /// 당일 시가 (장 시작 시점의 첫 체결가)
    /// </summary>
    public double OpenPrice { get; init; }

    /// <summary>
    /// 전일 종가 대비 시가의 갭 상승률 (단위: %, 예: 5.5)
    /// </summary>
    public double GapPct { get; init; }

    /// <summary>
    /// <see cref="MarketOpenSnapshot"/> 구조체의 새 인스턴스를 초기화합니다.
    /// </summary>
    /// <param name="symbol">종목 코드</param>
    /// <param name="tradeDate">거래일</param>
    /// <param name="prevClose">전일 종가</param>
    /// <param name="openPrice">당일 시가</param>
    /// <param name="gap_pct">갭 상승률 (%)</param>
    public MarketOpenSnapshot(string symbol, DateTime tradeDate, double prevClose, double openPrice, double gap_pct)
    {
        Symbol = symbol;
        TradeDate = tradeDate;
        PrevClose = prevClose;
        OpenPrice = openPrice;
        GapPct = gap_pct;
    }
}
