from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.analysis.daily_trade_window_selector import DailyTradeWindowSelector
from app.analysis.earnings_crush_analyzer_factory import EarningsCrushAnalyzerFactory
from app.analysis.trade_exporter import TradeExporter
from app.marketdata.savvytrader_earnings_calendar_provider import (
    SavvyTraderEarningsCalendarProvider,
)
from app.run_earnings_test import build_market_data, format_candidate, format_selection_details


def run_daily(
    trade_date: date,
    output_path: Path,
    calendar_provider=None,
    market_data=None,
    analyzer_factory=None,
):
    selector = DailyTradeWindowSelector()
    next_date = selector.next_trading_weekday(trade_date)
    calendar_provider = calendar_provider or SavvyTraderEarningsCalendarProvider()
    events = calendar_provider.get_events(trade_date, next_date)
    window = selector.select(events, trade_date)

    market_data = market_data or build_market_data()
    analyzer_factory = analyzer_factory or EarningsCrushAnalyzerFactory()
    analyzer = analyzer_factory.create(market_data)
    candidates = analyzer.create_candidates(list(window.events))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    TradeExporter().export_excel(candidates, output_path)

    print(f"Trade-Datum: {trade_date.isoformat()}")
    print(
        "Fenster: "
        f"{trade_date.isoformat()} after market close + "
        f"{window.next_trading_date.isoformat()} before market open"
    )
    print(f"Kandidaten: {len(window.events)}")
    print(f"Excel-Export: {output_path}")
    print()

    for candidate in candidates:
        print(format_candidate(candidate))
        for detail in format_selection_details(candidate):
            print(detail)

    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze today's after-market-close earnings and the next "
            "trading day's before-market-open earnings."
        )
    )
    parser.add_argument(
        "--trade-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Trade date in YYYY-MM-DD format. Default: today.",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output or Path("exports") / (
        f"daily_trades_{args.trade_date.isoformat()}.xlsx"
    )
    run_daily(args.trade_date, output)


if __name__ == "__main__":
    main()
