from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshotRepository
from app.analysis.historical_trade_management_context_loader import HistoricalTradeManagementContextLoader
from app.analysis.trade_manager_advisor import TradeManagerAdvisor, TradeManagerMarketState
from app.analysis.option_delta_resolver import OptionDeltaResolver
from app.analysis.trade_state import TradeState, TradeStateRepository
from app.analysis.trade_management_chart_context import TradeManagementChartContextAnalyzer
from app.marketdata.historical_earnings_date_provider import (
    YahooHistoricalEarningsDateProvider,
)
from app.marketdata.optionstrat_provider import OptionStratProvider
from app.marketdata.yahoo_price_history_provider import YahooPriceHistoryProvider
from app.marketdata.yahoo_provider import YahooPriceProvider


def _quote(chain, strike: float, option_type: str):
    return next((q for q in chain.quotes if q.strike == strike and q.option_type == option_type), None)


def _replacement_call(chain, underlying_price: float, old_ask: float | None):
    candidates = [
        q for q in chain.quotes
        if q.option_type == "call" and q.strike > underlying_price and q.bid is not None
    ]
    if not candidates:
        return None
    # Prefer at least 2% buffer, then best roll cash flow and tighter spread.
    eligible = [q for q in candidates if q.strike >= underlying_price * 1.02] or candidates
    def key(q):
        spread = q.bid_ask_spread_percent if q.bid_ask_spread_percent is not None else 999
        cash = q.bid - old_ask if old_ask is not None else q.bid
        return (cash, -spread, -q.strike)
    return max(eligible, key=key)


def run(as_of_date: date, decision_file: Path, state_file: Path) -> int:
    entries = EntryDecisionSnapshotRepository().load(decision_file)
    entry = next(item for item in entries if item.symbol == "GS")
    state_repository = TradeStateRepository()
    if state_file.exists():
        state = state_repository.load(state_file)
    else:
        state = TradeState.from_entry(entry)
        state_repository.save(state, state_file)
    if as_of_date < entry.report_date:
        raise ValueError("as_of_date must not be before the actual earnings date")
    if as_of_date > entry.expiration:
        raise ValueError("as_of_date must not be after expiration for this live trade")

    price_history_provider = YahooPriceHistoryProvider()
    chart = TradeManagementChartContextAnalyzer(price_history_provider).analyze(
        entry, as_of_date
    )
    price = YahooPriceProvider().get_quote("GS").price
    chain = OptionStratProvider().get_expiration_chain("GS", entry.expiration)
    if chain is None:
        print("GS: aktuelle Optionskette nicht verfügbar")
        return 1
    short_put = _quote(chain, entry.short_put_strike, "put")
    short_call = _quote(chain, entry.short_call_strike, "call")
    if short_put is None or short_call is None:
        print("GS: bestehende Short-Optionen nicht in der aktuellen Kette gefunden")
        return 1
    replacement = _replacement_call(chain, price, short_call.ask)
    history = HistoricalTradeManagementContextLoader(
        YahooHistoricalEarningsDateProvider(),
        price_history_provider,
    ).load(entry, as_of_date, price)
    delta_resolver = OptionDeltaResolver()
    days_to_expiration = max(0, (entry.expiration - as_of_date).days)
    call_delta = delta_resolver.resolve(
        short_call, underlying_price=price, days_to_expiration=days_to_expiration
    )
    put_delta = delta_resolver.resolve(
        short_put, underlying_price=price, days_to_expiration=days_to_expiration
    )
    advice = TradeManagerAdvisor().advise(
        entry,
        TradeManagerMarketState(
            underlying_price=price,
            days_to_expiration=days_to_expiration,
            short_put=short_put,
            short_call=short_call,
            replacement_call=replacement,
            short_call_delta=call_delta,
            short_put_delta=put_delta,
            existing_hedge_shares=state.hedge_shares,
            chart_context=chart,
        ),
        history,
    )
    print(
        f"GS Short Strangle 990 / 1095 | Kurs {price:.2f} | "
        f"Earnings {entry.report_date} | Stand {as_of_date} | Verfall {entry.expiration}"
    )
    print(
        f"Chart (letzter Handelstag {chart.as_of_trading_date}): "
        f"seit Entry {chart.return_since_entry_percent:+.2f} %, "
        f"Gap {chart.gap_from_pre_earnings_close_percent if chart.gap_from_pre_earnings_close_percent is not None else float('nan'):+.2f} %, "
        f"ATR14 {chart.atr14_percent if chart.atr14_percent is not None else float('nan'):.2f} %"
    )
    print(
        f"Neues 5J-Hoch: {'ja' if chart.is_new_period_high else 'nein'} | "
        f"Gap gehalten: {'ja' if chart.gap_held is True else 'nein' if chart.gap_held is False else 'n/a'} | "
        f"Schlusslage Tagesspanne: {chart.close_location_percent if chart.close_location_percent is not None else float('nan'):.1f} % | "
        f"Volumenfaktor: {chart.volume_ratio_20d if chart.volume_ratio_20d is not None else float('nan'):.2f}x"
    )
    print(f"Neubewertungs-Signale: {chart.revaluation_signal_count}/6")
    total_history = history.total_observation_count
    if total_history is not None:
        share = history.observation_count / total_history if total_history else 0.0
        print(
            f"Historisch vergleichbare Fälle: {history.observation_count} von "
            f"{total_history} ({share:.1%})"
        )
    else:
        print(f"Historisch vergleichbare Fälle: {history.observation_count}")
    for index, case in enumerate(history.comparable_cases, start=1):
        print(
            f"  {index}. {case.report_date} | "
            f"Max. Move {case.maximum_move_percent:+.2f}% "
            f"(Tag {case.maximum_move_trading_day}) | "
            f"Freitag {case.friday_close_move_percent:+.2f}% | "
            f"Allzeithoch: {'ja' if case.made_all_time_high else 'nein'}"
        )
    print(
        f"TradeState: Hedge-Aktien {state.hedge_shares} | "
        f"bisheriger Aktien-Cashflow {state.realized_cash_flow:+.2f} USD"
    )
    print(
        f"Delta: Put {put_delta if put_delta is not None else float('nan'):+.3f} | "
        f"Call {call_delta if call_delta is not None else float('nan'):+.3f}"
    )
    if history.probability_finish_back_inside is not None:
        print(f"Rückkehr unter 1095 bis Verfall: {history.probability_finish_back_inside:.1%}")
        print(f"Weiterer Anstieg bis Verfall: {history.probability_continue_higher:.1%}")
        print(f"Ø Restbewegung: {history.average_remaining_move_percent:+.2f}%")
    else:
        print("Historie: zu wenige direkt vergleichbare Fälle für belastbare Quoten")
    print(f"Empfehlung: {advice.recommended_action.value}")
    for alt in advice.alternatives:
        status = "verfügbar" if alt.available else "nicht verfügbar"
        cash = "-" if alt.estimated_cash_flow is None else f"{alt.estimated_cash_flow:+.2f} USD/Aktie"
        print(f"\n{alt.action.value}: {alt.score:.0f}/100 | {status} | Cashflow {cash}")
        for detail in alt.details:
            print(f"  - {detail}")
    state_repository.save(state.with_evaluation(datetime.now()), state_file)
    print(
        "\nHinweis: Eine Hedge-Empfehlung ändert den TradeState nicht automatisch. "
        "Ausgeführte Aktienkäufe/-verkäufe müssen anschließend ausdrücklich verbucht werden."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument(
        "--decision-file", type=Path,
        default=Path("app/data/decisions/2026-07-13.json"),
    )
    parser.add_argument(
        "--state-file", type=Path,
        default=Path("app/data/trade_states/GS.json"),
    )
    args = parser.parse_args()
    raise SystemExit(run(args.as_of_date, args.decision_file, args.state_file))


if __name__ == "__main__":
    main()
