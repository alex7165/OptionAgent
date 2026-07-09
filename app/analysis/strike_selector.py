from app.analysis.expected_move import ExpectedMove
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

        return self._select_by_targets(
            chain,
            put_target,
            call_target,
        )

    def select_by_expected_move(
        self,
        chain: ExpirationChain,
        expected_move: ExpectedMove,
    ) -> StrikeSelection:
        return self._select_by_targets(
            chain,
            expected_move.down_price,
            expected_move.up_price,
        )

    def _select_by_targets(
        self,
        chain: ExpirationChain,
        put_target: float,
        call_target: float,
    ) -> StrikeSelection:
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