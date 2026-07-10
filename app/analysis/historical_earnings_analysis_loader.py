from collections.abc import Callable
from datetime import date
from typing import Protocol

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsAnalysis,
)
from app.analysis.historical_earnings_price_series_loader import (
    HistoricalEarningsPriceSeriesLoader,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


class HistoricalEarningsReactionProvider(Protocol):

    def get_historical_reactions(
        self,
        symbol: str,
    ) -> tuple[HistoricalEarningsReaction, ...]:
        ...


class HistoricalEarningsAnalysisLoader:

    def __init__(
        self,
        earnings_provider: HistoricalEarningsReactionProvider,
        price_series_loader: HistoricalEarningsPriceSeriesLoader,
    ) -> None:
        self.earnings_provider = earnings_provider
        self.price_series_loader = price_series_loader

    def load(
        self,
        symbol: str,
        end_date_resolver: Callable[
            [HistoricalEarningsReaction],
            date,
        ],
    ) -> HistoricalEarningsAnalysis:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("symbol must not be empty")

        earnings_reactions = (
            self.earnings_provider.get_historical_reactions(
                normalized_symbol
            )
        )

        price_series = tuple(
            self.price_series_loader.load(
                earnings=earnings,
                end_date=end_date_resolver(earnings),
            )
            for earnings in earnings_reactions
        )

        return HistoricalEarningsAnalysis(
            price_series=price_series,
        )