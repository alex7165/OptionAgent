from dataclasses import dataclass
from datetime import date

from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class DailyMove:
    trading_day_index: int
    date: date
    open_percent: float
    high_percent: float
    low_percent: float
    close_percent: float


class DailyMoveAnalyzer:

    def analyze(
        self,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
    ) -> tuple[DailyMove, ...]:
        if reference_price <= 0:
            raise ValueError(
                "reference_price must be greater than zero"
            )

        if any(
            current.date >= following.date
            for current, following in zip(
                daily_bars,
                daily_bars[1:],
            )
        ):
            raise ValueError(
                "daily_bars must be ordered by ascending unique date"
            )

        return tuple(
            DailyMove(
                trading_day_index=index,
                date=bar.date,
                open_percent=self._calculate_percent(
                    price=bar.open,
                    reference_price=reference_price,
                ),
                high_percent=self._calculate_percent(
                    price=bar.high,
                    reference_price=reference_price,
                ),
                low_percent=self._calculate_percent(
                    price=bar.low,
                    reference_price=reference_price,
                ),
                close_percent=self._calculate_percent(
                    price=bar.close,
                    reference_price=reference_price,
                ),
            )
            for index, bar in enumerate(
                daily_bars,
                start=1,
            )
        )

    @staticmethod
    def _calculate_percent(
        price: float,
        reference_price: float,
    ) -> float:
        return (
            price / reference_price - 1
        ) * 100