from datetime import date

import pytest

from app.analysis.management_action import ManagementAction, ThreatenedSide
from app.analysis.management_action_knn_model import ManagementActionKnnModel
from app.analysis.management_action_training_dataset import ManagementActionTrainingDataset
from app.analysis.management_action_training_example import ManagementActionTrainingExample


def _row(*, symbol: str, action: ManagementAction, distance: float, pnl: float | None, day: int = 1) -> ManagementActionTrainingExample:
    return ManagementActionTrainingExample(
        symbol=symbol,
        decision_date=date(2026, 7, 23),
        threatened_side=ThreatenedSide.CALL,
        action=action,
        trading_day_index=day,
        underlying_price=110.0,
        short_strike=100.0,
        strike_distance_percent=distance,
        days_to_expiration=1,
        short_option_delta=0.80,
        expected_move_percent=8.0,
        iv_rank=55.0,
        iv_percentile=60.0,
        entry_strategy="short_strangle",
        capital_required=0.0,
        maximum_drawdown=-100.0,
        total_profit_loss=pnl,
        complete_profit_loss=pnl is not None,
        is_best_action=None if pnl is None else False,
    )


def test_predicts_profit_loss_from_same_action_neighbours() -> None:
    dataset = ManagementActionTrainingDataset(examples=(
        _row(symbol="A", action=ManagementAction.CLOSE, distance=9.0, pnl=-400.0),
        _row(symbol="B", action=ManagementAction.CLOSE, distance=10.0, pnl=-500.0),
        _row(symbol="C", action=ManagementAction.BUY_STOCK_HEDGE, distance=10.0, pnl=250.0),
    ))
    query = _row(symbol="Q", action=ManagementAction.CLOSE, distance=9.5, pnl=None)

    result = ManagementActionKnnModel(k=2).fit(dataset).predict(query)

    assert result.action is ManagementAction.CLOSE
    assert result.predicted_profit_loss == pytest.approx(-450.0)
    assert tuple(case.symbol for case in result.similar_cases) == ("A", "B")


def test_selects_action_with_best_predicted_profit_loss() -> None:
    dataset = ManagementActionTrainingDataset(examples=(
        _row(symbol="A", action=ManagementAction.CLOSE, distance=10.0, pnl=-500.0),
        _row(symbol="B", action=ManagementAction.BUY_STOCK_HEDGE, distance=10.0, pnl=200.0),
    ))
    close = _row(symbol="Q", action=ManagementAction.CLOSE, distance=10.0, pnl=None)
    hedge = _row(symbol="Q", action=ManagementAction.BUY_STOCK_HEDGE, distance=10.0, pnl=None)

    result = ManagementActionKnnModel(k=1).fit(dataset).select_best((close, hedge))

    assert result.action is ManagementAction.BUY_STOCK_HEDGE
    assert result.predicted_profit_loss == pytest.approx(200.0)
    assert result.confidence > 0.99


def test_ignores_incomplete_training_rows() -> None:
    dataset = ManagementActionTrainingDataset(examples=(
        _row(symbol="A", action=ManagementAction.CLOSE, distance=10.0, pnl=-100.0),
        _row(symbol="B", action=ManagementAction.CLOSE, distance=10.0, pnl=None),
    ))
    query = _row(symbol="Q", action=ManagementAction.CLOSE, distance=10.0, pnl=None)

    result = ManagementActionKnnModel(k=2).fit(dataset).predict(query)

    assert result.predicted_profit_loss == pytest.approx(-100.0)
    assert len(result.similar_cases) == 1


def test_rejects_dataset_without_complete_profit_loss() -> None:
    dataset = ManagementActionTrainingDataset(examples=(
        _row(symbol="A", action=ManagementAction.CLOSE, distance=10.0, pnl=None),
    ))

    with pytest.raises(ValueError, match="complete P/L"):
        ManagementActionKnnModel().fit(dataset)


def test_rejects_prediction_before_fit() -> None:
    query = _row(symbol="Q", action=ManagementAction.CLOSE, distance=10.0, pnl=None)

    with pytest.raises(RuntimeError, match="must be fitted"):
        ManagementActionKnnModel().predict(query)
