from datetime import date

from app.analysis.earnings_crush_analyzer import EarningsCrushAnalyzer
from app.marketdata.dummy_provider import DummyPriceProvider
from app.marketdata.service import MarketDataService
from app.marketdata.models import EarningsEvent


def test_create_candidates():
    market_data = MarketDataService(DummyPriceProvider())
    analyzer = EarningsCrushAnalyzer(market_data)

    events = [
        EarningsEvent(
            symbol="NVDA",
            report_date=date(2026, 8, 26),
            timing="after market close",
            source="test",
        ),
        EarningsEvent(
            symbol="AAPL",
            report_date=date(2026, 8, 27),
            timing="after market close",
            source="test",
        ),
    ]

    candidates = analyzer.create_candidates(events)

    assert len(candidates) == 2
    assert candidates[0].earnings_event.symbol == "NVDA"
    assert candidates[0].snapshot is not None
    assert candidates[0].snapshot.quote.price == 100.0
    assert candidates[1].earnings_event.symbol == "AAPL"
    assert "has_market_snapshot" in candidates[0].passed_rules
    assert candidates[0].snapshot.quote.price == 100.0