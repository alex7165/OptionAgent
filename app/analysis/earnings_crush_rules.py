from app.analysis.earnings_crush_candidate import EarningsCrushCandidate


class EarningsCrushRules:

    def evaluate(self, candidate: EarningsCrushCandidate) -> EarningsCrushCandidate:
        if candidate.snapshot is None:
            candidate.failed_rules.append("missing_market_snapshot")
        else:
            candidate.passed_rules.append("has_market_snapshot")

        return candidate