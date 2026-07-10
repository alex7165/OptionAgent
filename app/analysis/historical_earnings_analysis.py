from dataclasses import dataclass

from app.analysis.historical_earnings_moves import (
    HistoricalEarningsMove,
    HistoricalEarningsMoves,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class HistoricalEarningsPriceSeries:
    earnings: HistoricalEarningsReaction
    daily_bars: tuple[DailyBar, ...]


@dataclass(frozen=True, slots=True)
class HistoricalEarningsOutcome:
    first_day_move_percent: float
    expiration_week_move_percent: float

    @property
    def recovery_ratio(self) -> float:
        first_day_absolute = abs(self.first_day_move_percent)

        if first_day_absolute == 0:
            return 0.0

        remaining_move = abs(self.expiration_week_move_percent)

        if (
            self.first_day_move_percent
            * self.expiration_week_move_percent
            <= 0
        ):
            return 1.0

        recovery = 1 - (remaining_move / first_day_absolute)

        return max(0.0, min(recovery, 1.0))

    @property
    def continued_move(self) -> bool:
        same_direction = (
            self.first_day_move_percent
            * self.expiration_week_move_percent
            > 0
        )

        return (
            same_direction
            and abs(self.expiration_week_move_percent)
            > abs(self.first_day_move_percent)
        )


@dataclass(frozen=True, slots=True)
class HistoricalEarningsAnalysis:
    outcomes: tuple[HistoricalEarningsOutcome, ...] = ()
    price_series: tuple[HistoricalEarningsPriceSeries, ...] = ()

    @property
    def first_day_moves(self) -> HistoricalEarningsMoves:
        return HistoricalEarningsMoves(
            moves=tuple(
                HistoricalEarningsMove(
                    move_percent=outcome.first_day_move_percent
                )
                for outcome in self.outcomes
            )
        )

    @property
    def expiration_week_moves(self) -> HistoricalEarningsMoves:
        return HistoricalEarningsMoves(
            moves=tuple(
                HistoricalEarningsMove(
                    move_percent=outcome.expiration_week_move_percent
                )
                for outcome in self.outcomes
            )
        )

    @property
    def recovery_ratios(self) -> tuple[float, ...]:
        return tuple(
            outcome.recovery_ratio
            for outcome in self.outcomes
        )

    @property
    def continued_move_flags(self) -> tuple[bool, ...]:
        return tuple(
            outcome.continued_move
            for outcome in self.outcomes
        )