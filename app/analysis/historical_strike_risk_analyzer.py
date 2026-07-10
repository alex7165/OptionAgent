from dataclasses import dataclass
from enum import Enum

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)


class StrikeSide(Enum):
    CALL = "call"
    PUT = "put"


@dataclass(frozen=True, slots=True)
class HistoricalStrikeRisk:
    side: StrikeSide
    threshold_percent: float
    exit_trading_day_index: int
    observation_count: int
    finish_inside_probability: float
    finish_outside_probability: float
    reached_probability: float
    worst_historical_move_percent: float


class HistoricalStrikeRiskAnalyzer:

    def analyze(
        self,
        outcomes: tuple[HistoricalOutcome, ...],
        side: StrikeSide,
        threshold_percent: float,
    ) -> HistoricalStrikeRisk:
        if not outcomes:
            raise ValueError(
                "outcomes must not be empty"
            )

        self._validate_threshold(
            side=side,
            threshold_percent=threshold_percent,
        )

        exit_day_indexes = {
            outcome.exit_trading_day_index
            for outcome in outcomes
        }

        if len(exit_day_indexes) != 1:
            raise ValueError(
                "outcomes must use the same "
                "exit_trading_day_index"
            )

        exit_trading_day_index = next(
            iter(exit_day_indexes)
        )
        observation_count = len(outcomes)

        finish_outside_count = sum(
            self._finished_outside(
                outcome=outcome,
                side=side,
                threshold_percent=threshold_percent,
            )
            for outcome in outcomes
        )

        reached_count = sum(
            self._reached_threshold(
                outcome=outcome,
                side=side,
                threshold_percent=threshold_percent,
            )
            for outcome in outcomes
        )

        finish_outside_probability = (
            finish_outside_count / observation_count
        )

        return HistoricalStrikeRisk(
            side=side,
            threshold_percent=threshold_percent,
            exit_trading_day_index=exit_trading_day_index,
            observation_count=observation_count,
            finish_inside_probability=(
                1.0 - finish_outside_probability
            ),
            finish_outside_probability=(
                finish_outside_probability
            ),
            reached_probability=(
                reached_count / observation_count
            ),
            worst_historical_move_percent=(
                self._worst_historical_move(
                    outcomes=outcomes,
                    side=side,
                )
            ),
        )

    @staticmethod
    def _validate_threshold(
        side: StrikeSide,
        threshold_percent: float,
    ) -> None:
        if (
            side is StrikeSide.CALL
            and threshold_percent <= 0
        ):
            raise ValueError(
                "Call threshold_percent must be "
                "greater than zero"
            )

        if (
            side is StrikeSide.PUT
            and threshold_percent >= 0
        ):
            raise ValueError(
                "Put threshold_percent must be "
                "less than zero"
            )

    @staticmethod
    def _finished_outside(
        outcome: HistoricalOutcome,
        side: StrikeSide,
        threshold_percent: float,
    ) -> bool:
        if side is StrikeSide.CALL:
            return (
                outcome.exit_close_percent
                > threshold_percent
            )

        return (
            outcome.exit_close_percent
            < threshold_percent
        )

    @staticmethod
    def _reached_threshold(
        outcome: HistoricalOutcome,
        side: StrikeSide,
        threshold_percent: float,
    ) -> bool:
        if side is StrikeSide.CALL:
            return (
                outcome.highest_percent_until_exit
                >= threshold_percent
            )

        return (
            outcome.lowest_percent_until_exit
            <= threshold_percent
        )

    @staticmethod
    def _worst_historical_move(
        outcomes: tuple[HistoricalOutcome, ...],
        side: StrikeSide,
    ) -> float:
        if side is StrikeSide.CALL:
            return max(
                outcome.highest_percent_until_exit
                for outcome in outcomes
            )

        return min(
            outcome.lowest_percent_until_exit
            for outcome in outcomes
        )