from datetime import date

from app.analysis.earnings_crush_candidate import EarningsCrushCandidate
from app.marketdata.models import EarningsEvent


def test_earnings_crush_candidate_can_be_created():
    event = EarningsEvent(
        symbol="NVDA",
        report_date=date(2026, 8, 26),
        timing="after market close",
        source="test",
    )

    candidate = EarningsCrushCandidate(earnings_event=event)

    assert candidate.earnings_event.symbol == "NVDA"
    assert candidate.option_data is None
    assert candidate.passed_rules == []
    assert candidate.failed_rules == []