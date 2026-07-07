from app.analysis.earnings import EarningsAnalyzer
from app.marketdata.dummy_provider import DummyPriceProvider
from app.marketdata.service import MarketDataService


def create_analyzer():
    provider = DummyPriceProvider()
    market_data = MarketDataService(provider)
    return EarningsAnalyzer(market_data)


def test_earnings_analyzer_can_be_created():
    analyzer = create_analyzer()
    assert analyzer is not None


def test_analyze_returns_placeholder():
    analyzer = create_analyzer()
    result = analyzer.analyze("NVDA")

    assert result.summary == "NVDA: price 100.0 USD"