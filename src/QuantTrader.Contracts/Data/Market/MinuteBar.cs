namespace QuantTrader.Contracts.Data.Market;

/// <summary>
/// 1분 단위의 가격 데이터(분봉)를 나타냅니다.
/// </summary>
public readonly record struct MinuteBar
{
    /// <summary>
    /// 종목 코드 (예: 005930)
    /// </summary>
    public string Symbol { get; init; }

    /// <summary>
    /// 데이터의 기준 시간 (분 단위)
    /// </summary>
    public DateTime Timestamp { get; init; }

    /// <summary>
    /// 시가
    /// </summary>
    public double Open { get; init; }

    /// <summary>
    /// 고가
    /// </summary>
    public double High { get; init; }

    /// <summary>
    /// 저가
    /// </summary>
    public double Low { get; init; }

    /// <summary>
    /// 종가
    /// </summary>
    public double Close { get; init; }

    /// <summary>
    /// 해당 분의 거래량
    /// </summary>
    public double Volume { get; init; }

    public MinuteBar(string symbol, DateTime timestamp, double open, double high, double low, double close, double volume)
    {
        Symbol = symbol;
        Timestamp = timestamp;
        Open = open;
        High = high;
        Low = low;
        Close = close;
        Volume = volume;
    }
}
