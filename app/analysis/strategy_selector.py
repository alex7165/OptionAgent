from app.analysis.strategy import Strategy


class StrategySelector:

    def select(
        self,
        defined_risk: bool,
    ) -> Strategy:
        if defined_risk:
            return Strategy.IRON_CONDOR

        return Strategy.SHORT_STRANGLE