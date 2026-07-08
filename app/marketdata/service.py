from datetime import date

from app.marketdata.earnings_calendar_provider import EarningsCalendarProvider
from app.marketdata.earnings_provider import EarningsProvider
from app.marketdata.models import EarningsEvent, MarketSnapshot
from app.marketdata.option_data_provider import OptionDataProvider
from app.marketdata.provider import PriceProvider


class MarketDataService:

    def __init__(
        self,
        price_provider: PriceProvider,
        earnings_provider: EarningsProvider | None = None,
        earnings_calendar_provider: EarningsCalendarProvider | None = None,
        option_data_provider: OptionDataProvider | None = None,
    ):
        self.price_provider = price_provider
        self.earnings_provider = earnings_provider
        self.earnings_calendar_provider = earnings_calendar_provider
        self.option_data_provider = option_data_provider

    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        quote = self.price_provider.get_quote(symbol)
        earnings = None

        if self.earnings_provider is not None:
            earnings = self.earnings_provider.get_earnings(symbol)

        return MarketSnapshot(
            symbol=symbol.upper(),
            quote=quote,
            earnings=earnings,
        )

    def get_earnings_events(
        self,
        start_date: date,
        end_date: date,
    ) -> list[EarningsEvent]:
        if self.earnings_calendar_provider is None:
            return []

        return self.earnings_calendar_provider.get_events(
            start_date,
            end_date,
        )

    def get_option_data(self, symbol: str):
        if self.option_data_provider is None:
            return None

        return self.option_data_provider.get_option_data(symbol)