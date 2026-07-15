from datetime import date

import pytest

from app.analysis.trade_review import ExitReview, TradeReview
from app.analysis.trade_review_summary import TradeReviewSummaryAnalyzer


def exit_review(
    day: int,
    *,
    inside: bool = True,
    put_touched: bool = False,
    call_touched: bool = False,
) -> ExitReview:
    return ExitReview(
        trading_day_index=day,
        exit_date=date(2026, 7, 13 + day),
        exit_close=100.0,
        finished_inside_short_strikes=inside,
        put_touched=put_touched,
        call_touched=call_touched,
        put_finished_outside=not inside and put_touched,
        call_finished_outside=not inside and call_touched,
    )


def review(
    selected: ExitReview,
    alternatives: tuple[ExitReview, ...] = (),
    *,
    mae: float = -3.0,
    mfe: float = 4.0,
) -> TradeReview:
    return TradeReview(
        selected_exit=selected,
        alternative_exits=alternatives,
        assessment="test",
        observations=(),
        max_adverse_move_percent=mae,
        max_favorable_move_percent=mfe,
    )


def test_aggregates_review_quality_and_path_metrics() -> None:
    metrics = TradeReviewSummaryAnalyzer().analyze(
        (
            review(exit_review(1), mae=-2.0, mfe=3.0),
            review(
                exit_review(2, call_touched=True),
                mae=-4.0,
                mfe=5.0,
            ),
            review(
                exit_review(3, inside=False, put_touched=True),
                mae=-8.0,
                mfe=2.0,
            ),
        )
    )

    assert metrics.observation_count == 3
    assert metrics.very_good_rate == pytest.approx(1 / 3)
    assert metrics.successful_with_touch_rate == pytest.approx(1 / 3)
    assert metrics.strike_violation_rate == pytest.approx(1 / 3)
    assert metrics.put_touch_rate == pytest.approx(1 / 3)
    assert metrics.call_touch_rate == pytest.approx(1 / 3)
    assert metrics.average_selected_exit_trading_day == pytest.approx(2.0)
    assert metrics.average_max_adverse_move_percent == pytest.approx(-14 / 3)
    assert metrics.average_max_favorable_move_percent == pytest.approx(10 / 3)


def test_detects_earlier_safe_exit() -> None:
    metrics = TradeReviewSummaryAnalyzer().analyze(
        (
            review(
                exit_review(3, call_touched=True),
                alternatives=(
                    exit_review(1),
                    exit_review(2, call_touched=True),
                ),
            ),
            review(
                exit_review(2),
                alternatives=(exit_review(1, put_touched=True),),
            ),
        )
    )

    assert metrics.earlier_safe_exit_rate == pytest.approx(0.5)


def test_detects_additional_risk_after_selected_exit() -> None:
    metrics = TradeReviewSummaryAnalyzer().analyze(
        (
            review(
                exit_review(1),
                alternatives=(
                    exit_review(2, call_touched=True),
                    exit_review(3, inside=False, call_touched=True),
                ),
            ),
            review(
                exit_review(1, put_touched=True),
                alternatives=(exit_review(2, put_touched=True),),
            ),
        )
    )

    assert metrics.later_risk_increase_rate == pytest.approx(0.5)


def test_rejects_empty_reviews() -> None:
    with pytest.raises(ValueError, match="reviews must not be empty"):
        TradeReviewSummaryAnalyzer().analyze(())
