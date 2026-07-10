from app.marketdata.earnings_api_provider import EarningsApiProvider


class DummyResponse:

    def raise_for_status(self):
        pass

    def json(self):
        return [
            {
                "date": "2026-05-20",
                "symbol": "NVDA",
                "eps": {
                    "surprisePercent": 10.0,
                    "yoy": 142.8,
                    "beat": True,
                },
                "revenue": {
                    "surprisePercent": 4.1,
                    "yoy": 85.2,
                    "beat": True,
                },
                "reactions": [
                    {
                        "date": "2026-05-21",
                        "open": 222.29,
                        "high": 227.4,
                        "low": 217.93,
                        "close": 219.51,
                        "volume": 203381800,
                        "priceChange": -1.77,
                    },
                    {
                        "date": "2026-05-22",
                        "open": 220.9,
                        "high": 221.01,
                        "low": 214.8,
                        "close": 215.33,
                        "volume": 169275710,
                        "priceChange": -1.9,
                    },
                ],
            }
        ]


def test_gets_complete_historical_reaction(monkeypatch):
    def fake_get(url, params, timeout):
        assert params["symbol"] == "NVDA"
        assert params["apikey"] == "test-key"
        assert timeout == 30

        return DummyResponse()

    monkeypatch.setattr(
        "app.marketdata.earnings_api_provider.requests.get",
        fake_get,
    )

    provider = EarningsApiProvider(api_key="test-key")

    reactions = provider.get_historical_reactions("nvda")

    assert len(reactions) == 1

    earnings = reactions[0]

    assert earnings.symbol == "NVDA"
    assert earnings.eps_surprise_percent == 10.0
    assert earnings.eps_beat is True
    assert earnings.revenue_surprise_percent == 4.1
    assert len(earnings.reactions) == 2
    assert earnings.reactions[0].price_change_percent == -1.77
    assert earnings.reactions[1].close == 215.33