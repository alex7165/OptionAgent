from dataclasses import dataclass

from app.analysis.daily_move_analyzer import (
    DailyMove,
    DailyMoveAnalyzer,
)
from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsPriceSeries,
)
from app.analysis.price_series_analyzer import (
    PriceSeriesAnalysis,
    PriceSeriesAnalyzer,
)
from app.marketdata.earnings_api_provider import (
    HistoricalEarningsReaction,
)


@dataclass(frozen=True, slots=True)
class HistoricalEarningsPriceAnalysis:
    earnings: HistoricalEarningsReaction
    price_analysis: PriceSeriesAnalysis
    daily_moves: tuple[DailyMove, ...] = ()


class HistoricalEarningsPriceAnalyzer:

    def __init__(
        self,
        price_series_analyzer: PriceSeriesAnalyzer,
        daily_move_analyzer: DailyMoveAnalyzer | None = None,
    ) -> None:
        self.price_series_analyzer = price_series_analyzer
        self.daily_move_analyzer = (
            daily_move_analyzer
            if daily_move_analyzer is not None
            else DailyMoveAnalyzer()
        )

    def analyze(
        self,
        price_series: HistoricalEarningsPriceSeries,
        reference_price: float,
    ) -> HistoricalEarningsPriceAnalysis:
        price_analysis = self.price_series_analyzer.analyze(
            daily_bars=price_series.daily_bars,
            reference_price=reference_price,
        )

        daily_moves = self.daily_move_analyzer.analyze(
            daily_bars=price_series.daily_bars,
            reference_price=reference_price,
        )

        return HistoricalEarningsPriceAnalysis(
            earnings=price_series.earnings,
            price_analysis=price_analysis,
            daily_moves=daily_moves,
        )