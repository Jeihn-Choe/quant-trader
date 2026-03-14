namespace QuantTrader.Strategies.Abstractions;

public interface IExitRule
{
    string Name { get; }
    bool ShouldExit(object context);
}
