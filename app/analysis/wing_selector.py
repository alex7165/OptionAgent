from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.marketdata.models import ExpirationChain, OptionQuote


class WingSelector:

    def __init__(self):
        self.chain_analyzer = ExpirationChainAnalyzer()

    def select_long_put(
        self,
        chain: ExpirationChain,
        short_put: OptionQuote,
        width: float,
    ) -> OptionQuote | None:
        target_strike = short_put.strike - width

        return self.chain_analyzer.find_nearest_strike(
            chain,
            target_strike,
            "put",
        )

    def select_long_call(
        self,
        chain: ExpirationChain,
        short_call: OptionQuote,
        width: float,
    ) -> OptionQuote | None:
        target_strike = short_call.strike + width

        return self.chain_analyzer.find_nearest_strike(
            chain,
            target_strike,
            "call",
        )