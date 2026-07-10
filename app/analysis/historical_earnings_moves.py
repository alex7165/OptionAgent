from dataclasses import dataclass
from statistics import mean, median


@dataclass(frozen=True, slots=True)
class HistoricalEarningsMove:
    move_percent: float

    @property
    def absolute_move_percent(self) -> float:
        return abs(self.move_percent)


@dataclass(frozen=True, slots=True)
class HistoricalEarningsMoves:
    moves: tuple[HistoricalEarningsMove, ...]

    @property
    def average_absolute_move_percent(self) -> float:
        return mean(
            move.absolute_move_percent
            for move in self.moves
        )

    @property
    def median_absolute_move_percent(self) -> float:
        return median(
            move.absolute_move_percent
            for move in self.moves
        )

    @property
    def maximum_up_move_percent(self) -> float:
        return max(
            (
                move.move_percent
                for move in self.moves
                if move.move_percent > 0
            ),
            default=0.0,
        )

    @property
    def maximum_down_move_percent(self) -> float:
        return min(
            (
                move.move_percent
                for move in self.moves
                if move.move_percent < 0
            ),
            default=0.0,
        )

    @property
    def moves_over_20_percent(self) -> int:
        return sum(
            move.absolute_move_percent > 20
            for move in self.moves
        )

    @property
    def moves_over_30_percent(self) -> int:
        return sum(
            move.absolute_move_percent > 30
            for move in self.moves
        )

    @property
    def maximum_absolute_move_percent(self) -> float:
        return max(
            (
                move.absolute_move_percent
                for move in self.moves
            ),
            default=0.0,
        )

    @property
    def is_upside_skewed(self) -> bool:
        return (
            self.maximum_up_move_percent
            > abs(self.maximum_down_move_percent)
        )

    @property
    def is_downside_skewed(self) -> bool:
        return (
            abs(self.maximum_down_move_percent)
            > self.maximum_up_move_percent
        )