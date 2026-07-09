from datetime import date

from app.analysis.expiration_selector import ExpirationSelector


class FakeOptionProvider:

    def get_expiration_dates(self, symbol: str):
        return [
            date(2026, 7, 10),
            date(2026, 7, 17),
        ]


class FakeOptionProviderWithoutMatchingExpiration:

    def get_expiration_dates(self, symbol: str):
        return [
            date(2026, 7, 24),
        ]


def test_selects_friday_of_earnings_week():
    selector = ExpirationSelector(FakeOptionProvider())

    expiration = selector.select_earnings_week_expiration(
        symbol="NVDA",
        earnings_date=date(2026, 7, 9),
    )

    assert expiration == date(2026, 7, 10)


def test_returns_none_when_earnings_week_expiration_is_missing():
    selector = ExpirationSelector(FakeOptionProviderWithoutMatchingExpiration())

    expiration = selector.select_earnings_week_expiration(
        symbol="NVDA",
        earnings_date=date(2026, 7, 14),
    )

    assert expiration is None