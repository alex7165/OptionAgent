from app.marketdata.models import ExpirationChain, OptionQuote


class ExpirationChainAnalyzer:

    def get_calls(self, chain: ExpirationChain) -> list[OptionQuote]:
        return sorted(
            (
                quote
                for quote in chain.quotes
                if quote.option_type == "call"
            ),
            key=lambda quote: quote.strike,
        )

    def get_puts(self, chain: ExpirationChain) -> list[OptionQuote]:
        return sorted(
            (
                quote
                for quote in chain.quotes
                if quote.option_type == "put"
            ),
            key=lambda quote: quote.strike,
        )

    def find_nearest_strike(
        self,
        chain: ExpirationChain,
        target_strike: float,
        option_type: str,
    ) -> OptionQuote | None:
        quotes = (
            self.get_calls(chain)
            if option_type == "call"
            else self.get_puts(chain)
        )

        if not quotes:
            return None

        return min(
            quotes,
            key=lambda quote: abs(quote.strike - target_strike),
        )

    def find_call_above(
        self,
        chain: ExpirationChain,
        strike: float,
    ) -> OptionQuote | None:
        for quote in self.get_calls(chain):
            if quote.strike >= strike:
                return quote

        return None

    def find_put_below(
        self,
        chain: ExpirationChain,
        strike: float,
    ) -> OptionQuote | None:
        for quote in reversed(self.get_puts(chain)):
            if quote.strike <= strike:
                return quote

        return None

    def find_atm_straddle(
        self,
        chain: ExpirationChain,
        underlying_price: float,
    ) -> tuple[OptionQuote, OptionQuote] | None:
        call = self.find_nearest_strike(
            chain,
            underlying_price,
            "call",
        )

        put = self.find_nearest_strike(
            chain,
            underlying_price,
            "put",
        )

        if call is None or put is None:
            return None

        return call, put