import pytest

from app.marketdata.barchart_volatility_provider import BarchartVolatilityProvider


@pytest.mark.integration
def test_barchart_volatility_provider_returns_iv_data():
    provider = BarchartVolatilityProvider(headless=False)

    iv_rank = provider.get_iv_rank("NVDA")
    iv_percentile = provider.get_iv_percentile("NVDA")

    assert iv_rank is not None
    assert iv_percentile is not None