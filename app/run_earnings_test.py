from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from app.analysis.earnings_crush_analyzer_factory import (
    EarningsCrushAnalyzerFactory,
)
from app.analysis.strategy_selector import StrikeSelectionSource
from app.analysis.trade_exporter import TradeExporter
from app.marketdata.models import EarningsEvent
from app.marketdata.service import MarketDataService

DEFAULT_SYMBOLS = ("C", "GS", "JPM", "BAC", "WFC", "FAST", "ERIC", "ANGO")


def build_market_data() -> MarketDataService:
    from app.marketdata.dummy_earnings_provider import DummyEarningsProvider
    from app.marketdata.yahoo_provider import YahooPriceProvider

    return MarketDataService(
        price_provider=YahooPriceProvider(),
        earnings_provider=DummyEarningsProvider(),
    )


def build_events(
    symbols: Iterable[str],
    report_date: date,
) -> list[EarningsEvent]:
    return [
        EarningsEvent(
            symbol=symbol.strip().upper(),
            report_date=report_date,
            timing="before market open",
            source="manual_batch_test",
        )
        for symbol in symbols
        if symbol.strip()
    ]


def candidate_status(candidate) -> tuple[str, str]:
    if candidate.failed_rules:
        return "AUSGESCHLOSSEN", ", ".join(candidate.failed_rules)

    if candidate.strike_selection is None:
        return "AUSGESCHLOSSEN", "missing_strike_selection"

    return "GEEIGNET", "-"


def format_candidate(candidate) -> str:
    status, reason = candidate_status(candidate)
    symbol = candidate.earnings_event.symbol

    if candidate.snapshot is None or candidate.snapshot.quote is None:
        return f"{symbol:<6} {status:<14} Kurs: -       Grund: {reason}"

    price = candidate.snapshot.quote.price
    selection = candidate.strike_selection

    if selection is None:
        return (
            f"{symbol:<6} {status:<14} Kurs: {price:>8.2f}  "
            f"Grund: {reason}"
        )

    put_percent = (selection.put.strike / price - 1) * 100
    call_percent = (selection.call.strike / price - 1) * 100

    return (
        f"{symbol:<6} {status:<14} Kurs: {price:>8.2f}  "
        f"Put: {selection.put.strike:>8.2f} ({put_percent:>6.2f} %)  "
        f"Call: {selection.call.strike:>8.2f} ({call_percent:>6.2f} %)  "
        f"Grund: {reason}"
    )



def format_selection_details(candidate) -> list[str]:
    report = getattr(candidate, "decision_report", None)
    if report is None:
        source = getattr(candidate, "strike_selection_source", None)
        if source is None:
            return []
        source_text = (
            "Historisch"
            if source is StrikeSelectionSource.HISTORICAL
            else "Expected-Move-Fallback"
        )
        return [f"      Auswahlquelle: {source_text}"]

    source_text = (
        "Historisch"
        if report.selection_source is StrikeSelectionSource.HISTORICAL
        else "Expected-Move-Fallback"
    )
    lines = [
        "      Aktuelle Volatilität:",
        (
            "        IV Rank: "
            f"{report.iv_rank if report.iv_rank is not None else '-'}"
        ),
        (
            "        IV Percentile: "
            f"{report.iv_percentile if report.iv_percentile is not None else '-'}"
        ),
        "        Quelle: Barchart",
        "      Historische Earnings-Analyse:",
    ]

    historical_error = getattr(candidate, "historical_analysis_error", None)
    if historical_error:
        lines.extend([
            "        Status: nicht verfügbar; Expected-Move-Fallback aktiv",
            f"        Fehler: {historical_error}",
            "        Quelle: Earnings API + PriceHistoryProvider",
        ])
    elif report.historical_sample_size is None:
        lines.extend([
            "        Stichprobe: keine historischen Daten",
            "        Quelle: Earnings API + PriceHistoryProvider",
        ])
    else:
        lines.extend([
            f"        Stichprobe: {report.historical_sample_size}",
            "        Quelle: Earnings API + PriceHistoryProvider",
        ])

    lines.extend([
        f"      Strike-Auswahl: {source_text}",
        (
            "        Quelle: Historie + aktuelle Volatilität"
            if report.historical_sample_size is not None
            else "        Quelle: Expected Move + aktuelle Volatilität"
        ),
        (
            "      Trade Score: "
            f"{report.trade_score.total}/100 "
            "("
            f"Markt {report.trade_score.market_component:.1f}/35, "
            f"Historisches Risiko "
            f"{report.trade_score.historical_risk_component:.1f}/25, "
            f"Stichprobe "
            f"{report.trade_score.historical_sample_component:.1f}/10, "
            f"Liquidität "
            f"{report.trade_score.liquidity_component:.1f}/30"
            ")"
        ),
    ])

    if (
        report.initial_put_strike is not None
        and report.initial_call_strike is not None
    ):
        lines.append(
            "      Vor Liquidität: "
            f"Put {report.initial_put_strike:g}, "
            f"Call {report.initial_call_strike:g}"
        )

    if (
        report.final_put_strike is not None
        and report.final_call_strike is not None
    ):
        lines.append(
            "      Nach Liquidität: "
            f"Put {report.final_put_strike:g}, "
            f"Call {report.final_call_strike:g}"
        )

    if report.liquidity_optimization_reason:
        lines.append(
            "      Optimierung: "
            f"{report.liquidity_optimization_reason}"
        )

    lines.append(
        "      Aktueller Expected Move: "
        f"±{report.expected_move_percent:.2f} %"
    )

    if report.historical_sample_size is None:
        return lines

    lines.extend(
        [
            (
                "      Exit: Handelstag "
                f"{report.exit_trading_day_index}; "
                "Historische Fälle: "
                f"{report.historical_sample_size}"
            ),
            (
                "      Historische Schlussbewegung bis Exit: "
                f"Ø {report.historical_average_abs_close_move_percent:.2f} %, "
                f"Median {report.historical_median_abs_close_move_percent:.2f} %, "
                f"Max {report.historical_max_abs_close_move_percent:.2f} %"
            ),
            (
                "      Historische Ziele: "
                f"Put {report.historical_put_target_percent:.2f} %, "
                f"Call +{report.historical_call_target_percent:.2f} %"
            ),
            (
                "      Verwendete Ziele: "
                f"Put {report.used_put_target_percent:.2f} % "
                f"({report.put_target_basis}), "
                f"Call +{report.used_call_target_percent:.2f} % "
                f"({report.call_target_basis})"
            ),
            (
                "      Close außerhalb: "
                f"Put {report.put_finish_outside_probability * 100:.1f} %, "
                f"Call {report.call_finish_outside_probability * 100:.1f} %"
            ),
            (
                "      Berührung: "
                f"Put {report.put_reached_probability * 100:.1f} %, "
                f"Call {report.call_reached_probability * 100:.1f} %"
            ),
            (
                "      Ø Bewegung bis Exit: "
                f"Tief {report.average_low_percent_until_exit:.2f} %, "
                f"Hoch +{report.average_high_percent_until_exit:.2f} %"
            ),
        ]
    )
    return lines

def run_batch(
    symbols: Iterable[str],
    report_date: date,
    output_path: Path,
    market_data: MarketDataService | None = None,
    analyzer_factory: EarningsCrushAnalyzerFactory | None = None,
) -> list:
    market_data = market_data or build_market_data()
    analyzer_factory = analyzer_factory or EarningsCrushAnalyzerFactory()

    events = build_events(symbols, report_date)
    analyzer = analyzer_factory.create(market_data)
    candidates = analyzer.create_candidates(events)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    TradeExporter().export_excel(candidates, output_path)

    print(f"Earnings-Datum: {report_date.isoformat()} (before market open)")
    print(f"Excel-Export: {output_path}")
    print()

    for candidate in candidates:
        print(format_candidate(candidate))
        for detail_line in format_selection_details(candidate):
            print(detail_line)

    return candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an Earnings Crush batch test for selected symbols.",
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        default=list(DEFAULT_SYMBOLS),
        help="Ticker symbols to analyze.",
    )
    parser.add_argument(
        "--report-date",
        type=date.fromisoformat,
        default=date.today() + timedelta(days=1),
        help="Earnings date in YYYY-MM-DD format. Default: tomorrow.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Excel output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = args.output or Path("exports") / (
        f"earnings_test_{args.report_date.isoformat()}.xlsx"
    )

    run_batch(
        symbols=args.symbols,
        report_date=args.report_date,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
