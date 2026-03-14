using QuantTrader.Strategies.Abstractions;

namespace QuantTrader.Strategies.Orb;

/// <summary>
/// ORB (Opening Range Breakout) 전략의 메인 클래스입니다.
/// </summary>
public class OrbStrategy : IStrategy
{
    public string Name => "ORB";
    public string Version => "1.0.0";

    // 1. 대상주 선정 필터 (갭 상승률, 오프닝 거래량 등)
    public List<IStrategyFilter> Filters { get; } = new();

    // 2. 매수 진입 규칙 (돌파 시점 등)
    public IEntryRule? EntryRule { get; set; }

    // 3. 손절/익절 청산 규칙
    public List<IExitRule> ExitRules { get; } = new();

    // IStrategy 인터페이스 요구사항을 List에서 IEnumerable로 변환하여 제공
    IEnumerable<IStrategyFilter> IStrategy.Filters => Filters;
    IEntryRule IStrategy.EntryRule => EntryRule ?? throw new InvalidOperationException("EntryRule must be set.");
    IEnumerable<IExitRule> IStrategy.ExitRules => ExitRules;
}
