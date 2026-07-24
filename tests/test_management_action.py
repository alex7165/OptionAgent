from app.analysis.management_action import ManagementAction, ThreatenedSide


def test_call_side_actions_include_stock_hedge_but_not_assignment() -> None:
    actions = ManagementAction.allowed_for_side(ThreatenedSide.CALL)

    assert ManagementAction.BUY_STOCK_HEDGE in actions
    assert ManagementAction.ASSIGN_AND_SELL_COVERED_CALL not in actions


def test_put_side_actions_include_assignment_but_not_stock_sale() -> None:
    actions = ManagementAction.allowed_for_side(ThreatenedSide.PUT)

    assert ManagementAction.HOLD_FOR_ASSIGNMENT in actions
    assert ManagementAction.ASSIGN_AND_SELL_COVERED_CALL in actions
    assert ManagementAction.BUY_STOCK_HEDGE not in actions
