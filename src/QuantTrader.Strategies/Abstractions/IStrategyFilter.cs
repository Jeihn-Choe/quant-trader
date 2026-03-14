namespace QuantTrader.Strategies.Abstractions;

public interface IStrategyFilter
{
    string Name { get; }
    bool IsMatch(object context); 
}
