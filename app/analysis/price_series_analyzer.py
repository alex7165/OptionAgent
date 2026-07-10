from dataclasses import dataclass
from datetime import date

from app.marketdata.price_history_provider import DailyBar


@dataclass(frozen=True, slots=True)
class PriceSeriesAnalysis:
    reference_price: float
    first_date: date
    last_date: date
    first_open: float
    first_close: float
    last_close: float
    highest_high: float
    lowest_low: float
    max_gain_percent: float
    max_loss_percent: float


class PriceSeriesAnalyzer:

    def analyze(
        self,
        daily_bars: tuple[DailyBar, ...],
        reference_price: float,
    ) -> PriceSeriesAnalysis:
        if not daily_bars:
            raise ValueError("daily_bars must not be empty")

        if reference_price <= 0:
            raise ValueError("reference_price must be greater than zero")

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

        first_bar = daily_bars[0]
        last_bar = daily_bars[-1]

        highest_high = max(
            bar.high
            for bar in daily_bars
        )
        lowest_low = min(
            bar.low
            for bar in daily_bars
        )

        max_gain_percent = (
            highest_high / reference_price - 1
        ) * 100
        max_loss_percent = (
            lowest_low / reference_price - 1
        ) * 100

        return PriceSeriesAnalysis(
            reference_price=reference_price,
            first_date=first_bar.date,
            last_date=last_bar.date,
            first_open=first_bar.open,
            first_close=first_bar.close,
            last_close=last_bar.close,
            highest_high=highest_high,
            lowest_low=lowest_low,
            max_gain_percent=max_gain_percent,
            max_loss_percent=max_loss_percent,
        )