from app.analysis.expected_move import ExpectedMove
from app.analysis.expiration_chain_analyzer import ExpirationChainAnalyzer
from app.marketdata.models import ExpirationChain, OptionQuote


class ExpectedMoveAnalyzer:

    def __init__(self):
        self.chain_analyzer = ExpirationChainAnalyzer()

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

    def from_atm_straddle(
        self,
        chain: ExpirationChain,
        underlying_price: float,
    ) -> ExpectedMove | None:
        straddles = self._valid_straddles(chain)

        if not straddles:
            return None

        call, put = min(
            straddles,
            key=lambda pair: abs(pair[0].strike - underlying_price),
        )

        move = call.mid + put.mid

        return ExpectedMove(
            percent=move / underlying_price,
            up_price=underlying_price + move,
            down_price=underlying_price - move,
        )

    def _valid_straddles(
        self,
        chain: ExpirationChain,
    ) -> list[tuple[OptionQuote, OptionQuote]]:
        calls = {
            quote.strike: quote
            for quote in self.chain_analyzer.get_calls(chain)
            if quote.mid is not None
        }

        puts = {
            quote.strike: quote
            for quote in self.chain_analyzer.get_puts(chain)
            if quote.mid is not None
        }

        return [
            (calls[strike], puts[strike])
            for strike in calls.keys() & puts.keys()
        ]