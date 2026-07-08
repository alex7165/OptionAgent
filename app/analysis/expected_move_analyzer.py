from app.analysis.expected_move import ExpectedMove


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