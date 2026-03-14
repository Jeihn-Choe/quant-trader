using QuantTrader.Contracts.Data.Market;

namespace QuantTrader.Contracts.Interfaces;

/// <summary>
/// 시장 데이터를 조회하기 위한 데이터 공급자 인터페이스입니다.
/// </summary>
public interface IMarketDataProvider
{
    /// <summary>
    /// 특정 종목의 과거 분봉 데이터를 조회합니다.
    /// </summary>
    /// <param name="symbol">조회할 종목 코드</param>
    /// <param name="from">조회 시작 시점</param>
    /// <param name="to">조회 종료 시점</param>
    /// <returns>조회된 분봉 리스트</returns>
    Task<IEnumerable<MinuteBar>> GetMinuteBarsAsync(string symbol, DateTime from, DateTime to);

    /// <summary>
    /// 특정 날짜의 종목 시가 스냅샷(시가, 갭 정보 등)을 조회합니다.
    /// </summary>
    /// <param name="symbol">조회할 종목 코드</param>
    /// <param name="tradeDate">거래일</param>
    /// <returns>시가 스냅샷 정보 (없을 경우 null)</returns>
    Task<MarketOpenSnapshot?> GetOpenSnapshotAsync(string symbol, DateTime tradeDate);
}
