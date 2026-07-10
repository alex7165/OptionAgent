from dataclasses import dataclass

from app.analysis.historical_earnings_analysis import (
    HistoricalEarningsAnalysis,
)
from app.analysis.historical_earnings_price_analyzer import (
    HistoricalEarningsPriceAnalysis,
    HistoricalEarningsPriceAnalyzer,
)
from app.analysis.historical_price_statistics_analyzer import (
    HistoricalPriceStatistics,
    HistoricalPriceStatisticsAnalyzer,
)
from app.analysis.reference_price_resolver import (
    ReferencePriceResolver,
)


@dataclass(frozen=True, slots=True)
class HistoricalEarningsAnalysisResult:
    price_analyses: tuple[HistoricalEarningsPriceAnalysis, ...]
    statistics: HistoricalPriceStatistics


class HistoricalEarningsAnalysisAnalyzer:

    def __init__(
        self,
        price_analyzer: HistoricalEarningsPriceAnalyzer,
        statistics_analyzer: HistoricalPriceStatisticsAnalyzer,
    ) -> None:
        self.price_analyzer = price_analyzer
        self.statistics_analyzer = statistics_analyzer

    def analyze(
        self,
        analysis: HistoricalEarningsAnalysis,
        reference_price_resolver: ReferencePriceResolver,
    ) -> HistoricalEarningsAnalysisResult:
        price_analyses = tuple(
            self.price_analyzer.analyze(
                price_series=price_series,
                reference_price=reference_price_resolver.resolve(
                    price_series
                ),
            )
            for price_series in analysis.price_series
        )

        statistics = self.statistics_analyzer.analyze(
            price_analyses
        )

        return HistoricalEarningsAnalysisResult(
            price_analyses=price_analyses,
            statistics=statistics,
        )