import yfinance as yf

from app.marketdata.earnings_provider import EarningsProvider
from app.marketdata.models import EarningsEvent


class YahooEarningsProvider(EarningsProvider):

    def get_earnings(self, symbol: str) -> EarningsEvent | None:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar

        earnings_dates = calendar.get("Earnings Date")

        if not earnings_dates:
            return None

        report_date = earnings_dates[0]

        return EarningsEvent(
            symbol=symbol.upper(),
            report_date=report_date,
            timing=None,
            source="yahoo",
        )