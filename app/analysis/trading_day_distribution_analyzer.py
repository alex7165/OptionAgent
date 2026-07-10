from dataclasses import dataclass
from statistics import fmean, median

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)


@dataclass(frozen=True, slots=True)
class MoveDistribution:
    observation_count: int
    average_percent: float
    median_percent: float
    minimum_percent: float
    maximum_percent: float
    percentile_25: float
    percentile_75: float
    positive_ratio: float
    negative_ratio: float
    unchanged_ratio: float


@dataclass(frozen=True, slots=True)
class TradingDayDistribution:
    trading_day_index: int
    observation_count: int
    open_distribution: MoveDistribution
    high_distribution: MoveDistribution
    low_distribution: MoveDistribution
    close_distribution: MoveDistribution


class TradingDayDistributionAnalyzer:

    def analyze(
        self,
        price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ],
    ) -> tuple[TradingDayDistribution, ...]:
        moves_by_day: dict[int, list[object]] = {}

        for price_analysis in price_analyses:
            seen_day_indexes: set[int] = set()

            for daily_move in price_analysis.daily_moves:
                if daily_move.trading_day_index < 1:
                    raise ValueError(
                        "trading_day_index must be at least 1"
                    )

                if (
                    daily_move.trading_day_index
                    in seen_day_indexes
                ):
                    raise ValueError(
                        "daily_moves must contain unique "
                        "trading_day_index values per earnings event"
                    )

                seen_day_indexes.add(
                    daily_move.trading_day_index
                )
                moves_by_day.setdefault(
                    daily_move.trading_day_index,
                    [],
                ).append(daily_move)

        return tuple(
            self._build_trading_day_distribution(
                trading_day_index=trading_day_index,
                daily_moves=moves_by_day[trading_day_index],
            )
            for trading_day_index in sorted(moves_by_day)
        )

    def _build_trading_day_distribution(
        self,
        trading_day_index: int,
        daily_moves: list[object],
    ) -> TradingDayDistribution:
        open_values = tuple(
            move.open_percent
            for move in daily_moves
        )
        high_values = tuple(
            move.high_percent
            for move in daily_moves
        )
        low_values = tuple(
            move.low_percent
            for move in daily_moves
        )
        close_values = tuple(
            move.close_percent
            for move in daily_moves
        )

        return TradingDayDistribution(
            trading_day_index=trading_day_index,
            observation_count=len(daily_moves),
            open_distribution=self._build_distribution(
                open_values
            ),
            high_distribution=self._build_distribution(
                high_values
            ),
            low_distribution=self._build_distribution(
                low_values
            ),
            close_distribution=self._build_distribution(
                close_values
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