from app.analysis.expected_move_analyzer import ExpectedMoveAnalyzer


def test_expected_move_from_percent():
    analyzer = ExpectedMoveAnalyzer()

    move = analyzer.from_percent(
        underlying_price=200,
        expected_move_percent=0.10,
    )

    assert move.percent == 0.10
    assert move.up_price == 220
    assert move.down_price == 180