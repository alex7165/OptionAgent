from app.analysis.earnings import EarningsAnalyzer
from app.marketdata.dummy_earnings_provider import DummyEarningsProvider
from app.marketdata.dummy_provider import DummyPriceProvider
from app.marketdata.service import MarketDataService


def create_analyzer():
    price_provider = DummyPriceProvider()
    earnings_provider = DummyEarningsProvider()
    market_data = MarketDataService(price_provider, earnings_provider)
    return EarningsAnalyzer(market_data)


def test_earnings_analyzer_can_be_created():
    analyzer = create_analyzer()
    assert analyzer is not None


def test_analyze_returns_market_price_summary():
    analyzer = create_analyzer()
    result = analyzer.analyze("NVDA")

    assert result.symbol == "NVDA"
    assert result.summary == "NVDA: price 100.0 USD"
    assert result.snapshot.quote.price == 100.0

    assert result.snapshot.earnings is not None
    assert result.snapshot.earnings.symbol == "NVDA"
    assert result.snapshot.earnings.source == "dummy"

    assert result.snapshot.earnings.report_date.year == 2026
    assert result.snapshot.earnings.timing == "after market close"