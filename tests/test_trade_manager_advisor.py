from datetime import date

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategy import Strategy
from app.analysis.trade_manager_advisor import (
    HistoricalManagementContext,
    ManagementAction,
    TradeManagerAdvisor,
    TradeManagerMarketState,
)
from app.marketdata.models import OptionQuote


def quote(strike, option_type, bid, ask):
    return OptionQuote(
        symbol="GS",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=bid,
        ask=ask,
    )


def entry():
    return EntryDecisionSnapshot(
        symbol="GS",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        expiration=date(2026, 7, 17),
        strategy=Strategy.SHORT_STRANGLE,
        reference_price=1042.45,
        short_put_strike=990,
        short_call_strike=1095,
    )


def test_advisor_preserves_strategy_and_uses_current_market_and_history():
    advice = TradeManagerAdvisor().advise(
        entry(),
        TradeManagerMarketState(
            underlying_price=1138.85,
            days_to_expiration=2,
            short_put=quote(990, "put", 0.1, 0.2),
            short_call=quote(1095, "call", 44.0, 46.0),
            replacement_call=quote(1160, "call", 7.0, 8.0),
            short_call_delta=0.82,
        ),
        HistoricalManagementContext(
            observation_count=12,
            probability_finish_back_inside=0.10,
            probability_continue_higher=0.70,
            average_remaining_move_percent=1.8,
        ),
    )

    assert advice.strategy == "Short Strangle"
    assert advice.breached_side == "call"
    assert advice.history_observation_count == 12
    assert advice.recommended_action in {
        ManagementAction.CLOSE,
        ManagementAction.ROLL_CALL,
    }


def test_roll_cash_flow_uses_current_call_ask_and_new_call_bid():
    advice = TradeManagerAdvisor().advise(
        entry(),
        TradeManagerMarketState(
            underlying_price=1138.85,
            days_to_expiration=2,
            short_put=quote(990, "put", 0.1, 0.2),
            short_call=quote(1095, "call", 44.0, 46.0),
            replacement_call=quote(1160, "call", 7.0, 8.0),
        ),
        HistoricalManagementContext(5, 0.2, 0.6, 1.0),
    )
    roll = next(item for item in advice.alternatives if item.action is ManagementAction.ROLL_CALL)

    assert roll.available is True
    assert roll.estimated_cash_flow == -39.0


def test_share_hedge_is_unavailable_without_delta():
    advice = TradeManagerAdvisor().advise(
        entry(),
        TradeManagerMarketState(
            underlying_price=1138.85,
            days_to_expiration=2,
            short_put=quote(990, "put", 0.1, 0.2),
            short_call=quote(1095, "call", 44.0, 46.0),
            replacement_call=None,
            short_call_delta=None,
        ),
        HistoricalManagementContext(0, None, None, None),
    )
    hedge = next(item for item in advice.alternatives if item.action is ManagementAction.ADJUST_DELTA_HEDGE)

    assert hedge.available is False


def test_delta_hedge_uses_net_strangle_delta_and_existing_shares():
    put = quote(990, "put", 0.1, 0.2)
    put.delta = -0.02
    call = quote(1095, "call", 44.0, 46.0)
    call.delta = 0.65
    advice = TradeManagerAdvisor().advise(
        entry(),
        TradeManagerMarketState(
            underlying_price=1152.0,
            days_to_expiration=1,
            short_put=put,
            short_call=call,
            replacement_call=None,
            existing_hedge_shares=20,
        ),
        HistoricalManagementContext(3, 0.0, 0.33, 0.26),
    )
    hedge = next(
        item for item in advice.alternatives
        if item.action is ManagementAction.ADJUST_DELTA_HEDGE
    )

    assert hedge.available is True
    assert hedge.estimated_cash_flow == -(43 * 1152.0)
    assert any("Zielbestand Hedge: 63 Aktien; aktuell: 20" in x for x in hedge.details)
    assert any("Heute 43 GS-Aktien kaufen" in x for x in hedge.details)
