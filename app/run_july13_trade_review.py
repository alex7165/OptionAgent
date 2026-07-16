from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from app.analysis.entry_decision_snapshot import EntryDecisionSnapshotRepository
from app.analysis.trade_snapshot_review import (
    TradeSnapshot,
    TradeSnapshotReviewRunner,
)
from app.marketdata.yahoo_price_history_provider import YahooPriceHistoryProvider


DEFAULT_SNAPSHOT_PATH = Path("app/data/decisions/2026-07-13.json")


def run(end_date: date, snapshot_path: Path = DEFAULT_SNAPSHOT_PATH) -> int:
    stored = EntryDecisionSnapshotRepository().load(snapshot_path)
    snapshots = tuple(TradeSnapshot.from_entry_decision(item) for item in stored)
    runner = TradeSnapshotReviewRunner(YahooPriceHistoryProvider())
    reviews = runner.run(snapshots, end_date=end_date)

    print(f"Snapshot-Datei: {snapshot_path}")
    print(f"Kursverlauf bis: {end_date.isoformat()}")
    print("Strategie und Strikes stammen ausschließlich aus dem gespeicherten Entry-Snapshot.")

    reviewed_symbols = {review.snapshot.symbol for review in reviews}
    for snapshot in snapshots:
        if snapshot.symbol not in reviewed_symbols:
            print(f"{snapshot.symbol:<5} KEINE KURSDATEN")

    for review in reviews:
        snapshot = review.snapshot
        print("\n" + "=" * 72)
        print(
            f"{snapshot.symbol} | {snapshot.strategy.value} | "
            f"Referenz {snapshot.reference_price:.2f} | "
            f"Put {snapshot.short_put_strike:g} | Call {snapshot.short_call_strike:g} | "
            f"Verfall {snapshot.expiration}"
        )
        for outcome in review.outcomes:
            status = "INNERHALB" if outcome.finished_inside_short_strikes else "VERLETZT"
            touches = []
            if outcome.put_touched:
                touches.append("Put-Touch")
            if outcome.call_touched:
                touches.append("Call-Touch")
            touch_text = ", ".join(touches) if touches else "kein Touch"
            print(
                f"Tag {outcome.exit_trading_day_index}: {outcome.exit_date} "
                f"Close {outcome.exit_close:.2f} | {status} | {touch_text} | "
                f"MAE {outcome.max_adverse_move_percent:.2f}% | "
                f"MFE {outcome.max_favorable_move_percent:.2f}%"
            )

        repair = review.repair
        if not repair.triggered:
            print("Underlying-Reparatursimulation: nicht ausgelöst")
        else:
            held = not bool(repair.repaired_strike_finished_outside)
            print(
                f"Underlying-Reparatursimulation: Tag {repair.trigger_day_index} "
                f"({repair.trigger_date}), Seite {repair.threatened_side.value}, "
                f"Strike {repair.original_strike:.2f} → {repair.repaired_strike:.2f}, "
                f"am Ende {'gehalten' if held else 'verletzt'}"
            )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end-date", type=date.fromisoformat, default=date(2026, 7, 15))
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    args = parser.parse_args()
    raise SystemExit(run(args.end_date, args.snapshot))


if __name__ == "__main__":
    main()
