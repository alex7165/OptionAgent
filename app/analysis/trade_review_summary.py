from __future__ import annotations

from dataclasses import dataclass

from app.analysis.trade_review import TradeReview


@dataclass(frozen=True, slots=True)
class TradeReviewMetrics:
    observation_count: int
    very_good_rate: float
    successful_with_touch_rate: float
    strike_violation_rate: float
    put_touch_rate: float
    call_touch_rate: float
    earlier_safe_exit_rate: float
    later_risk_increase_rate: float
    average_selected_exit_trading_day: float
    average_max_adverse_move_percent: float
    average_max_favorable_move_percent: float


class TradeReviewSummaryAnalyzer:
    """Aggregate multiple structured trade reviews.

    The summary measures how well the selected exits controlled the observed
    underlying path. It intentionally does not infer option P&L.
    """

    def analyze(
        self,
        reviews: tuple[TradeReview, ...],
    ) -> TradeReviewMetrics:
        if not reviews:
            raise ValueError("reviews must not be empty")

        count = len(reviews)

        very_good_count = sum(
            review.selected_exit.finished_inside_short_strikes
            and not review.selected_exit.put_touched
            and not review.selected_exit.call_touched
            for review in reviews
        )
        successful_with_touch_count = sum(
            review.selected_exit.finished_inside_short_strikes
            and (
                review.selected_exit.put_touched
                or review.selected_exit.call_touched
            )
            for review in reviews
        )
        violation_count = sum(
            not review.selected_exit.finished_inside_short_strikes
            for review in reviews
        )

        return TradeReviewMetrics(
            observation_count=count,
            very_good_rate=very_good_count / count,
            successful_with_touch_rate=successful_with_touch_count / count,
            strike_violation_rate=violation_count / count,
            put_touch_rate=sum(
                review.selected_exit.put_touched for review in reviews
            ) / count,
            call_touch_rate=sum(
                review.selected_exit.call_touched for review in reviews
            ) / count,
            earlier_safe_exit_rate=sum(
                self._has_earlier_safe_exit(review) for review in reviews
            ) / count,
            later_risk_increase_rate=sum(
                self._has_later_risk_increase(review) for review in reviews
            ) / count,
            average_selected_exit_trading_day=sum(
                review.selected_exit.trading_day_index for review in reviews
            ) / count,
            average_max_adverse_move_percent=sum(
                review.max_adverse_move_percent for review in reviews
            ) / count,
            average_max_favorable_move_percent=sum(
                review.max_favorable_move_percent for review in reviews
            ) / count,
        )

    @staticmethod
    def _has_earlier_safe_exit(review: TradeReview) -> bool:
        selected_day = review.selected_exit.trading_day_index
        return any(
            alternative.trading_day_index < selected_day
            and alternative.finished_inside_short_strikes
            and not alternative.put_touched
            and not alternative.call_touched
            for alternative in review.alternative_exits
        )

    @staticmethod
    def _has_later_risk_increase(review: TradeReview) -> bool:
        selected_day = review.selected_exit.trading_day_index
        selected_put_touch = review.selected_exit.put_touched
        selected_call_touch = review.selected_exit.call_touched

        return any(
            alternative.trading_day_index > selected_day
            and (
                not alternative.finished_inside_short_strikes
                or (
                    alternative.put_touched
                    and not selected_put_touch
                )
                or (
                    alternative.call_touched
                    and not selected_call_touch
                )
            )
            for alternative in review.alternative_exits
        )
