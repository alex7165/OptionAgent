from dataclasses import dataclass
from enum import Enum

from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRisk,
    StrikeSide,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
)


class ExpectedMoveRiskAssessment(Enum):
    TIGHT = "tight"
    NEUTRAL = "neutral"
    WIDE = "wide"


@dataclass(frozen=True, slots=True)
class ExpectedMoveSideComparison:
    side: StrikeSide
    expected_move_threshold_percent: float
    matched_risk: HistoricalStrikeRisk
    next_outward_risk: HistoricalStrikeRisk | None
    threshold_difference_percent: float
    finish_outside_probability_difference: float | None
    reached_probability_difference: float | None
    assessment: ExpectedMoveRiskAssessment


@dataclass(frozen=True, slots=True)
class ExpectedMoveStrikeRiskComparison:
    expected_move_percent: float
    call_comparison: ExpectedMoveSideComparison | None
    put_comparison: ExpectedMoveSideComparison | None


class ExpectedMoveStrikeRiskComparator:

    def compare(
        self,
        expected_move_percent: float,
        risk_grid: HistoricalStrikeRiskGrid,
        target_finish_outside_probability: float,
        neutral_tolerance: float = 0.02,
    ) -> ExpectedMoveStrikeRiskComparison:
        if expected_move_percent <= 0:
            raise ValueError(
                "expected_move_percent must be greater than zero"
            )

        if not 0 <= target_finish_outside_probability <= 1:
            raise ValueError(
                "target_finish_outside_probability must be "
                "between 0 and 1"
            )

        if neutral_tolerance < 0:
            raise ValueError(
                "neutral_tolerance must not be negative"
            )

        return ExpectedMoveStrikeRiskComparison(
            expected_move_percent=expected_move_percent,
            call_comparison=self._compare_side(
                risks=risk_grid.call_risks,
                side=StrikeSide.CALL,
                expected_move_threshold_percent=(
                    expected_move_percent
                ),
                target_finish_outside_probability=(
                    target_finish_outside_probability
                ),
                neutral_tolerance=neutral_tolerance,
            ),
            put_comparison=self._compare_side(
                risks=risk_grid.put_risks,
                side=StrikeSide.PUT,
                expected_move_threshold_percent=(
                    -expected_move_percent
                ),
                target_finish_outside_probability=(
                    target_finish_outside_probability
                ),
                neutral_tolerance=neutral_tolerance,
            ),
        )

    def _compare_side(
        self,
        risks: tuple[HistoricalStrikeRisk, ...],
        side: StrikeSide,
        expected_move_threshold_percent: float,
        target_finish_outside_probability: float,
        neutral_tolerance: float,
    ) -> ExpectedMoveSideComparison | None:
        if not risks:
            return None

        self._validate_risks(
            risks=risks,
            side=side,
        )

        matched_index = min(
            range(len(risks)),
            key=lambda index: (
                abs(
                    risks[index].threshold_percent
                    - expected_move_threshold_percent
                ),
                self._distance_from_reference(
                    risks[index].threshold_percent
                ),
            ),
        )
        matched_risk = risks[matched_index]

        outward_risks = tuple(
            risk
            for risk in risks
            if self._is_farther_out(
                candidate_threshold=risk.threshold_percent,
                matched_threshold=(
                    matched_risk.threshold_percent
                ),
                side=side,
            )
        )

        next_outward_risk = (
            min(
                outward_risks,
                key=lambda risk: abs(
                    risk.threshold_percent
                    - matched_risk.threshold_percent
                ),
            )
            if outward_risks
            else None
        )

        return ExpectedMoveSideComparison(
            side=side,
            expected_move_threshold_percent=(
                expected_move_threshold_percent
            ),
            matched_risk=matched_risk,
            next_outward_risk=next_outward_risk,
            threshold_difference_percent=(
                matched_risk.threshold_percent
                - expected_move_threshold_percent
            ),
            finish_outside_probability_difference=(
                self._probability_difference(
                    current_probability=(
                        matched_risk.finish_outside_probability
                    ),
                    outward_probability=(
                        next_outward_risk
                        .finish_outside_probability
                        if next_outward_risk is not None
                        else None
                    ),
                )
            ),
            reached_probability_difference=(
                self._probability_difference(
                    current_probability=(
                        matched_risk.reached_probability
                    ),
                    outward_probability=(
                        next_outward_risk.reached_probability
                        if next_outward_risk is not None
                        else None
                    ),
                )
            ),
            assessment=self._assess(
                finish_outside_probability=(
                    matched_risk.finish_outside_probability
                ),
                target_finish_outside_probability=(
                    target_finish_outside_probability
                ),
                neutral_tolerance=neutral_tolerance,
            ),
        )

    @staticmethod
    def _validate_risks(
        risks: tuple[HistoricalStrikeRisk, ...],
        side: StrikeSide,
    ) -> None:
        if any(risk.side is not side for risk in risks):
            raise ValueError(
                f"{side.value} risks must all use "
                f"{side.value} side"
            )

        exit_day_indexes = {
            risk.exit_trading_day_index
            for risk in risks
        }

        if len(exit_day_indexes) != 1:
            raise ValueError(
                f"{side.value} risks must use the same "
                "exit_trading_day_index"
            )

        observation_counts = {
            risk.observation_count
            for risk in risks
        }

        if len(observation_counts) != 1:
            raise ValueError(
                f"{side.value} risks must use the same "
                "observation_count"
            )

    @staticmethod
    def _distance_from_reference(
        threshold_percent: float,
    ) -> float:
        return abs(threshold_percent)

    @staticmethod
    def _is_farther_out(
        candidate_threshold: float,
        matched_threshold: float,
        side: StrikeSide,
    ) -> bool:
        if side is StrikeSide.CALL:
            return candidate_threshold > matched_threshold

        return candidate_threshold < matched_threshold

    @staticmethod
    def _probability_difference(
        current_probability: float,
        outward_probability: float | None,
    ) -> float | None:
        if outward_probability is None:
            return None

        return (
            outward_probability
            - current_probability
        )

    @staticmethod
    def _assess(
        finish_outside_probability: float,
        target_finish_outside_probability: float,
        neutral_tolerance: float,
    ) -> ExpectedMoveRiskAssessment:
        upper_limit = (
            target_finish_outside_probability
            + neutral_tolerance
        )
        lower_limit = max(
            0.0,
            target_finish_outside_probability
            - neutral_tolerance,
        )

        if finish_outside_probability > upper_limit:
            return ExpectedMoveRiskAssessment.TIGHT

        if finish_outside_probability < lower_limit:
            return ExpectedMoveRiskAssessment.WIDE

        return ExpectedMoveRiskAssessment.NEUTRAL