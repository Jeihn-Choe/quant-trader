namespace QuantTrader.Strategies.Abstractions;

/// <summary>
/// 모든 전략이 구현해야 할 공통 인터페이스입니다.
/// </summary>
public interface IStrategy
{
    string Name { get; }
    string Version { get; }
    
    // 전략의 각 구성 요소를 반환합니다.
    IEnumerable<IStrategyFilter> Filters { get; }
    IEntryRule EntryRule { get; }
    IEnumerable<IExitRule> ExitRules { get; }
}
