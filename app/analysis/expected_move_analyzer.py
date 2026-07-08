from app.analysis.expected_move import ExpectedMove
from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.marketdata.models import ExpirationChain

class ExpectedMoveAnalyzer:

    def from_percent(
        self,
        underlying_price: float,
        expected_move_percent: float,
    ) -> ExpectedMove:
        move = underlying_price * expected_move_percent

        return ExpectedMove(
            percent=expected_move_percent,
            up_price=underlying_price + move,
            down_price=underlying_price - move,
        )

    def __init__(self):
        self.chain_analyzer = ExpirationChainAnalyzer()

    def from_atm_straddle(
        self,
        chain: ExpirationChain,
        underlying_price: float,
    ) -> ExpectedMove | None:
        straddle = self.chain_analyzer.find_atm_straddle(
            chain,
            underlying_price,
        )

        if straddle is None:
            return None

        call, put = straddle

        if call.mid is None or put.mid is None:
            return None

        move = call.mid + put.mid

        return ExpectedMove(
            percent=move / underlying_price,
            up_price=underlying_price + move,
            down_price=underlying_price - move,
        )