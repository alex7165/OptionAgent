from app.analysis.earnings_crush_candidate import EarningsCrushCandidate


class EarningsCrushRules:

    MAX_BID_ASK_SPREAD = 0.10

    def evaluate(
        self,
        candidate: EarningsCrushCandidate,
    ) -> EarningsCrushCandidate:
        if candidate.snapshot is None:
            candidate.failed_rules.append("missing_market_snapshot")
        else:
            candidate.passed_rules.append("has_market_snapshot")

        if candidate.option_data is None:
            candidate.failed_rules.append("missing_option_data")
            return candidate

        candidate.passed_rules.append("has_option_data")

        spread = candidate.option_data.bid_ask_spread_percent

        if spread is None:
            candidate.failed_rules.append("missing_bid_ask_spread")
        elif spread <= self.MAX_BID_ASK_SPREAD:
            candidate.passed_rules.append("bid_ask_spread_ok")
        else:
            candidate.failed_rules.append("bid_ask_spread_too_wide")

        return candidate