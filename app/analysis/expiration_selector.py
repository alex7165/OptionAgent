from datetime import date, timedelta

from app.marketdata.optionstrat_provider import OptionStratProvider


class ExpirationSelector:

    def __init__(self, option_provider: OptionStratProvider):
        self.option_provider = option_provider

    def select_earnings_week_expiration(
        self,
        symbol: str,
        earnings_date: date,
    ) -> date | None:
        target_expiration = self._friday_of_week(earnings_date)
        expirations = self.option_provider.get_expiration_dates(symbol)

        if target_expiration in expirations:
            return target_expiration

        return None

    def _friday_of_week(self, earnings_date: date) -> date:
        days_until_friday = 4 - earnings_date.weekday()
        return earnings_date + timedelta(days=days_until_friday)