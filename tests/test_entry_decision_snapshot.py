from datetime import date

from app.analysis.entry_decision_snapshot import (
    EntryDecisionSnapshot,
    EntryDecisionSnapshotRepository,
)
from app.analysis.strategy import Strategy


def test_snapshot_round_trip_preserves_short_strangle(tmp_path):
    snapshot = EntryDecisionSnapshot(
        symbol="GS",
        decision_date=date(2026, 7, 13),
        report_date=date(2026, 7, 14),
        expiration=date(2026, 7, 17),
        strategy=Strategy.SHORT_STRANGLE,
        reference_price=1042.45,
        short_put_strike=990,
        short_call_strike=1095,
    )
    path = tmp_path / "decisions.json"

    repository = EntryDecisionSnapshotRepository()
    repository.save((snapshot,), path)

    assert repository.load(path) == (snapshot,)
