namespace QuantTrader.Strategies.Abstractions;

public interface IEntryRule
{
    string Name { get; }
    bool ShouldEntry(object context);
}
