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

        if candidate.strike_selection is None:
            candidate.failed_rules.append("missing_strike_selection")
        elif candidate.strike_selection.is_complete:
            candidate.passed_rules.append("has_strike_selection")
        else:
            candidate.failed_rules.append("incomplete_strike_selection")

        if candidate.option_data is None:
            candidate.failed_rules.append("missing_option_data")
            return candidate

        candidate.passed_rules.append("has_option_data")

        if candidate.option_data.call is None:
            candidate.failed_rules.append("missing_call_option")
            return candidate

        if candidate.option_data.put is None:
            candidate.failed_rules.append("missing_put_option")
            return candidate

        call_spread = candidate.option_data.call.bid_ask_spread_percent
        put_spread = candidate.option_data.put.bid_ask_spread_percent

        if call_spread is None or put_spread is None:
            candidate.failed_rules.append("missing_bid_ask_spread")
        elif (
            call_spread <= self.MAX_BID_ASK_SPREAD
            and put_spread <= self.MAX_BID_ASK_SPREAD
            ):
            candidate.passed_rules.append("bid_ask_spread_ok")
        else:
            candidate.failed_rules.append("bid_ask_spread_too_wide")