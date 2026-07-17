from datetime import date

import pytest

from app.analysis.management_outcome import ManagementOutcome
from app.analysis.management_outcome_collection import ManagementOutcomeCollection


def _outcome(strategy_name: str) -> ManagementOutcome:
    return ManagementOutcome(
        strategy_name=strategy_name,
        entry_day=1,
        exit_day=4,
        exit_reason="friday_close",
        max_adverse_move=-3.2,
        max_favorable_move=5.4,
        finished_inside_strikes=True,
        all_time_high_after_entry=False,
        final_move_percent=1.8,
    )


def test_management_outcome_collection_stores_case_and_outcomes() -> None:
    close_day_one = _outcome("close_day_one")
    hold_friday = _outcome("hold_friday")

    collection = ManagementOutcomeCollection(
        symbol=" gs ",
        earnings_date=date(2026, 7, 14),
        reference_price=1042.45,
        outcomes=(close_day_one, hold_friday),
    )

    assert collection.symbol == "GS"
    assert collection.earnings_date == date(2026, 7, 14)
    assert collection.reference_price == 1042.45
    assert collection.outcomes == (close_day_one, hold_friday)


def test_management_outcome_collection_validates_required_case_data() -> None:
    with pytest.raises(ValueError, match="symbol must not be empty"):
        ManagementOutcomeCollection(
            symbol="   ",
            earnings_date=date(2026, 7, 14),
            reference_price=1042.45,
            outcomes=(),
        )

    with pytest.raises(
        ValueError,
        match="reference_price must be greater than zero",
    ):
        ManagementOutcomeCollection(
            symbol="GS",
            earnings_date=date(2026, 7, 14),
            reference_price=0,
            outcomes=(),
        )
