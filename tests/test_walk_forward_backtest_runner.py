from datetime import date

import pytest

from app.analysis.expected_move import ExpectedMove
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)
from app.analysis.historical_outcome_analyzer import HistoricalOutcome
from app.analysis.historical_strike_risk_analyzer import StrikeSide
from app.analysis.historical_strike_risk_grid_analyzer import HistoricalStrikeRiskGrid
from app.analysis.historical_strike_selection_service import (
    HistoricalStrikeSelectionResult,
)
from app.analysis.historical_strike_selector import (
    HistoricalStrikeRecommendation,
    HistoricalStrikeSelection,
    HistoricalStrikeSelectionPolicy,
    HistoricalStrikeSelectionReason,
)
from app.analysis.price_series_analyzer import PriceSeriesAnalysis
from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import (
    StrategyStrikeSelectionResult,
    StrikeSelectionSource,
)
from app.analysis.strike_selection import StrikeSelection
from app.analysis.walk_forward_backtest_runner import (
    WalkForwardBacktestCase,
    WalkForwardBacktestRunner,
)
from app.marketdata.earnings_api_provider import HistoricalEarningsReaction
from app.marketdata.models import ExpirationChain, OptionQuote
from app.marketdata.price_history_provider import DailyBar


class RecordingSelector:
    def __init__(self, result: StrategyStrikeSelectionResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def select_strikes_with_details(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def quote(option_type: str, strike: float) -> OptionQuote:
    return OptionQuote(
        symbol="TEST",
        expiration=date(2026, 7, 17),
        strike=strike,
        option_type=option_type,
        bid=1.0,
        ask=1.1,
        volume=100,
        open_interest=1_000,
    )


def selection() -> StrikeSelection:
    return StrikeSelection(
        put=quote("put", 95.0),
        call=quote("call", 105.0),
        put_target=95.0,
        call_target=105.0,
        strategy=Strategy.SHORT_STRANGLE,
    )


def recommendation(side: StrikeSide, exit_day: int) -> HistoricalStrikeRecommendation:
    threshold = 5.0 if side is StrikeSide.CALL else -5.0
    return HistoricalStrikeRecommendation(
        side=side,
        recommended_threshold_percent=threshold,
        expected_move_threshold_percent=threshold,
        adjustment_from_expected_move=0.0,
        finish_outside_probability=0.05,
        reached_probability=0.10,
        exit_trading_day_index=exit_day,
        observation_count=10,
        reason=HistoricalStrikeSelectionReason.EXPECTED_MOVE_MATCH,
    )


def historical_result(exit_day: int = 2) -> StrategyStrikeSelectionResult:
    details = HistoricalStrikeSelectionResult(
        outcomes=(
            HistoricalOutcome(
                exit_trading_day_index=exit_day,
                exit_date=date(2026, 7, 2),
                exit_close_percent=1.0,
                highest_percent_until_exit=2.0,
                lowest_percent_until_exit=-2.0,
                trading_days_observed=exit_day,
            ),
        ),
        risk_grid=HistoricalStrikeRiskGrid(call_risks=(), put_risks=()),
        selection=HistoricalStrikeSelection(
            expected_move_percent=5.0,
            call_recommendation=recommendation(StrikeSide.CALL, exit_day),
            put_recommendation=recommendation(StrikeSide.PUT, exit_day),
        ),
    )
    return StrategyStrikeSelectionResult(
        strike_selection=selection(),
        source=StrikeSelectionSource.HISTORICAL,
        historical_result=details,
    )


def fallback_result() -> StrategyStrikeSelectionResult:
    return StrategyStrikeSelectionResult(
        strike_selection=selection(),
        source=StrikeSelectionSource.EXPECTED_MOVE,
    )


def bar(day: int, close: float = 100.0) -> DailyBar:
    return DailyBar(
        date=date(2026, 7, day),
        open=100.0,
        high=102.0,
        low=98.0,
        close=close,
        volume=1_000_000,
    )


def case(report_day: int, fallback_exit: int | None = None) -> WalkForwardBacktestCase:
    return WalkForwardBacktestCase(
        report_date=date(2026, 7, report_day),
        chain=ExpirationChain(
            symbol="TEST",
            expiration=date(2026, 7, report_day + 4),
            quotes=[],
        ),
        expected_move=ExpectedMove(
            percent=0.05,
            up_price=105.0,
            down_price=95.0,
        ),
        reference_price=100.0,
        daily_bars=(bar(report_day + 1), bar(report_day + 2)),
        strategy=Strategy.SHORT_STRANGLE,
        fallback_exit_trading_day_index=fallback_exit,
    )


def analysis(report_day: int) -> HistoricalEarningsPriceAnalysis:
    earnings = HistoricalEarningsReaction(
        report_date=date(2026, 7, report_day),
        symbol="TEST",
        eps_surprise_percent=None,
        eps_yoy_percent=None,
        eps_beat=None,
        revenue_surprise_percent=None,
        revenue_yoy_percent=None,
        revenue_beat=None,
        reactions=(),
    )
    return HistoricalEarningsPriceAnalysis(
        earnings=earnings,
        price_analysis=PriceSeriesAnalysis(
            reference_price=100.0,
            first_date=date(2026, 7, report_day + 1),
            last_date=date(2026, 7, report_day + 1),
            first_open=100.0,
            first_close=100.0,
            last_close=100.0,
            highest_high=102.0,
            lowest_low=98.0,
            max_gain_percent=2.0,
            max_loss_percent=-2.0,
        ),
        daily_moves=(),
    )


def policy() -> HistoricalStrikeSelectionPolicy:
    return HistoricalStrikeSelectionPolicy(
        max_finish_outside_probability=0.10,
        max_reached_probability=0.25,
    )


def test_uses_only_earlier_earnings_for_each_decision() -> None:
    historical = RecordingSelector(historical_result(exit_day=2))
    fallback = RecordingSelector(fallback_result())
    runner = WalkForwardBacktestRunner(
        historical_selector=historical,
        fallback_selector=fallback,
        minimum_training_observations=1,
    )

    result = runner.run(
        symbol=" test ",
        cases=(case(20), case(10, fallback_exit=1)),
        historical_price_analyses=(analysis(5), analysis(15), analysis(25)),
        call_thresholds=(5.0, 7.5),
        put_thresholds=(-5.0, -7.5),
        policy=policy(),
    )

    assert result.symbol == "TEST"
    assert tuple(item.report_date.day for item in result.decisions) == (10, 20)
    assert [item.training_observation_count for item in result.decisions] == [1, 2]
    assert len(historical.calls) == 2
    assert [
        tuple(item.earnings.report_date.day for item in call["price_analyses"])
        for call in historical.calls
    ] == [(5,), (5, 15)]
    assert all(call["exit_trading_day_index"] == 0 for call in historical.calls)
    assert fallback.calls == []
    assert result.backtest.overall.observation_count == 2


def test_falls_back_until_minimum_training_sample_is_available() -> None:
    historical = RecordingSelector(historical_result(exit_day=1))
    fallback = RecordingSelector(fallback_result())
    runner = WalkForwardBacktestRunner(
        historical_selector=historical,
        fallback_selector=fallback,
        minimum_training_observations=2,
    )

    result = runner.run(
        symbol="TEST",
        cases=(case(10, fallback_exit=1), case(20)),
        historical_price_analyses=(analysis(5), analysis(15)),
        call_thresholds=(5.0,),
        put_thresholds=(-5.0,),
        policy=policy(),
    )

    assert [item.selection_source for item in result.decisions] == [
        StrikeSelectionSource.EXPECTED_MOVE,
        StrikeSelectionSource.HISTORICAL,
    ]
    assert [item.exit_trading_day_index for item in result.decisions] == [1, 1]
    assert len(fallback.calls) == 1
    assert len(historical.calls) == 1


def test_fallback_uses_all_available_bars_when_no_exit_is_configured() -> None:
    runner = WalkForwardBacktestRunner(
        historical_selector=RecordingSelector(historical_result()),
        fallback_selector=RecordingSelector(fallback_result()),
        minimum_training_observations=2,
    )

    result = runner.run(
        symbol="TEST",
        cases=(case(10),),
        historical_price_analyses=(analysis(5),),
        call_thresholds=(5.0,),
        put_thresholds=(-5.0,),
        policy=policy(),
    )

    assert result.decisions[0].exit_trading_day_index == 2
    assert result.backtest.results[0].outcome.holding_days == 2


def test_rejects_historical_result_without_matching_exit_days() -> None:
    base = historical_result(exit_day=2)
    invalid_details = HistoricalStrikeSelectionResult(
        outcomes=base.historical_result.outcomes,
        risk_grid=base.historical_result.risk_grid,
        selection=HistoricalStrikeSelection(
            expected_move_percent=5.0,
            call_recommendation=recommendation(StrikeSide.CALL, 2),
            put_recommendation=recommendation(StrikeSide.PUT, 1),
        ),
    )
    invalid = StrategyStrikeSelectionResult(
        strike_selection=base.strike_selection,
        source=StrikeSelectionSource.HISTORICAL,
        historical_result=invalid_details,
    )
    runner = WalkForwardBacktestRunner(
        historical_selector=RecordingSelector(invalid),
        fallback_selector=RecordingSelector(fallback_result()),
    )

    with pytest.raises(ValueError, match="same exit day"):
        runner.run(
            symbol="TEST",
            cases=(case(10),),
            historical_price_analyses=(analysis(5),),
            call_thresholds=(5.0,),
            put_thresholds=(-5.0,),
            policy=policy(),
        )


def test_rejects_duplicate_case_dates() -> None:
    runner = WalkForwardBacktestRunner(
        historical_selector=RecordingSelector(historical_result()),
        fallback_selector=RecordingSelector(fallback_result()),
    )
    duplicate = case(10)

    with pytest.raises(ValueError, match="unique report dates"):
        runner.run(
            symbol="TEST",
            cases=(duplicate, duplicate),
            historical_price_analyses=(),
            call_thresholds=(5.0,),
            put_thresholds=(-5.0,),
            policy=policy(),
        )
