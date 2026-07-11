from dataclasses import dataclass
from enum import Enum

from app.analysis.historical_strike_risk_analyzer import (
    HistoricalStrikeRisk,
    StrikeSide,
)
from app.analysis.historical_strike_risk_grid_analyzer import (
    HistoricalStrikeRiskGrid,
)


class HistoricalStrikeSelectionReason(Enum):
    EXPECTED_MOVE_MATCH = "expected_move_match"
    ADJUSTED_INWARD = "adjusted_inward"
    ADJUSTED_OUTWARD = "adjusted_outward"


@dataclass(frozen=True, slots=True)
class HistoricalStrikeSelectionPolicy:
    max_finish_outside_probability: float
    max_reached_probability: float | None = None
    allow_inward_adjustment: bool = True
    prefer_farther_on_tie: bool = True

    def __post_init__(self) -> None:
        if not (
            0
            <= self.max_finish_outside_probability
            <= 1
        ):
            raise ValueError(
                "max_finish_outside_probability must be "
                "between 0 and 1"
            )

        if (
            self.max_reached_probability is not None
            and not (
                0
                <= self.max_reached_probability
                <= 1
            )
        ):
            raise ValueError(
                "max_reached_probability must be "
                "between 0 and 1"
            )


@dataclass(frozen=True, slots=True)
class HistoricalStrikeRecommendation:
    side: StrikeSide
    recommended_threshold_percent: float
    expected_move_threshold_percent: float
    adjustment_from_expected_move: float
    finish_outside_probability: float
    reached_probability: float
    exit_trading_day_index: int
    observation_count: int
    reason: HistoricalStrikeSelectionReason


@dataclass(frozen=True, slots=True)
class HistoricalStrikeSelection:
    expected_move_percent: float
    call_recommendation: HistoricalStrikeRecommendation | None
    put_recommendation: HistoricalStrikeRecommendation | None


class HistoricalStrikeSelector:

    def select(
        self,
        risk_grid: HistoricalStrikeRiskGrid,
        expected_move_percent: float,
        policy: HistoricalStrikeSelectionPolicy,
    ) -> HistoricalStrikeSelection:
        if expected_move_percent <= 0:
            raise ValueError(
                "expected_move_percent must be greater than zero"
            )

        return HistoricalStrikeSelection(
            expected_move_percent=expected_move_percent,
            call_recommendation=self._select_side(
                risks=risk_grid.call_risks,
                side=StrikeSide.CALL,
                expected_move_threshold_percent=(
                    expected_move_percent
                ),
                policy=policy,
            ),
            put_recommendation=self._select_side(
                risks=risk_grid.put_risks,
                side=StrikeSide.PUT,
                expected_move_threshold_percent=(
                    -expected_move_percent
                ),
                policy=policy,
            ),
        )

    def _select_side(
        self,
        risks: tuple[HistoricalStrikeRisk, ...],
        side: StrikeSide,
        expected_move_threshold_percent: float,
        policy: HistoricalStrikeSelectionPolicy,
    ) -> HistoricalStrikeRecommendation | None:
        if not risks:
            return None

        self._validate_risks(
            risks=risks,
            side=side,
        )

        acceptable_risks = tuple(
            risk
            for risk in risks
            if self._is_acceptable(
                risk=risk,
                policy=policy,
            )
            and (
                policy.allow_inward_adjustment
                or self._is_at_or_outside_expected_move(
                    threshold_percent=risk.threshold_percent,
                    expected_move_threshold_percent=(
                        expected_move_threshold_percent
                    ),
                )
            )
        )

        if not acceptable_risks:
            return None

        selected_risk = min(
            acceptable_risks,
            key=lambda risk: self._selection_key(
                risk=risk,
                expected_move_threshold_percent=(
                    expected_move_threshold_percent
                ),
                prefer_farther_on_tie=(
                    policy.prefer_farther_on_tie
                ),
            ),
        )

        adjustment = (
            selected_risk.threshold_percent
            - expected_move_threshold_percent
        )

        return HistoricalStrikeRecommendation(
            side=side,
            recommended_threshold_percent=(
                selected_risk.threshold_percent
            ),
            expected_move_threshold_percent=(
                expected_move_threshold_percent
            ),
            adjustment_from_expected_move=adjustment,
            finish_outside_probability=(
                selected_risk.finish_outside_probability
            ),
            reached_probability=(
                selected_risk.reached_probability
            ),
            exit_trading_day_index=(
                selected_risk.exit_trading_day_index
            ),
            observation_count=selected_risk.observation_count,
            reason=self._selection_reason(
                selected_threshold_percent=(
                    selected_risk.threshold_percent
                ),
                expected_move_threshold_percent=(
                    expected_move_threshold_percent
                ),
            ),
        )

    @staticmethod
    def _is_acceptable(
        risk: HistoricalStrikeRisk,
        policy: HistoricalStrikeSelectionPolicy,
    ) -> bool:
        if (
            risk.finish_outside_probability
            > policy.max_finish_outside_probability
        ):
            return False

        if (
            policy.max_reached_probability is not None
            and risk.reached_probability
            > policy.max_reached_probability
        ):
            return False

        return True

    @staticmethod
    def _is_at_or_outside_expected_move(
        threshold_percent: float,
        expected_move_threshold_percent: float,
    ) -> bool:
        return (
            abs(threshold_percent)
            >= abs(expected_move_threshold_percent)
        )

    @staticmethod
    def _selection_key(
        risk: HistoricalStrikeRisk,
        expected_move_threshold_percent: float,
        prefer_farther_on_tie: bool,
    ) -> tuple[float, float]:
        difference = abs(
            risk.threshold_percent
            - expected_move_threshold_percent
        )
        distance_from_reference = abs(
            risk.threshold_percent
        )

        tie_breaker = (
            -distance_from_reference
            if prefer_farther_on_tie
            else distance_from_reference
        )

        return (
            difference,
            tie_breaker,
        )

    @staticmethod
    def _selection_reason(
        selected_threshold_percent: float,
        expected_move_threshold_percent: float,
    ) -> HistoricalStrikeSelectionReason:
        selected_distance = abs(
            selected_threshold_percent
        )
        expected_distance = abs(
            expected_move_threshold_percent
        )

        if selected_distance == expected_distance:
            return (
                HistoricalStrikeSelectionReason
                .EXPECTED_MOVE_MATCH
            )

        if selected_distance < expected_distance:
            return (
                HistoricalStrikeSelectionReason
                .ADJUSTED_INWARD
            )

        return (
            HistoricalStrikeSelectionReason
            .ADJUSTED_OUTWARD
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