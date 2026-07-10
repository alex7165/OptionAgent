from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.marketdata.models import ExpirationChain, OptionQuote


class WingSelector:

    def __init__(self):
        self.chain_analyzer = ExpirationChainAnalyzer()

    def width_for_price(self, underlying_price: float) -> float:
        if underlying_price < 50:
            return 2.5

        if underlying_price < 150:
            return 5

        if underlying_price < 300:
            return 10

        return 20

    def select_long_put(
        self,
        chain: ExpirationChain,
        short_put: OptionQuote,
        width: float,
    ) -> OptionQuote | None:
        target_strike = short_put.strike - width

        candidates = [
            quote
            for quote in self.chain_analyzer.get_puts(chain)
            if quote.strike < short_put.strike
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda quote: abs(quote.strike - target_strike),
        )

    def select_long_call(
        self,
        chain: ExpirationChain,
        short_call: OptionQuote,
        width: float,
    ) -> OptionQuote | None:
        target_strike = short_call.strike + width

        candidates = [
            quote
            for quote in self.chain_analyzer.get_calls(chain)
            if quote.strike > short_call.strike
        ]

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda quote: abs(quote.strike - target_strike),
        )