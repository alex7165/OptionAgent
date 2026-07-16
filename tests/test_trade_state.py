from datetime import date, datetime

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshot
from app.analysis.strategy import Strategy
from app.analysis.trade_state import TradeState, TradeStateRepository


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


def test_trade_state_tracks_existing_delta_hedge_and_cash_flow(tmp_path):
    state = TradeState.from_entry(entry()).apply_share_trade(
        timestamp=datetime(2026, 7, 16, 16, 0),
        quantity=63,
        price=1152.0,
        note="Initialer Delta-Hedge",
    )

    assert state.hedge_shares == 63
    assert state.realized_cash_flow == -72576.0
    assert state.actions[0].quantity == 63

    path = tmp_path / "gs.json"
    TradeStateRepository().save(state, path)
    loaded = TradeStateRepository().load(path)
    assert loaded == state
