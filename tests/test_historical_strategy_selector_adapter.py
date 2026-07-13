from datetime import date

import pytest

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.historical_strike_adjusted_selector import (
    HistoricalStrikeAdjustedSelection,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
)
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionResult,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeSelection,
    HistoricalStrikeSelectionPolicy,
)
from app.analysis.historical_strategy_selector_adapter import (
    HistoricalStrategySelectorAdapter,
)
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import ExpirationChain


class RecordingHistoricalSelectionService:

    def __init__(
        self,
        result: HistoricalStrikeSelectionResult,
    ) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def select(
        self,
        *,
        price_analyses: tuple[object, ...],
        expected_move_percent: float,
        exit_trading_day_index: int,
        call_thresholds: tuple[float, ...],
        put_thresholds: tuple[float, ...],
        policy: HistoricalStrikeSelectionPolicy,
    ) -> HistoricalStrikeSelectionResult:
        self.calls.append(
            {
                "price_analyses": price_analyses,
                "expected_move_percent": (
                    expected_move_percent
                ),
                "exit_trading_day_index": (
                    exit_trading_day_index
                ),
                "call_thresholds": call_thresholds,
                "put_thresholds": put_thresholds,
                "policy": policy,
            }
        )

        return self.result


class RecordingAdjustedSelector:

    def __init__(
        self,
        result: HistoricalStrikeAdjustedSelection,
    ) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def select(
        self,
        *,
        chain: ExpirationChain,
        underlying_price: float,
        historical_selection: HistoricalStrikeSelection,
        strategy: Strategy,
    ) -> HistoricalStrikeAdjustedSelection:
        self.calls.append(
            {
                "chain": chain,
                "underlying_price": underlying_price,
                "historical_selection": (
                    historical_selection
                ),
                "strategy": strategy,
            }
        )

        return self.result


def make_chain() -> ExpirationChain:
    return ExpirationChain(
        symbol="NVDA",
        expiration=date(2026, 7, 17),
        quotes=[],
    )


def make_historical_selection() -> HistoricalStrikeSelection:
    return HistoricalStrikeSelection(
        expected_move_percent=10.0,
        call_recommendation=None,
        put_recommendation=None,
    )


def make_historical_result() -> (
    HistoricalStrikeSelectionResult
):
    return HistoricalStrikeSelectionResult(
        outcomes=(
            HistoricalOutcome(
                exit_trading_day_index=2,
                exit_date=date(2026, 4, 20),
                exit_close_percent=4.0,
                highest_percent_until_exit=8.0,
                lowest_percent_until_exit=-6.0,
                trading_days_observed=2,
            ),
        ),
        risk_grid=HistoricalStrikeRiskGrid(
            call_risks=(),
            put_risks=(),
        ),
        selection=make_historical_selection(),
    )


def make_adjusted_result() -> (
    HistoricalStrikeAdjustedSelection
):
    from app.analysis.historical_strike_adjusted_selector import (
        HistoricalStrikeAdjustment,
    )

    return HistoricalStrikeAdjustedSelection(
        adjustment=HistoricalStrikeAdjustment(
            expected_move_percent=10.0,
            put_percent=0.10,
            call_percent=0.10,
            put_was_adjusted=False,
            call_was_adjusted=False,
        ),
        strike_selection=StrikeSelection(
            put=None,
            call=None,
            put_target=180.0,
            call_target=220.0,
            strategy=Strategy.SHORT_STRANGLE,
        ),
    )


def test_runs_historical_and_adjusted_strike_selection() -> None:
    historical_result = make_historical_result()
    adjusted_result = make_adjusted_result()

    historical_service = (
        RecordingHistoricalSelectionService(
            result=historical_result
        )
    )
    adjusted_selector = RecordingAdjustedSelector(
        result=adjusted_result
    )

    adapter = HistoricalStrategySelectorAdapter(
        historical_selection_service=historical_service,
        adjusted_selector=adjusted_selector,
    )

    chain = make_chain()
    policy = HistoricalStrikeSelectionPolicy(
        max_finish_outside_probability=0.10,
        max_reached_probability=0.25,
    )
    price_analyses = (object(),)

    result = adapter.select(
        chain=chain,
        underlying_price=200.0,
        expected_move=ExpectedMove(
            percent=0.10,
            up_price=220.0,
            down_price=180.0,
        ),
        price_analyses=price_analyses,
        exit_trading_day_index=2,
        call_thresholds=(
            7.5,
            10.0,
            12.5,
        ),
        put_thresholds=(
            -7.5,
            -10.0,
            -12.5,
        ),
        policy=policy,
        strategy=Strategy.SHORT_STRANGLE,
    )

    assert result.historical_result is historical_result
    assert result.adjusted_selection is adjusted_result

    assert historical_service.calls == [
        {
            "price_analyses": price_analyses,
            "expected_move_percent": 10.0,
            "exit_trading_day_index": 2,
            "call_thresholds": (
                7.5,
                10.0,
                12.5,
            ),
            "put_thresholds": (
                -7.5,
                -10.0,
                -12.5,
            ),
            "policy": policy,
        }
    ]

    assert adjusted_selector.calls == [
        {
            "chain": chain,
            "underlying_price": 200.0,
            "historical_selection": (
                historical_result.selection
            ),
            "strategy": Strategy.SHORT_STRANGLE,
        }
    ]


def test_converts_decimal_expected_move_to_percentage_points() -> None:
    historical_service = (
        RecordingHistoricalSelectionService(
            result=make_historical_result()
        )
    )

    adapter = HistoricalStrategySelectorAdapter(
        historical_selection_service=historical_service,
        adjusted_selector=RecordingAdjustedSelector(
            result=make_adjusted_result()
        ),
    )

    adapter.select(
        chain=make_chain(),
        underlying_price=150.0,
        expected_move=ExpectedMove(
            percent=0.075,
            up_price=161.25,
            down_price=138.75,
        ),
        price_analyses=(object(),),
        exit_trading_day_index=1,
        call_thresholds=(7.5, 10.0),
        put_thresholds=(-7.5, -10.0),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
        ),
    )

    assert (
        historical_service.calls[0][
            "expected_move_percent"
        ]
        == pytest.approx(7.5)
    )


def test_preserves_selected_strategy() -> None:
    adjusted_selector = RecordingAdjustedSelector(
        result=make_adjusted_result()
    )

    adapter = HistoricalStrategySelectorAdapter(
        historical_selection_service=(
            RecordingHistoricalSelectionService(
                result=make_historical_result()
            )
        ),
        adjusted_selector=adjusted_selector,
    )

    adapter.select(
        chain=make_chain(),
        underlying_price=200.0,
        expected_move=ExpectedMove(
            percent=0.10,
            up_price=220.0,
            down_price=180.0,
        ),
        price_analyses=(object(),),
        exit_trading_day_index=2,
        call_thresholds=(10.0,),
        put_thresholds=(-10.0,),
        policy=HistoricalStrikeSelectionPolicy(
            max_finish_outside_probability=0.10,
        ),
        strategy=Strategy.IRON_CONDOR,
    )

    assert (
        adjusted_selector.calls[0]["strategy"]
        is Strategy.IRON_CONDOR
    )


@pytest.mark.parametrize(
    "underlying_price",
    (
        0.0,
        -100.0,
    ),
)
def test_rejects_non_positive_underlying_price(
    underlying_price: float,
) -> None:
    adapter = HistoricalStrategySelectorAdapter(
        historical_selection_service=(
            RecordingHistoricalSelectionService(
                result=make_historical_result()
            )
        ),
        adjusted_selector=RecordingAdjustedSelector(
            result=make_adjusted_result()
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "underlying_price must be greater than zero"
        ),
    ):
        adapter.select(
            chain=make_chain(),
            underlying_price=underlying_price,
            expected_move=ExpectedMove(
                percent=0.10,
                up_price=220.0,
                down_price=180.0,
            ),
            price_analyses=(object(),),
            exit_trading_day_index=2,
            call_thresholds=(10.0,),
            put_thresholds=(-10.0,),
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.10,
            ),
        )


@pytest.mark.parametrize(
    "expected_move_percent",
    (
        0.0,
        -0.10,
    ),
)
def test_rejects_non_positive_expected_move_percent(
    expected_move_percent: float,
) -> None:
    adapter = HistoricalStrategySelectorAdapter(
        historical_selection_service=(
            RecordingHistoricalSelectionService(
                result=make_historical_result()
            )
        ),
        adjusted_selector=RecordingAdjustedSelector(
            result=make_adjusted_result()
        ),
    )

    with pytest.raises(
        ValueError,
        match=(
            "expected_move.percent must be greater than zero"
        ),
    ):
        adapter.select(
            chain=make_chain(),
            underlying_price=200.0,
            expected_move=ExpectedMove(
                percent=expected_move_percent,
                up_price=220.0,
                down_price=180.0,
            ),
            price_analyses=(object(),),
            exit_trading_day_index=2,
            call_thresholds=(10.0,),
            put_thresholds=(-10.0,),
            policy=HistoricalStrikeSelectionPolicy(
                max_finish_outside_probability=0.10,
            ),
        )