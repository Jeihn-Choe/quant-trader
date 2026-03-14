namespace QuantTrader.Contracts.Common.Enums;

/// <summary>
/// 자산 종목의 유형을 나타냅니다.
/// </summary>
public enum SecurityType
{
    /// <summary>
    /// 일반 주식
    /// </summary>
    Stock,

    /// <summary>
    /// 상장지수펀드 (ETF)
    /// </summary>
    ETF,

    /// <summary>
    /// 상장지수증권 (ETN)
    /// </summary>
    ETN,

    /// <summary>
    /// 선물
    /// </summary>
    Future,

    /// <summary>
    /// 옵션
    /// </summary>
    Option
}
