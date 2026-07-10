from dataclasses import dataclass
from statistics import fmean, median

from app.analysis.historical_outcome_analyzer import (
    HistoricalOutcome,
)
from app.analysis.trading_day_distribution_analyzer import (
    MoveDistribution,
)


@dataclass(frozen=True, slots=True)
class HistoricalOutcomeDistribution:
    exit_trading_day_index: int
    observation_count: int
    exit_close_distribution: MoveDistribution
    highest_until_exit_distribution: MoveDistribution
    lowest_until_exit_distribution: MoveDistribution


class HistoricalOutcomeDistributionAnalyzer:

    def analyze(
        self,
        outcomes: tuple[HistoricalOutcome, ...],
    ) -> tuple[HistoricalOutcomeDistribution, ...]:
        outcomes_by_exit_day: dict[
            int,
            list[HistoricalOutcome],
        ] = {}

        for outcome in outcomes:
            if outcome.exit_trading_day_index < 1:
                raise ValueError(
                    "exit_trading_day_index must be at least 1"
                )

            outcomes_by_exit_day.setdefault(
                outcome.exit_trading_day_index,
                [],
            ).append(outcome)

        return tuple(
            self._build_outcome_distribution(
                exit_trading_day_index=exit_day,
                outcomes=outcomes_by_exit_day[exit_day],
            )
            for exit_day in sorted(outcomes_by_exit_day)
        )

    def _build_outcome_distribution(
        self,
        exit_trading_day_index: int,
        outcomes: list[HistoricalOutcome],
    ) -> HistoricalOutcomeDistribution:
        exit_close_values = tuple(
            outcome.exit_close_percent
            for outcome in outcomes
        )
        highest_values = tuple(
            outcome.highest_percent_until_exit
            for outcome in outcomes
        )
        lowest_values = tuple(
            outcome.lowest_percent_until_exit
            for outcome in outcomes
        )

        return HistoricalOutcomeDistribution(
            exit_trading_day_index=exit_trading_day_index,
            observation_count=len(outcomes),
            exit_close_distribution=self._build_distribution(
                exit_close_values
            ),
            highest_until_exit_distribution=(
                self._build_distribution(
                    highest_values
                )
            ),
            lowest_until_exit_distribution=(
                self._build_distribution(
                    lowest_values
                )
            ),
        )

    def _build_distribution(
        self,
        values: tuple[float, ...],
    ) -> MoveDistribution:
        observation_count = len(values)

        return MoveDistribution(
            observation_count=observation_count,
            average_percent=fmean(values),
            median_percent=median(values),
            minimum_percent=min(values),
            maximum_percent=max(values),
            percentile_25=self._percentile(
                values=values,
                percentile=0.25,
            ),
            percentile_75=self._percentile(
                values=values,
                percentile=0.75,
            ),
            positive_ratio=(
                sum(value > 0 for value in values)
                / observation_count
            ),
            negative_ratio=(
                sum(value < 0 for value in values)
                / observation_count
            ),
            unchanged_ratio=(
                sum(value == 0 for value in values)
                / observation_count
            ),
        )

    @staticmethod
    def _percentile(
        values: tuple[float, ...],
        percentile: float,
    ) -> float:
        ordered_values = sorted(values)

        if len(ordered_values) == 1:
            return ordered_values[0]

        position = percentile * (
            len(ordered_values) - 1
        )
        lower_index = int(position)
        upper_index = min(
            lower_index + 1,
            len(ordered_values) - 1,
        )
        fraction = position - lower_index

        lower_value = ordered_values[lower_index]
        upper_value = ordered_values[upper_index]

        return lower_value + (
            upper_value - lower_value
        ) * fraction