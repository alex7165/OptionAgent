from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.analysis.daily_trade_window_selector import DailyTradeWindowSelector
from app.analysis.earnings_crush_analyzer_factory import EarningsCrushAnalyzerFactory
from app.analysis.trade_exporter import TradeExporter
from app.marketdata.savvytrader_earnings_calendar_provider import (
    SavvyTraderEarningsCalendarProvider,
)
from app.run_earnings_test import (
    build_market_data,
    format_candidate,
    format_selection_details,
)


def run_daily(
    trade_date: date,
    output_path: Path,
    calendar_provider=None,
    market_data=None,
    analyzer_factory=None,
):
    load_dotenv()

    selector = DailyTradeWindowSelector()
    next_date = selector.next_trading_weekday(trade_date)
    calendar_provider = calendar_provider or SavvyTraderEarningsCalendarProvider()

    # SavvyTrader's end boundary is treated conservatively as exclusive.
    # Request one extra calendar day; the selector still accepts only the two
    # exact earnings windows required for this trade date.
    query_end = next_date + timedelta(days=1)
    events = calendar_provider.get_events(trade_date, query_end)
    window = selector.select(events, trade_date)

    print(f"Trade-Datum: {trade_date.isoformat()}")
    print(
        "Fenster: "
        f"{trade_date.isoformat()} after market close + "
        f"{window.next_trading_date.isoformat()} before market open"
    )
    print(f"Kalender-Rohdaten: {len(events)}")
    print(f"Passende Earnings: {len(window.events)}")

    if not window.events:
        timings = Counter(
            (event.timing or "<ohne Timing>")
            for event in events
            if event.report_date in {trade_date, next_date}
        )
        if timings:
            print("Gefundene Timing-Werte im relevanten Datumsbereich:")
            for timing, count in sorted(timings.items()):
                print(f"  {timing}: {count}")
        else:
            print("Keine Kalendereinträge für die beiden relevanten Tage gefunden.")

    market_data = market_data or build_market_data()
    analyzer_factory = analyzer_factory or EarningsCrushAnalyzerFactory()
    analyzer = analyzer_factory.create(market_data)
    historical_enabled = (
        getattr(analyzer, "historical_inputs_loader", None) is not None
    )
    print(
        "Historische Auswahl: "
        + ("aktiv" if historical_enabled else "nicht aktiv")
    )
    candidates = []
    technical_errors: list[tuple[str, str]] = []

    for event in window.events:
        try:
            event_candidates = analyzer.create_candidates([event])
        except Exception as exc:  # One bad symbol must not stop the day.
            reason = _technical_error_reason(exc)
            technical_errors.append((event.symbol, reason))
            print(
                f"{event.symbol:<6} TECHNISCHER FEHLER "
                f"Grund: {reason}"
            )
            continue

        candidates.extend(event_candidates)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    TradeExporter().export_excel(candidates, output_path)

    print(f"Excel-Export: {output_path}")
    print(f"Analysiert: {len(candidates)}")
    print(f"Technische Fehler: {len(technical_errors)}")
    print()

    for candidate in candidates:
        print(format_candidate(candidate))
        for detail in format_selection_details(candidate):
            print(detail)

    if technical_errors:
        print("Technische Fehler im Überblick:")
        for symbol, reason in technical_errors:
            print(f"  {symbol}: {reason}")

    return candidates


def _technical_error_reason(exc: Exception) -> str:
    response: Any | None = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)

    if status_code == 404:
        return "option_chain_not_available"

    message = str(exc).strip()
    if not message:
        return type(exc).__name__

    return f"{type(exc).__name__}: {message}"


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
