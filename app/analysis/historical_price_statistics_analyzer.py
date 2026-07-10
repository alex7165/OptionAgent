from dataclasses import dataclass
from statistics import fmean, median

from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
)


@dataclass(frozen=True, slots=True)
class HistoricalPriceStatistics:
    earnings_count: int
    average_max_gain_percent: float | None
    average_max_loss_percent: float | None
    highest_max_gain_percent: float | None
    worst_max_loss_percent: float | None
    median_max_gain_percent: float | None
    median_max_loss_percent: float | None


class HistoricalPriceStatisticsAnalyzer:

    def analyze(
        self,
        price_analyses: tuple[
            HistoricalEarningsPriceAnalysis,
            ...,
        ],
    ) -> HistoricalPriceStatistics:
        if not price_analyses:
            return HistoricalPriceStatistics(
                earnings_count=0,
                average_max_gain_percent=None,
                average_max_loss_percent=None,
                highest_max_gain_percent=None,
                worst_max_loss_percent=None,
                median_max_gain_percent=None,
                median_max_loss_percent=None,
            )

        max_gains = tuple(
            analysis.price_analysis.max_gain_percent
            for analysis in price_analyses
        )
        max_losses = tuple(
            analysis.price_analysis.max_loss_percent
            for analysis in price_analyses
        )

        return HistoricalPriceStatistics(
            earnings_count=len(price_analyses),
            average_max_gain_percent=fmean(max_gains),
            average_max_loss_percent=fmean(max_losses),
            highest_max_gain_percent=max(max_gains),
            worst_max_loss_percent=min(max_losses),
            median_max_gain_percent=median(max_gains),
            median_max_loss_percent=median(max_losses),
        )