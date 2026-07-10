from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.marketdata.price_history_provider import (
    PriceHistoryProvider,
)


class ReferencePriceResolver(Protocol):

    def resolve(
        self,
        price_series: HistoricalEarningsPriceSeries,
    ) -> float:
        ...


@dataclass(frozen=True, slots=True)
class FixedReferencePriceResolver:
    reference_price: float

    def resolve(
        self,
        price_series: HistoricalEarningsPriceSeries,
    ) -> float:
        return self.reference_price


@dataclass(frozen=True, slots=True)
class PreviousCloseReferencePriceResolver:
    price_history_provider: PriceHistoryProvider
    lookback_days: int = 10

    def __post_init__(self) -> None:
        if self.lookback_days < 1:
            raise ValueError(
                "lookback_days must be at least 1"
            )

    def resolve(
        self,
        price_series: HistoricalEarningsPriceSeries,
    ) -> float:
        earnings = price_series.earnings
        end_date = earnings.report_date - timedelta(days=1)
        start_date = (
            earnings.report_date
            - timedelta(days=self.lookback_days)
        )

        daily_bars = self.price_history_provider.get_daily_bars(
            symbol=earnings.symbol,
            start_date=start_date,
            end_date=end_date,
        )

        eligible_bars = tuple(
            bar
            for bar in daily_bars
            if bar.date < earnings.report_date
        )

        if not eligible_bars:
            raise ValueError(
                "No price history found before earnings date "
                f"for {earnings.symbol} on "
                f"{earnings.report_date.isoformat()}"
            )

        previous_bar = max(
            eligible_bars,
            key=lambda bar: bar.date,
        )

        if previous_bar.close <= 0:
            raise ValueError(
                "Previous close must be greater than zero"
            )

        return previous_bar.close