from app.analysis.strategy import Strategy
from app.analysis.strategy_selector import StrategySelector


def test_selects_iron_condor_for_defined_risk():
    selector = StrategySelector()

    strategy = selector.select(defined_risk=True)

    assert strategy is Strategy.IRON_CONDOR


def test_selects_short_strangle_for_undefined_risk():
    selector = StrategySelector()

    strategy = selector.select(defined_risk=False)

    assert strategy is Strategy.SHORT_STRANGLE