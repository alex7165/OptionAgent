from app.marketdata.dummy_provider import DummyStockDataProvider
from app.marketdata.service import MarketDataService


def test_market_data_service_returns_stock_data():
    provider = DummyStockDataProvider()
    market_data = MarketDataService(provider)

    stock = market_data.get_stock("nvda")

    assert stock.symbol == "NVDA"
    assert stock.price == 100.0
    assert stock.currency == "USD"
    assert stock.source == "dummy"