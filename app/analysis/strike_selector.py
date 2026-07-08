from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import ExpirationChain


class StrikeSelector:

    def __init__(self):
        self.chain_analyzer = ExpirationChainAnalyzer()

    def select_by_percent(
        self,
        chain: ExpirationChain,
        underlying_price: float,
        percent: float,
    ) -> StrikeSelection:
        put_target = underlying_price * (1 - percent)
        call_target = underlying_price * (1 + percent)

        put = self.chain_analyzer.find_put_below(
            chain,
            put_target,
        )

        call = self.chain_analyzer.find_call_above(
            chain,
            call_target,
        )

        return StrikeSelection(
            put=put,
            call=call,
            put_target=put_target,
            call_target=call_target,
        )