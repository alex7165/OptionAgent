from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_training_example import (
    ManagementActionTrainingExample,
)


def test_incomplete_row_has_no_best_action_label() -> None:
    row = ManagementActionTrainingExample(
        symbol=" tsla ",
        decision_date=date(2026, 7, 23),
        threatened_side=ThreatenedSide.CALL,
        action=ManagementAction.BUY_STOCK_HEDGE,
        trading_day_index=2,
        underlying_price=319.69,
        short_strike=355.0,
        strike_distance_percent=-9.95,
        days_to_expiration=1,
        short_option_delta=0.86,
        expected_move_percent=7.0,
        iv_rank=None,
        iv_percentile=None,
        entry_strategy="Short Strangle",
        capital_required=27_493.34,
        maximum_drawdown=-800.0,
        total_profit_loss=None,
        complete_profit_loss=False,
        is_best_action=None,
    )

    assert row.symbol == "TSLA"
    assert row.entry_strategy == "short strangle"


def test_rejects_best_action_label_for_incomplete_row() -> None:
    with pytest.raises(ValueError, match="must not receive"):
        ManagementActionTrainingExample(
            symbol="TSLA",
            decision_date=date(2026, 7, 23),
            threatened_side=ThreatenedSide.CALL,
            action=ManagementAction.BUY_STOCK_HEDGE,
            trading_day_index=2,
            underlying_price=319.69,
            short_strike=355.0,
            strike_distance_percent=-9.95,
            days_to_expiration=1,
            short_option_delta=0.86,
            expected_move_percent=None,
            iv_rank=None,
            iv_percentile=None,
            entry_strategy=None,
            capital_required=27_493.34,
            maximum_drawdown=-800.0,
            total_profit_loss=None,
            complete_profit_loss=False,
            is_best_action=True,
        )
