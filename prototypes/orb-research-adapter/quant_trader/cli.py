from __future__ import annotations

import argparse
from pathlib import Path

from .backtest.engine import OrbBacktestEngine
from .config import load_config
from .io.csv_loader import load_sessions
from .io.result_writer import write_results
from .ui.console import print_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ORB research backtest.")
    parser.add_argument(
        "--config",
        default="configs/orb_research.toml",
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the console summary.",
    )
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    sessions = load_sessions(config.files.minute_bar_csv, config.files.tick_csv)
    engine = OrbBacktestEngine(config)
    records = engine.run(sessions)
    write_results(config.files.output_csv, records, config.strategy.confirmation_windows)

    if not args.quiet:
        print_summary(records, config.files.output_csv)

    return 0
