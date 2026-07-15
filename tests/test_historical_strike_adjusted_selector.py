from datetime import date

import pytest

from app.analysis.historical_strike_adjusted_selector import (
    HistoricalStrikeAdjustedSelector,
)
from app.analysis.historical_strike_risk_analyzer import (
    StrikeSide,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeRecommendation,
    HistoricalStrikeSelection,
    HistoricalStrikeSelectionReason,
)
from app.analysis.strategy import Strategy
from app.analysis.strike_selector import StrikeSelector
from app.marketdata.models import (
    ExpirationChain,
    OptionQuote,
)


def make_recommendation(
    *,
    side: StrikeSide,
    threshold_percent: float,
    expected_move_threshold_percent: float,
) -> HistoricalStrikeRecommendation:
    return HistoricalStrikeRecommendation(
        side=side,
        recommended_threshold_percent=(
            threshold_percent
        ),
        expected_move_threshold_percent=(
            expected_move_threshold_percent
        ),
        adjustment_from_expected_move=(
            threshold_percent
            - expected_move_threshold_percent
        ),
        finish_outside_probability=0.05,
        reached_probability=0.15,
        exit_trading_day_index=2,
        observation_count=20,
        reason=(
            HistoricalStrikeSelectionReason
            .ADJUSTED_OUTWARD
        ),
    )


def make_chain() -> ExpirationChain:
    expiration = date(2026, 7, 17)

    return ExpirationChain(
        symbol="NVDA",
        expiration=expiration,
        quotes=[
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=165.0,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=170.0,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=175.0,
                option_type="put",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=215.0,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=220.0,
                option_type="call",
            ),
            OptionQuote(
                symbol="NVDA",
                expiration=expiration,
                strike=225.0,
                option_type="call",
            ),
        ],
    )


def make_selector() -> HistoricalStrikeAdjustedSelector:
    return HistoricalStrikeAdjustedSelector(
        strike_selector=StrikeSelector(),
    )


def test_selects_available_strikes_from_asymmetric_history() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=make_recommendation(
            side=StrikeSide.CALL,
            threshold_percent=12.5,
            expected_move_threshold_percent=10.0,
        ),
        put_recommendation=make_recommendation(
            side=StrikeSide.PUT,
            threshold_percent=-15.0,
            expected_move_threshold_percent=-10.0,
        ),
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.adjustment.put_percent == pytest.approx(
        0.15
    )
    assert result.adjustment.call_percent == pytest.approx(
        0.125
    )
    assert result.adjustment.put_was_adjusted
    assert result.adjustment.call_was_adjusted

    assert (
        result.strike_selection.put_target
        == pytest.approx(170.0)
    )
    assert (
        result.strike_selection.call_target
        == pytest.approx(225.0)
    )

    assert result.strike_selection.put is not None
    assert result.strike_selection.put.strike == 170.0

    assert result.strike_selection.call is not None
    assert result.strike_selection.call.strike == 225.0


def test_falls_back_to_expected_move_for_missing_recommendation() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=make_recommendation(
            side=StrikeSide.CALL,
            threshold_percent=12.5,
            expected_move_threshold_percent=10.0,
        ),
        put_recommendation=None,
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.adjustment.put_percent == pytest.approx(
        0.10
    )
    assert result.adjustment.call_percent == pytest.approx(
        0.125
    )
    assert not result.adjustment.put_was_adjusted
    assert result.adjustment.call_was_adjusted

    assert (
        result.strike_selection.put_target
        == pytest.approx(180.0)
    )
    assert (
        result.strike_selection.call_target
        == pytest.approx(225.0)
    )

    assert result.strike_selection.put is not None
    assert result.strike_selection.put.strike == 175.0


def test_falls_back_to_expected_move_on_both_sides() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=None,
        put_recommendation=None,
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.adjustment.put_percent == pytest.approx(
        0.10
    )
    assert result.adjustment.call_percent == pytest.approx(
        0.10
    )
    assert not result.adjustment.put_was_adjusted
    assert not result.adjustment.call_was_adjusted

    assert (
        result.strike_selection.put_target
        == pytest.approx(180.0)
    )
    assert (
        result.strike_selection.call_target
        == pytest.approx(220.0)
    )

    assert result.strike_selection.put is not None
    assert result.strike_selection.put.strike == 175.0

    assert result.strike_selection.call is not None
    assert result.strike_selection.call.strike == 220.0


def test_preserves_iron_condor_wing_selection() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=None,
        put_recommendation=None,
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.IRON_CONDOR,
    )

    assert result.strike_selection.strategy is (
        Strategy.IRON_CONDOR
    )
    assert result.strike_selection.put is not None
    assert result.strike_selection.call is not None

    assert result.strike_selection.long_put is not None
    assert (
        result.strike_selection.long_put.strike
        == 165.0
    )

    assert result.strike_selection.long_call is not None
    assert (
        result.strike_selection.long_call.strike
        == 225.0
    )


@pytest.mark.parametrize(
    "expected_move_percent",
    (
        0.0,
        -5.0,
    ),
)
def test_rejects_invalid_expected_move(
    expected_move_percent: float,
) -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=expected_move_percent,
        call_recommendation=None,
        put_recommendation=None,
    )

    with pytest.raises(
        ValueError,
        match=(
            "expected_move_percent must be greater than zero"
        ),
    ):
        make_selector().select(
            chain=make_chain(),
            underlying_price=200.0,
            historical_selection=historical_selection,
        )

def test_expected_move_is_hard_minimum_for_both_sides() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=make_recommendation(
            side=StrikeSide.CALL,
            threshold_percent=7.5,
            expected_move_threshold_percent=10.0,
        ),
        put_recommendation=make_recommendation(
            side=StrikeSide.PUT,
            threshold_percent=-7.5,
            expected_move_threshold_percent=-10.0,
        ),
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.adjustment.put_percent == pytest.approx(0.10)
    assert result.adjustment.call_percent == pytest.approx(0.10)
    assert not result.adjustment.put_was_adjusted
    assert not result.adjustment.call_was_adjusted
    assert result.strike_selection.put_target == pytest.approx(180.0)
    assert result.strike_selection.call_target == pytest.approx(220.0)


def test_compares_expected_move_and_history_per_side() -> None:
    historical_selection = HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=make_recommendation(
            side=StrikeSide.CALL,
            threshold_percent=7.5,
            expected_move_threshold_percent=10.0,
        ),
        put_recommendation=make_recommendation(
            side=StrikeSide.PUT,
            threshold_percent=-15.0,
            expected_move_threshold_percent=-10.0,
        ),
    )

    result = make_selector().select(
        chain=make_chain(),
        underlying_price=200.0,
        historical_selection=historical_selection,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.adjustment.put_percent == pytest.approx(0.15)
    assert result.adjustment.call_percent == pytest.approx(0.10)
    assert result.adjustment.put_was_adjusted
    assert not result.adjustment.call_was_adjusted
    assert result.strike_selection.put_target == pytest.approx(170.0)
    assert result.strike_selection.call_target == pytest.approx(220.0)
