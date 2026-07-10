from datetime import date

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)
from app.marketdata.price_history_provider import (
    PriceHistoryProvider,
)


class HistoricalEarningsPriceSeriesLoader:

    def __init__(
        self,
        price_history_provider: PriceHistoryProvider,
    ) -> None:
        self.price_history_provider = price_history_provider

    def load(
        self,
        earnings: HistoricalEarningsReaction,
        end_date: date,
    ) -> HistoricalEarningsPriceSeries:
        if end_date < earnings.report_date:
            raise ValueError(
                "end_date must be on or after the earnings report date"
            )

        daily_bars = self.price_history_provider.get_daily_bars(
            symbol=earnings.symbol,
            start_date=earnings.report_date,
            end_date=end_date,
        )

        return HistoricalEarningsPriceSeries(
            earnings=earnings,
            daily_bars=daily_bars,
        )