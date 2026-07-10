from app.analysis.expected_move import ExpectedMove
from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.analysis.strategy import Strategy
from app.analysis.strike_selection import StrikeSelection
from app.analysis.wing_selector import WingSelector
from app.marketdata.models import ExpirationChain


class StrikeSelector:

    def __init__(self, wing_width: float | None = None):
        self.chain_analyzer = ExpirationChainAnalyzer()
        self.wing_selector = WingSelector()
        self.wing_width = wing_width

    def select_by_percent(
        self,
        chain: ExpirationChain,
        underlying_price: float,
        percent: float,
        strategy: Strategy = Strategy.IRON_CONDOR,
    ) -> StrikeSelection:
        put_target = underlying_price * (1 - percent)
        call_target = underlying_price * (1 + percent)

        return self._select_by_targets(
            chain=chain,
            put_target=put_target,
            call_target=call_target,
            underlying_price=underlying_price,
            strategy=strategy,
        )

    def select_by_expected_move(
        self,
        chain: ExpirationChain,
        expected_move: ExpectedMove,
        strategy: Strategy = Strategy.IRON_CONDOR,
    ) -> StrikeSelection:
        underlying_price = (
            expected_move.down_price + expected_move.up_price
        ) / 2

        return self._select_by_targets(
            chain=chain,
            put_target=expected_move.down_price,
            call_target=expected_move.up_price,
            underlying_price=underlying_price,
            strategy=strategy,
        )

    def _select_by_targets(
        self,
        chain: ExpirationChain,
        put_target: float,
        call_target: float,
        underlying_price: float,
        strategy: Strategy,
    ) -> StrikeSelection:
        put = self.chain_analyzer.find_put_below(
            chain,
            put_target,
        )

        call = self.chain_analyzer.find_call_above(
            chain,
            call_target,
        )

        long_put = None
        long_call = None

        if strategy is Strategy.IRON_CONDOR:
            width = self.wing_width

            if width is None:
                width = self.wing_selector.width_for_price(
                    underlying_price
                )

            if put is not None:
                long_put = self.wing_selector.select_long_put(
                    chain,
                    put,
                    width,
                )

            if call is not None:
                long_call = self.wing_selector.select_long_call(
                    chain,
                    call,
                    width,
                )

        return StrikeSelection(
            put=put,
            call=call,
            put_target=put_target,
            call_target=call_target,
            long_put=long_put,
            long_call=long_call,
            strategy=strategy,
        )