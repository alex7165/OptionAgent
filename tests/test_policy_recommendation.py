from datetime import date

import pytest

from app.analysis.failure_attribution import (
    FailureAttribution,
    FailureCause,
    FailureSeverity,
    SideFailureAttribution,
)
from app.analysis.historical_strike_risk_analyzer import StrikeSide
from app.analysis.policy_recommendation import (
    PolicyRecommendationAnalyzer,
    PolicyRecommendationType,
)
from app.analysis.trade_review import ExitReview, TradeReview


def _side(
    side: StrikeSide,
    *,
    finished_outside: bool = True,
    shortfall: float = 0.8,
) -> SideFailureAttribution:
    return SideFailureAttribution(
        side=side,
        touched=True,
        finished_outside=finished_outside,
        actual_extreme_move_percent=-6.0 if side is StrikeSide.PUT else 6.0,
        final_strike_distance_percent=-5.2 if side is StrikeSide.PUT else 5.2,
        used_target_percent=-5.0 if side is StrikeSide.PUT else 5.0,
        target_basis="Expected Move",
        historical_target_percent=-4.8 if side is StrikeSide.PUT else 4.8,
        distance_shortfall_percent=shortfall,
    )


def _attribution(
    *,
    cause: FailureCause = FailureCause.NONE,
    side: StrikeSide | None = None,
    severity: FailureSeverity = FailureSeverity.NONE,
    shortfall: float = 0.8,
) -> FailureAttribution:
    affected = () if side is None else (_side(side, shortfall=shortfall),)
    return FailureAttribution(
        severity=severity,
        primary_cause=cause,
        affected_sides=affected,
        expected_move_percent=5.0,
        historical_max_abs_close_move_percent=8.0,
        observations=(),
    )


def _exit(
    day: int,
    *,
    inside: bool = True,
    put_touched: bool = False,
    call_touched: bool = False,
) -> ExitReview:
    return ExitReview(
        trading_day_index=day,
        exit_date=date(2026, 7, 14 + day),
        exit_close=100.0,
        finished_inside_short_strikes=inside,
        put_finished_outside=not inside and put_touched,
        call_finished_outside=not inside and call_touched,
        put_touched=put_touched,
        call_touched=call_touched,
    )


def _review(*, earlier_safe: bool = False) -> TradeReview:
    alternatives = (_exit(1), _exit(3, call_touched=True)) if earlier_safe else ()
    return TradeReview(
        selected_exit=_exit(2),
        alternative_exits=alternatives,
        assessment="test",
        max_adverse_move_percent=-2.0,
        max_favorable_move_percent=2.0,
        observations=(),
    )


def test_recommends_no_change_for_small_sample() -> None:
    analyzer = PolicyRecommendationAnalyzer(minimum_observations=8)

    report = analyzer.analyze(
        attributions=tuple(_attribution() for _ in range(4)),
        reviews=tuple(_review() for _ in range(4)),
    )

    assert report.recommendations[0].recommendation_type is (
        PolicyRecommendationType.NO_CHANGE
    )
    assert report.recommendations[0].confidence == 0.5


def test_recommends_wider_call_distance_for_repeated_call_failures() -> None:
    analyzer = PolicyRecommendationAnalyzer(
        minimum_observations=5,
        side_failure_rate_threshold=0.20,
    )
    attributions = (
        _attribution(
            cause=FailureCause.CURRENT_MARKET_UNDERESTIMATED,
            side=StrikeSide.CALL,
            severity=FailureSeverity.FAILURE,
            shortfall=0.7,
        ),
        _attribution(
            cause=FailureCause.STRIKE_DISTANCE_INSUFFICIENT,
            side=StrikeSide.CALL,
            severity=FailureSeverity.FAILURE,
            shortfall=1.1,
        ),
        *tuple(_attribution() for _ in range(8)),
    )

    report = analyzer.analyze(
        attributions=attributions,
        reviews=tuple(_review() for _ in attributions),
    )

    recommendation = next(
        item
        for item in report.recommendations
        if item.recommendation_type
        is PolicyRecommendationType.WIDEN_CALL_DISTANCE
    )
    assert recommendation.affected_observations == 2
    assert recommendation.confidence == pytest.approx(0.2)
    assert recommendation.suggested_change_percent == pytest.approx(0.9)


def test_recommends_earlier_exit_for_repeated_safe_earlier_exits() -> None:
    analyzer = PolicyRecommendationAnalyzer(
        minimum_observations=5,
        earlier_exit_rate_threshold=0.40,
    )
    attributions = tuple(_attribution() for _ in range(10))
    reviews = tuple(_review(earlier_safe=index < 5) for index in range(10))

    report = analyzer.analyze(attributions=attributions, reviews=reviews)

    recommendation = next(
        item
        for item in report.recommendations
        if item.recommendation_type is PolicyRecommendationType.EXIT_EARLIER
    )
    assert recommendation.affected_observations == 5
    assert recommendation.confidence == 0.5


def test_recommends_reviewing_outlier_handling_instead_of_widening() -> None:
    analyzer = PolicyRecommendationAnalyzer(
        minimum_observations=5,
        outlier_rate_threshold=0.20,
    )
    attributions = tuple(
        _attribution(
            cause=FailureCause.POSSIBLE_EXTREME_OUTLIER,
            side=StrikeSide.CALL,
            severity=FailureSeverity.FAILURE,
        )
        if index < 2
        else _attribution()
        for index in range(10)
    )

    report = analyzer.analyze(
        attributions=attributions,
        reviews=tuple(_review() for _ in attributions),
    )

    types = {item.recommendation_type for item in report.recommendations}
    assert PolicyRecommendationType.REVIEW_OUTLIER_HANDLING in types
    assert PolicyRecommendationType.WIDEN_CALL_DISTANCE not in types


def test_returns_no_change_when_no_pattern_reaches_threshold() -> None:
    analyzer = PolicyRecommendationAnalyzer(minimum_observations=5)
    attributions = tuple(_attribution() for _ in range(10))

    report = analyzer.analyze(
        attributions=attributions,
        reviews=tuple(_review() for _ in attributions),
    )

    assert len(report.recommendations) == 1
    assert report.recommendations[0].recommendation_type is (
        PolicyRecommendationType.NO_CHANGE
    )


def test_rejects_mismatched_inputs() -> None:
    analyzer = PolicyRecommendationAnalyzer(minimum_observations=1)

    with pytest.raises(ValueError, match="equal length"):
        analyzer.analyze(
            attributions=(_attribution(),),
            reviews=(),
        )
