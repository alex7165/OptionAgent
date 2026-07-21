from datetime import date
from types import SimpleNamespace

from app.analysis.strategy import Strategy
from app.analysis.strategy_decision import (
    StrategyDecisionPolicy,
    StrategyDecisionService,
)
from app.analysis.strike_selection import StrikeSelection
from app.marketdata.models import OptionQuote


def quote(strike: float, option_type: str, bid: float, ask: float) -> OptionQuote:
    return OptionQuote(
        symbol="NVDA",
        expiration=date(2026, 7, 24),
        strike=strike,
        option_type=option_type,
        bid=bid,
        ask=ask,
    )


def selection(strategy: Strategy) -> StrikeSelection:
    return StrikeSelection(
        put=quote(180, "put", 4.0, 4.2),
        call=quote(220, "call", 4.0, 4.2),
        put_target=180,
        call_target=220,
        long_put=(quote(170, "put", 1.0, 1.2) if strategy is Strategy.IRON_CONDOR else None),
        long_call=(quote(230, "call", 1.0, 1.2) if strategy is Strategy.IRON_CONDOR else None),
        strategy=strategy,
    )


def historical(maximum_move: float):
    outcome = SimpleNamespace(
        highest_percent_until_exit=maximum_move,
        lowest_percent_until_exit=-5.0,
    )
    return SimpleNamespace(outcomes=(outcome,))


def test_defaults_to_short_strangle_without_history() -> None:
    service = StrategyDecisionService()
    assert service.select(
        selection(Strategy.SHORT_STRANGLE),
        selection(Strategy.IRON_CONDOR),
        None,
    ) is Strategy.SHORT_STRANGLE


def test_keeps_short_strangle_when_history_has_no_extreme_move() -> None:
    service = StrategyDecisionService()
    assert service.select(
        selection(Strategy.SHORT_STRANGLE),
        selection(Strategy.IRON_CONDOR),
        historical(29.9),
    ) is Strategy.SHORT_STRANGLE


def test_uses_iron_condor_for_extreme_history_and_attractive_credit() -> None:
    service = StrategyDecisionService(
        StrategyDecisionPolicy(
            extreme_move_threshold_percent=30.0,
            minimum_iron_condor_credit_retention=0.50,
        )
    )
    assert service.select(
        selection(Strategy.SHORT_STRANGLE),
        selection(Strategy.IRON_CONDOR),
        historical(35.0),
    ) is Strategy.IRON_CONDOR


def test_keeps_strangle_when_wings_destroy_too_much_credit() -> None:
    condor = selection(Strategy.IRON_CONDOR)
    condor.long_put.ask = 2.5
    condor.long_call.ask = 2.5
    service = StrategyDecisionService()
    assert service.select(
        selection(Strategy.SHORT_STRANGLE),
        condor,
        historical(35.0),
    ) is Strategy.SHORT_STRANGLE
